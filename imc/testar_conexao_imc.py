#!/usr/bin/env python3
"""Teste manual somente GET; nenhuma credencial fixa ou consulta no import."""
from imc_client import IMCClient
from policy import PolicyError
from runtime import LOG, configuration, execution_lock, load_environment, setup_logging
import os

def main():
    formatter = setup_logging('connection-test')
    client = None
    try:
        with execution_lock():
            load_environment()
            formatter.secrets.extend(os.environ.get(k, '') for k in
                                     ('IMC_PASSWORD', 'NETBOX_TOKEN', 'IMC_USERNAME') if os.environ.get(k))
            imc_settings, _ = configuration(service='IMC')
            client = IMCClient(**imc_settings)
            client.login()
            LOG.info('Consulta GET iMC concluída')
            return 0
    except (PolicyError, OSError, ValueError):
        LOG.error('Falha na configuração ou consulta iMC; verifique conectividade e credenciais localmente')
        return 2
    finally:
        if client:
            client.logout()
        LOG.info('Fim')

if __name__ == '__main__':
    raise SystemExit(main())
