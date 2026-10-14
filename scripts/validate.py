#!/usr/bin/env python3
"""Executa verificações offline e guarda saídas completas em artifacts/."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
def main():
    ARTIFACTS.mkdir(exist_ok=True)
    env = dict(os.environ)
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
    checks = [('pytest', [sys.executable, '-m', 'pytest', '-v']),
              ('compileall', [sys.executable, '-m', 'compileall', '-q', 'imc', 'scripts', 'tests', 'sincronizacao_imc_netbox.py']),
              ('bash_requested', ['bash', '-n', *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'imc').glob('*.sh'))]]),
              *[(p.stem, ['bash', '-n', str(p)]) for p in sorted((ROOT/'imc').glob('*.sh'))],
              ('mock_dry_run', [sys.executable, 'scripts/mock_dry_run.py']),
              ('pip_check', [sys.executable, '-m', 'pip', 'check']),
              ('static_review', [sys.executable, 'scripts/review_repository.py']),
              ('diff_check', ['git', 'diff', '--check'])]
    results = []
    for name, command in checks:
        (ARTIFACTS / (name + '.txt')).touch(exist_ok=True)
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        (ARTIFACTS / (name + '.txt')).write_text(result.stdout)
        results.append({'check': name, 'command': command, 'exit_code': result.returncode})
        print(name, 'PASS' if result.returncode == 0 else 'FAIL')
        if result.returncode:
            print(result.stdout[-6000:])
    (ARTIFACTS / 'validation.json').write_text(json.dumps(results, indent=2) + '\n')
    return int(any(r['exit_code'] for r in results))
if __name__ == '__main__':
    raise SystemExit(main())
