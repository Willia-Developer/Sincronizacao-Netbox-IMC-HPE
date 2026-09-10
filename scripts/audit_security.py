#!/usr/bin/env python3
"""Auditoria local sem imprimir segredos; histórico permanece intocado."""
import hashlib
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'private_ipv4': r'\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b',
    'mac_address': r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b',
    'credential_assignment_review': r"""(?im)(?:password|senha|token|username|usuário)\s*[:=]\s*["']?[^\s"']{3,}""",
    'internal_url_review': r'https?://[^\s/"<>]+',
}
SAFE = re.compile(r'example\.(?:test|com|org)|exemplo\.local|localhost|127\.0\.0\.1|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|github\.com|pypi\.org|python\.org|netboxlabs\.com|docs\.netbox\.dev|requests\.readthedocs|openai\.com|www\.w3\.org|purl\.org|schemas\.')
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def text(data, name):
    if name.lower().endswith('.pdf'):
        result = subprocess.run(['pdftotext', '-', '-'], input=data, capture_output=True)
        return result.stdout.decode('utf-8', 'replace')
    return data.decode('utf-8', 'replace')

def inspect(data, name):
    result = {}
    for category, pattern in PATTERNS.items():
        matches = [m for m in re.finditer(pattern, text(data, name)) if not SAFE.search(m.group())]
        if matches:
            result[category] = len(matches)
    return result

def main():
    commits = git('rev-list', '--all').decode().splitlines()
    history = []
    known = {}
    for commit in commits:
        for name in git('ls-tree', '-r', '--name-only', commit).decode().splitlines():
            data = git('show', commit + ':' + name)
            if name in ('imc/.env.example', 'imc/testar_conexao_imc.py', 'imc/teste-home'):
                source = data.decode('utf-8', 'replace')
                for key, value in re.findall(r'(?m)^[ \t]*(IMC_PASSWORD|IMC_USERNAME|IMC_HOST|NETBOX_TOKEN|NETBOX_URL)[ \t]*=[ \t]*([^\n#]*)', source):
                    value = value.strip().strip('\"\'')
                    if len(value) >= 4 and not SAFE.search(value) and not re.search(r'(?i)alterar|exemplo|example|sua_|seu_|changeme|placeholder', value):
                        known[value] = key
                for value in re.findall(r'<sysName>([^<]+)</sysName>', source):
                    if len(value) >= 4:
                        known[value] = 'device_name'
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    tree = None
                for node in ast.walk(tree) if tree else []:
                    if isinstance(node, ast.keyword) and node.arg in ('password', 'username', 'token') and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        value = node.value.value
                        if len(value) >= 6 and not re.search(r'(?i)senha|token|example|alterar|password', value):
                            known[value] = node.arg
            hits = inspect(data, name)
            if hits:
                history.append({'commit': commit, 'file': name, 'findings': hits,
                                'blob_sha256': hashlib.sha256(data).hexdigest()})
    output = ROOT / 'artifacts' / 'auditoria-historico.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({'note': 'Candidatos para revisão; contagens não provam que todo valor é segredo.',
                                 'commits': commits, 'findings': history}, indent=2) + '\n')
    current, residual = {}, {}
    names = set(git('ls-files', '--cached', '--others', '--exclude-standard').decode().splitlines())
    for name in sorted(names):
        path = ROOT / name
        if path.is_file():
            hits = inspect(path.read_bytes(), name)
            if hits:
                current[name] = hits
            source = text(path.read_bytes(), name)
            remaining = sorted({category for value, category in known.items()
                                if re.search(r'(?<![\w])' + re.escape(value) + r'(?![\w])', source)})
            if remaining:
                residual[name] = remaining
    (ROOT / 'artifacts' / 'auditoria-atual.json').write_text(json.dumps({
        'known_historical_values_checked': len(known),
        'known_value_residues': residual, 'pattern_candidates': current,
        'note': 'Valores nunca são incluídos. Fixtures e padrões de código podem gerar candidatos.'
    }, indent=2) + '\n')
    print(json.dumps({'historical_commits': len(commits), 'historical_file_snapshots': len(history),
                      'current_candidates': current,
                      'known_historical_values_checked': len(known),
                      'known_value_residues': residual,
                      'python_modules': {m: bool(importlib.util.find_spec(m)) for m in
                                         ('pytest', 'reportlab', 'requests', 'pptx')}}, indent=2))
if __name__ == '__main__':
    main()
