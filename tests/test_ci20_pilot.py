from fastapi.testclient import TestClient
from backend.main import create_app
from backend.domain import validate
from scripts.build_ci20_pilot import build, PROJECT_ID
from scripts.migrate_ci20_single_iems import migrate
import copy

def test_single_iems_migration_preserves_site_edits_and_rewires_commands():
    old=build()
    old['device_assets'][0]['installed_location']='User recorded location'
    controller=next(n for n in old['nodes'] if n['node_type']=='EMS')
    asset=next(a for a in old['device_assets'] if a['asset_id']==controller['device_asset_id'])
    for family in ['PV','BESS']:
        nid='EMS_'+family
        old['nodes'].append({**copy.deepcopy(controller),'node_id':nid,'logical_id':nid,'device_asset_id':'ASSET-'+nid})
        old['device_assets'].append({**copy.deepcopy(asset),'asset_id':'ASSET-'+nid})
        for i in range(1,11):
            source=f'EMS_MASTER.{family}_SETPOINT_{i}'
            port=copy.deepcopy(next(p for p in old['ports'] if p['port_id']==source))
            port.update(port_id=f'{nid}.SETPOINT_{i}',node_id=nid)
            old['ports'].append(port)
            next(e for e in old['edges'] if e['from_port_id']==source)['from_port_id']=port['port_id']
    result=migrate(old)
    assert result['device_assets'][0]['installed_location']=='User recorded location'
    assert len([n for n in result['nodes'] if n['node_type']=='EMS'])==1
    assert all(e['from_port_id'].startswith('EMS_MASTER.') for e in result['edges'] if e['edge_type']=='CONTROL')
    assert validate(result)['valid']

def test_ci20_topology_and_honest_evidence():
    m=build()
    assert validate(m)['valid']
    assert sum(n['node_type']=='PV_INVERTER' for n in m['nodes'])==10
    assert sum(n['node_type']=='BESS' for n in m['nodes'])==10
    assert sum(n['node_type']=='EMS' for n in m['nodes'])==1
    assert all(a['serial_number'] is None and a['firmware_version'] is None for a in m['device_assets'])
    assert all(p['actual'] is None and p['approved'] is None for p in m['parameters'])
    ips=[n['attributes']['l5_settings']['ip_address']['planned'] for n in m['nodes'] if 'ip_address' in n['attributes'].get('l5_settings',{})]
    assert len(ips)==len(set(ips))
    ports={p['port_id']:p for p in m['ports']}
    # Signed power balances at the main board and both five-device collectors.
    for mode in ['normal','reverse']:
        for nid in ['LV_BUS_01','PV_ACB_1','PV_ACB_2','BESS_ACB_1','BESS_ACB_2']:
            total=0
            for e in m['edges']:
                v=e.get('attributes',{}).get('simulation_profile',{}).get(mode,0)
                if ports[e['to_port_id']]['node_id']==nid:total+=v
                if ports[e['from_port_id']]['node_id']==nid:total-=v
            assert abs(total)<1e-8

def test_ci20_save_reload_simulation_and_sop_gate(tmp_path):
    client=TestClient(create_app(tmp_path/'ci20.db'))
    response=client.post('/api/projects',json={'model':build(),'expected_revision':0})
    assert response.status_code==200
    assert client.get('/api/projects/'+PROJECT_ID).json()['model']==response.json()['model']
    normal=client.get(f'/api/projects/{PROJECT_ID}/telemetry').json()['flows']
    reverse=client.get(f'/api/projects/{PROJECT_ID}/telemetry?scenario=reverse').json()['flows']
    assert normal['CI-001']['value']==25
    assert reverse['CI-001']['value']==1100
    assert all(not x['available'] for x in client.get(f'/api/projects/{PROJECT_ID}/telemetry?scenario=stale').json()['flows'].values())
    plan=client.post(f'/api/projects/{PROJECT_ID}/plans').json()
    assert plan['tasks'] and all(t['readiness']=='BLOCKED' for t in plan['tasks'])
    assert client.post('/api/plans/'+plan['id']+'/publish').status_code==403
