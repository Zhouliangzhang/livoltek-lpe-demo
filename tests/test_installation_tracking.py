import base64
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.domain import pilot
from backend.installation_tracking import targets
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')

def test_target_records_photos_and_stale_plan(tmp_path):
    app=create_app(str(tmp_path/'records.db'))
    client=TestClient(app)
    m=pilot();pid=m['project']['project_id']
    plan=client.post(f'/api/projects/{pid}/plans').json();url='/api/plans/'+plan['id']+'/installation'
    listing=client.get(url).json();target=listing['targets']['INSTALL-POSITION'][0]['id']
    body={'task_id':'INSTALL-POSITION','target_id':target,'status':'COMPLETED','recorder':'Test EPC','note':'Test only','photo_ids':[]}
    assert client.post(url,json=body).status_code==422
    invalid=client.post(url+'/photos',params={'task_id':'INSTALL-POSITION','target_id':target,'filename':'bad.svg'},content=b'<svg/>')
    assert invalid.status_code==415
    uploaded=client.post(url+'/photos',params={'task_id':'INSTALL-POSITION','target_id':target,'filename':'test-not-site.png'},content=PNG)
    assert uploaded.status_code==200
    photo=uploaded.json()['id'];body['photo_ids']=[photo]
    assert client.get('/api/installation/photos/'+photo).content==PNG
    assert client.post(url,json={**body,'task_id':'INSTALL-EARTH'}).status_code==422
    assert client.post(url,json={**body,'target_id':'unknown'}).status_code==422
    saved=client.post(url,json=body);assert saved.status_code==200
    assert saved.json()['approval']=='NOT_APPROVED'
    assert client.post(url,json={**body,'status':'BLOCKED','note':'Reopened'}).status_code==200
    assert len(client.get(url).json()['records'])==2
    assert plan['tasks'][0]['readiness']=='BLOCKED'
    fresh=client.post(f'/api/projects/{pid}/plans').json()
    assert client.get('/api/plans/'+fresh['id']+'/installation').json()['records']==[]
    # Changed engineering data blocks new records, but keeps old records and photos readable.
    current=client.get('/api/projects/'+pid).json();current['model']['project']['name']+=' changed'
    assert client.post('/api/projects',json={'model':current['model'],'expected_revision':current['revision']}).status_code==200
    assert client.post(url,json=body).status_code==409
    assert len(client.get(url).json()['records'])==2

def test_circuits_are_bound_to_saved_ports():
    m=pilot()
    power=targets(m,{'task_id':'INSTALL-POWER'})
    comm=targets(m,{'task_id':'INSTALL-COMMS'})
    assert {x['id'] for x in power}=={e['edge_id'] for e in m['edges'] if e['edge_type']=='ELECTRICAL'}
    assert {x['id'] for x in comm}=={e['edge_id'] for e in m['edges'] if e['edge_type']=='COMMUNICATION'}
    assert all(' → ' in x['detail'] for x in power+comm)
