"""Contrato local explícito da API instalada; não inventa endpoint de portas físicas."""
import json
import re
from pathlib import Path
from .policy import PolicyError

def load_profile(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise PolicyError('Perfil WUG ausente ou JSON inválido') from None
    validate_profile(data)
    return data

def validate_profile(data, *, interfaces=False, apply=False):
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data.get('schema_version') != 1:
        raise PolicyError('Versão do perfil WUG inválida')
    if type(data.get('validated')) is not bool or type(data.get('allow_description_clear')) is not bool:
        raise PolicyError('Flags do perfil devem ser booleanos')
    if apply and (not data['validated'] or not all(isinstance(data.get(k), str) and data[k].strip()
                                                  for k in ('product_version', 'validated_by', 'validated_at', 'evidence'))):
        raise PolicyError('Aplicação exige perfil homologado e evidência da API instalada')
    for key in ('devices', 'interfaces'):
        cfg = data.get(key)
        if not isinstance(cfg, dict):
            raise PolicyError('Coleção não configurada no perfil')
        endpoint = cfg.get('endpoint')
        if key == 'interfaces' and not endpoint:
            if interfaces:
                raise PolicyError('Configure endpoint/mapeamento de portas físicas em config/wug.json')
            continue
        pattern = (r'device-groups/[0-9]+/devices' if key == 'devices'
                   else r'devices/\{device_id\}/(?:interfaces|inventory/interfaces|reports/[a-z0-9-]+)')
        if not isinstance(endpoint, str) or not re.fullmatch(pattern, endpoint):
            raise PolicyError('Endpoint de leitura fora dos formatos permitidos')
        for mapping in ('items_path', 'id_field', 'name_field'):
            if not isinstance(cfg.get(mapping), str) or not cfg[mapping]:
                raise PolicyError('Mapeamento obrigatório ausente')
        pagination = cfg.get('pagination', {})
        if not isinstance(pagination, dict):
            raise PolicyError('Paginação deve ser objeto')
        mode = pagination.get('mode')
        if mode not in ('cursor', 'offset', 'none'):
            raise PolicyError('Modo de paginação não suportado')
        required = {'cursor': ('container_path', 'next_field', 'parameter'),
                    'offset': ('total_path', 'parameter', 'limit_parameter'),
                    'none': ('complete_path',)}[mode]
        if any(not isinstance(pagination.get(k), str) or not pagination[k] for k in required):
            raise PolicyError('Evidência de paginação/completude ausente')
        if key == 'interfaces':
            if not isinstance(cfg.get('vlans'), dict) or type(cfg['vlans'].get('enabled')) is not bool:
                raise PolicyError('Ativação VLAN deve ser booleana')
            if cfg['vlans']['enabled']:
                for k in ('mode_field', 'untagged_field', 'tagged_field'):
                    if not isinstance(cfg['vlans'].get(k), str) or not cfg['vlans'][k]:
                        raise PolicyError('Mapeamento VLAN incompleto')
                if not isinstance(cfg['vlans'].get('mode_map'), dict):
                    raise PolicyError('Mapa de modos VLAN ausente')
    for key in ('device_map', 'interface_map'):
        mapping = data.get(key, {})
        if not isinstance(mapping, dict) or any(not isinstance(v, str) or not v.strip() for v in mapping.values()):
            raise PolicyError('Mapeamento de nomes inválido')
    return data
