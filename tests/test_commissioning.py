import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import create_app

def test_m3_dependency_modes_and_stale_baseline(tmp_path):
    c=TestClient(create_app(str(tmp_path/'m3.db')))
    model=json.loads(Path('examples/ci20-pilot.json').read_text(encoding='utf-8'));pid=model['project']['project_id']
    c.post('/api/projects',json={'model':model,'expected_revision':0})
    plan=c.post(f'/api/projects/{pid}/plans').json();url=f'/api/plans/{plan["id"]}/commissioning'
    edge=c.get(url).json()['edges'][0]['edge_id']
    body={'edge_id':edge,'mode':'SIMULATION','step':'identity'}
    assert c.post(url,json=body).status_code==409
    for step in ['conditions','wiring','settings','identity','data']:
        r=c.post(url,json={**body,'step':step});assert r.status_code==200;assert r.json()['status']=='PASS'
        assert r.json()['source']=='SYNTHETIC'
    field={**body,'mode':'FIELD','recorder':'EPC','observation':'现场记录','reference':'EPC permit'}
    assert c.post(url,json={**field,'step':'identity','status':'PASS'}).status_code==409
    assert c.post(url,json={**field,'step':'conditions','status':'PASS'}).status_code==200
    assert c.post(url,json={**field,'step':'wiring','status':'PASS'}).status_code==422
    assert c.post(url,json={**field,'step':'wiring','status':'PENDING'}).status_code==200
    assert c.post(url,json={**field,'step':'settings'}).status_code==409
    assert c.post(url,json={**body,'step':'wiring','scenario':'failure'}).json()['status']=='FAIL'
    assert c.post(url,json={**body,'step':'data'}).status_code==409
    assert c.post(url,json={**body,'step':'wiring'}).status_code==200
    assert c.post(url,json={**body,'step':'data'}).status_code==409
    assert c.post(url,json={**body,'edge_id':'invalid','step':'conditions'}).status_code==422
    model['project']['name']+=' changed'
    c.post('/api/projects',json={'model':model,'expected_revision':1})
    assert c.post(url,json={**body,'step':'conditions'}).status_code==409
    assert c.get(url).json()['stale']
