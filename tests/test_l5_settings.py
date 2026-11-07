import copy
import pytest
from backend.domain import pilot, validate
from backend.l5_settings import CATALOG, applicable

def entry(m, key, planned=None, actual=None):
    node=next(n for n in m['nodes'] if n['node_id']=='BESS_01')
    asset=next(a for a in m['device_assets'] if a['asset_id']==node['device_asset_id'])
    device=next(d for d in m['device_models'] if d['model_id']==asset['model_id'])
    record=dict(planned=planned,actual=actual,reference_doc='',model_id=device['model_id'],master_data_version=device['master_data_version'],template_version=CATALOG['version'])
    node['attributes'].setdefault('l5_settings',{})[key]=record
    return record

def test_l5_candidate_data_remains_pending():
    m=pilot();entry(m,'soc_min',20,20);entry(m,'ip_address','192.0.2.10','192.0.2.10')
    result=validate(m)
    assert result['valid'],result['errors']
    assert any('manufacturer confirmation' in w for w in result['warnings'])

@pytest.mark.parametrize('key,value',[('soc_min',101),('soc_min',True),('ip_address','999.1.1.1'),('service_port',70000),('charge_power_limit',-1)])
def test_l5_invalid_types_and_universal_format_bounds(key,value):
    m=pilot();entry(m,key,value)
    assert not validate(m)['valid']

def test_l5_cross_value_conflict_and_stale_version():
    m=pilot();entry(m,'soc_min',90);entry(m,'soc_max',20)
    assert any('SOC minimum exceeds' in e for e in validate(m)['errors'])
    m=pilot();record=entry(m,'soc_min',20);record['master_data_version']='OLD'
    assert validate(m)['valid']
    assert any('version changed' in w for w in validate(m)['warnings'])

def test_mode_change_keeps_old_values_as_inactive():
    m=pilot();node=next(n for n in m['nodes'] if n['node_id']=='BESS_01')
    entry(m,'charge_schedule','reference-only')
    assert 'charge_schedule' in {d['key'] for d in applicable(m,node)}
    m['project']['operation_modes']=['OFF_GRID']
    assert 'reserve_soc' in {d['key'] for d in applicable(m,node)}
    assert 'charge_schedule' not in {d['key'] for d in applicable(m,node)}
    assert any('no longer applicable' in w for w in validate(m)['warnings'])
    assert node['attributes']['l5_settings']['charge_schedule']['planned']=='reference-only'
