"""Regressões das etapas e resultados observáveis, com rede bloqueada pelo conftest."""
import copy
from unittest.mock import Mock, patch
import pytest
import requests

from test_imc_netbox_core import fixture, current, response, config
from etapas import stage_arguments, compare_inventory, inspect_switch, main as stage_main
from imc_client import IMCClient, VlanState
from netbox_client import NetBoxClient, NotFound, Ambiguous
from policy import PolicyError
from runtime import configuration
from sincronizacao_imc_netbox import arguments
from sync import plan, execute


def test_lab_filters_before_any_interface_or_netbox_lookup():
    imc, nb = fixture()
    imc.iter_devices.return_value.append({'id': 2, 'sysName': 'SW-FORA'})
    changes, summary = plan(imc, nb, device_name='SW-LAB-01')
    execute(nb, changes, summary, apply=True, non_interactive=True)
    imc.iter_interfaces.assert_called_once_with(1)
    nb.find_device.assert_called_once_with('SW-LAB-01')
    assert summary.devices_filtered == 1 and summary.applied == 1


def test_production_missing_device_is_expected_logged_skip(caplog):
    imc, nb = fixture()
    imc.iter_devices.return_value.append({'id': 2, 'sysName': 'SW-AUSENTE'})
    nb.find_device.side_effect = lambda name: {'id': 10} if name == 'SW-LAB-01' else missing()
    with caplog.at_level('INFO', logger='pilot'):
        changes, summary = plan(imc, nb)
    imc.iter_interfaces.assert_called_once_with(1)
    assert summary.devices == 2 and summary.devices_not_found == 1
    assert summary.errors == 0 and summary.planned == 1
    assert 'SW-AUSENTE' in caplog.text and 'descartado' in caplog.text


def missing():
    raise NotFound('ausente')


def test_production_visits_all_existing_devices():
    imc, nb = fixture()
    imc.iter_devices.return_value.append({'id': 2, 'sysName': 'SW-DOIS'})
    nb.find_device.side_effect = lambda name: {'id': 10 if name == 'SW-LAB-01' else 11}
    nb.find_interface.side_effect = lambda device, name: {
        **current(), 'id': 20 if device == 10 else 21, 'device': {'id': device}}
    changes, summary = plan(imc, nb)
    assert summary.devices_found == 2 and len(changes) == 2
    assert [c.args[0] for c in imc.iter_interfaces.call_args_list] == [1, 2]


def test_unknown_selected_switch_has_no_changes():
    imc, nb = fixture()
    changes, summary = plan(imc, nb, device_name='NOME-ERRADO')
    assert not changes and summary.errors == 1
    imc.iter_interfaces.assert_not_called()
    nb.find_device.assert_not_called()


def test_http_200_without_effect_is_not_applied():
    imc, nb = fixture()
    nb.session.request.side_effect = None
    nb.session.request.return_value = response({})
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary, apply=True, non_interactive=True)
    assert summary.accepted == 1 and summary.applied == 0
    assert summary.unconfirmed == 1 and summary.errors == 1
    assert not nb.session.apply


@pytest.mark.parametrize('persisted', [True, False])
def test_patch_timeout_reconciles_without_retry(persisted):
    imc, nb = fixture()
    state = current()
    nb.find_interface.side_effect = lambda *args: copy.deepcopy(state)
    def send(*args, **kwargs):
        if persisted:
            state.update(kwargs['json'])
        raise requests.Timeout()
    nb.session.request.side_effect = send
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary, apply=True, non_interactive=True)
    assert nb.session.request.call_count == 1
    assert summary.uncertain == 1
    assert summary.applied == int(persisted)
    assert summary.errors == int(not persisted)


def test_post_patch_read_failure_is_unconfirmed():
    imc, nb = fixture()
    nb.find_interface.side_effect = [current(), current(), PolicyError('GET indisponível')]
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary, apply=True, non_interactive=True)
    assert summary.accepted == 1 and summary.applied == 0 and summary.unconfirmed == 1


def test_second_run_after_confirmed_patch_is_idempotent():
    imc, nb = fixture()
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary, apply=True, non_interactive=True)
    assert summary.applied == 1
    nb.session.request.reset_mock()
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary, apply=True, non_interactive=True)
    assert summary.synchronized == 1 and summary.planned == 0
    nb.session.request.assert_not_called()


def test_count_missing_vlan_and_interface_separately():
    imc, nb = fixture()
    nb.find_vlan.side_effect = NotFound('VLAN')
    _, summary = plan(imc, nb)
    assert summary.vlans_not_found == 1 and summary.interfaces_not_found == 0
    imc, nb = fixture()
    nb.find_interface.side_effect = NotFound('interface')
    _, summary = plan(imc, nb)
    assert summary.interfaces_not_found == 1 and summary.vlans_not_found == 0


def test_simulation_count_and_duration():
    imc, nb = fixture()
    changes, summary = plan(imc, nb)
    execute(nb, changes, summary)
    assert summary.interfaces_simulated == 1 and summary.report()['duration_seconds'] >= 0


@pytest.mark.parametrize('argv', [['--apply'], ['--apply', '--device', ' '],
                                 ['--device', 'SW', '--all-devices']])
def test_cli_requires_unambiguous_application_scope(argv):
    with pytest.raises(SystemExit):
        arguments(argv)


@pytest.mark.parametrize('stage', ['inspect', 'simulate', 'apply'])
def test_lab_stages_require_a_switch(stage):
    with pytest.raises(SystemExit):
        stage_arguments(stage, [])


def test_imc_stage_needs_no_netbox_configuration():
    env = {k: v for k, v in config().items() if k.startswith('IMC')}
    imc, nb = configuration(env, service='IMC')
    assert imc['host'] == env['IMC_HOST'] and nb is None


def test_netbox_stage_needs_no_imc_configuration():
    env = {k: v for k, v in config().items() if k.startswith('NETBOX')}
    imc, nb = configuration(env, service='NETBOX')
    assert imc is None and nb['base_url'] == env['NETBOX_URL']


def test_inventory_comparison_does_not_read_interfaces():
    imc, nb = fixture()
    nb.find_device.side_effect = NotFound('ausente')
    assert compare_inventory(imc, nb) == 0
    imc.iter_interfaces.assert_not_called()
    nb.find_interface.assert_not_called()
    nb.session.request.assert_not_called()


def test_inspect_switch_queries_only_selected_device():
    imc, _ = fixture()
    imc.iter_devices.return_value.append({'id': 2, 'sysName': 'SW-FORA'})
    assert inspect_switch(imc, 'SW-LAB-01') == 0
    imc.iter_interfaces.assert_called_once_with(1)


@pytest.mark.parametrize('stage,argv,forwarded', [
    ('simulate', ['--device', 'SW'], ['--device', 'SW', '--dry-run']),
    ('apply', ['--device', 'SW'], ['--device', 'SW', '--apply']),
    ('production', [], ['--all-devices', '--dry-run']),
    ('production', ['--apply', '--non-interactive'], ['--all-devices', '--apply', '--non-interactive']),
])
def test_stage_routes_preserve_scope(stage, argv, forwarded):
    with patch('sincronizacao_imc_netbox.main', return_value=0) as run:
        assert stage_main(stage, argv) == 0
    run.assert_called_once_with(forwarded)


def test_vlan_group_filters_and_checks_response():
    nb = NetBoxClient('https://netbox.example.test', 'fixture', vlan_group_id=3)
    nb.records = Mock(return_value=iter([{'id': 70, 'vid': 7, 'group': {'id': 3}},
                                        {'id': 71, 'vid': 7, 'group': {'id': 4}}]))
    assert nb.find_vlan(7)['id'] == 70
    nb.records.assert_called_once_with('ipam/vlans/', vid=7, group_id=3)
    nb.records.return_value = iter([{'id': 71, 'vid': 7, 'group': {'id': 4}}])
    with pytest.raises(NotFound):
        nb.find_vlan(7)


@pytest.mark.parametrize('group', ['0', '-1', 'abc'])
def test_invalid_vlan_group(group):
    with pytest.raises(PolicyError):
        configuration({**config(), 'NETBOX_VLAN_GROUP_ID': group})


def vlan_client(mode, unavailable):
    imc = IMCClient('imc.example.test')
    def records(endpoint, element, **filters):
        if endpoint in unavailable:
            raise PolicyError('Endpoint indisponível')
        return iter({
            'vlan/portvlan': [{'vlanId': 7}],
            'vlan/' + mode: [{'ifIndex': 1, 'pvid': 7}],
        }.get(endpoint, []))
    imc.records = Mock(side_effect=records)
    return imc


def test_confirmed_access_survives_unavailable_other_modules():
    imc = vlan_client('access', {'vlan/trunk', 'vlan/hybrid'})
    assert imc.get_port_vlans(1, 1) == VlanState('access', 7, ())
    imc.get_port_vlans(1, 1)
    assert sum(c.args[0] == 'vlan/access' for c in imc.records.call_args_list) == 1


def test_trunk_preserved_when_classification_incomplete():
    imc = vlan_client('trunk', {'vlan/hybrid'})
    with pytest.raises(PolicyError):
        imc.get_port_vlans(1, 1)
