from fastapi.testclient import TestClient
from backend.main import create_app
from backend.domain import pilot
from tests.test_installation_tracking import PNG

def test_checklist_records_and_guards(tmp_path):
    client=TestClient(create_app(str(tmp_path/'check.db')))
    model=pilot();pid=model['project']['project_id']
    plan=client.post(f'/api/projects/{pid}/plans').json()
    url=f'/api/plans/{plan["id"]}/checklist'
    listing=client.get(url).json();items=listing['items']
    assert {i['stage'] for i in items} >= {'ELECTRICAL','COMMUNICATION'}
    assert len({i['id'] for i in items})==len(items)
    assert {e['edge_id'] for e in model['edges']} <= {i['target_id'] for i in items}
    item=items[0]['id'];body=dict(item_id=item,status='PENDING',recorder='EPC',note='现场待确认',photo_ids=[])
    assert client.post(url,json={**body,'status':'PASS'}).status_code==422
    assert client.post(url,json={**body,'status':'NA','note':' '}).status_code==422
    assert client.post(url,json={**body,'item_id':'unknown'}).status_code==422
    photo=client.post(url+'/photos',params={'item_id':item,'filename':'test.png'},content=PNG).json()['id']
    body['photo_ids']=[photo]
    assert client.post(url,json=body).status_code==200
    assert client.get('/api/checklist/photos/'+photo).content==PNG
    assert client.post(url,json={**body,'item_id':items[1]['id']}).status_code==422
    assert client.post(url,json={**body,'status':'FAIL','note':'标识不一致'}).status_code==200
    assert client.get(url).json()['records'][0]['status']=='FAIL'
    fresh=client.post(f'/api/projects/{pid}/plans').json()
    assert client.get(f'/api/plans/{fresh["id"]}/checklist').json()['records']==[]
    current=client.get('/api/projects/'+pid).json();current['model']['project']['name']+=' changed'
    client.post('/api/projects',json={'model':current['model'],'expected_revision':current['revision']})
    assert client.post(url,json=body).status_code==409
    assert len(client.get(url).json()['records'])==2
