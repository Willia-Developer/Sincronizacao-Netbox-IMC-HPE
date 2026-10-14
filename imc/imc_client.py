"""iMC somente GET; VLAN incerta bloqueia a proposta da interface."""
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import requests
import logging
from requests.auth import HTTPDigestAuth
from policy import PolicyError, RestrictedSession

IMCError = PolicyError

@dataclass(frozen=True)
class VlanState:
    mode: str
    untagged: int
    tagged: tuple

def vid(value):
    if isinstance(value, dict):
        value = value.get('vid', value.get('vlanId'))
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise IMCError('VID inválido')
    try:
        result = int(value)
    except ValueError:
        raise IMCError('VID inválido') from None
    if not 1 <= result <= 4094:
        raise IMCError('VID fora do intervalo')
    return result

class IMCClient:
    def __init__(self, host, port='8443', username='', password='', *,
                 use_https=True, verify_ssl=True, request_timeout=30, proxies=None):
        self.base_url = f'{"https" if use_https else "http"}://{host}:{port}/imcrs/'
        self.session = RestrictedSession(self.base_url)
        self.session.verify = verify_ssl
        self.session.auth = HTTPDigestAuth(username, password)
        self.session.headers['Accept'] = 'application/xml, application/json'
        if proxies:
            self.session.proxies.update(proxies)
        self.timeout = request_timeout
        self._modes = {}

    def _request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint.lstrip('/')
        self.session.check(method.upper(), url)
        try:
            response = self.session.request(method.upper(), url, timeout=self.timeout,
                                            allow_redirects=False, **kwargs)
        except requests.Timeout:
            raise IMCError('Timeout iMC') from None
        except requests.RequestException:
            raise IMCError('Falha de comunicação iMC') from None
        if not 200 <= response.status_code < 300:
            raise IMCError(f'iMC HTTP {response.status_code}')
        return response

    @staticmethod
    def parse(response, element):
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            try:
                payload = response.json()
            except ValueError:
                raise IMCError('Erro de parsing iMC') from None
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict) and element in payload:
                rows = payload[element]
                if isinstance(rows, dict):
                    rows = [rows]
            elif isinstance(payload, dict) and 'list' in payload:
                rows = payload['list']
            else:
                raise IMCError('Formato iMC não reconhecido')
        else:
            tag = root.tag.split('}')[-1]
            if tag not in ('list', element):
                raise IMCError('Raiz XML iMC não reconhecida')
            elements = [root] if tag == element else list(root)
            rows = []
            for item in elements:
                if item.tag.split('}')[-1] != element:
                    raise IMCError('Coleção XML iMC não reconhecida')
                row = {}
                for child in item:
                    key = child.tag.split('}')[-1]
                    if key in row or list(child):
                        raise IMCError('Campo XML ambíguo')
                    row[key] = child.text or ''
                rows.append(row)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise IMCError('Coleção iMC inválida')
        return rows

    def records(self, endpoint, element, **filters):
        start, size, seen = 0, 100, set()
        while True:
            rows = self.parse(self._request('GET', endpoint,
                              params={**filters, 'start': start, 'size': size}), element)
            fingerprint = repr(rows)
            if rows and fingerprint in seen:
                raise IMCError('Paginação iMC repetida')
            seen.add(fingerprint)
            yield from rows
            # Continuar mesmo em página curta: o servidor pode limitar o size.
            if not rows:
                return
            start += len(rows)

    def iter_devices(self):
        self._modes.clear()
        return self.records('plat/res/device', 'device')

    def iter_interfaces(self, device_id):
        return self.records(f'plat/res/device/{device_id}/interface', 'interface')

    def get_port_vlans(self, device_id, if_index):
        rows = list(self.records('vlan/portvlan', 'vlan', devId=device_id, ifIndex=if_index))
        if not rows:
            raise IMCError('VLAN vazia/inconclusiva; preservar interface')
        vlans = {vid(r) for r in rows}
        if device_id not in self._modes:
            modes = []
            unavailable = []
            for mode, element in (('access', 'accessIf'), ('trunk', 'trunkIf'), ('hybrid', 'hybridIf')):
                try:
                    rows = list(self.records(f'vlan/{mode}', element, devId=device_id))
                except IMCError as exc:
                    unavailable.append(mode)
                    logging.getLogger('pilot').warning('Endpoint VLAN %s indisponível: %s', mode, exc)
                    continue
                modes.extend((mode, row) for row in rows)
            self._modes[device_id] = modes, unavailable
        modes, unavailable = self._modes[device_id]
        matches = [(m, r) for m, r in modes if str(r.get('ifIndex')) == str(if_index)]
        if len(matches) != 1:
            raise IMCError('Modo VLAN ausente/ambíguo; preservar interface')
        mode, row = matches[0]
        native = vid(row.get('pvid'))
        if native not in vlans:
            raise IMCError('PVID não confirmado na associação de VLANs')
        if mode == 'hybrid':
            raise IMCError('Hybrid sem classificação tagged/untagged inequívoca; preservar interface')
        if mode == 'access' and vlans != {native}:
            raise IMCError('VLANs access inconsistentes')
        if mode != 'access' and unavailable:
            raise IMCError('Classificação trunk incompleta; preservar interface')
        return VlanState('access' if mode == 'access' else 'tagged', native,
                         tuple(sorted(vlans - {native})))

    def login(self):
        self._request('GET', 'plat/res/device', params={'start': 0, 'size': 1})

    def logout(self):
        """Limpeza exclusivamente local, sem DELETE."""
        self.session.cookies.clear()
        self.session.close()
