"""Regressões de segurança, exclusivamente com mocks."""
import pathlib
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'imc'))
from imc_client import IMCClient
from netbox_client import NetBoxClient


class PilotPolicyTests(unittest.TestCase):
    def test_imc_blocks_mutations(self):
        client = IMCClient('imc.example.test', username='fixture', password='fixture')
        client.session.request = Mock()
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(method=method), self.assertRaises(RuntimeError):
                client._request(method, '/plat/res/device')
        client.session.request.assert_not_called()

    def test_netbox_rejects_entire_payload(self):
        client = NetBoxClient('https://netbox.example.test', 'fixture')
        client.session.request = Mock()
        for field in ('enabled', 'status', 'type', 'ip_addresses', 'mac_address',
                      'primary_mac_address', 'unknown'):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                client._request('PATCH', 'dcim/interfaces/1/', json={'description': 'ok', field: True})
        client.session.request.assert_not_called()

    def test_logout_never_uses_network(self):
        client = IMCClient('imc.example.test', username='fixture', password='fixture')
        client._session_id = 'fixture'
        client.session.delete = Mock()
        client.logout()
        client.session.delete.assert_not_called()
