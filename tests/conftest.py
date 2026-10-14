"""Guardião global: nenhum teste pytest pode usar rede real."""
import pytest

@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Rede real proibida nos testes')
    monkeypatch.setattr('requests.adapters.HTTPAdapter.send', forbidden)
