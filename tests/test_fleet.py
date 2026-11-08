import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import create_app

def setup(tmp_path, disconnected=False):
    c=TestClient(create_app(str(tmp_path/'fleet.db')))
    m=json.loads(Path('examples/ci20-pilot.json').read_text(encoding='utf-8'))
    if disconnected:
        m['edges']=[e for e in m['edges'] if not (e['edge_type']=='COMMUNICATION' and e['to_port_id']=='PV_01.RS485')]
    pid=m['project']['project_id']
    assert c.post('/api/projects',json={'model':m,'expected_revision':0}).status_code==200
    plan=c.post(f'/api/projects/{pid}/plans').json()
    url=f'/api/plans/{plan["id"]}/fleet'
    return c,m,pid,url

def ready(c,pid):
    for action in ['send','readback']:
        assert c.post(f'/api/projects/{pid}/iems-configuration',json={'mode':'SIMULATION','revision':1,'action':action}).status_code==200

def test_grouped_fleet_and_result_isolation(tmp_path):
    c,m,pid,url=setup(tmp_path)
    r=c.get(url);assert r.status_code==200
    groups=r.json()['groups'];assert [len(g['devices']) for g in groups]==[10,10]
    assert all(d['route'] for g in groups for d in g['devices'])
    body={'mode':'SIMULATION','node_id':'PV_01'}
    assert c.post(url,json=body).status_code==409
    ready(c,pid)
    fail=c.post(url,json={**body,'failure_step':'identity'}).json()
    assert fail['status']=='FAIL' and fail['steps'][-1]['key']=='identity'
    assert not any(s['key']=='limit' for s in fail['steps'])
    good=c.post(url,json={**body,'node_id':'PV_02'}).json()
    assert good['status']=='PASS' and good['steps'][-1]['key']=='restore'
    bess=c.post(url,json={**body,'node_id':'BESS_01'}).json()
    assert [s['key'] for s in bess['steps']][-3:]==['charge','discharge','restore']
    records=c.get(url).json()['records'];assert len(records)==3
    assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
    assert c.get(url).json()['records']==records
    assert c.post(url,json={**body,'node_id':'NET_01'}).status_code==422
    assert c.post(url,json={**body,'failure_step':'charge'}).status_code==422
    m['project']['name']+=' changed'
    c.post('/api/projects',json={'model':m,'expected_revision':1})
    assert c.post(url,json=body).status_code==409

def test_missing_path_is_not_simulated_pass(tmp_path):
    c,m,pid,url=setup(tmp_path,True);ready(c,pid)
    result=c.post(url,json={'mode':'SIMULATION','node_id':'PV_01'}).json()
    assert result['status']=='BLOCKED'
    assert result['steps'][0]['code']=='M1_ROUTE_MISSING'
