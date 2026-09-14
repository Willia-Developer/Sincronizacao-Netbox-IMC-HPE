"""Cobertura funcional e de segurança com transporte inteiramente mockado."""
import copy
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'imc'))
from imc_client import IMCClient, VlanState, vid
from netbox_client import NetBoxClient
from policy import PolicyError, RestrictedSession, validate_patch
from runtime import Redactor, configuration, execution_lock, load_environment
from sincronizacao_imc_netbox import arguments
from sync import MISSING, differences, execute, plan, snapshot

ROOT = Path(__file__).resolve().parents[1]

def response(payload=None, text='', status=200):
    r = Mock(status_code=status, text=text)
    r.json.return_value = payload
    return r

def current():
    return {'id': 20, 'name': 'Gi1', 'device': {'id': 10},
            'description': 'Sala A', 'mode': {'value': 'access'},
            'untagged_vlan': {'id': 70, 'vid': 7}, 'tagged_vlans': []}

def fixture():
    imc = Mock()
    imc.iter_devices.return_value = [{'id': '1', 'sysName': 'SW-LAB-01'}]
    imc.iter_interfaces.return_value = [{'ifName': 'Gi1', 'ifIndex': '1', 'ifAlias': 'Sala B'}]
    imc.get_port_vlans.return_value = VlanState('access', 7, ())
    nb = NetBoxClient('https://netbox.example.test', 'fixture')
    nb.find_device = Mock(return_value={'id': 10, 'name': 'SW-LAB-01'})
    state = current()
    nb.find_interface = Mock(side_effect=lambda *a: copy.deepcopy(state))
    nb.find_vlan = Mock(side_effect=lambda value: {'id': value * 10, 'vid': value})
    def send(method, url, **kwargs):
        if method == 'PATCH':
            state.update(kwargs['json'])
        return response(copy.deepcopy(state))
    nb.session.request = Mock(side_effect=send)
    return imc, nb

def config():
    return dict(IMC_HOST='imc.example.test', IMC_USERNAME='fixture_user',
                IMC_PASSWORD='fixture_password', NETBOX_URL='https://netbox.example.test',
                NETBOX_TOKEN='fixture_token')

class TransportTests(unittest.TestCase):
    def test_imc_get(self):
        c = IMCClient('imc.example.test')
        c.session.request = Mock(return_value=response({}))
        c._request('GET', 'plat/res/device')
        self.assertEqual(c.session.request.call_args.args[0], 'GET')
        self.assertEqual(c.session.request.call_args.kwargs['timeout'], 30)

    def test_netbox_get(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', request_timeout=17)
        c.session.request = Mock(return_value=response({'results': []}))
        c._get('dcim/devices/')
        self.assertEqual(c.session.request.call_args.kwargs['timeout'], 17)

    def test_netbox_valid_patch(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
        c.session.request = Mock(return_value=response({}))
        c.patch_interface(1, {'description': 'Sala B'})
        c.session.request.assert_called_once()

    def test_netbox_blocks_methods(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
        c.session.request = Mock()
        for method in ('POST', 'PUT', 'DELETE'):
            with self.subTest(method=method), self.assertRaises(PolicyError):
                c._request(method, 'dcim/interfaces/1/', json={})
        c.session.request.assert_not_called()

    def test_session_direct_and_prepared_bypass_blocked(self):
        for netbox, method in ((False, 'DELETE'), (True, 'POST'), (True, 'PATCH')):
            s = RestrictedSession('https://example.test/api/', netbox=netbox)
            with patch('requests.adapters.HTTPAdapter.send') as send:
                with self.assertRaises(PolicyError):
                    s.request(method, 'https://example.test/api/dcim/interfaces/1/', json={'enabled': True})
                req = requests.Request(method, 'https://example.test/api/dcim/interfaces/1/',
                                       json={'enabled': True}).prepare()
                with self.assertRaises(PolicyError):
                    s.send(req)
                send.assert_not_called()

    def test_payload_forbidden_even_with_apply(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
        c.session.request = Mock()
        for field in ('enabled', 'status', 'type', 'mac_address', 'primary_mac_address',
                      'ip_addresses', 'device', 'name', 'site', 'role', 'device_type',
                      'platform', 'rack', 'position', 'face', 'tags', 'custom_fields', 'comments', 'unknown'):
            with self.subTest(field=field), self.assertRaises(PolicyError):
                c._request('PATCH', 'dcim/interfaces/1/', json={'description': 'ok', field: True})
        c.session.request.assert_not_called()

    def test_patch_device_and_bulk_blocked(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
        c.session.request = Mock()
        for endpoint in ('dcim/devices/1/', 'dcim/interfaces/', 'ipam/vlans/1/'):
            with self.subTest(endpoint=endpoint), self.assertRaises(PolicyError):
                c._request('PATCH', endpoint, json={'description': 'ok'})
        c.session.request.assert_not_called()

    def test_payload_allowlist(self):
        self.assertEqual(validate_patch({'description': ''}), {'description': ''})
        validate_patch({'mode': 'tagged', 'untagged_vlan': 1, 'tagged_vlans': [2]})

    def test_payload_types(self):
        for value in ({}, [], {'mode': None}, {'description': 3}, {'tagged_vlans': [True]},
                      {'untagged_vlan': 0}, {'tagged_vlans': None}):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                validate_patch(value)

    def test_dry_run_client_blocks_patch(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture')
        c.session.request = Mock()
        with self.assertRaises(PolicyError):
            c.patch_interface(1, {'description': 'ok'})
        c.session.request.assert_not_called()

    def test_creation_blocked(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
        c.session.request = Mock()
        with self.assertRaises(PolicyError):
            c._post('dcim/devices/', {})
        c.session.request.assert_not_called()
        self.assertNotIn('legacy', sys.modules)
        scope = {}
        with self.assertRaisesRegex(RuntimeError, 'FORA DO ESCOPO'):
            exec(compile((ROOT / 'imc/legacy/netbox_client.py.disabled').read_text(),
                         'legacy', 'exec'), scope)

    def test_redirects_and_errors_do_not_leak(self):
        c = NetBoxClient('https://netbox.example.test', 'fixture')
        c.session.request = Mock(return_value=response(text='password=DO_NOT_LOG', status=302))
        with self.assertRaises(PolicyError) as exc:
            c._get('dcim/devices/')
        self.assertNotIn('DO_NOT_LOG', str(exc.exception))
        self.assertFalse(c.session.request.call_args.kwargs['allow_redirects'])

    def test_timeout_safe(self):
        c = IMCClient('imc.example.test')
        c.session.request = Mock(side_effect=requests.Timeout('password=DO_NOT_LOG'))
        with self.assertRaisesRegex(PolicyError, 'Timeout') as exc:
            c._request('GET', 'plat/res/device')
        self.assertNotIn('DO_NOT_LOG', str(exc.exception))

class MatchingTests(unittest.TestCase):
    def client(self, rows):
        c = NetBoxClient('https://netbox.example.test', 'fixture')
        c._get = Mock(return_value={'results': rows, 'next': None})
        return c

    def test_missing_device(self):
        with self.assertRaises(PolicyError):
            self.client([]).find_device('SW-LAB-01')

    def test_exact_device_no_approximation(self):
        with self.assertRaises(PolicyError):
            self.client([{'id': 1, 'name': 'SW-LAB-010'}]).find_device('SW-LAB-01')

    def test_ambiguous_device(self):
        with self.assertRaisesRegex(PolicyError, 'ambígua'):
            self.client([{'id': 1, 'name': 'SW'}, {'id': 2, 'name': 'SW'}]).find_device('SW')

    def test_missing_interface(self):
        with self.assertRaises(PolicyError):
            self.client([]).find_interface(10, 'Gi1')

    def test_ambiguous_interface(self):
        with self.assertRaises(PolicyError):
            self.client([{'id': 1, 'name': 'Gi1'}, {'id': 2, 'name': 'Gi1'}]).find_interface(10, 'Gi1')

    def test_wrong_device(self):
        with self.assertRaises(PolicyError):
            self.client([{'id': 1, 'name': 'Gi1', 'device': {'id': 11}}]).find_interface(10, 'Gi1')

    def test_missing_vlan(self):
        with self.assertRaisesRegex(PolicyError, 'VLAN não encontrada'):
            self.client([]).find_vlan(7)

    def test_ambiguous_vlan(self):
        with self.assertRaisesRegex(PolicyError, 'ambígua'):
            self.client([{'id': 1, 'vid': 7}, {'id': 2, 'vid': '7'}]).find_vlan(7)

    def test_pagination_finds_ambiguity_across_pages(self):
        c = self.client([])
        c._get.side_effect = [{'results': [{'id': 1, 'name': 'SW'}], 'next': 'untrusted'},
                              {'results': [{'id': 2, 'name': 'SW'}], 'next': None}]
        with self.assertRaisesRegex(PolicyError, 'ambígua'):
            c.find_device('SW')
        self.assertEqual(c._get.call_args.kwargs['params']['offset'], 1)

class ComparisonTests(unittest.TestCase):
    def compare(self, desc='Sala A', state=None, row=None):
        _, nb = fixture()
        return differences(desc, state or VlanState('access', 7, ()), row or current(), nb)[1]

    def test_no_difference(self):
        self.assertEqual(self.compare(), {})

    def test_description_only(self):
        self.assertEqual(self.compare('  Sala B  '), {'description': 'Sala B'})

    def test_vlan_only_minimal(self):
        self.assertEqual(self.compare(state=VlanState('access', 9, ())), {'untagged_vlan': 90})

    def test_confirmed_access_removes_previous_tagged_list(self):
        row = current()
        row.update(mode={'value': 'tagged'}, tagged_vlans=[{'id': 80}])
        self.assertEqual(self.compare(row=row), {'mode': 'access', 'tagged_vlans': []})

    def test_both_only_allowed_fields(self):
        self.assertEqual(self.compare('Sala B', VlanState('tagged', 9, (8,))),
                         {'description': 'Sala B', 'mode': 'tagged', 'untagged_vlan': 90, 'tagged_vlans': [80]})

    def test_description_missing_preserved(self):
        for value in (MISSING, 123, {}, []):
            with self.subTest(value=value):
                self.assertEqual(self.compare(value), {})

    def test_null_and_empty_description_explicitly_clear(self):
        for value in (None, '', '   '):
            with self.subTest(value=value):
                self.assertEqual(self.compare(value), {'description': ''})

    def test_legitimate_case_and_internal_spaces(self):
        self.assertEqual(self.compare('Sala  A'), {'description': 'Sala  A'})
        self.assertEqual(self.compare('sala A'), {'description': 'sala A'})

    def test_vlan_order_duplicates_and_types(self):
        row = current()
        row.update(mode={'value': 'tagged'}, tagged_vlans=[{'id': 90}, {'id': '80'}, {'id': 90}])
        self.assertEqual(self.compare(state=VlanState('tagged', '7', ('9', 8, 9, {'vid': 8})), row=row), {})

    def test_vlan_inconclusive_preserves_entire_interface(self):
        _, nb = fixture()
        for state in (None, (), [], {}):
            with self.subTest(state=state), self.assertRaises(PolicyError):
                differences('changed', state, current(), nb)

    def test_missing_vlan_blocks_description_too(self):
        _, nb = fixture()
        nb.find_vlan.side_effect = PolicyError('VLAN não encontrada')
        with self.assertRaises(PolicyError):
            differences('changed', VlanState('access', 9, ()), current(), nb)

    def test_malformed_netbox_blocks(self):
        row = current()
        del row['tagged_vlans']
        with self.assertRaises(PolicyError):
            self.compare(row=row)

    def test_no_fixed_vlan_or_reserved_filter(self):
        for value in (1, 99, 1002, 4094):
            with self.subTest(value=value):
                self.assertEqual(vid(str(value)), value)

class IMCParsingTests(unittest.TestCase):
    def client(self, mapping):
        c = IMCClient('imc.example.test')
        c.records = Mock(side_effect=lambda endpoint, element, **filters: iter(mapping.get(endpoint, [])))
        return c

    def test_access(self):
        c = self.client({'vlan/portvlan': [{'vlanId': '99'}],
                         'vlan/access': [{'ifIndex': '1', 'pvid': '99'}]})
        self.assertEqual(c.get_port_vlans(1, 1), VlanState('access', 99, ()))

    def test_trunk_native(self):
        c = self.client({'vlan/portvlan': [{'vlanId': 7}, {'vlanId': 8}],
                         'vlan/trunk': [{'ifIndex': 1, 'pvid': 7}]})
        self.assertEqual(c.get_port_vlans(1, 1), VlanState('tagged', 7, (8,)))

    def test_hybrid_uncertain(self):
        c = self.client({'vlan/portvlan': [{'vlanId': 7}, {'vlanId': 8}],
                         'vlan/hybrid': [{'ifIndex': 1, 'pvid': 7}]})
        with self.assertRaisesRegex(PolicyError, 'Hybrid'):
            c.get_port_vlans(1, 1)

    def test_empty_vlan(self):
        with self.assertRaises(PolicyError):
            self.client({}).get_port_vlans(1, 1)

    def test_invalid_vlan_among_valid_blocks_all(self):
        c = self.client({'vlan/portvlan': [{'vlanId': 7}, {'vlanId': 'invalid'}]})
        with self.assertRaises(PolicyError):
            c.get_port_vlans(1, 1)

    def test_mode_missing_no_inference_from_single_vid(self):
        with self.assertRaises(PolicyError):
            self.client({'vlan/portvlan': [{'vlanId': 7}]}).get_port_vlans(1, 1)

    def test_mode_ambiguity(self):
        c = self.client({'vlan/portvlan': [{'vlanId': 7}],
                         'vlan/access': [{'ifIndex': 1, 'pvid': 7}],
                         'vlan/trunk': [{'ifIndex': 1, 'pvid': 7}]})
        with self.assertRaises(PolicyError):
            c.get_port_vlans(1, 1)

    def test_xml_and_json(self):
        self.assertEqual(IMCClient.parse(response(text='<list><interface><ifAlias/></interface></list>'),
                                        'interface'), [{'ifAlias': ''}])
        self.assertEqual(IMCClient.parse(response({'device': {'id': '1'}}), 'device'), [{'id': '1'}])

    def test_html_and_unknown_json_not_empty_success(self):
        for r in (response(text='<html/>'), response({'error': 'unauthorized'})):
            with self.subTest(response=r), self.assertRaises(PolicyError):
                IMCClient.parse(r, 'vlan')

    def test_parsing_error(self):
        r = response(text='invalid')
        r.json.side_effect = ValueError()
        with self.assertRaises(PolicyError):
            IMCClient.parse(r, 'vlan')

    def test_repeated_page_stops(self):
        c = IMCClient('imc.example.test')
        c._request = Mock(return_value=response({'device': [{'id': i} for i in range(100)]}))
        with self.assertRaises(PolicyError):
            list(c.iter_devices())
        self.assertEqual(c._request.call_count, 2)

    def test_short_pages_are_not_assumed_complete(self):
        c = IMCClient('imc.example.test')
        c._request = Mock(side_effect=[response({'device': [{'id': 1}]}),
                                      response({'device': [{'id': 2}]}),
                                      response({'device': []})])
        self.assertEqual(list(c.iter_devices()), [{'id': 1}, {'id': 2}])
        self.assertEqual(c._request.call_args.kwargs['params']['start'], 2)

class FlowTests(unittest.TestCase):
    def test_dry_run_never_patch(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        execute(nb, changes, summary)
        nb.session.request.assert_not_called()
        self.assertEqual((summary.devices, summary.devices_found, summary.interfaces,
                          summary.divergent, summary.planned, summary.applied), (1, 1, 1, 1, 1, 0))

    def test_apply_validated(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        execute(nb, changes, summary, apply=True, non_interactive=True)
        self.assertEqual(summary.applied, 1)
        self.assertEqual(nb.session.request.call_args.kwargs['json'], {'description': 'Sala B'})
        self.assertFalse(nb.session.apply)

    def test_interactive_denial(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        execute(nb, changes, summary, apply=True, confirm=lambda _: 'não')
        nb.session.request.assert_not_called()

    def test_interactive_acceptance(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        execute(nb, changes, summary, apply=True, confirm=lambda _: 'SIM')
        self.assertEqual(summary.applied, 1)

    def test_changed_since_plan_blocks(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        nb.find_interface.side_effect = lambda *a: {**current(), 'description': 'concorrente'}
        execute(nb, changes, summary, apply=True, non_interactive=True)
        nb.session.request.assert_not_called()
        self.assertEqual(summary.errors, 1)

    def test_apply_revalidates_mutated_payload(self):
        imc, nb = fixture()
        changes, summary = plan(imc, nb)
        changes[0].payload['enabled'] = True
        execute(nb, changes, summary, apply=True, non_interactive=True)
        nb.session.request.assert_not_called()

    def test_up_down_ignored(self):
        for state in ('1', '2', 'up', 'down'):
            imc, nb = fixture()
            imc.iter_interfaces.return_value[0]['operStatus'] = state
            changes, _ = plan(imc, nb)
            self.assertEqual(changes[0].payload, {'description': 'Sala B'})

    def test_no_ip_name_fallback(self):
        imc, nb = fixture()
        imc.iter_devices.return_value = [{'id': 1, 'ip': '192.0.2.1'}]
        changes, summary = plan(imc, nb)
        self.assertFalse(changes)
        nb.find_device.assert_not_called()
        self.assertEqual(summary.skipped, 1)

    def test_duplicate_source_device_no_patch(self):
        imc, nb = fixture()
        imc.iter_devices.return_value *= 2
        changes, summary = plan(imc, nb)
        self.assertFalse(changes)
        self.assertEqual(summary.errors, 2)

    def test_duplicate_source_interface_no_patch(self):
        imc, nb = fixture()
        imc.iter_interfaces.return_value *= 2
        changes, summary = plan(imc, nb)
        self.assertFalse(changes)
        self.assertEqual(summary.errors, 2)

    def test_interface_failure_does_not_stop_next(self):
        imc, nb = fixture()
        imc.iter_interfaces.return_value.append({'ifName': 'Gi2', 'ifIndex': 2, 'ifAlias': 'Sala C'})
        nb.find_interface.side_effect = [PolicyError('ausente'), {**current(), 'id': 21, 'name': 'Gi2'}]
        changes, summary = plan(imc, nb)
        self.assertEqual(len(changes), 1)
        self.assertEqual((summary.interfaces, summary.skipped, summary.errors), (2, 1, 1))

    def test_device_failure_does_not_stop_next(self):
        imc, nb = fixture()
        imc.iter_devices.return_value.append({'id': 2, 'sysName': 'SW-LAB-02'})
        nb.find_device.side_effect = [PolicyError('ausente'), {'id': 10}]
        changes, summary = plan(imc, nb)
        self.assertEqual(len(changes), 1)
        self.assertEqual(summary.devices, 2)

    def test_uncertain_vlan_skips_whole_interface(self):
        imc, nb = fixture()
        imc.get_port_vlans.side_effect = PolicyError('parsing')
        changes, summary = plan(imc, nb)
        self.assertFalse(changes)
        self.assertEqual(summary.skipped, 1)

    def test_synchronized_counts(self):
        imc, nb = fixture()
        imc.iter_interfaces.return_value[0]['ifAlias'] = 'Sala A'
        changes, summary = plan(imc, nb)
        self.assertEqual(summary.synchronized, 1)
        self.assertFalse(changes)

    def test_default_and_contradictory_cli(self):
        self.assertFalse(arguments([]).apply)
        for argv in (['--dry-run', '--apply'], ['--non-interactive']):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                arguments(argv)

class RuntimeTests(unittest.TestCase):
    def test_valid_config(self):
        a, b = configuration(config())
        self.assertTrue(a['verify_ssl'])
        self.assertTrue(b['verify_ssl'])

    def test_missing_and_placeholder_config(self):
        for key in config():
            for value in ('', 'ALTERAR_LOCALMENTE'):
                with self.subTest(key=key, value=value), self.assertRaises(PolicyError):
                    configuration({**config(), key: value})

    def test_invalid_config(self):
        for overrides in ({'IMC_PORT': '0'}, {'IMC_PORT': '65536'}, {'IMC_PORT': 'abc'},
                          {'IMC_PORT': '8080'}, {'IMC_HOST': 'http://invalid'},
                          {'NETBOX_URL': 'https://user:pass@netbox.example.test'},
                          {'NETBOX_URL': 'ftp://netbox.example.test'},
                          {'NETBOX_URL': 'https://netbox.example.test/api'},
                          {'NETBOX_URL': 'https://netbox.example.test:8080'},
                          {'NETBOX_VERIFY_SSL': 'false'}, {'IMC_USE_HTTPS': 'yes'},
                          {'REQUEST_TIMEOUT': '0'}, {'SYNC_INTERVAL': '10'},
                          {'IMC_CA_BUNDLE': '/nonexistent-ca-file'}):
            with self.subTest(overrides=overrides), self.assertRaises(PolicyError):
                configuration({**config(), **overrides})

    def test_log_password_token_headers_cookies_and_url(self):
        f = Redactor('fixture', 'dry-run', ['known_password', 'known_token'])
        msg = """known_password known_token https://user:pass@example.test/ password=unexpected; token=other; Authorization: Bearer abc; Cookie: a=b"""
        value = f.format(logging.LogRecord('pilot', logging.INFO, '', 1, msg, (), None))
        for secret in ('known_password', 'known_token', 'unexpected', 'other', 'Bearer abc', 'a=b', 'user:pass'):
            self.assertNotIn(secret, value)

    def test_log_quoted_json_and_newline(self):
        f = Redactor('fixture', 'dry-run')
        msg = """{"token": "hidden"}\nforged"""
        value = f.format(logging.LogRecord('pilot', logging.INFO, '', 1, msg, (), None))
        self.assertNotIn('hidden', value)
        self.assertNotIn('\n', value)

    def test_env_is_not_executed_and_quotes_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            path.write_text("IMC_PASSWORD='value with spaces'\nIMC_USERNAME='$(id)'\n")
            load_environment(path)
            self.assertEqual(os.environ['IMC_PASSWORD'], 'value with spaces')
            self.assertEqual(os.environ['IMC_USERNAME'], '$(id)')

    def test_concurrent_python_execution_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'lock'
            with execution_lock(lock):
                with self.assertRaisesRegex(PolicyError, 'Outra execução'):
                    with execution_lock(lock):
                        self.fail('Lock was bypassed')

    def test_wrapper_concurrency_blocked_before_python(self):
        import fcntl
        with open(ROOT / '.wrapper.lock', 'a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(['bash', str(ROOT / 'imc/executar_sincronizacao.sh')],
                                    capture_output=True, text=True, env={**os.environ, 'IMC_PYTHON_BIN': '/nonexistent'})
            self.assertEqual(result.returncode, 2)
            self.assertIn('outra execução', result.stderr)

    def test_import_has_no_network(self):
        with patch('requests.sessions.Session.request', side_effect=AssertionError('network')):
            import importlib
            import sincronizacao_imc_netbox
            importlib.reload(sincronizacao_imc_netbox)

if __name__ == '__main__':
    unittest.main()
