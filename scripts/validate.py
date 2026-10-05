#!/usr/bin/env python3
"""Validação offline: não lê .env nem utiliza APIs corporativas."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    directory=ROOT/'artifacts'; directory.mkdir(exist_ok=True)
    checks=[('pytest',[sys.executable,'-m','pytest','-q']),
            ('compileall',[sys.executable,'-m','compileall','-q','wug','scripts','tests']),
            ('docs',[sys.executable,'scripts/review_repository.py']),
            ('shell',['bash','-n','scripts/executar_sincronizacao.sh'])]
    results=[]
    for name,command in checks:
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        (directory/(name+'.txt')).write_text(result.stdout+result.stderr)
        results.append({'check':name,'exit_code':result.returncode})
        print(name, 'PASS' if result.returncode==0 else 'FAIL')
        if result.returncode: print((result.stdout+result.stderr)[-3000:])
    (directory/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
    return int(any(r['exit_code'] for r in results))
if __name__=='__main__': raise SystemExit(main())
