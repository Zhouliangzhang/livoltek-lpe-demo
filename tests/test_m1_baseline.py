import copy
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.m1_baseline import content_hash
from scripts.build_ci20_pilot import build

@pytest.fixture
def setup(tmp_path):
    app=create_app(tmp_path/'baseline.db');m=build()
    m['project']['system_boundary']={'timezone':'Africa/Johannesburg','scope':'Test only','reference':'TEST','domains':[{'id':'D1','pcc_id':'PCC_01','controller_id':'EMS_MASTER','scope':''}],'status':'DRAFT'}
    app.state.store.save(m,0)
    return TestClient(app),app.state.store,m['project']['project_id']

def request(env='SIMULATION',scope='FULL',revision=1):
    return dict(expected_revision=revision,environment=env,domain_id='D1',scope_type=scope,selected_ids=[])

def preview(c,p,r):
    response=c.post(f'/api/projects/{p}/config-baselines/preview',json=r)
    assert response.status_code==200,response.text
    return response.json()

def freeze(c,p,r,v):
    return c.post(f'/api/projects/{p}/config-baselines/freeze',json={**r,'author':'Test engineer','authorization_ref':'UNVERIFIED TEST','expected_hash':v['content_hash']})

def test_full_snapshot_includes_dependencies_and_is_never_approved(setup):
    c,db,p=setup;r=request();v=preview(c,p,r)
    assert len(v['snapshot']['scope']['target_ids'])==20
    assert {'EMS_MASTER','METER_PCC','PCC_01'}<=set(v['snapshot']['scope']['dependency_ids'])
    assert not v['deployable'] and v['findings']
    f=freeze(c,p,r,v);assert f.status_code==200
    data=f.json();assert data['status']=='FROZEN_DRAFT'
    assert not any(data[k] for k in ('deployable','approved','applied'))
    assert content_hash(data['snapshot'])==data['content_hash']
    assert content_hash({k:v for k,v in data.items() if k!='archive_hash'})==data['archive_hash']
    assert db.get(p)['revision']==1

def test_partial_scope_retains_meter_bus_and_outside_scope_configuration(setup):
    c,db,p=setup;r=request(scope='PARTIAL');r['selected_ids']=['PV_01'];v=preview(c,p,r)
    assert v['snapshot']['scope']['target_ids']==['PV_01']
    assert 'METER_PCC' in v['snapshot']['scope']['dependency_ids']
    assert 'PV_02' in v['snapshot']['scope']['dependency_ids']
    assert v['snapshot']['scope']['outside_scope_action']=='PRESERVE'
    r['selected_ids']=[];assert c.post(f'/api/projects/{p}/config-baselines/preview',json=r).status_code==422
    r['selected_ids']=['METER_PCC'];assert c.post(f'/api/projects/{p}/config-baselines/preview',json=r).status_code==422

def test_revision_and_content_tampering_rejected(setup):
    c,db,p=setup;r=request();v=preview(c,p,r)
    bad={**v,'content_hash':'0'*64};assert freeze(c,p,r,bad).status_code==409
    m=db.get(p)['model'];m['project']['name']='Changed';db.save(m,1)
    assert freeze(c,p,r,v).status_code==409

def test_versions_immutable_diff_and_environment_separation(setup):
    c,db,p=setup;r=request();v=preview(c,p,r);first=freeze(c,p,r,v).json()
    m=db.get(p)['model'];m['project']['name']='Changed project name';db.save(m,1)
    r=request(revision=2);v=preview(c,p,r)
    assert any(d['path']=='/project/name' and d['kind']=='CHANGE' for d in v['diff'])
    second=freeze(c,p,r,v).json();assert first['id']!=second['id']
    old=c.get(f'/api/projects/{p}/config-baselines/{first["id"]}').json();assert old==first
    real=preview(c,p,request('REAL',revision=2));assert real['comparison_id'] is None
    assert c.get(f'/api/projects/{p}/config-baselines?environment=REAL').json()==[]
    assert len(c.get(f'/api/projects/{p}/config-baselines?environment=SIMULATION').json())==2
    assert c.get(f'/api/projects/wrong/config-baselines/{first["id"]}').status_code==404

def test_read_only_omits_control_dependencies_from_blockers_not_snapshot(setup):
    c,db,p=setup;v=preview(c,p,request(scope='READ_ONLY'))
    assert v['snapshot']['scope']['write_intent']=='NONE'
    assert not any(f['step'] in (8,9) for f in v['findings'])
    assert v['snapshot']['approvals']['manufacturer']=='PENDING'
    assert not v['deployable']

def test_freeze_cannot_accept_client_approval_or_empty_operator(setup):
    c,db,p=setup;r=request();v=preview(c,p,r)
    body={**r,'author':'Test','expected_hash':v['content_hash'],'approved':True}
    assert c.post(f'/api/projects/{p}/config-baselines/freeze',json=body).status_code==422

    del body['approved'];body['author']='   '
    assert c.post(f'/api/projects/{p}/config-baselines/freeze',json=body).status_code==422

def test_meter_identity_change_is_reported_as_stale_basis(setup):
    import json
    from backend.m1_metering import FIELDS
    from backend.m1_baseline import network_plan_edges
    c,db,p=setup;m=db.get(p)['model']
    n=next(n for n in m['nodes'] if n['node_id']=='METER_PCC')
    a=next(a for a in m['device_assets'] if a['asset_id']==n['device_asset_id'])
    dm=next(d for d in m['device_models'] if d['model_id']==a['model_id'])
    ports=[v for v in m['ports'] if v['node_id']==n['node_id']];ids={v['port_id'] for v in ports}
    edges=[e for e in network_plan_edges(m,'SIMULATION') if e['from_port_id'] in ids or e['to_port_id'] in ids]
    r={k:'' for k in FIELDS};r.update(meter_id='METER_PCC',pcc_id='PCC_01',status='PENDING',signature=json.dumps([a,dm,ports,edges,n.get('attributes',{}).get('identity_records')]))
    m['project']['metering_settings']={'SIMULATION':[r]};db.save(copy.deepcopy(m),1)
    v=preview(c,p,request(revision=2));assert not any('计量草案与当前身份' in f['message'] for f in v['findings'])
    a['firmware_version']='changed';db.save(m,2)
    v=preview(c,p,request(revision=3));assert any('计量草案与当前身份' in f['message'] for f in v['findings'])
