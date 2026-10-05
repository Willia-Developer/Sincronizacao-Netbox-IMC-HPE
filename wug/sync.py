"""Comparação por campo e aplicação somente em interfaces existentes do NetBox."""
from collections import Counter
from dataclasses import dataclass, field
import logging
import time
from .models import MISSING, VlanState, vlan_state
from .netbox_client import NotFound, Ambiguous, PatchUncertain
from .policy import PolicyError, positive_id, validate_patch

LOG = logging.getLogger('pilot')

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
    if not isinstance(row['description'], str):
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
    return {'description': row['description'], 'mode': mode or None,
            'untagged_vlan': api_id(row['untagged_vlan']), 'tagged_vlans': sorted(set(tagged))}

def differences(interface, current, netbox):
    before, desired, issues = snapshot(current), {}, list(interface.issues)
    if isinstance(interface.description, str):
        desired['description'] = interface.description
    if interface.vlans is not None:
        try:
            state = interface.vlans
            if not isinstance(state, VlanState):
                raise PolicyError('Estado VLAN inválido')
            state = vlan_state(state.mode, state.untagged, list(state.tagged))
            vids = set(state.tagged)
            if state.untagged is not None:
                vids.add(state.untagged)
            resolved = {v: positive_id(netbox.find_vlan(v)['id']) for v in sorted(vids)}
            desired.update(mode=state.mode, untagged_vlan=resolved.get(state.untagged),
                           tagged_vlans=sorted(resolved[v] for v in state.tagged))
        except PolicyError as exc:
            issues.append('VLAN preservada: ' + str(exc))
    changes = {k: v for k, v in desired.items() if before[k] != v}
    if changes:
        validate_patch(changes)
    return before, changes, issues

@dataclass
class Summary:
    started: float = field(default_factory=time.monotonic, repr=False)
    devices: int = 0
    devices_found: int = 0
    devices_not_found: int = 0
    devices_filtered: int = 0
    interfaces: int = 0
    interfaces_not_found: int = 0
    synchronized: int = 0
    inconclusive: int = 0
    skipped: int = 0
    errors: int = 0
    planned: int = 0
    simulated: int = 0
    accepted: int = 0
    applied: int = 0
    uncertain: int = 0
    unconfirmed: int = 0
    cancelled: bool = False
    fields: set = field(default_factory=set)

    def report(self):
        return {**{k: v for k, v in self.__dict__.items() if k not in ('started', 'fields')},
                'fields': sorted(self.fields), 'duration_seconds': round(time.monotonic() - self.started, 3)}

@dataclass
class Change:
    device_id: int
    device: str
    interface: str
    interface_id: int
    before: dict
    payload: dict
    status: str = 'planned'
    error: str = ''

def plan(source, netbox, *, device_name=None):
    summary, changes, targets = Summary(), [], set()
    devices = list(source.iter_devices())  # falha de página impede qualquer execução
    summary.devices = len(devices)
    if not devices:
        raise PolicyError('Inventário WUG vazio: execução inconclusiva')
    names = Counter(d.name for d in devices)
    for device in devices:
        if device_name is not None and device.name != device_name:
            summary.devices_filtered += 1
            continue
        try:
            if names[device.name] != 1:
                raise Ambiguous('Nome WUG duplicado após mapeamento')
            nb_device = netbox.find_device(device.name)
            summary.devices_found += 1
            interfaces = list(source.iter_interfaces(device.source_id))
            summary.interfaces += len(interfaces)
            if not interfaces:
                raise PolicyError('Coleção de interfaces vazia; sem evidência de cobertura')
        except NotFound:
            summary.devices_not_found += 1
            summary.skipped += 1
            LOG.info('Dispositivo ausente no NetBox: %s', device.name)
            continue
        except PolicyError as exc:
            summary.errors += 1
            summary.skipped += 1
            LOG.warning('Dispositivo ignorado %s: %s', device.name, exc)
            continue
        counts = Counter(i.name for i in interfaces)
        for iface in interfaces:
            try:
                if counts[iface.name] != 1:
                    raise Ambiguous('Nome de interface duplicado após mapeamento')
                current = netbox.find_interface(nb_device['id'], iface.name)
                target = positive_id(current['id'])
                if target in targets:
                    raise PolicyError('Destino NetBox repetido')
                targets.add(target)
                before, payload, issues = differences(iface, current, netbox)
                if issues:
                    summary.inconclusive += 1
                    for issue in issues:
                        LOG.warning('%s / %s: %s', device.name, iface.name, issue)
                if not payload:
                    summary.synchronized += int(not issues)
                    continue
                summary.fields.update(payload)
                changes.append(Change(nb_device['id'], device.name, iface.name, target, before, payload))
                LOG.info('Proposta %s / %s anterior=%r proposto=%r', device.name, iface.name, before, payload)
            except PolicyError as exc:
                summary.interfaces_not_found += int(isinstance(exc, NotFound))
                summary.errors += 1
                summary.skipped += 1
                LOG.warning('Interface ignorada %s / %s: %s', device.name, iface.name, exc)
    summary.planned = len(changes)
    if device_name is not None and device_name not in names:
        summary.errors += 1
        LOG.error('Switch selecionado não encontrado no WUG')
    if summary.devices_found == 0:
        summary.errors += 1
        LOG.error('Nenhum dispositivo pareado: conferir escopo e nomes')
    return changes, summary

def execute(netbox, changes, summary, *, apply=False, non_interactive=False, confirm=input, checkpoint=None):
    if non_interactive and not apply:
        raise PolicyError('--non-interactive exige --apply')
    if not apply:
        summary.simulated = len(changes)
        return summary
    if not changes:
        return summary
    # Erros de identidade/coleta bloqueiam o lote; inconclusão por campo pode preservar VLAN e aplicar descrição.
    if summary.errors:
        raise PolicyError('Plano com erros: nenhum PATCH autorizado')
    if not non_interactive and confirm('Aplicar o plano apresentado? Digite SIM: ') != 'SIM':
        summary.cancelled = True
        return summary
    netbox.session.apply = True
    try:
        for change in changes:
            sent = False
            try:
                validate_patch(change.payload)
                current = netbox.find_interface(change.device_id, change.interface)
                if current['id'] != change.interface_id or snapshot(current) != change.before:
                    raise PolicyError('NetBox mudou após planejamento: gerar novo plano')
                # Persistir intenção ANTES do envio permite reconciliar um processo interrompido.
                change.status = 'sending'
                if checkpoint:
                    checkpoint()
                sent = True
                try:
                    netbox.patch_interface(change.interface_id, change.payload)
                    summary.accepted += 1
                except PatchUncertain:
                    summary.uncertain += 1
                final = netbox.find_interface(change.device_id, change.interface)
                if final['id'] != change.interface_id or any(snapshot(final)[k] != v for k, v in change.payload.items()):
                    raise PolicyError('Estado pós-PATCH não confirmado')
                summary.applied += 1
                change.status = 'confirmed'
            except PolicyError as exc:
                summary.errors += 1
                summary.unconfirmed += int(sent)
                change.status = 'unconfirmed' if sent else 'blocked'
                change.error = str(exc)
                LOG.error('Aplicação interrompida %s/%s: %s', change.device, change.interface, exc)
                break  # interrompe lote após primeira falha; não faz rollback automático
            finally:
                if checkpoint:
                    checkpoint()
    finally:
        netbox.session.apply = False
    return summary
