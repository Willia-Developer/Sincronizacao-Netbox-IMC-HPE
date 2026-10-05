"""Política aplicada antes do envio, inclusive em PreparedRequest."""
import json
import re
from urllib.parse import urlsplit
import requests

ALLOWED_INTERFACE_PATCH_FIELDS = frozenset({'description', 'mode', 'untagged_vlan', 'tagged_vlans'})

class PolicyError(RuntimeError):
    pass

def positive_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PolicyError('Identificador inválido')
    return value

def validate_patch(payload):
    if not isinstance(payload, dict) or not payload or set(payload) - ALLOWED_INTERFACE_PATCH_FIELDS:
        raise PolicyError('Payload vazio ou campo fora da lista permitida')
    if 'description' in payload and not isinstance(payload['description'], str):
        raise PolicyError('Descrição inválida')
    if 'mode' in payload and payload['mode'] not in ('access', 'tagged'):
        raise PolicyError('Modo VLAN inválido')
    if payload.get('untagged_vlan') is not None:
        positive_id(payload['untagged_vlan'])
    if 'tagged_vlans' in payload:
        if not isinstance(payload['tagged_vlans'], list):
            raise PolicyError('Lista VLAN inválida')
        for value in payload['tagged_vlans']:
            positive_id(value)
    return payload

def safe_origin(value):
    try:
        parts = urlsplit(value)
        port = parts.port
    except (TypeError, ValueError):
        raise PolicyError('URL inválida') from None
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.path not in ('', '/')
            or any(c.isspace() for c in value) or '\\' in value
            or (port is not None and not 1 <= port <= 65535)):
        raise PolicyError('Use origem HTTPS sem credenciais, caminho ou parâmetros')
    return value.rstrip('/')

class RestrictedSession(requests.Session):
    """NetBox GET/PATCH; WUG GET explícito e POST exclusivamente de autenticação."""
    def __init__(self, base_url, *, netbox=False, apply=False, read_paths=()):
        super().__init__()
        self.base_url = base_url.rstrip('/') + '/'
        self.netbox, self.apply = netbox, apply
        self.read_paths = tuple(read_paths)
        self.trust_env = False  # evita .netrc/proxy herdado; proxy explícito continua disponível

    def check(self, method, url, payload=None):
        base, target = urlsplit(self.base_url), urlsplit(url)
        if (target.scheme, target.netloc) != (base.scheme, base.netloc):
            raise PolicyError('Destino HTTP bloqueado')
        if not target.path.startswith(base.path) or target.fragment:
            raise PolicyError('Caminho HTTP bloqueado')
        suffix = target.path[len(base.path):]
        if '%' in suffix or '\\' in suffix or any(x in ('.', '..', '') for x in suffix.rstrip('/').split('/')):
            raise PolicyError('Caminho não canônico bloqueado')
        if self.netbox:
            if method == 'GET' and suffix in ('dcim/devices/', 'dcim/interfaces/', 'ipam/vlans/'):
                return
            if method == 'PATCH' and re.fullmatch(r'dcim/interfaces/[1-9][0-9]*/', suffix):
                if target.query or not self.apply:
                    raise PolicyError('PATCH não autorizado')
                validate_patch(payload)
                return
        else:
            if method == 'POST' and suffix == 'token' and not target.query:
                return
            if method == 'GET' and any(re.fullmatch(p, suffix) for p in self.read_paths):
                return
        raise PolicyError('Método ou recurso HTTP bloqueado')

    def request(self, method, url, **kwargs):
        method = method.upper()
        self.check(method, url, kwargs.get('json'))
        if method == 'PATCH' and any(k in kwargs for k in ('data', 'files', 'params')):
            raise PolicyError('PATCH exige apenas JSON validado')
        if method == 'POST':
            data = kwargs.get('data')
            if (not isinstance(data, dict) or set(data) != {'grant_type', 'username', 'password'}
                    or data['grant_type'] != 'password' or any(k in kwargs for k in ('json', 'files', 'params'))):
                raise PolicyError('POST restrito à autenticação')
        kwargs['allow_redirects'] = False
        return super().request(method, url, **kwargs)

    def send(self, request, **kwargs):
        payload = None
        if request.method == 'PATCH':
            try:
                payload = json.loads(request.body)
            except (ValueError, TypeError):
                raise PolicyError('Corpo PATCH inválido') from None
        if request.method == 'POST':
            from urllib.parse import parse_qs
            body = request.body.decode() if isinstance(request.body, bytes) else request.body
            data = parse_qs(body or '', keep_blank_values=True)
            if (set(data) != {'grant_type', 'username', 'password'} or data['grant_type'] != ['password']
                    or any(len(v) != 1 for v in data.values())):
                raise PolicyError('POST preparado restrito à autenticação')
        self.check(request.method, request.url, payload)
        kwargs['allow_redirects'] = False
        return super().send(request, **kwargs)
