import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import create_app

def test_configuration_readback_auto_test_and_real_guards(tmp_path):
    c=TestClient(create_app(str(tmp_path/'wb.db')))
    model=json.loads(Path('examples/ci20-pilot.json').read_text(encoding='utf-8'));pid=model['project']['project_id']
    c.post('/api/projects',json={'model':model,'expected_revision':0})
    plan=c.post(f'/api/projects/{pid}/plans').json();url=f'/api/plans/{plan["id"]}/commissioning'
    edge=c.get(url).json()['edges'][0]['edge_id'];config=f'/api/projects/{pid}/iems-configuration'
    cmd={'mode':'SIMULATION','revision':1,'action':'readback'};run={'edge_id':edge,'mode':'SIMULATION'}
    assert c.post(config,json=cmd).status_code==409
    assert c.post(url+'/auto',json=run).status_code==409
    assert c.post(config,json={**cmd,'action':'send'}).json()['status']=='SENT'
    assert c.post(config,json={**cmd,'mismatch':True}).json()['status']=='MISMATCH'
    assert c.post(url+'/auto',json=run).status_code==409
    assert c.post(config,json=cmd).json()['status']=='MATCHED'
    result=c.post(url+'/auto',json=run).json();assert result['completed'];assert len(result['results'])==5
    assert result['configuration_id'] and result['run_id']
    fail=c.post(url+'/auto',json={**run,'failure_step':'identity'}).json()
    assert not fail['completed'] and len(fail['results'])==4 and fail['results'][-1]['status']=='FAIL'
    count=len(c.get(url).json()['records'])
    assert c.post(url+'/auto',json={**run,'mode':'REAL'}).status_code==503
    assert c.post(config,json={**cmd,'mode':'REAL','action':'send'}).status_code==503
    assert len(c.get(url).json()['records'])==count
    model['project']['name']+=' new';c.post('/api/projects',json={'model':model,'expected_revision':1})
    assert c.post(config,json=cmd).status_code==409
    assert c.post(url+'/auto',json=run).status_code==409
