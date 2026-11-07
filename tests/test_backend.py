import copy
import pytest
from fastapi.testclient import TestClient
from backend.domain import pilot, validate, load, digest
from backend.main import create_app, flow_state
from backend.sop import generate, seed_templates

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'test.db')) as c:
        yield c

PID='LPE-DEMO-LV01-001'

def test_original_contracts():
    for name in ('lv01-demo.engineering-model.json','lv01-mixed-vendors.engineering-model.json'):
        assert validate(load(name))['valid']
    assert validate(pilot())['valid']

@pytest.mark.parametrize('change', ['reference','domain','cycle','sn','permission','duplicate','telemetry'])
def test_semantic_rejection(change):
    m=pilot()
    if change=='reference': m['edges'][0]['to_port_id']='absent'
    if change=='domain': m['ports'][0]['domain']='DC'
    if change=='cycle': m['nodes'][0]['parent_node_id']=m['nodes'][0]['node_id']
    if change=='sn': m['device_assets'][0]['sn_status']='VERIFIED'
    if change=='permission': m['device_assets'][0]['authorization']['write_allowed']=True
    if change=='duplicate': m['device_models'].append(copy.deepcopy(m['device_models'][0]))
    if change=='telemetry': m['telemetry_bindings'][0]['target_id']='absent'
    assert not validate(m)['valid']

def test_save_history_conflict_and_restart(client):
    p=client.get(f'/api/projects/{PID}').json()
    p['model']['nodes'][0]['name']='Edited PCC'
    payload={'model':p['model'],'expected_revision':p['revision']}
    assert client.post('/api/projects',json=payload).status_code==200
    assert client.post('/api/projects',json=payload).status_code==409
    assert client.get(f'/api/projects/{PID}?revision=1').json()['model']['nodes'][0]['name']!='Edited PCC'
    with TestClient(create_app(client.app.state.store.path)) as second:
        assert second.get(f'/api/projects/{PID}').json()['model']['nodes'][0]['name']=='Edited PCC'

def test_plans_block_production_and_stale_evidence(client):
    plan=client.post(f'/api/projects/{PID}/plans').json()
    assert client.post(f'/api/plans/{plan["id"]}/publish').status_code==403
    task=plan['tasks'][0]
    evidence={'task_id':task['task_id'],'result':'PASS','reviewer':'EPC','note':'test','evidence':{}}
    assert client.post(f'/api/plans/{plan["id"]}/evidence',json=evidence).status_code==409
    evidence['result']='BLOCKED'
    assert client.post(f'/api/plans/{plan["id"]}/evidence',json=evidence).status_code==200
    p=client.get(f'/api/projects/{PID}').json()
    p['model']['nodes'][0]['name']='changed'
    client.post('/api/projects',json={'model':p['model'],'expected_revision':p['revision']})
    assert client.get(f'/api/projects/{PID}/plans').json()[0]['stale']
    assert client.post(f'/api/plans/{plan["id"]}/evidence',json=evidence).status_code==409

def test_template_versions_and_plan_freeze(client):
    old_plan=client.post(f'/api/projects/{PID}/plans').json()
    t=next(x for x in client.get('/api/templates').json() if 'BESS' in x['template_id'])
    body={'expected_version':t['version'],'title':t['title'],'instructions':'Revised guidance','source_document_ref':'DEMO-REVIEW-REF','status':'APPROVED','reviewer':'Engineer','reason':'simulation review'}
    assert client.post('/api/templates/'+t['template_id'],json=body).status_code==200
    new=client.post(f'/api/projects/{PID}/plans').json()
    assert next(x for x in new['tasks'] if x['template_id']==t['template_id'])['template_version']==2
    assert old_plan['tasks'][0]['template_version']==1
    assert client.post('/api/templates/'+t['template_id'],json=body).status_code==409

def test_layout_not_engineering_change():
    m=pilot(); before=digest(m)
    m['view_layout']['positions']['PCC_01']['x']=999
    assert digest(m)==before

def test_rule_scoping_and_safety_gate():
    m=pilot(); m['parameters']=[]
    plan=generate(m,1,seed_templates())
    assert next(t for t in plan['tasks'] if t['risk']=='SAFETY_CRITICAL')['readiness']=='BLOCKED'
    m['edges']=[e for e in m['edges'] if e['edge_id']!='C02']
    plan=generate(m,1,seed_templates())
    assert not any(t['task_id']=='RULE-METER-COMM' for t in plan['tasks'])
    assert all(t['scope_type']=='THIRD_PARTY_INTERFACE' for t in plan['tasks'] if t['task_id'].startswith('INTERFACE-'))

def test_telemetry_age_quality_sign():
    assert flow_state(-20,'GOOD',100,30,clock=110)['reverse']
    assert not flow_state(20,'GOOD',100,30,clock=131)['animate']
    assert not flow_state(20,'BAD',100,30,clock=110)['available']
    assert not flow_state(None,'GOOD',100,30,clock=110)['available']
    assert not flow_state(20,'GOOD',100,30,clock=90)['available']
    assert flow_state(20,'GOOD',100,30,'TO_FROM',clock=110)['reverse']

def test_reviews(client):
    r={'target_id':'PCC_01','reviewer':'EPC','comment':'Confirm boundary','decision':'UNDER_REVIEW','revision':1}
    assert client.post(f'/api/projects/{PID}/reviews',json=r).status_code==200
    assert len(client.get(f'/api/projects/{PID}/reviews').json())==1
    r['target_id']='absent'
    assert client.post(f'/api/projects/{PID}/reviews',json=r).status_code==422
