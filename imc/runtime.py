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

from policy import PolicyError

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
        os.environ.get(k, '') for k in ('IMC_PASSWORD', 'NETBOX_TOKEN', 'IMC_USERNAME')
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
    path = Path(path or os.environ.get('IMC_ENV_FILE', ROOT / 'imc' / '.env'))
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
    env = os.environ if env is None else env
    if service not in (None, 'IMC', 'NETBOX'):
        raise PolicyError('Serviço de configuração inválido')
    required = (('IMC_HOST', 'IMC_USERNAME', 'IMC_PASSWORD') if service == 'IMC'
                else ('NETBOX_URL', 'NETBOX_TOKEN') if service == 'NETBOX'
                else ('IMC_HOST', 'IMC_USERNAME', 'IMC_PASSWORD', 'NETBOX_URL', 'NETBOX_TOKEN'))
    for key in required:
        value = env.get(key, '')
        if not value.strip() or any(p in value.lower() for p in
                ('alterar_localmente', 'changeme', 'your_token', 'sua_senha', 'seu_token', 'placeholder', 'exemplo.local')):
            raise PolicyError(f'{key} ausente ou placeholder')
    # Validar somente o serviço solicitado. Os placeholders internos abaixo
    # nunca são retornados nem usados em chamadas de rede.
    env = dict(env)
    if service == 'IMC':
        env.update(NETBOX_URL='https://unused.example.test', NETBOX_TOKEN='unused',
                   NETBOX_VERIFY_SSL='true', NETBOX_CA_BUNDLE='', NETBOX_VLAN_GROUP_ID='')
    elif service == 'NETBOX':
        env.update(IMC_HOST='unused.example.test', IMC_USERNAME='unused', IMC_PASSWORD='unused',
                   IMC_USE_HTTPS='true', IMC_PORT='8443', IMC_VERIFY_SSL='true', IMC_CA_BUNDLE='')
    host = env['IMC_HOST']
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', host):
        raise PolicyError('IMC_HOST inválido; use hostname ou IPv4 sem protocolo/porta')
    https = boolean(env, 'IMC_USE_HTTPS')
    try:
        port = int(env.get('IMC_PORT', '8443' if https else '8080'))
        timeout = int(env.get('REQUEST_TIMEOUT', '30'))
        url = urlsplit(env['NETBOX_URL'])
        nb_port = url.port
    except ValueError:
        raise PolicyError('Porta/URL/timeout inválido') from None
    if not 1 <= port <= 65535 or not 1 <= timeout <= 300:
        raise PolicyError('Porta/timeout fora do intervalo')
    if (https and port in (80, 8080)) or (not https and port in (443, 8443)):
        raise PolicyError('Protocolo e porta iMC incoerentes')
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
            or not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', url.hostname)
            or url.query or url.fragment or url.path not in ('', '/')
            or any(c.isspace() for c in env['NETBOX_URL'])
            or (nb_port is not None and not 1 <= nb_port <= 65535)):
        raise PolicyError('NETBOX_URL inválida; informe a origem sem /api')
    if (url.scheme == 'https' and nb_port in (80, 8080)) or (url.scheme == 'http' and nb_port in (443, 8443)):
        raise PolicyError('Protocolo e porta NetBox incoerentes')
    if not https or url.scheme != 'https':
        LOG.warning('HTTP sem TLS foi configurado explicitamente')
    verify = {}
    for target_service in ('IMC', 'NETBOX'):
        if not boolean(env, target_service + '_VERIFY_SSL'):
            raise PolicyError('Desativar validação TLS não é permitido; configure CA interna')
        ca = env.get(target_service + '_CA_BUNDLE')
        if ca and not Path(ca).is_file():
            raise PolicyError(f'{target_service}_CA_BUNDLE não é arquivo')
        verify[target_service] = ca or True
    if env.get('SYNC_INTERVAL', '0') != '0':
        raise PolicyError('SYNC_INTERVAL fora do escopo; execução única')
    try:
        group = int(env['NETBOX_VLAN_GROUP_ID']) if env.get('NETBOX_VLAN_GROUP_ID') else None
    except ValueError:
        raise PolicyError('NETBOX_VLAN_GROUP_ID deve ser um ID inteiro positivo') from None
    if group is not None and group <= 0:
        raise PolicyError('NETBOX_VLAN_GROUP_ID deve ser positivo')
    settings = ({'host': host, 'port': str(port), 'username': env['IMC_USERNAME'],
             'password': env['IMC_PASSWORD'], 'use_https': https,
             'verify_ssl': verify['IMC'], 'request_timeout': timeout},
            {'base_url': env['NETBOX_URL'], 'token': env['NETBOX_TOKEN'],
             'verify_ssl': verify['NETBOX'], 'request_timeout': timeout, 'vlan_group_id': group})
    if service == 'IMC':
        return settings[0], None
    if service == 'NETBOX':
        return None, settings[1]
    return settings
