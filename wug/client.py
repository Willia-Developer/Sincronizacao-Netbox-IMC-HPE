"""Coletor WUG: GET de inventário, POST apenas para obter token, logout local."""
import re
import requests
from .models import Device, Interface, MISSING, field, vlan_state
from .policy import PolicyError, RestrictedSession, safe_origin
from .profile import validate_profile

class WUGClient:
    def __init__(self, base_url, profile, *, token='', username='', password='', verify_ssl=True,
                 request_timeout=30, max_pages=1000, max_records=100000, proxies=None):
        validate_profile(profile)
        if verify_ssl is False:
            raise PolicyError('Validação TLS obrigatória')
        self.base_url = safe_origin(base_url) + '/api/v1/'
        self.profile = profile
        self.username, self.password = username, password
        self.timeout, self.max_pages, self.max_records = request_timeout, max_pages, max_records
        paths = ['product', re.escape(profile['devices']['endpoint'])]
        endpoint = profile['interfaces'].get('endpoint')
        if endpoint:
            paths.append(re.escape(endpoint).replace(re.escape('{device_id}'), r'[0-9]+'))
        self.session = RestrictedSession(self.base_url, read_paths=paths)
        self.session.verify = verify_ssl
        self.session.headers['Accept'] = 'application/json'
        if token:
            self.session.headers['Authorization'] = 'Bearer ' + token
        if proxies:
            self.session.proxies.update(proxies)
        self.evidence = []

    def _request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint
        self.session.check(method, url)
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException:
            raise PolicyError('Falha de comunicação WUG; nenhuma escrita de inventário autorizada') from None
        if not 200 <= response.status_code < 300:
            raise PolicyError(f'WUG HTTP {response.status_code}; revise autenticação/permissões')
        try:
            data = response.json()
        except ValueError:
            raise PolicyError('Resposta WUG não é JSON válido') from None
        if not isinstance(data, (dict, list)):
            raise PolicyError('Resposta WUG inválida')
        return data

    def login(self):
        if 'Authorization' not in self.session.headers:
            if not self.username or not self.password:
                raise PolicyError('Informe WUG_TOKEN ou WUG_USERNAME/WUG_PASSWORD')
            data = self._request('POST', 'token', data={
                'grant_type': 'password', 'username': self.username, 'password': self.password})
            token = data.get('access_token') if isinstance(data, dict) else None
            if not isinstance(token, str) or not token or any(c.isspace() for c in token):
                raise PolicyError('Token WUG inválido')
            self.session.headers['Authorization'] = 'Bearer ' + token
        return self._request('GET', 'product')

    def records(self, cfg, device_id=None):
        endpoint = cfg['endpoint']
        if device_id is not None:
            if not str(device_id).isdecimal():
                raise PolicyError('ID WUG inválido')
            endpoint = endpoint.replace('{device_id}', str(device_id))
        pg = cfg['pagination']
        rows, ids, cursors = [], set(), set()
        params = {}
        if pg['mode'] == 'offset':
            params = {pg['parameter']: 0, pg['limit_parameter']: 200}
        expected_total = None
        for page_number in range(1, self.max_pages + 1):
            data = self._request('GET', endpoint, params=params)
            batch = field(data, cfg['items_path'])
            if not isinstance(batch, list) or any(not isinstance(r, dict) for r in batch):
                raise PolicyError('Coleção WUG incompleta ou mapeamento incompatível')
            for row in batch:
                identifier = field(row, cfg['id_field'])
                if isinstance(identifier, bool) or not isinstance(identifier, (str, int)) or not str(identifier).isdecimal():
                    raise PolicyError('ID de registro WUG ausente/inválido')
                identifier = str(int(identifier))
                if identifier in ids:
                    raise PolicyError('Registro WUG duplicado; coleta rejeitada')
                ids.add(identifier)
                rows.append(row)
            if len(rows) > self.max_records:
                raise PolicyError('Limite de registros excedido; coleta rejeitada')
            if pg['mode'] == 'cursor':
                container = field(data, pg['container_path'])
                if not isinstance(container, dict):
                    raise PolicyError('Metadados de paginação WUG ausentes')
                cursor = container.get(pg['next_field'])
                done = cursor is None or cursor == ''
                if not done:
                    if not isinstance(cursor, str) or cursor in cursors or not batch:
                        raise PolicyError('Paginação WUG repetida/inválida')
                    cursors.add(cursor)
                    params = {pg['parameter']: cursor}
            elif pg['mode'] == 'offset':
                total = field(data, pg['total_path'])
                if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                    raise PolicyError('Total WUG inválido')
                if expected_total is not None and total != expected_total:
                    raise PolicyError('Inventário mudou durante paginação')
                expected_total = total
                if len(rows) > total or (not batch and len(rows) < total):
                    raise PolicyError('Contagem WUG incompleta')
                done = len(rows) == total
                params[pg['parameter']] = len(rows)
            else:
                if field(data, pg['complete_path']) is not True:
                    raise PolicyError('Completude WUG não confirmada')
                done = True
            if done:
                self.evidence.append({'endpoint': endpoint, 'pages': page_number, 'records': len(rows), 'complete': True})
                return rows
        raise PolicyError('Limite de páginas excedido; coleta rejeitada')

    def iter_devices(self):
        cfg = self.profile['devices']
        for row in self.records(cfg):
            identifier = str(int(field(row, cfg['id_field'])))
            name = self.profile.get('device_map', {}).get(identifier, field(row, cfg['name_field']))
            if not isinstance(name, str) or not name.strip():
                raise PolicyError('Nome WUG ausente; configure mapeamento explícito')
            yield Device(identifier, name)

    def iter_interfaces(self, device_id):
        validate_profile(self.profile, interfaces=True)
        cfg = self.profile['interfaces']
        normalized = []
        for row in self.records(cfg, device_id):
            identifier = str(int(field(row, cfg['id_field'])))
            name = self.profile.get('interface_map', {}).get(f'{device_id}:{identifier}', field(row, cfg['name_field']))
            if not isinstance(name, str) or not name.strip():
                raise PolicyError('Nome de interface WUG ausente')
            value = field(row, cfg.get('description_field'))
            issues = []
            if value is None or value is MISSING or not isinstance(value, str):
                value = MISSING
                issues.append('Descrição ausente/null/inválida: preservar')
            elif not value.strip() and not self.profile['allow_description_clear']:
                value = MISSING
                issues.append('Limpeza de descrição não autorizada: preservar')
            else:
                value = value.strip()
            vlans = None
            vc = cfg['vlans']
            if vc['enabled']:
                try:
                    raw_mode = field(row, vc['mode_field'])
                    mode = vc['mode_map'].get(raw_mode) if isinstance(raw_mode, str) else None
                    vlans = vlan_state(mode, field(row, vc['untagged_field']), field(row, vc['tagged_field']))
                except PolicyError:
                    issues.append('VLAN inconclusiva: preservar associações')
            normalized.append(Interface(identifier, name, value, vlans, tuple(issues)))
        return iter(normalized)

    def logout(self):
        self.session.headers.pop('Authorization', None)
        self.session.cookies.clear()
        self.session.close()
