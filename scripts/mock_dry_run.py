#!/usr/bin/env python3
"""Demonstração offline com os clientes reais e transporte mockado."""
import json
from pathlib import Path
import sys
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'imc'))
from imc_client import IMCClient
from netbox_client import NetBoxClient
from runtime import LOG, setup_logging
from sync import plan, execute

def fake_request(session, method, url, **kwargs):
    if method != 'GET':
        raise AssertionError('Dry-run tentou mutação')
    if '/imcrs/' in url:
        endpoint = url.split('/imcrs/')[1]
        payload = {
            'plat/res/device': {'device': [{'id': 1, 'sysName': 'SW-LAB-01'}]},
            'plat/res/device/1/interface': {'interface': [
                {'ifName': 'Gi1', 'ifIndex': 1, 'ifAlias': 'Ponto laboratório'}]},
            'vlan/portvlan': {'vlan': [{'vlanId': 99}]},
            'vlan/access': {'accessIf': [{'ifIndex': 1, 'pvid': 99}]},
            'vlan/trunk': {'trunkIf': []},
            'vlan/hybrid': {'hybridIf': []},
        }[endpoint]
        key = next(iter(payload))
        rows = payload[key]
        start = kwargs.get('params', {}).get('start', 0)
        payload = {key: rows[start:start + 100]}
    else:
        endpoint = url.split('/api/')[1]
        payload = {'results': {
            'dcim/devices/': [{'id': 10, 'name': 'SW-LAB-01'}],
            'dcim/interfaces/': [{'id': 20, 'name': 'Gi1', 'device': {'id': 10},
                                 'description': '', 'mode': {'value': 'access'},
                                 'untagged_vlan': {'id': 10, 'vid': 1}, 'tagged_vlans': []}],
            'ipam/vlans/': [{'id': 990, 'vid': 99}],
        }[endpoint], 'next': None}
    response = Mock(status_code=200, text=json.dumps(payload))
    response.json.return_value = payload
    return response

def main():
    setup_logging('dry-run-mock')
    with patch('requests.sessions.Session.request', new=fake_request), \
         patch('requests.adapters.HTTPAdapter.send', side_effect=AssertionError('Rede proibida')):
        imc = IMCClient('imc.example.test', username='fixture', password='fixture')
        nb = NetBoxClient('https://netbox.example.test', 'fixture')
        changes, summary = plan(imc, nb)
        execute(nb, changes, summary)
        assert summary.planned == 1 and summary.applied == 0
        assert changes[0].payload == {'description': 'Ponto laboratório', 'untagged_vlan': 990}
        LOG.info('Resumo final: %s', summary.report())
        LOG.info('Fim; PATCH enviado=não; transporte mockado')
        print(json.dumps(summary.report(), ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
