import copy
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.m1_baseline import ScopeRequest,build_preview
from scripts.build_ci20_pilot import build

@pytest.fixture
def setup(tmp_path):
    app=create_app(tmp_path/'delivery.db');db=app.state.store;m=build()
    m['project']['system_boundary']={'timezone':'Africa/Johannesburg','scope':'Test only','reference':'TEST','domains':[{'id':'D1','pcc_id':'PCC_01','controller_id':'EMS_MASTER','scope':''}],'status':'DRAFT'}
    ports=['EMS_MASTER.PV_RS485','PV_01.RS485']
    m['project']['communication_settings']={'SIMULATION':[dict(id='|'.join(ports),domain='RS485',ports=ports,signature='TEST_ONLY',shared={},devices={'PV_01.RS485':{'address':'1'}},reference='',status='PENDING')]}
    saved=db.save(m,0);p=m['project']['project_id'];client=TestClient(app)
    req=dict(expected_revision=1,environment='SIMULATION',domain_id='D1',scope_type='FULL',selected_ids=[])
    v=client.post(f'/api/projects/{p}/config-baselines/preview',json=req).json()
    b=client.post(f'/api/projects/{p}/config-baselines/freeze',json={**req,'author':'TEST','expected_hash':v['content_hash']}).json()
    return client,db,p,b

def request(b,scenario='MATCH',action='REHEARSE'):
    return dict(baseline_id=b['id'],environment=b['environment'],request_id='test-request-1234',action=action,scenario=scenario,fault_device='PV_01' if scenario!='MATCH' else '')

def test_missing_approval_blocks_deploy_without_any_commands(setup):
    c,db,p,b=setup
    check=c.get(f'/api/projects/{p}/config-tasks/preflight/{b["id"]}?environment=SIMULATION').json()
    assert not check['can_deploy'] and check['can_rehearse']
    r=c.post(f'/api/projects/{p}/config-tasks',json=request(b,action='DEPLOY')).json()
    assert r['status']=='BLOCKED' and r['devices']==[]
    assert r['controller_config']=='NOT_SENT' and r['events'][0]['stage']=='BLOCKED'

@pytest.mark.parametrize('scenario,state',[('MATCH','SIM_CANDIDATE_MATCH'),('DIFFERENCE','SIM_DIFFERENCE'),('READ_FAILED','SIM_READ_FAILED'),('UNSUPPORTED','SIM_UNSUPPORTED'),('REJECTED','REJECTED'),('ACK_LOST','ACK_UNKNOWN'),('INTERRUPTED','INTERRUPTED')])
def test_per_device_rehearsal_never_creates_actual_or_approved_values(setup,scenario,state):
    c,db,p,b=setup;response=c.post(f'/api/projects/{p}/config-tasks',json=request(b,scenario));assert response.status_code==200,response.text
    r=response.json();d=next(d for d in r['devices'] if d['node_id']=='PV_01')
    assert d['status']==state
    assert all(v['actual'] is None and v['approved'] is None for device in r['devices'] for v in device['parameters'])
    assert not r['applied'] and not r['approved'] and r['actual_state']=='UNKNOWN'
    assert r['strategy_activation']=='NOT_ACTIVATED' and r['rollback']=='NOT_ATTEMPTED'
    if scenario=='DIFFERENCE':assert d['command']=='SIM_ACK' and d['parameters'][0]['planned']!=d['parameters'][0]['simulated_readback']
    if scenario in ('ACK_LOST','INTERRUPTED'):assert any(v['status']=='NOT_ATTEMPTED' for v in r['devices'])
    assert db.record(b['id'])==b

def test_idempotent_request_resume_and_changed_payload_conflict(setup):
    c,db,p,b=setup;body=request(b,'DIFFERENCE');r=c.post(f'/api/projects/{p}/config-tasks',json=body).json()
    assert c.post(f'/api/projects/{p}/config-tasks',json=body).json()==r
    assert len(db.records('m1_delivery_task',p))==1
    assert c.get(f'/api/projects/{p}/config-tasks/{r["id"]}?environment=SIMULATION').json()==r
    body['scenario']='READ_FAILED';assert c.post(f'/api/projects/{p}/config-tasks',json=body).status_code==409

def test_stale_baseline_and_wrong_environment_rejected(setup):
    c,db,p,b=setup;body=request(b);body['environment']='REAL'
    assert c.post(f'/api/projects/{p}/config-tasks',json=body).status_code==409
    m=db.get(p)['model'];m['project']['name']='new';db.save(m,1)
    assert c.post(f'/api/projects/{p}/config-tasks',json=request(b)).status_code==409

def test_task_history_isolated_and_unknown_fault_device_rejected(setup):
    c,db,p,b=setup;r=c.post(f'/api/projects/{p}/config-tasks',json=request(b)).json()
    assert c.get(f'/api/projects/{p}/config-tasks?environment=REAL').json()==[]
    assert c.get(f'/api/projects/{p}/config-tasks/{r["id"]}?environment=REAL').status_code==404
    body=request(b,'DIFFERENCE');body.update(request_id='new-request-123',fault_device='NOT_IN_SCOPE')
    assert c.post(f'/api/projects/{p}/config-tasks',json=body).status_code==422

def test_tampered_archive_is_not_executed(setup):
    c,db,p,b=setup;bad=copy.deepcopy(b);bad['snapshot']['scope']['target_ids']=[]
    with db.db() as conn:conn.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(bad),b['id']))
    assert c.post(f'/api/projects/{p}/config-tasks',json=request(b)).status_code==409

def test_read_only_never_sends_mock_write(setup):
    c,db,p,b=setup;req=dict(expected_revision=1,environment='SIMULATION',domain_id='D1',scope_type='READ_ONLY',selected_ids=[])
    v=c.post(f'/api/projects/{p}/config-baselines/preview',json=req).json();b=c.post(f'/api/projects/{p}/config-baselines/freeze',json={**req,'author':'TEST','expected_hash':v['content_hash']}).json()
    r=c.post(f'/api/projects/{p}/config-tasks',json=request(b)).json()
    assert all(d['command']=='NOT_REQUESTED' for d in r['devices'])
    assert not any(e['stage']=='ACK' for e in r['events'])
