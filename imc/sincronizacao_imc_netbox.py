#!/usr/bin/env python3
"""Entrada do piloto. Nenhuma comunicação ou configuração no import."""
import argparse
import os
import sys

from imc_client import IMCClient
from netbox_client import NetBoxClient
from policy import PolicyError
from runtime import LOG, configuration, execution_lock, load_environment, setup_logging
from sync import Summary, execute, plan


def arguments(argv=None):
    parser = argparse.ArgumentParser(description='Piloto iMC → NetBox: descrição e VLAN')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dry-run', action='store_true')
    group.add_argument('--apply', action='store_true')
    parser.add_argument('--non-interactive', action='store_true')
    args = parser.parse_args(argv)
    if args.non_interactive and not args.apply:
        parser.error('--non-interactive exige --apply')
    return args


def main(argv=None):
    args = arguments(argv)
    formatter = setup_logging('apply' if args.apply else 'dry-run')
    imc = netbox = None
    summary = Summary()
    try:
        with execution_lock():
            load_environment()
            formatter.secrets.extend(os.environ.get(k, '') for k in
                                     ('IMC_PASSWORD', 'NETBOX_TOKEN', 'IMC_USERNAME') if os.environ.get(k))
            imc_settings, nb_settings = configuration()
            if args.apply and not args.non_interactive and not sys.stdin.isatty():
                raise PolicyError('Aplicação interativa exige terminal; use --apply --non-interactive explicitamente')
            imc, netbox = IMCClient(**imc_settings), NetBoxClient(**nb_settings)
            changes, summary = plan(imc, netbox)
            execute(netbox, changes, summary, apply=args.apply, non_interactive=args.non_interactive)
            return 1 if summary.errors else 0
    except PolicyError as exc:
        summary.errors += 1
        LOG.error('Execução interrompida: %s', exc)
        return 2
    except (OSError, ValueError):
        summary.errors += 1
        # Do not render arbitrary exception text containing configuration values.
        LOG.error('Execução interrompida: configuração, comunicação ou bloqueio inválido')
        return 2
    finally:
        LOG.info('Resumo final: %s', summary.report())
        if imc:
            imc.logout()
        if netbox:
            netbox.session.close()
        LOG.info('Fim')


if __name__ == '__main__':
    raise SystemExit(main())
