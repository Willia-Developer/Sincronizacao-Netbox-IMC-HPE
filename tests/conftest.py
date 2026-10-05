"""Testes offline: qualquer transporte real falha imediatamente."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Rede real proibida nos testes')
    monkeypatch.setattr('requests.adapters.HTTPAdapter.send', forbidden)
