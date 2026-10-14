#!/usr/bin/env python3
"""Popula um NetBox de laboratório com sites, locais, switches, interfaces e VLANs.

Idempotente: reexecutar não duplica objetos. O token vem de NETBOX_TOKEN
(nunca gravar em arquivo). Uso:
    NETBOX_URL=http://host:8080 NETBOX_TOKEN='nbt_xxx.yyy' python3 scripts/popular_netbox_teste.py [--dry-run]
"""
import argparse
import os
import sys

import requests

NUM_SITES = 10
LOCAIS_POR_SITE = 2
NUM_SWITCHES = 100
NUM_VLANS = 10
VLAN_BASE = 101


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--interfaces', type=int, default=24, help='interfaces por switch')
    ap.add_argument('--dry-run', action='store_true', help='apenas testa a conexão')
    args = ap.parse_args()

    base = os.environ.get('NETBOX_URL', '').rstrip('/')
    token = os.environ.get('NETBOX_TOKEN', '')
    if not base or not token:
        sys.exit('Defina NETBOX_URL e NETBOX_TOKEN')
    s = requests.Session()
    s.headers.update({'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
    api = base + '/api/'

    def req(method, path, **kw):
        r = s.request(method, api + path, timeout=60, **kw)
        if not r.ok:
            sys.exit(f'{method} {path} -> {r.status_code}: {r.text[:400]}')
        return r.json()

    def get_or_create(path, lookup, data):
        res = req('GET', path, params={**lookup, 'limit': 1})
        if res['count']:
            return res['results'][0]
        return req('POST', path, json=data)

    status = req('GET', 'status/')
    print('NetBox', status.get('netbox-version'))
    if args.dry_run:
        return

    mfr = get_or_create('dcim/manufacturers/', {'slug': 'teste-lab'},
                        {'name': 'Teste Lab', 'slug': 'teste-lab'})
    dtype = get_or_create('dcim/device-types/', {'slug': 'switch-teste-24p'},
                          {'manufacturer': mfr['id'], 'model': 'Switch Teste 24p',
                           'slug': 'switch-teste-24p'})
    role = get_or_create('dcim/device-roles/', {'slug': 'switch-teste'},
                         {'name': 'Switch Teste', 'slug': 'switch-teste', 'color': '2196f3'})

    vlans = [get_or_create('ipam/vlans/', {'vid': VLAN_BASE + i, 'name': f'VLAN-TESTE-{VLAN_BASE + i}'},
                           {'vid': VLAN_BASE + i, 'name': f'VLAN-TESTE-{VLAN_BASE + i}'})
             for i in range(NUM_VLANS)]
    print(f'{len(vlans)} VLANs ok')

    locais = []
    for i in range(1, NUM_SITES + 1):
        site = get_or_create('dcim/sites/', {'slug': f'site-teste-{i:02d}'},
                             {'name': f'Site Teste {i:02d}', 'slug': f'site-teste-{i:02d}',
                              'status': 'active'})
        for j in range(1, LOCAIS_POR_SITE + 1):
            slug = f'local-teste-{i:02d}-{j:02d}'
            loc = get_or_create('dcim/locations/', {'slug': slug, 'site_id': site['id']},
                                {'name': f'Local Teste {i:02d}-{j:02d}', 'slug': slug,
                                 'site': site['id'], 'status': 'active'})
            locais.append((site, loc))
    print(f'{NUM_SITES} sites e {len(locais)} locais ok')

    for n in range(1, NUM_SWITCHES + 1):
        name = f'SW-TESTE-{n:03d}'
        site, loc = locais[(n - 1) % len(locais)]
        res = req('GET', 'dcim/devices/', params={'name': name, 'limit': 1})
        if res['count']:
            dev = res['results'][0]
        else:
            dev = req('POST', 'dcim/devices/', json={
                'name': name, 'device_type': dtype['id'], 'role': role['id'],
                'site': site['id'], 'location': loc['id'], 'status': 'active'})
        existentes = {i['name'] for i in req(
            'GET', 'dcim/interfaces/', params={'device_id': dev['id'], 'limit': 1000})['results']}
        novas = []
        for k in range(1, args.interfaces + 1):
            ifname = f'GigabitEthernet {k:02d}'
            if ifname in existentes:
                continue
            vlan = vlans[(n + k) % NUM_VLANS]
            novas.append({'device': dev['id'], 'name': ifname, 'type': '1000base-t',
                          'mode': 'access', 'untagged_vlan': vlan['id']})
        if novas:
            req('POST', 'dcim/interfaces/', json=novas)
        print(f'{name} ({site["name"]} / {loc["name"]}): +{len(novas)} interfaces')


if __name__ == '__main__':
    main()
