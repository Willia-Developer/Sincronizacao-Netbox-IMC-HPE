"""Configuração, logs protegidos e exclusão mútua do piloto."""
import contextlib
import fcntl
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
from urllib.parse import urlsplit
import uuid

from .policy import PolicyError

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger('pilot')


class Redactor(logging.Formatter):
    converter = time.gmtime

    def __init__(self, run_id, mode, secrets=()):
        super().__init__('%(asctime)sZ %(levelname)s run=' + run_id + ' mode=' + mode + ' %(message)s')
        self.secrets = [v for v in secrets if v]

    def format(self, record):
        value = super().format(record)
        for secret in sorted(self.secrets, key=len, reverse=True):
            value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'(?i)(https?://)[^/\s@]+@', r'\1[REDACTED]@', value)
        value = re.sub(r"""(?ix)(["']?(?:authorization|cookie|set-cookie|password|senha|token|secret|api[_-]?key)["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^,;\n}]+)""", r'\1[REDACTED]', value)
        return value.replace('\n', '\\n').replace('\r', '\\r')


def setup_logging(mode):
    os.umask(0o077)
    directory = ROOT / 'logs'
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    formatter = Redactor(uuid.uuid4().hex, mode, [
        os.environ.get(k, '') for k in ('WUG_PASSWORD', 'WUG_TOKEN', 'NETBOX_TOKEN', 'WUG_USERNAME')
    ])
    LOG.setLevel(logging.INFO)
    for handler in LOG.handlers[:]:
        handler.close()
        LOG.removeHandler(handler)
    handlers = [logging.StreamHandler(), RotatingFileHandler(
        directory / 'pilot.log', maxBytes=5_000_000, backupCount=5, encoding='utf-8')]
    for handler in handlers:
        handler.setFormatter(formatter)
        LOG.addHandler(handler)
    LOG.propagate = False
    try:
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                         cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'],
                                             cwd=ROOT, stderr=subprocess.DEVNULL, text=True))
        commit += '+local' if dirty else ''
    except (OSError, subprocess.SubprocessError):
        commit = 'indisponivel'
    LOG.info('Início commit=%s', commit)
    return formatter


@contextlib.contextmanager
def execution_lock(path=None):
    path = path or ROOT / '.pilot.lock'
    with open(path, 'a', encoding='utf-8') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PolicyError('Outra execução está em andamento') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_environment(path=None):
    path = Path(path or os.environ.get('SYNC_ENV_FILE', ROOT / '.env'))
    if not path.exists():
        return
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:]
        key, separator, value = line.partition('=')
        key = key.strip()
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise PolicyError(f'Configuração inválida na linha {number}')
        try:
            words = shlex.split(value, comments=True)
        except ValueError:
            raise PolicyError(f'Aspas inválidas na linha {number}') from None
        if len(words) > 1:
            raise PolicyError(f'Valor com espaços exige aspas na linha {number}')
        os.environ.setdefault(key, words[0] if words else '')


def boolean(env, key, default='true'):
    value = env.get(key, default).lower()
    if value not in ('true', 'false'):
        raise PolicyError(f'{key} deve ser true ou false')
    return value == 'true'



def configuration(env=None, *, service=None):
    from .policy import safe_origin
    env = os.environ if env is None else env
    if service not in (None, 'WUG', 'NETBOX'):
        raise PolicyError('Serviço inválido')
    def required(key):
        value = env.get(key, '').strip()
        if not value or any(s in value.lower() for s in ('alterar_localmente', 'changeme', 'placeholder')):
            raise PolicyError(key + ' ausente ou placeholder')
        return value
    try:
        timeout = int(env.get('REQUEST_TIMEOUT', '30'))
        group = int(env['NETBOX_VLAN_GROUP_ID']) if env.get('NETBOX_VLAN_GROUP_ID') else None
    except ValueError:
        raise PolicyError('Timeout/grupo VLAN inválido') from None
    if not 1 <= timeout <= 300 or (group is not None and group <= 0):
        raise PolicyError('Timeout/grupo VLAN fora do intervalo')
    settings = []
    proxy = env.get('HTTPS_PROXY_URL')
    if proxy:
        parsed = urlsplit(proxy)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise PolicyError('Proxy inválido; não inclua credenciais na URL')
    for name in ('WUG', 'NETBOX'):
        if service and name != service:
            settings.append(None)
            continue
        origin = safe_origin(required(name + '_URL'))
        if not boolean(env, name + '_VERIFY_SSL'):
            raise PolicyError('Desativar validação TLS não é permitido')
        ca = env.get(name + '_CA_BUNDLE')
        if ca and not Path(ca).is_file():
            raise PolicyError('CA interna não encontrada')
        cfg = {'base_url': origin, 'verify_ssl': ca or True, 'request_timeout': timeout,
               'proxies': {'https': proxy} if proxy else None}
        if name == 'NETBOX':
            cfg.update(token=required('NETBOX_TOKEN'), vlan_group_id=group)
        elif env.get('WUG_TOKEN'):
            cfg.update(token=required('WUG_TOKEN'))
        else:
            cfg.update(username=required('WUG_USERNAME'), password=required('WUG_PASSWORD'))
        settings.append(cfg)
    return tuple(settings)


def write_report(path, payload):
    """Escrita atômica de evidência local, sem credenciais; não é backup do banco."""
    import json
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
