#!/usr/bin/env python3
"""Confere links Markdown locais e compila o perfil de exemplo sem rede."""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from wug.profile import load_profile

def main():
    errors=[]
    for path in ROOT.rglob('*.md'):
        if any(part.startswith('.') for part in path.relative_to(ROOT).parts): continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            if '://' in target or target.startswith('#'): continue
            if not (path.parent/target.split('#')[0]).exists(): errors.append(str(path.relative_to(ROOT))+': '+target)
    load_profile(ROOT/'config/wug.example.json')
    print('\n'.join(errors) if errors else 'Links locais e perfil de exemplo válidos')
    return int(bool(errors))
if __name__=='__main__': raise SystemExit(main())
