"""CLI única: python -m wug. Nenhuma rede no import."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from .client import WUGClient
from .netbox_client import NetBoxClient
from .policy import PolicyError
from .profile import load_profile, validate_profile
from .runtime import ROOT, LOG, setup_logging, load_environment, configuration, execution_lock, write_report
from .sync import plan, execute, Summary


def arguments(argv=None):
    p = argparse.ArgumentParser(description='WhatsUp Gold -> NetBox: fonte somente leitura')
    p.add_argument('command', choices=('check-wug', 'list-devices', 'inspect', 'check-netbox', 'sync'))
    p.add_argument('--profile', default=str(ROOT / 'config/wug.json'))
    scope = p.add_mutually_exclusive_group()
    scope.add_argument('--device')
    scope.add_argument('--all-devices', action='store_true')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    p.add_argument('--non-interactive', action='store_true')
    p.add_argument('--max-changes', type=int, default=100)
    args = p.parse_args(argv)
    if args.device is not None and not args.device.strip():
        p.error('--device não pode ser vazio')
    if args.command == 'inspect' and not args.device:
        p.error('inspect exige --device')
    if args.command == 'sync' and not (args.device or args.all_devices):
        p.error('sync exige --device ou --all-devices, inclusive em simulação')
    if args.apply and args.command != 'sync':
        p.error('--apply somente em sync')
    if args.non_interactive and not args.apply:
        p.error('--non-interactive exige --apply')
    if args.max_changes < 1:
        p.error('--max-changes deve ser positivo')
    return args


def main(argv=None):
    args = arguments(argv)
    formatter = setup_logging('apply' if args.apply else args.command)
    source = nb = None
    report_path = None
    summary, changes = Summary(), []
    profile_hash, evidence = None, []
    run_id = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    def checkpoint():
        write_report(report_path, {
            'schema_version': 1, 'run_id': run_id, 'started_at': started_at,
            'updated_at': datetime.now(timezone.utc).isoformat(), 'source': 'WhatsUp Gold',
            'target': 'NetBox', 'mode': 'apply' if args.apply else 'dry-run',
            'scope': args.device or 'all-devices', 'profile_sha256': profile_hash,
            'collection': source.evidence if source else evidence,
            'summary': summary.report(), 'changes': [asdict(c) for c in changes]})
    try:
        with execution_lock():
            load_environment()
            formatter.secrets.extend(os.environ.get(k, '') for k in ('WUG_USERNAME', 'WUG_PASSWORD', 'WUG_TOKEN', 'NETBOX_TOKEN'))
            service = 'NETBOX' if args.command == 'check-netbox' else 'WUG' if args.command != 'sync' else None
            wug_config, nb_config = configuration(service=service)
            if wug_config:
                profile = load_profile(args.profile)
                validate_profile(profile, interfaces=args.command in ('sync', 'inspect'), apply=args.apply)
                profile_hash = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
                source = WUGClient(profile=profile, **wug_config)
                source.login()
                LOG.info('Autenticação e GET product confirmados; validação de campos depende do perfil')
            if nb_config:
                nb = NetBoxClient(**nb_config)
            if args.command == 'check-netbox':
                for endpoint in ('dcim/devices/', 'dcim/interfaces/', 'ipam/vlans/'):
                    page = nb._get(endpoint, params={'limit': 1})
                    if not isinstance(page, dict) or not isinstance(page.get('results'), list):
                        raise PolicyError('Coleção NetBox inválida')
                LOG.info('GET NetBox confirmado; permissão PATCH não testada')
            elif args.command == 'list-devices':
                for d in source.iter_devices():
                    LOG.info('WUG ID=%s nome=%s', d.source_id, d.name)
            elif args.command == 'inspect':
                matches = [d for d in source.iter_devices() if d.name == args.device]
                if len(matches) != 1:
                    raise PolicyError('Switch ausente/ambíguo')
                interfaces = list(source.iter_interfaces(matches[0].source_id))
                if not interfaces:
                    raise PolicyError('Nenhuma interface retornada')
                for i in interfaces:
                    from .models import MISSING
                    LOG.info('Interface id=%s nome=%s descrição=%r VLAN=%s pendências=%s',
                             i.source_id, i.name, '[preservar]' if i.description is MISSING else i.description,
                             i.vlans, i.issues)
                return int(any(i.issues for i in interfaces))
            elif args.command == 'sync':
                report_path = ROOT / 'relatorios' / (run_id + '.json')
                changes, summary = plan(source, nb, device_name=args.device)
                checkpoint()  # falha ao persistir impede toda escrita
                LOG.info('Plano persistido: %s; resumo=%s', report_path, summary.report())
                if len(changes) > args.max_changes:
                    raise PolicyError('Limite de alterações excedido: revisar escopo e --max-changes')
                if args.apply and not args.non_interactive and not sys.stdin.isatty():
                    raise PolicyError('Aplicação exige terminal ou --non-interactive explícito')
                execute(nb, changes, summary, apply=args.apply, non_interactive=args.non_interactive, checkpoint=checkpoint)
                checkpoint()
                return 1 if summary.errors or summary.inconclusive or summary.cancelled else 0
            return 0
    except (PolicyError, OSError, ValueError, KeyError, TypeError) as exc:
        summary.errors += 1
        LOG.error('Execução interrompida: %s', str(exc) if isinstance(exc, PolicyError) else 'configuração/dados/arquivo inválido')
        if report_path:
            try:
                checkpoint()
            except OSError:
                LOG.error('Não foi possível persistir relatório final; reconciliar estados sending')
        return 2
    finally:
        if source:
            source.logout()
        if nb:
            nb.session.close()
        LOG.info('Fim: %s', summary.report())

if __name__ == '__main__':
    raise SystemExit(main())
