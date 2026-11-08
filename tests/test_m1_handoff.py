import copy
import json
from test_m1_delivery import setup,request
from backend.m1_handoff import checked_package
from fastapi import HTTPException
import pytest

def body(b,task=''):
    return dict(baseline_id=b['id'],environment=b['environment'],task_id=task)

def test_handoff_preserves_evidence_and_not_a_pass(setup):
    c,db,p,b=setup
    t=c.post(f'/api/projects/{p}/config-tasks',json=request(b,'DIFFERENCE')).json()
    r=c.post(f'/api/projects/{p}/commissioning-basis',json=body(b,t['id']))
    assert r.status_code==200,r.text
    r=r.json();assert r['task']==t and r['baseline']==b
    assert not r['control_allowed'] and not r['commissioning_passed'] and not r['sat_passed']
    assert any('PV_01' in i['objects'] for i in r['issues'])
    assert c.post(f'/api/projects/{p}/commissioning-basis',json=body(b,t['id'])).json()==r
    assert len(db.records('m1_commissioning_basis',p))==1
    assert c.get(f'/api/projects/{p}/commissioning-basis?environment=REAL').json()==[]
    assert c.get(f'/api/projects/{p}/commissioning-basis/{r["id"]}?environment=REAL').status_code==409

def test_wrong_task_stale_and_tamper(setup):
    c,db,p,b=setup
    q=body(b);q['environment']='REAL'
    assert c.post(f'/api/projects/{p}/commissioning-basis',json=q).status_code==409
    assert c.post(f'/api/projects/{p}/commissioning-basis',json=body(b,b['id'])).status_code==409
    r=c.post(f'/api/projects/{p}/commissioning-basis',json=body(b)).json()
    m=db.get(p)['model'];m['project']['name']='changed';db.save(m,1)
    assert c.post(f'/api/projects/{p}/commissioning-basis',json=body(b)).status_code==409
    detail=c.get(f'/api/projects/{p}/commissioning-basis/{r["id"]}?environment=SIMULATION').json()
    assert detail['stale'] and detail['baseline']==b
    with pytest.raises(HTTPException):checked_package(db,p,r['id'],'SIMULATION')
    bad=copy.deepcopy(r);bad['control_allowed']=True
    with db.db() as con:con.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(bad),r['id']))
    assert c.get(f'/api/projects/{p}/commissioning-basis/{r["id"]}?environment=SIMULATION').status_code==409

def test_m2_session_freezes_inherited_reference_and_blocks_control(setup):
    c,db,p,b=setup
    r=c.post(f'/api/projects/{p}/commissioning-basis',json=body(b)).json()
    response=c.post(f'/api/projects/{p}/plans',json={})
    assert response.status_code==200,response.text
    plan=response.json();pid=plan['id']
    page=c.get(f'/api/plans/{pid}/meter-workflow?mode=SIMULATION').json()
    route=page['routes'][0]
    data=dict(mode='SIMULATION',edge_id=route['edge_id'],acknowledged=True,operator='Test',reference='SIM only',basis_id=r['id'])
    s=c.post(f'/api/plans/{pid}/meter-workflow',json=data)
    assert s.status_code==200,s.text
    s=s.json();assert s['m1_basis']==r and s['basis_id']==r['id']
    ctrl=c.post(f'/api/plans/{pid}/pv-control',json=dict(mode='SIMULATION',session_id=s['id'],request_id='handoff-control-test',scenario='normal',acknowledged=True))
    assert ctrl.status_code==409,ctrl.text
    assert not db.records('pv_control',s['id'])
    data['mode']='REAL';assert c.post(f'/api/plans/{pid}/meter-workflow',json=data).status_code==409

@pytest.mark.parametrize('env',['OFFLINE','REAL'])
def test_environment_specific_preparation_never_releases_tests(setup,env):
    c,db,p,b=setup
    req=dict(expected_revision=1,environment=env,domain_id='D1',scope_type='FULL',selected_ids=[])
    preview=c.post(f'/api/projects/{p}/config-baselines/preview',json=req).json()
    frozen=c.post(f'/api/projects/{p}/config-baselines/freeze',json={**req,'author':'TEST','expected_hash':preview['content_hash']}).json()
    r=c.post(f'/api/projects/{p}/commissioning-basis',json=body(frozen)).json()
    assert r['environment']==env and not r['control_allowed'] and not r['commissioning_passed']
    assert r['field_result'] is None and r['task'] is None
    assert c.get(f'/api/projects/{p}/commissioning-basis?environment=SIMULATION').json()==[]
