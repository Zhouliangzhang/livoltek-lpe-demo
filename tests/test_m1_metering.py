import copy
import pytest
from backend.domain import validate
from backend.m1_metering import FIELDS
from scripts.build_ci20_pilot import build

def fixture():
    m = build()
    r = {k:'' for k in FIELDS}
    r.update(meter_id='METER_PCC', pcc_id='PCC_01', signature='test', status='PENDING')
    m['project']['metering_settings'] = {'SIMULATION':[r]}
    return m, r

def test_missing_evidence_is_draft_not_approved():
    m, r = fixture()
    assert validate(m)['valid']
    assert any('计量缺项' in w for w in validate(m)['warnings'])
    r['status'] = 'APPROVED'
    assert not validate(m)['valid']

@pytest.mark.parametrize('field,value',[('ct_secondary','0'),('pt_primary','-1'),('driver_scale','NaN'),('refresh_seconds','inf'),('input_unit','kWh'),('raw_sign','guess')])
def test_invalid_scaling_and_semantics_rejected(field,value):
    m, r = fixture(); r[field] = value
    assert not validate(m)['valid']

def test_primary_ratio_mismatch_and_direct_input_conflict():
    m, r = fixture()
    r.update(ct_mode='EXTERNAL',ct_primary='4000',ct_secondary='5',meter_ct_ratio='800',read_side='PRIMARY')
    assert validate(m)['valid']
    r['meter_ct_ratio']='400'
    assert any('倍率与铭牌' in e for e in validate(m)['errors'])
    r.update(ct_mode='DIRECT',meter_ct_ratio='1')
    assert any('直接接入' in e for e in validate(m)['errors'])

def test_mapping_and_quality_conflicts():
    m, r = fixture();r['pcc_id']='METER_PCC'
    assert not validate(m)['valid']
    r['pcc_id']='PCC_01';r.update(refresh_seconds='10',stale_seconds='5')
    assert not validate(m)['valid']
    r.update(stale_seconds='20');m['project']['metering_settings']['SIMULATION'].append(copy.deepcopy(r))
    assert not validate(m)['valid']

def test_environment_scoping_and_real_draft_no_promotion():
    m, r = fixture()
    m['project']['metering_settings']['REAL']=[copy.deepcopy(r)]
    m['project']['metering_settings']['OFFLINE']=[copy.deepcopy(r)]
    r.update(driver_scale='1',input_unit='kW')
    assert validate(m)['valid']
    assert m['project']['metering_settings']['REAL'][0]['input_unit']==''
    assert all('待核验' in w for w in validate(m)['warnings'] if '未下发或现场验证' in w)
