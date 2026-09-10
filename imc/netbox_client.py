"""NetBox: GET e PATCH mínimo de interfaces existentes."""
import requests
from policy import PolicyError, RestrictedSession, positive_id, validate_patch

NetBoxError = PolicyError

class NetBoxClient:
    def __init__(self, base_url, token, *, verify_ssl=True, request_timeout=30,
                 proxies=None, apply=False):
        self.base_url = base_url.rstrip('/') + '/api/'
        self.session = RestrictedSession(self.base_url, netbox=True, apply=apply)
        self.session.verify = verify_ssl
        self.session.headers['Authorization'] = ('Bearer ' if token.startswith('nbt_') else 'Token ') + token
        self.session.headers['Accept'] = 'application/json'
        if proxies:
            self.session.proxies.update(proxies)
        self.timeout = request_timeout

    def _request(self, method, endpoint, **kwargs):
        method = method.upper()
        url = self.base_url + endpoint
        self.session.check(method, url, kwargs.get('json'))
        if method == 'PATCH' and any(k in kwargs for k in ('data', 'files', 'params')):
            raise NetBoxError('PATCH exige apenas JSON validado')
        try:
            response = self.session.request(method, url, timeout=self.timeout,
                                            allow_redirects=False, **kwargs)
        except requests.Timeout:
            raise NetBoxError('Timeout NetBox') from None
        except requests.RequestException:
            raise NetBoxError('Falha de comunicação NetBox') from None
        if not 200 <= response.status_code < 300:
            raise NetBoxError(f'NetBox HTTP {response.status_code}')
        return response

    def _get(self, endpoint, *, params=None):
        try:
            return self._request('GET', endpoint, params=params).json()
        except ValueError:
            raise NetBoxError('Resposta NetBox inválida') from None

    def records(self, endpoint, **filters):
        offset, seen = 0, set()
        while True:
            page = self._get(endpoint, params={**filters, 'limit': 200, 'offset': offset})
            if not isinstance(page, dict) or not isinstance(page.get('results'), list):
                raise NetBoxError('Coleção NetBox inválida')
            rows = page['results']
            for row in rows:
                if not isinstance(row, dict) or row.get('id') in seen:
                    raise NetBoxError('Paginação NetBox inconsistente')
                positive_id(row.get('id'))
                seen.add(row['id'])
                yield row
            if not page.get('next'):
                break
            if not rows:
                raise NetBoxError('Paginação NetBox incompleta')
            offset += len(rows)

    def exact(self, endpoint, field, value, **filters):
        rows = [r for r in self.records(endpoint, **{field: value}, **filters) if r.get(field) == value]
        if len(rows) != 1:
            raise NetBoxError('correspondência ambígua' if rows else 'objeto não encontrado no NetBox')
        return rows[0]

    def find_device(self, name):
        if not isinstance(name, str) or not name.strip():
            raise NetBoxError('dispositivo sem nome')
        return self.exact('dcim/devices/', 'name', name)

    def find_interface(self, device_id, name):
        if not isinstance(name, str) or not name.strip():
            raise NetBoxError('interface sem nome')
        row = self.exact('dcim/interfaces/', 'name', name, device_id=positive_id(device_id))
        if not isinstance(row.get('device'), dict) or row['device'].get('id') != device_id:
            raise NetBoxError('Interface pertence a outro dispositivo')
        return row

    def find_vlan(self, vid):
        rows = [r for r in self.records('ipam/vlans/', vid=vid) if str(r.get('vid')) == str(vid)]
        if len(rows) != 1:
            raise NetBoxError(f'VLAN {vid}: ' + ('correspondência ambígua' if rows else 'VLAN não encontrada'))
        return rows[0]

    def patch_interface(self, interface_id, changes):
        validate_patch(changes)
        return self._request('PATCH', f'dcim/interfaces/{positive_id(interface_id)}/', json=changes)

    def _post(self, *args, **kwargs):
        # FORA DO ESCOPO DO PILOTO; referência em legacy/*.disabled.
        raise NetBoxError('FORA DO ESCOPO DO PILOTO: criação bloqueada')
