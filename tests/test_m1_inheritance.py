import copy
from test_m1_delivery import setup
from backend.m1_inheritance import environment_model
from backend.session_scope import preflight
from backend.meter_workflow import Start
from backend.session_scope import freeze

def test_environment_identity_and_third_party_are_inherited_without_mutation(setup):
    c,db,p,b=setup;m=db.get(p)['model'];before=copy.deepcopy(m)
    n=next(n for n in m['nodes'] if n['node_id']=='METER_PCC')
    n.setdefault('attributes',{})['identity_records']={'SIMULATION':{'sn':'SIM-METER-NEW','firmware':'SIM-FW','location':'模拟柜','third_party':{'manufacturer':'模拟厂家','model':'模拟表'}}}
    original=copy.deepcopy(m)
    sim=environment_model(m,'SIMULATION');real=environment_model(m,'REAL')
    a=next(a for a in sim['device_assets'] if a['asset_id']==n['device_asset_id'])
    assert a['serial_number']=='SIM-METER-NEW' and a['firmware_version']=='SIM-FW'
    assert next(d for d in sim['device_models'] if d['model_id']==a['model_id'])['model_name']=='模拟表'
    assert next(a for a in real['device_assets'] if a['asset_id']==n['device_asset_id'])['serial_number']!='SIM-METER-NEW'
    assert m==original and db.get(p)['model']==before

def test_m2_listing_and_new_session_inherit_saved_environment_settings(setup):
    c,db,p,b=setup;m=db.get(p)['model'];n=next(n for n in m['nodes'] if n['node_id']=='METER_PCC')
    n.setdefault('attributes',{})['identity_records']={'SIMULATION':{'sn':'SIM-METER-NEW','firmware':'SIM-FW','location':'模拟柜','factory_firmware':'','structure':'ZONE_01','circuit':'','source':'SIMULATION_MANUAL','raw_scan':'','updated_at':'2026-11-09T00:00:00Z','replacement_reason':'','basis_status':'PENDING'}}
    db.save(m,1)
    response=c.post(f'/api/projects/{p}/plans',json={});assert response.status_code==200,response.text
    plan=response.json();pid=plan['id']
    data=c.get(f'/api/plans/{pid}/meter-workflow?mode=SIMULATION').json();route=data['routes'][0]
    device=next(d for d in data['preflights'][route['edge_id']]['devices'] if d['node_id']=='METER_PCC')
    assert device['serial_number']=='SIM-METER-NEW'
    session=c.post(f'/api/plans/{pid}/meter-workflow',json=dict(mode='SIMULATION',edge_id=route['edge_id'],acknowledged=True,operator='EPC',reference='模拟')).json()
    assert session['snapshot']['inheritance_version']=='M1-ENV-1'
    assert session['snapshot']['m1_environment_settings']['communication_settings']==m['project']['communication_settings']['SIMULATION']
    assert next(d for d in session['snapshot']['devices'] if d['node_id']=='METER_PCC')['firmware_version']=='SIM-FW'
    assert not session['gate']['field_release']

    for step in ['selfcheck','route']:
        response=c.post(f'/api/plans/{pid}/meter-workflow/{session["id"]}/run',json=dict(step=step,scenario='normal',request_id='inherited-'+step))
        assert response.status_code==200,response.text
        assert response.json()['source']=='SIMULATOR'
