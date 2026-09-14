"""Etapas independentes; cada entrada tem seu próprio escopo e argumentos."""
import argparse
import os

from imc_client import IMCClient
from netbox_client import NetBoxClient, NotFound
from policy import PolicyError
from runtime import LOG, configuration, execution_lock, load_environment, setup_logging
from sync import first_present, source_id


def stage_arguments(stage, argv=None):
    parser = argparse.ArgumentParser(description={
        'devices': 'Listar dispositivos IMC, somente GET',
        'inspect': 'Ler interfaces e VLANs de um switch IMC, somente GET',
        'netbox': 'Testar leitura de dispositivos, interfaces e VLANs no NetBox',
        'compare': 'Comparar inventários por nome exato, sem consultar interfaces',
        'simulate': 'Simular atualização de interfaces de um único switch',
        'apply': 'Aplicar atualização controlada de interfaces de um único switch',
        'production': 'Comparar todos os dispositivos e atualizar somente interfaces existentes',
    }[stage])
    if stage in ('inspect', 'simulate', 'apply'):
        parser.add_argument('--device', required=True, help='Nome exato retornado pelo IMC')
    if stage == 'production':
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--dry-run', action='store_true')
        group.add_argument('--apply', action='store_true')
        parser.add_argument('--non-interactive', action='store_true')
    args = parser.parse_args(argv)
    if getattr(args, 'device', None) is not None and not args.device.strip():
        parser.error('--device exige nome não vazio')
    if getattr(args, 'non_interactive', False) and not args.apply:
        parser.error('--non-interactive exige --apply')
    return args


def inventory(imc):
    rows = list(imc.iter_devices())
    for row in rows:
        LOG.info('Dispositivo IMC id=%s nome=%s', first_present(row, ('id', 'deviceId'), ''),
                 first_present(row, ('sysName', 'label', 'name'), ''))
    LOG.info('Total de dispositivos IMC: %s', len(rows))
    return rows


def inspect_switch(imc, name):
    devices = list(imc.iter_devices())
    matches = [d for d in devices if first_present(d, ('sysName', 'label', 'name'), '') == name]
    if len(matches) != 1:
        raise PolicyError('Switch selecionado ausente ou ambíguo no IMC')
    device_id = source_id(first_present(matches[0], ('id', 'deviceId')))
    count, errors = 0, 0
    for iface in imc.iter_interfaces(device_id):
        count += 1
        LOG.info('Interface IMC nome=%s ifIndex=%s descrição=%r',
                 first_present(iface, ('ifName', 'name', 'ifDescription'), ''),
                 first_present(iface, ('ifIndex', 'ifindex'), ''),
                 first_present(iface, ('ifAlias', 'description', 'ifDesc'), '[ausente]'))
        try:
            state = imc.get_port_vlans(device_id, source_id(first_present(iface, ('ifIndex', 'ifindex'))))
            LOG.info('VLAN interpretada: %s', state)
        except PolicyError as exc:
            errors += 1
            LOG.warning('VLAN inconclusiva: %s', exc)
    LOG.info('Switch %s: interfaces=%s VLANs inconclusivas=%s', name, count, errors)
    return int(bool(errors))


def compare_inventory(imc, netbox):
    rows = list(imc.iter_devices())
    names = [first_present(r, ('sysName', 'label', 'name'), '') for r in rows]
    found, missing, errors = 0, 0, 0
    for name in names:
        try:
            if not isinstance(name, str) or not name.strip() or names.count(name) != 1:
                raise PolicyError('Nome IMC ausente/ambíguo')
            target = netbox.find_device(name)
            found += 1
            LOG.info('Correspondência nome=%s id NetBox=%s', name, target['id'])
        except NotFound:
            missing += 1
            LOG.info('Dispositivo ausente no NetBox; descartado: %s', name)
        except (PolicyError, KeyError) as exc:
            errors += 1
            LOG.warning('Dispositivo ignorado %s: %s', name, exc)
    LOG.info('Comparação: IMC=%s encontrados=%s ausentes=%s erros=%s',
             len(rows), found, missing, errors)
    return int(bool(errors))


def main(stage, argv=None):
    args = stage_arguments(stage, argv)
    if stage in ('simulate', 'apply', 'production'):
        from sincronizacao_imc_netbox import main as synchronize
        if stage == 'production':
            forwarded = ['--all-devices', '--apply' if args.apply else '--dry-run']
            if args.non_interactive:
                forwarded.append('--non-interactive')
        else:
            forwarded = ['--device', args.device, '--apply' if stage == 'apply' else '--dry-run']
        return synchronize(forwarded)

    formatter = setup_logging(stage)
    imc = netbox = None
    try:
        with execution_lock():
            load_environment()
            formatter.secrets.extend(os.environ.get(k, '') for k in
                                     ('IMC_PASSWORD', 'NETBOX_TOKEN', 'IMC_USERNAME') if os.environ.get(k))
            service = 'IMC' if stage in ('devices', 'inspect') else 'NETBOX' if stage == 'netbox' else None
            imc_settings, nb_settings = configuration(service=service)
            if imc_settings:
                imc = IMCClient(**imc_settings)
            if nb_settings:
                netbox = NetBoxClient(**nb_settings)
            if stage == 'devices':
                inventory(imc)
            elif stage == 'inspect':
                return inspect_switch(imc, args.device)
            elif stage == 'compare':
                return compare_inventory(imc, netbox)
            elif stage == 'netbox':
                for endpoint in ('dcim/devices/', 'dcim/interfaces/', 'ipam/vlans/'):
                    page = netbox._get(endpoint, params={'limit': 1})
                    if not isinstance(page, dict) or not isinstance(page.get('results'), list):
                        raise PolicyError('Coleção NetBox inválida')
                    LOG.info('GET NetBox confirmado: %s', endpoint)
            return 0
    except (PolicyError, OSError, ValueError, TypeError, KeyError) as exc:
        LOG.error('Etapa interrompida (%s): %s', type(exc).__name__, exc if isinstance(exc, PolicyError) else 'configuração/dados inválidos')
        return 2
    finally:
        if imc:
            imc.logout()
        if netbox:
            netbox.session.close()
        LOG.info('Fim da etapa %s', stage)
