import copy
import pytest
from backend.domain import validate
from backend.m1_strategy import TEXT,ENUMS,FLAGS,scope_devices,total_rating
from scripts.build_ci20_pilot import build

def fixture():
    m=build()
    m['project']['system_boundary']={'timezone':'Africa/Johannesburg','scope':'Test only','reference':'TEST','domains':[{'id':'D1','pcc_id':'PCC_01','controller_id':'EMS_MASTER','scope':''}],'status':'DRAFT'}
    r={k:'' for k in TEXT+list(ENUMS)}
    r.update({k:True for k in FLAGS});r.update(domain_id='D1',signature='TEST',status='PENDING')
    m['project']['operating_strategies']={'SIMULATION':[r]}
    return m,r

def test_missing_basis_can_save_only_pending_and_scope_is_correct():
    m,r=fixture();assert validate(m)['valid']
    assert any('策略缺项' in w for w in validate(m)['warnings'])
    devices,owners=scope_devices(m,'SIMULATION','EMS_MASTER')
    assert len(devices)==20 and not owners
    assert total_rating(m,[n for n in devices if n['node_type']=='PV_INVERTER'])==1250
    assert total_rating(m,[n for n in devices if n['node_type']=='BESS'],'capacity','kWh')==2612
    r['status']='APPROVED';assert not validate(m)['valid']

@pytest.mark.parametrize('changes',[
    {'soc_min':'90','soc_max':'20'}, {'charge_limit':'1251'},
    {'pv_mode':'PERCENT','pv_limit':'101'}, {'pv_mode':'KW','pv_limit':'1251'},
    {'bess_mode':'CHARGE_ONLY','discharge_limit':'1'}, {'bess_mode':'DISCHARGE_ONLY','charge_limit':'1'},
    {'export_limit':'5'}, {'priority':'SELF_CONSUMPTION_FIRST'},
    {'cycle_seconds':'5','response_seconds':'1'}, {'stable_seconds':'0'}, {'charge_limit':'NaN'}])
def test_conflicts_rejected(changes):
    m,r=fixture();r.update(changes);assert not validate(m)['valid']

def test_grid_and_control_paths_are_dependencies():
    m,r=fixture();m['project']['operation_modes']=['ISLANDED'];assert not validate(m)['valid']
    m,r=fixture();m['edges']=[e for e in m['edges'] if not(e['edge_type']=='CONTROL' and 'PV_' in e['to_port_id'])]
    assert not validate(m)['valid']

def test_plans_isolate_environments_and_keep_unresolved_capability():
    m,r=fixture();r.update(export_limit='0',charge_limit='500',discharge_limit='500',soc_min='20',soc_max='90')
    m['project']['operating_strategies']['REAL']=[copy.deepcopy(r)]
    r['charge_limit']='600';assert validate(m)['valid']
    assert m['project']['operating_strategies']['REAL'][0]['charge_limit']=='500'
    assert any('实时能力未知' in w for w in validate(m)['warnings'])

def test_duplicate_domain_and_overlapping_bess_pcs_are_not_silently_accepted():
    m,r=fixture();m['project']['operating_strategies']['SIMULATION'].append(copy.deepcopy(r));assert not validate(m)['valid']
    devices,_=scope_devices(m,'SIMULATION','EMS_MASTER');b=next(n for n in devices if n['node_type']=='BESS')
    assert total_rating(m,[b,dict(b,node_type='PCS')]) is None
