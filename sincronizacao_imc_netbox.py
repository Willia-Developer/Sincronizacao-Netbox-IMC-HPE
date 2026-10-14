#!/usr/bin/env python3
"""Entrada equivalente na raiz, sem efeitos de rede no import."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'imc'))
    runpy.run_path(str(Path(__file__).resolve().parent / 'imc' / 'sincronizacao_imc_netbox.py'), run_name='__main__')
