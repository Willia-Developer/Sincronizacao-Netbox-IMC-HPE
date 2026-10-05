#!/usr/bin/env python3
"""Executa a regressão de simulação sintética com rede real proibida."""
from pathlib import Path
import subprocess
import sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,'-m','pytest','-q','tests/test_integration.py::test_description_updates_without_vlan_data'],cwd=Path(__file__).resolve().parents[1]))
