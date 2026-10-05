import copy
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
from wug.client import WUGClient
from wug.models import Device, Interface, MISSING, VlanState, vlan_state
from wug.netbox_client import NetBoxClient, NotFound, Ambiguous, PatchUncertain
from wug.policy import PolicyError, RestrictedSession, safe_origin
from wug.profile import validate_profile
from wug.runtime import configuration, load_environment, execution_lock, Redactor, write_report
from wug.sync import plan, execute, differences, snapshot
from wug.__main__ import arguments

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def profile():
    p = json.loads((ROOT/'config/wug.example.json').read_text())
    # Contrato SINTÉTICO: não comprova um endpoint da instalação real.
    p['interfaces'].update(endpoint='devices/{device_id}/interfaces', items_path='data.ports',
        id_field='id', name_field='ifName', description_field='ifAlias')
    p['validated'] = True
    p.update(product_version='fixture', validated_by='fixture', validated_at='2026-10-05', evidence='synthetic fixture only')
    return p

def response(data, status=200):
    r = Mock(status_code=status)
    r.json.return_value = data
    return r

def page(rows, key='devices', **paging):
    return {'data': {key: rows}, 'paging': paging}

def current():
    return {'id': 20, 'name': 'Gi1', 'device': {'id': 10}, 'description': 'Sala A',
            'mode': {'value': 'access'}, 'untagged_vlan': {'id': 70}, 'tagged_vlans': []}

def fixture():
    source = Mock()
    source.iter_devices.return_value = [Device('1', 'SW-LAB-01')]
    source.iter_interfaces.return_value = [Interface('1', 'Gi1', 'Sala B')]
    nb = NetBoxClient('https://netbox.example.test', 'fixture')
    state = current()
    nb.find_device = Mock(return_value={'id': 10, 'name': 'SW-LAB-01'})
    nb.find_interface = Mock(side_effect=lambda *a: copy.deepcopy(state))
    nb.find_vlan = Mock(side_effect=lambda v: {'id': v * 10})
    def send(method, url, **kwargs):
        if method == 'PATCH':
            state.update(kwargs['json'])
        return response(copy.deepcopy(state))
    nb.session.request = Mock(side_effect=send)
    return source, nb, state

@pytest.mark.parametrize('method', ['PUT', 'PATCH', 'DELETE', 'POST'])
@pytest.mark.parametrize('endpoint', ['devices/1/interfaces', 'devices/1/config', 'devices/-/poll', 'device-groups/0/devices'])
def test_wug_mutations_never_reach_transport(profile, method, endpoint):
    c = WUGClient('https://wug.example.test:9644', profile, token='fixture')
    c.session.request = Mock()
    with pytest.raises(PolicyError):
        c._request(method, endpoint)
    c.session.request.assert_not_called()

@pytest.mark.parametrize('url', ['https://evil.example.test/api/v1/product',
 'https://wug.example.test/api/v1/../token', 'https://wug.example.test/api/v1/%2e%2e/token',
 'https://wug.example.test/api/v1/devices/1/poll', 'https://wug.example.test/api/v1/product#x'])
def test_wug_get_destinations_blocked(profile, url):
    c = WUGClient('https://wug.example.test', profile, token='fixture')
    with pytest.raises(PolicyError):
        c.session.get(url)

def test_authentication_is_only_post(profile, monkeypatch):
    c = WUGClient('https://wug.example.test', profile, username='fixture', password='fixture')
    transport = Mock(side_effect=[response({'access_token': 'fixturetoken'}), response({'version': 'fixture'})])
    monkeypatch.setattr(requests.Session, 'request', transport)
    c.login()
    assert [x.args[0] for x in transport.call_args_list] == ['POST', 'GET']
    assert transport.call_args_list[0].args[1].endswith('/api/v1/token')
    assert transport.call_args_list[0].kwargs['allow_redirects'] is False
    c.logout()
    assert transport.call_count == 2

def test_prepared_post_cannot_bypass_policy(profile):
    c = WUGClient('https://wug.example.test', profile)
    req = requests.Request('POST', c.base_url+'devices/1/interfaces', data={'grant_type':'password','username':'x','password':'x'}).prepare()
    with pytest.raises(PolicyError):
        c.session.send(req)
    req = requests.Request('POST', c.base_url+'token', json={'other': 1}).prepare()
    with pytest.raises(PolicyError):
        c.session.send(req)

def test_token_does_not_require_password_post(profile):
    c = WUGClient('https://wug.example.test', profile, token='fixture')
    c.session.request = Mock(return_value=response({}))
    c.login()
    assert c.session.request.call_args.args[0] == 'GET'

@pytest.mark.parametrize('status', [301, 302, 400, 401, 403, 500])
def test_wug_error_does_not_return_secret_body(profile, status):
    c = WUGClient('https://wug.example.test', profile, token='fixture')
    c.session.request = Mock(return_value=response({'password': 'secret'}, status))
    with pytest.raises(PolicyError) as exc:
        c.login()
    assert 'secret' not in str(exc.value)

def test_cursor_pagination_and_exact_mapping(profile):
    profile['device_map'] = {'2': 'SW-LAB-02'}
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(side_effect=[page([{'id':'1','name':'SW-LAB-01'}], nextPageId='next'), page([{'id':'2','name':'display'}])])
    assert list(c.iter_devices()) == [Device('1', 'SW-LAB-01'), Device('2', 'SW-LAB-02')]
    assert c._request.call_args.kwargs['params'] == {'pageId': 'next'}
    assert c.evidence[0]['pages'] == 2

@pytest.mark.parametrize('pages', [
    [{'data': {'devices': []}}],
    [page([{'id': '1', 'name': 'A'}], nextPageId='x'), page([{'id': '1', 'name': 'A'}])],
    [page([{'id': '1', 'name': 'A'}], nextPageId='x'), page([{'id': '2', 'name': 'B'}], nextPageId='x')],
    [page([], nextPageId='x')],
    [page([{'name': 'A'}])],
])
def test_partial_or_duplicate_inventory_rejected(profile, pages):
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(side_effect=pages)
    with pytest.raises(PolicyError):
        list(c.iter_devices())
    assert not c.evidence

def test_offset_and_none_pagination(profile):
    cfg = profile['devices']
    cfg['pagination'] = {'mode':'offset','parameter':'offset','limit_parameter':'limit','total_path':'total'}
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(side_effect=[{'total':2, **page([{'id':1,'name':'A'}])}, {'total':2, **page([{'id':2,'name':'B'}])}])
    assert len(list(c.iter_devices())) == 2
    cfg['pagination'] = {'mode':'none','complete_path':'complete'}
    c._request = Mock(return_value={'complete':False, **page([])})
    with pytest.raises(PolicyError): list(c.iter_devices())
    c._request.return_value['complete'] = True
    assert list(c.iter_devices()) == []

@pytest.mark.parametrize('value', [None, '', '  ', 42, False])
def test_missing_null_empty_description_preserved(profile, value):
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(return_value=page([{'id':'1','ifName':'Gi1','ifAlias':value}], 'ports'))
    i = list(c.iter_interfaces('1'))[0]
    assert i.description is MISSING and i.issues

def test_explicit_clear_only_empty_string(profile):
    profile['allow_description_clear'] = True
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(return_value=page([{'id':'1','ifName':'Gi1','ifAlias':''}], 'ports'))
    assert list(c.iter_interfaces('1'))[0].description == ''
    c._request.return_value['data']['ports'][0]['ifAlias'] = None
    assert list(c.iter_interfaces('1'))[0].description is MISSING

def test_vlan_mapping_is_explicit_and_field_independent(profile):
    profile['interfaces']['vlans'] = dict(enabled=True, mode_field='mode', untagged_field='native', tagged_field='tags', mode_map={'trunk':'tagged'})
    c = WUGClient('https://wug.example.test', profile)
    c._request = Mock(return_value=page([{'id':'1','ifName':'Gi1','ifAlias':'Sala B','mode':'trunk','native':7,'tags':[8,9]}], 'ports'))
    iface = list(c.iter_interfaces('1'))[0]
    assert iface.vlans == VlanState('tagged',7,(8,9))
    c._request.return_value['data']['ports'][0]['tags'] = None
    iface = list(c.iter_interfaces('1'))[0]
    assert iface.vlans is None and iface.description == 'Sala B'

@pytest.mark.parametrize('mode,native,tags', [('access',None,[]),('access',7,[8]),('tagged',7,[7]),('hybrid',7,[]),('tagged',0,[]),('tagged',7,[True])])
def test_invalid_vlan_states(mode,native,tags):
    with pytest.raises(PolicyError): vlan_state(mode,native,tags)

def test_default_profile_blocks_interface_and_apply():
    p = json.loads((ROOT/'config/wug.example.json').read_text())
    validate_profile(p)
    with pytest.raises(PolicyError): validate_profile(p, interfaces=True)
    with pytest.raises(PolicyError): validate_profile(p, apply=True)

@pytest.mark.parametrize('value', ['https://host.example.test', '../interfaces', 'devices/{device_id}/poll', 'devices/{device_id}/interfaces?x=1'])
def test_profile_blocks_unsafe_endpoint(profile, value):
    profile['interfaces']['endpoint'] = value
    with pytest.raises(PolicyError): validate_profile(profile)

@pytest.mark.parametrize('field', ['enabled','status','type','ip_addresses','mac_address','unknown'])
def test_netbox_payload_allowlist(field):
    nb = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
    nb.session.request = Mock()
    with pytest.raises(PolicyError): nb.patch_interface(1, {'description':'ok',field:True})
    nb.session.request.assert_not_called()

@pytest.mark.parametrize('method,endpoint', [('POST','dcim/interfaces/'),('PUT','dcim/interfaces/1/'),('DELETE','dcim/interfaces/1/'),('PATCH','dcim/devices/1/'),('PATCH','dcim/interfaces/')])
def test_netbox_wrong_operations(method,endpoint):
    nb = NetBoxClient('https://netbox.example.test', 'fixture', apply=True)
    nb.session.request = Mock()
    with pytest.raises(PolicyError): nb._request(method,endpoint,json={'description':'ok'})
    nb.session.request.assert_not_called()

def test_description_updates_without_vlan_data():
    source, nb, _ = fixture()
    changes, summary = plan(source, nb)
    assert changes[0].payload == {'description':'Sala B'}
    nb.find_vlan.assert_not_called()
    execute(nb, changes, summary)
    nb.session.request.assert_not_called()
    assert summary.simulated == 1

def test_missing_vlan_preserves_vlan_but_updates_description():
    _, nb, _ = fixture()
    nb.find_vlan.side_effect = NotFound('VLAN não encontrada')
    before, payload, issues = differences(Interface('1','Gi1','Sala B',VlanState('access',9,())), current(), nb)
    assert payload == {'description':'Sala B'} and issues

def test_vlan_only_and_native_none():
    _, nb, _ = fixture()
    _, payload, issues = differences(Interface('1','Gi1',MISSING,VlanState('tagged',None,(8,))), current(), nb)
    assert payload == {'mode':'tagged','untagged_vlan':None,'tagged_vlans':[80]} and not issues

def test_selected_device_filter_and_missing_device():
    source, nb, _ = fixture()
    source.iter_devices.return_value += [Device('2','OUTSIDE')]
    changes, summary = plan(source,nb,device_name='SW-LAB-01')
    assert summary.devices_filtered == 1 and len(changes) == 1
    source.iter_interfaces.assert_called_once_with('1')
    nb.find_device.side_effect = NotFound()
    changes, summary = plan(source,nb,device_name='SW-LAB-01')
    assert not changes and summary.devices_not_found == 1

@pytest.mark.parametrize('kind', ['device','interface','empty'])
def test_ambiguous_or_empty_inventory_no_application(kind):
    source,nb,_ = fixture()
    if kind == 'device': source.iter_devices.return_value *= 2
    if kind == 'interface': source.iter_interfaces.return_value *= 2
    if kind == 'empty':
        source.iter_devices.return_value=[]
        with pytest.raises(PolicyError): plan(source,nb)
        return
    changes,summary=plan(source,nb)
    assert not changes and summary.errors

def test_apply_checkpoints_and_idempotency():
    source,nb,_=fixture()
    changes,summary=plan(source,nb)
    events=[]
    execute(nb,changes,summary,apply=True,non_interactive=True,checkpoint=lambda:events.append(changes[0].status))
    assert summary.applied==1 and events==['sending','confirmed'] and nb.session.apply is False
    assert plan(source,nb)[0]==[]

@pytest.mark.parametrize('persisted',[True,False])
def test_timeout_reconciles_without_resend(persisted):
    source,nb,state=fixture()
    changes,summary=plan(source,nb)
    def uncertain(*args):
        if persisted: state.update(changes[0].payload)
        raise PatchUncertain()
    nb.patch_interface=Mock(side_effect=uncertain)
    execute(nb,changes,summary,apply=True,non_interactive=True)
    assert nb.patch_interface.call_count==1 and summary.uncertain==1
    assert summary.applied==int(persisted)
    assert changes[0].status==('confirmed' if persisted else 'unconfirmed')

def test_concurrent_change_and_partial_plan_blocked():
    source,nb,state=fixture()
    changes,summary=plan(source,nb)
    state['description']='Changed concurrently'
    execute(nb,changes,summary,apply=True,non_interactive=True)
    nb.session.request.assert_not_called()
    assert changes[0].status=='blocked'
    with pytest.raises(PolicyError): execute(nb,changes,summary,apply=True,non_interactive=True)

def test_checkpoint_failure_before_patch_blocks_write():
    source,nb,_=fixture()
    changes,summary=plan(source,nb)
    with pytest.raises(OSError):
        execute(nb,changes,summary,apply=True,non_interactive=True,checkpoint=Mock(side_effect=OSError()))
    nb.session.request.assert_not_called()
    assert nb.session.apply is False

def test_operator_cancel():
    source,nb,_=fixture()
    changes,summary=plan(source,nb)
    execute(nb,changes,summary,apply=True,confirm=lambda _: 'NAO')
    assert summary.cancelled and not nb.session.request.called

@pytest.mark.parametrize('argv',[['sync'], ['sync','--apply'], ['sync','--device',''], ['inspect'], ['check-wug','--apply'], ['sync','--device','A','--non-interactive'], ['sync','--device','A','--dry-run','--apply']])
def test_cli_scope_and_apply(argv):
    with pytest.raises(SystemExit): arguments(argv)

@pytest.mark.parametrize('url',['http://example.test','https://user:pass@example.test','https://example.test/api','https://example.test?x=1','https://example.test/#x'])
def test_insecure_origins(url):
    with pytest.raises(PolicyError): safe_origin(url)

def test_config_services_are_independent():
    wug,nb=configuration({'WUG_URL':'https://wug.example.test','WUG_TOKEN':'fixture'},service='WUG')
    assert nb is None and wug['token']=='fixture'
    wug,nb=configuration({'NETBOX_URL':'https://nb.example.test','NETBOX_TOKEN':'fixture'},service='NETBOX')
    assert wug is None and nb['token']=='fixture'

def test_reports_atomic_and_restricted(tmp_path):
    p=tmp_path/'r.json'
    write_report(p,{'changes':[{'before':{'description':'A'},'payload':{'description':'B'}}]})
    assert json.loads(p.read_text())['changes'][0]['before']['description']=='A'
    assert p.stat().st_mode & 0o777==0o600
    assert not p.with_suffix('.tmp').exists()

def test_lock_and_env_not_executed(tmp_path,monkeypatch):
    p=tmp_path/'env'
    p.write_text('WUG_TOKEN="$(echo unsafe)"\n')
    monkeypatch.delenv('WUG_TOKEN',raising=False)
    load_environment(p)
    import os
    assert os.environ['WUG_TOKEN']=='$(echo unsafe)'
    with execution_lock(tmp_path/'lock'):
        with pytest.raises(PolicyError):
            with execution_lock(tmp_path/'lock'): pass


def test_netbox_pagination_group_and_ambiguity():
    nb=NetBoxClient('https://netbox.example.test','fixture',vlan_group_id=3)
    nb._get=Mock(side_effect=[{'results':[{'id':1,'vid':7,'group':{'id':3}}],'next':'more'},
                              {'results':[{'id':2,'vid':7,'group':{'id':3}}],'next':None}])
    with pytest.raises(Ambiguous): nb.find_vlan(7)
    assert nb._get.call_args.kwargs['params']['group_id']==3
    nb._get=Mock(return_value={'results':[{'id':1,'vid':7,'group':{'id':4}}],'next':None})
    with pytest.raises(NotFound): nb.find_vlan(7)


def test_netbox_prepared_bypass_and_dry_run():
    nb=NetBoxClient('https://netbox.example.test','fixture')
    with pytest.raises(PolicyError): nb.patch_interface(1,{'description':'x'})
    nb.session.apply=True
    req=requests.Request('PATCH',nb.base_url+'dcim/interfaces/1/',json={'enabled':True}).prepare()
    with pytest.raises(PolicyError): nb.session.send(req)


def test_redactor_masks_credentials_and_newlines():
    import logging
    formatter=Redactor('fixture','test',['supersecret'])
    record=logging.LogRecord('test',logging.INFO,'',0,'password=supersecret\nvalue',(),None)
    result=formatter.format(record)
    assert 'supersecret' not in result and '\n' not in result


def test_all_collections_finished_before_any_patch():
    source,nb,_=fixture()
    source.iter_devices.return_value=[Device('1','A'),Device('2','B')]
    source.iter_interfaces.side_effect=[[Interface('1','Gi1','New')],PolicyError('coleta incompleta')]
    changes,summary=plan(source,nb)
    assert changes and summary.errors
    with pytest.raises(PolicyError): execute(nb,changes,summary,apply=True,non_interactive=True)
    nb.session.request.assert_not_called()


def test_cli_end_to_end_offline(profile,tmp_path,monkeypatch):
    import wug.__main__ as cli
    source,nb,_=fixture()
    source.evidence=[{'endpoint':'fixture','pages':1,'records':1,'complete':True}]
    monkeypatch.setattr(cli,'ROOT',tmp_path)
    monkeypatch.setattr(cli,'setup_logging',lambda _:Mock(secrets=[]))
    monkeypatch.setattr(cli,'load_environment',lambda:None)
    monkeypatch.setattr(cli,'execution_lock',lambda:execution_lock(tmp_path/'lock'))
    monkeypatch.setattr(cli,'configuration',lambda **kw: ({'base_url':'https://wug.example.test'},{'base_url':'https://nb.example.test','token':'fixture'}))
    monkeypatch.setattr(cli,'load_profile',lambda _:profile)
    monkeypatch.setattr(cli,'WUGClient',lambda **kw:source)
    monkeypatch.setattr(cli,'NetBoxClient',lambda **kw:nb)
    assert cli.main(['sync','--device','SW-LAB-01','--dry-run'])==0
    nb.session.request.assert_not_called()
    assert cli.main(['sync','--device','SW-LAB-01','--apply','--non-interactive'])==0
    reports=[json.loads(p.read_text()) for p in (tmp_path/'relatorios').glob('*.json')]
    applied=next(r for r in reports if r['mode']=='apply')
    assert applied['changes'][0]['status']=='confirmed'
    assert applied['changes'][0]['before']['description']=='Sala A'
    assert 'fixture' not in json.dumps(applied.get('credentials',{}))
    source.logout.assert_called()


def test_cli_apply_unvalidated_profile_before_network(profile,tmp_path,monkeypatch):
    import wug.__main__ as cli
    profile['validated']=False
    monkeypatch.setattr(cli,'setup_logging',lambda _:Mock(secrets=[]))
    monkeypatch.setattr(cli,'load_environment',lambda:None)
    monkeypatch.setattr(cli,'execution_lock',lambda:execution_lock(tmp_path/'lock'))
    monkeypatch.setattr(cli,'configuration',lambda **kw: ({'base_url':'https://wug.example.test'},None))
    monkeypatch.setattr(cli,'load_profile',lambda _:profile)
    constructor=Mock()
    monkeypatch.setattr(cli,'WUGClient',constructor)
    assert cli.main(['sync','--device','A','--apply','--non-interactive'])==2
    constructor.assert_not_called()


def test_legacy_entries_exit_without_network():
    import subprocess
    import sys
    for path in ['sincronizacao_imc_netbox.py','imc/sincronizacao_imc_netbox.py','imc/aplicar_switch.py']:
        result=subprocess.run([sys.executable,str(ROOT/path)],text=True,capture_output=True)
        assert result.returncode!=0 and 'desativado' in result.stderr


def test_page_limits_fail_closed(profile):
    c=WUGClient('https://wug.example.test',profile,max_pages=1)
    c._request=Mock(return_value=page([{'id':1,'name':'A'}],nextPageId='x'))
    with pytest.raises(PolicyError): list(c.iter_devices())
    c=WUGClient('https://wug.example.test',profile,max_records=1)
    c._request=Mock(return_value=page([{'id':1,'name':'A'},{'id':2,'name':'B'}]))
    with pytest.raises(PolicyError): list(c.iter_devices())

@pytest.mark.parametrize('target',['wug','netbox'])
def test_clients_cannot_disable_tls(profile,target):
    with pytest.raises(PolicyError):
        if target=='wug': WUGClient('https://wug.example.test',profile,verify_ssl=False)
        else: NetBoxClient('https://nb.example.test','fixture',verify_ssl=False)
