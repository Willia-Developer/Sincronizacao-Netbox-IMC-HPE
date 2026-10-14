#!/usr/bin/env python3
"""Revisão estática, links locais, PDFs e diff sanitizado para apresentação."""
import ast
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
def main():
    issues = []
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    (artifacts / 'diff-sanitizado.patch.txt').touch(exist_ok=True)
    for source in (ROOT / 'imc').glob('*.py'):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and 'legacy' in (node.module or ''):
                issues.append(str(source.name) + ': import legado')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('post', 'put', 'delete', 'patch'):
                issues.append(str(source.name) + ': chamada de mutação direta')
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                                     cwd=ROOT, text=True).splitlines()
    pdf_count = 0
    for name in sorted(set(names)):
        path = ROOT / name
        if path.suffix == '.md' and path.is_file() and name != 'escopo-correcoes.md':
            for target in re.findall(r'\[[^]]*\]\(([^)]+)\)', path.read_text()):
                if '://' not in target and not target.startswith('#'):
                    target = target.split('#')[0]
                    if not (path.parent / target).exists():
                        issues.append(name + ': link ausente ' + target)
        if path.suffix == '.pdf' and path.is_file():
            result = subprocess.run(['pdftotext', str(path), '-'], capture_output=True, text=True)
            if result.returncode or not result.stdout.strip():
                issues.append(name + ': PDF não legível')
            pdf_count += 1
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    raw = subprocess.check_output(['git', 'diff', '--no-ext-diff', '--no-color'], cwd=ROOT, text=True)
    # Não compartilhar segredos que ainda aparecem nas linhas removidas/contexto.
    redacted = []
    for line in raw.splitlines():
        if line.startswith(('diff --git ', 'index ', '--- ', '+++ ', '@@', 'Binary files ')):
            redacted.append(line)
        elif line.startswith('+'):
            redacted.append(line)
        elif line.startswith('-'):
            redacted.append('-[CONTEÚDO ANTIGO OMITIDO]')
        else:
            redacted.append(' [CONTEXTO ANTIGO OMITIDO]')
    (artifacts / 'diff-sanitizado.patch.txt').write_text('\n'.join(redacted) + '\n')
    modified = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).splitlines()
    new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    inventory = ['# Arquivos alterados', '', *['- ' + name for name in modified],
                 '', '# Arquivos novos', '', *['- ' + name for name in new if name != 'escopo-correcoes.md'],
                 '', 'escopo-correcoes.md já existia como não versionado e foi preservado.', '']
    (artifacts / 'ARQUIVOS_ALTERADOS.md').write_text('\n'.join(inventory))
    print('AST:', 'PASS' if not issues else 'FAIL')
    print('PDFs extraídos:', pdf_count)
    print('PPTX encontrados:', len([n for n in names if n.lower().endswith('.pptx')]))
    print('Arquivos rastreados modificados:', len(modified))
    print('Arquivos novos da correção:', len([n for n in new if n != 'escopo-correcoes.md']))
    for issue in issues:
        print(issue)
    return int(bool(issues))
if __name__ == '__main__':
    raise SystemExit(main())
