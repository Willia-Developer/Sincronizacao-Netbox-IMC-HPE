"""Valores normalizados independentes do fornecedor; ausência não significa vazio."""
from dataclasses import dataclass
from .policy import PolicyError

MISSING = object()

@dataclass(frozen=True)
class VlanState:
    mode: str
    untagged: int | None
    tagged: tuple

@dataclass(frozen=True)
class Interface:
    source_id: str
    name: str
    description: object = MISSING
    vlans: VlanState | None = None
    issues: tuple = ()

@dataclass(frozen=True)
class Device:
    source_id: str
    name: str

def vid(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isdecimal():
        raise PolicyError('VID inválido')
    result = int(value)
    if not 1 <= result <= 4094:
        raise PolicyError('VID fora do intervalo')
    return result

def vlan_state(mode, native, tagged):
    if mode not in ('access', 'tagged') or not isinstance(tagged, list):
        raise PolicyError('Modo ou associação VLAN inconclusiva')
    native = None if native is None else vid(native)
    tags = tuple(sorted({vid(v) for v in tagged}))
    if native in tags or (mode == 'access' and (native is None or tags)):
        raise PolicyError('Associação VLAN inconsistente')
    return VlanState(mode, native, tags)

def field(row, path):
    value = row
    if not isinstance(path, str) or not path:
        return MISSING
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value
