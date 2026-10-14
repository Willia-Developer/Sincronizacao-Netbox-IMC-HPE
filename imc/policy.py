"""Validação central antes da rede."""
import logging
import re
import json
import requests

ALLOWED_INTERFACE_PATCH_FIELDS = frozenset({'description', 'mode', 'untagged_vlan', 'tagged_vlans'})
LOG = logging.getLogger('pilot')

class PolicyError(RuntimeError):
    pass

def positive_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PolicyError('Identificador inválido')
    return value

def validate_patch(payload):
    try:
        if not isinstance(payload, dict) or not payload:
            raise PolicyError('Payload vazio ou inválido')
        if set(payload) - ALLOWED_INTERFACE_PATCH_FIELDS:
            raise PolicyError('Campo fora da allowlist')
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
    except PolicyError:
        LOG.error('Payload bloqueado pela allowlist/validação')
        raise
    return payload

class RestrictedSession(requests.Session):
    def __init__(self, base_url, *, netbox=False, apply=False):
        super().__init__()
        self.base_url = base_url.rstrip('/') + '/'
        self.netbox = netbox
        self.apply = apply

    def check(self, method, url, payload=None):
        if method not in ({'GET', 'PATCH'} if self.netbox else {'GET'}) or not url.startswith(self.base_url):
            LOG.error('Método ou destino HTTP bloqueado')
            raise PolicyError('Método ou destino HTTP bloqueado')
        if method == 'PATCH':
            if not re.fullmatch(r'dcim/interfaces/[1-9][0-9]*/', url[len(self.base_url):]):
                raise PolicyError('PATCH somente em interface individual')
            validate_patch(payload)
            if not self.apply:
                raise PolicyError('PATCH bloqueado no dry-run')

    def request(self, method, url, **kwargs):
        method = method.upper()
        self.check(method, url, kwargs.get('json'))
        if method == 'PATCH' and any(k in kwargs for k in ('data', 'files', 'params')):
            raise PolicyError('PATCH exige apenas JSON validado')
        kwargs['allow_redirects'] = False
        return super().request(method, url, **kwargs)

    def send(self, request, **kwargs):
        payload = None
        if request.method == 'PATCH':
            try:
                payload = json.loads(request.body)
            except (ValueError, TypeError):
                raise PolicyError('Corpo PATCH inválido') from None
        self.check(request.method, request.url, payload)
        kwargs['allow_redirects'] = False
        return super().send(request, **kwargs)
