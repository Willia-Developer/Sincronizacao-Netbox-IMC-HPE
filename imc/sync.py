"""Planejamento completo antes da autorização; comparação mínima por interface."""
from dataclasses import dataclass, field
import logging
import time
from netbox_client import NotFound, Ambiguous, PatchUncertain

from imc_client import VlanState, vid
from policy import PolicyError, positive_id, validate_patch

LOG = logging.getLogger('pilot')
MISSING = object()


def first_present(row, names, default=MISSING):
    for name in names:
        if name in row:
            return row[name]
    return default


def description(value):
    if value is MISSING:
        return MISSING
    if value is None:
        return ''
    if not isinstance(value, str):
        return MISSING
    return value.strip()


def api_id(value):
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get('id')
    if isinstance(value, str) and value.isdecimal():
        value = int(value)
    return positive_id(value)


def snapshot(row):
    if any(k not in row for k in ('description', 'mode', 'untagged_vlan', 'tagged_vlans')):
        raise PolicyError('Interface NetBox incompleta')
    desc = description(row['description'])
    if desc is MISSING:
        raise PolicyError('Descrição NetBox inválida')
    mode = row['mode']
    if isinstance(mode, dict):
        mode = mode.get('value')
    if mode not in (None, '', 'access', 'tagged', 'tagged-all'):
        raise PolicyError('Modo NetBox inválido')
    if not isinstance(row['tagged_vlans'], list):
        raise PolicyError('Lista VLAN NetBox inválida')
    tagged = [api_id(v) for v in row['tagged_vlans']]
    if None in tagged:
        raise PolicyError('VLAN tagged NetBox inválida')
    return {'description': desc, 'mode': mode or None,
            'untagged_vlan': api_id(row['untagged_vlan']), 'tagged_vlans': sorted(set(tagged))}


def differences(source_description, vlans, current, netbox):
    before = snapshot(current)
    if not isinstance(vlans, VlanState) or vlans.mode not in ('access', 'tagged'):
        raise PolicyError('VLAN iMC inconclusiva')
    native = vid(vlans.untagged)
    tagged = {vid(v) for v in vlans.tagged}
    if native in tagged or (vlans.mode == 'access' and tagged):
        raise PolicyError('VLAN iMC inconsistente')
    try:
        resolved = {v: positive_id(netbox.find_vlan(v)['id']) for v in sorted(tagged | {native})}
    except NotFound as exc:
        raise MissingVlan(str(exc)) from exc
    LOG.info('VLANs confirmadas VID -> ID NetBox: %s', resolved)
    desired = {'mode': vlans.mode, 'untagged_vlan': resolved[native],
               'tagged_vlans': sorted({resolved[v] for v in tagged})}
    desc = description(source_description)
    if desc is not MISSING:
        desired['description'] = desc
    else:
        LOG.warning('Descrição ausente/inválida; preservar descrição NetBox')
    changes = {k: v for k, v in desired.items() if before[k] != v}
    if changes:
        validate_patch(changes)
    return before, changes


@dataclass
class Summary:
    started: float = field(default_factory=time.monotonic, repr=False)
    devices_not_found: int = 0
    devices_filtered: int = 0
    interfaces_found: int = 0
    interfaces_not_found: int = 0
    vlans_not_found: int = 0
    ambiguities: int = 0
    accepted: int = 0
    uncertain: int = 0
    unconfirmed: int = 0
    interfaces_simulated: int = 0
    devices_skipped: int = 0
    interfaces_skipped: int = 0
    devices: int = 0
    devices_found: int = 0
    interfaces: int = 0
    divergent: int = 0
    synchronized: int = 0
    skipped: int = 0
    errors: int = 0
    planned: int = 0
    applied: int = 0
    fields: set = field(default_factory=set)

    def report(self):
        return {**{k: v for k, v in self.__dict__.items() if k != 'started'},
                'fields': sorted(self.fields), 'duration_seconds': round(time.monotonic() - self.started, 3)}


class MissingVlan(NotFound):
    pass


@dataclass
class Change:
    device_id: int
    device: str
    interface: str
    interface_id: int
    before: dict
    payload: dict


def source_id(value):
    if isinstance(value, str) and value.isdecimal():
        value = int(value)
    return positive_id(value)


def plan(imc, netbox, *, device_name=None):
    summary, changes, targets = Summary(), [], set()
    devices = list(imc.iter_devices())
    summary.devices = len(devices)
    # Duplicate source names are unsafe too, even when NetBox is unique.
    names = [first_present(d, ('sysName', 'label', 'name'), '') for d in devices]
    for device, name in zip(devices, names):
        if device_name is not None and name != device_name:
            summary.devices_filtered += 1
            continue
        try:
            if not isinstance(name, str) or not name.strip() or names.count(name) != 1:
                raise Ambiguous('Nome iMC ausente/ambíguo; sem fallback por IP')
            device_id = source_id(first_present(device, ('id', 'deviceId')))
            nb_device = netbox.find_device(name)
            summary.devices_found += 1
            LOG.info('Dispositivo encontrado: %s', name)
            interfaces = list(imc.iter_interfaces(device_id))
            summary.interfaces += len(interfaces)
        except NotFound:
            summary.devices_not_found += 1
            summary.devices_skipped += 1
            summary.skipped += 1
            LOG.info('Dispositivo ausente no NetBox; descartado: %s', name)
            continue
        except (PolicyError, ValueError, TypeError, KeyError) as exc:
            summary.ambiguities += int(isinstance(exc, Ambiguous))
            summary.devices_skipped += 1
            summary.skipped += 1
            summary.errors += 1
            LOG.warning('Dispositivo ignorado %s: %s', name if isinstance(name, str) else '[inválido]', exc)
            continue
        interface_names = [first_present(i, ('ifName', 'name', 'ifDescription'), '') for i in interfaces]
        for iface, iface_name in zip(interfaces, interface_names):
            try:
                if not isinstance(iface_name, str) or not iface_name.strip() or interface_names.count(iface_name) != 1:
                    raise Ambiguous('Nome de interface ausente/ambíguo')
                LOG.info('Interface consultada: %s / %s', name, iface_name)
                current = netbox.find_interface(nb_device['id'], iface_name)
                summary.interfaces_found += 1
                target = positive_id(current['id'])
                if target in targets:
                    raise PolicyError('Interface NetBox repetida no planejamento')
                targets.add(target)
                index = source_id(first_present(iface, ('ifIndex', 'ifindex')))
                vlans = imc.get_port_vlans(device_id, index)
                before, payload = differences(first_present(iface, ('ifAlias', 'description', 'ifDesc')),
                                              vlans, current, netbox)
                if not payload:
                    summary.synchronized += 1
                    LOG.info('interface já sincronizada: %s / %s', name, iface_name)
                    continue
                summary.divergent += 1
                summary.fields.update(payload)
                change = Change(nb_device['id'], name, iface_name, target, before, payload)
                changes.append(change)
                for key, value in payload.items():
                    LOG.info('Proposta %s / %s campo=%s anterior=%r proposto=%r PATCH enviado=não',
                             name, iface_name, key, before[key], value)
                LOG.info('Payload validado %s / %s: %s', name, iface_name, payload)
            except (PolicyError, ValueError, TypeError, KeyError) as exc:
                summary.vlans_not_found += int(isinstance(exc, MissingVlan))
                summary.interfaces_not_found += int(isinstance(exc, NotFound) and not isinstance(exc, MissingVlan))
                summary.ambiguities += int(isinstance(exc, Ambiguous))
                summary.interfaces_skipped += 1
                summary.skipped += 1
                summary.errors += 1
                LOG.warning('Interface ignorada %s / %s: %s', name, iface_name, exc)
    summary.planned = len(changes)
    if device_name is not None and device_name not in names:
        summary.errors += 1
        LOG.error('Switch selecionado não encontrado no IMC: %s', device_name)
    LOG.info('Resumo prévio: %s', summary.report())
    return changes, summary


def execute(netbox, changes, summary, *, apply=False, non_interactive=False, confirm=input):
    if non_interactive and not apply:
        raise PolicyError('--non-interactive exige --apply')
    if not apply or not changes:
        if not apply:
            summary.interfaces_simulated = len(changes)
        return summary
    if not non_interactive and confirm('Aplicar os PATCHes apresentados? Digite SIM: ') != 'SIM':
        LOG.info('Aplicação cancelada; nenhum PATCH enviado')
        return summary
    # Authorization is set only after the complete plan and confirmation.
    netbox.session.apply = True
    try:
        for change in changes:
            sent = False
            try:
                validate_patch(change.payload)
                current = netbox.find_interface(change.device_id, change.interface)
                if current['id'] != change.interface_id or snapshot(current) != change.before:
                    raise PolicyError('NetBox mudou após planejamento; preservar e executar novo dry-run')
                try:
                    sent = True
                    netbox.patch_interface(change.interface_id, change.payload)
                    summary.accepted += 1
                except PatchUncertain:
                    summary.uncertain += 1
                    LOG.warning('PATCH incerto; conferindo estado por GET, sem reenvio')
                final = netbox.find_interface(change.device_id, change.interface)
                if final['id'] != change.interface_id or any(
                        snapshot(final)[k] != v for k, v in change.payload.items()):
                    raise PolicyError('Alteração não confirmada após PATCH; revisar novo dry-run')
                summary.applied += 1
                for key, value in change.payload.items():
                    LOG.info('PATCH sucesso %s / %s campo=%s anterior=%r proposto=%r',
                             change.device, change.interface, key, change.before[key], value)
            except (PolicyError, ValueError, TypeError, KeyError) as exc:
                summary.unconfirmed += int(sent)
                summary.errors += 1
                LOG.error('PATCH falhou/bloqueado %s / %s: %s', change.device, change.interface, exc)
    finally:
        netbox.session.apply = False
    return summary
