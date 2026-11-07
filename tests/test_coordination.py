from fastapi.testclient import TestClient
from backend.main import create_app
from backend.domain import pilot

def test_request_confirmation_and_new_version_invalidate_old_arrangement(tmp_path):
    c=TestClient(create_app(str(tmp_path/'coordination.db')))
    m=pilot();pid=m['project']['project_id'];url=f'/api/projects/{pid}/coordination'
    demand={'revision':1,'epc_contact':'Demo EPC','requested_time':'2026-11-10T10:00:00+08:00','support_mode':'REMOTE','target_ids':[m['nodes'][0]['node_id']],'subject':'Technical support','details':'Demo only'}
    req=c.post(url+'/requests',json=demand);assert req.status_code==200
    reply={'request_id':req.json()['id'],'decision':'CONFIRMED','manufacturer_contact':'Demo manufacturer','support_mode':'REMOTE','note':'Demo only'}
    assert c.post(url+'/arrangements',json=reply).status_code==422
    assert c.post(url+'/arrangements',json={**reply,'agreed_time':'2026-11-10T10:00:00+08:00'}).status_code==200
    assert c.post(url+'/requests',json=demand).status_code==409
    updated=c.post(url+'/requests',json={**demand,'expected_id':req.json()['id'],'subject':'Changed request'})
    assert updated.status_code==200
    assert c.post(url+'/arrangements',json={**reply,'agreed_time':'2026-11-10T10:00:00+08:00'}).status_code==409
    state=c.get(url).json();assert len(state['requests'])==2 and len(state['arrangements'])==1
    assert c.post(url+'/requests',json={**demand,'expected_id':updated.json()['id'],'target_ids':['unknown']}).status_code==422
