from test_pv_control import ready
from backend.pv_control import control_context


def test_simulation_uses_own_gate_without_granting_field_control(tmp_path, monkeypatch):
    c,m,url,cfg,pv,meter,s,body=ready(tmp_path)
    db=c.app.state.store
    original=db.record
    def record(key):
        value=original(key)
        if key==s['id']:
            value={**value,'m1_basis':{'control_allowed':False,'environment':'SIMULATION'}}
        return value
    monkeypatch.setattr(db,'record',record)
    plan_id=url.split('/')[3]
    assert control_context(db,plan_id,s['id'],'SIMULATION')[3] is not None
    result=c.post(url,json=body)
    assert result.status_code==200,result.text
    result=result.json()
    assert result['passed']==10 and result['manufacturer_basis']=='PENDING'
    assert result['source']=='SIMULATOR' and result['field_result'] is None
    assert result['physical_control_allowed'] is False
    assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
    assert control_context(db,plan_id,s['id'],'REAL')[3] is None


from test_m1_delivery import setup


def test_frozen_m1_full_simulation_chain_preserves_field_locks(setup):
    c,db,p,b=setup
    package=c.post(f'/api/projects/{p}/commissioning-basis',json={'baseline_id':b['id'],'environment':'SIMULATION'}).json()
    plan=c.post(f'/api/projects/{p}/plans',json={}).json()
    root='/api/plans/'+plan['id']
    route=c.get(root+'/meter-workflow?mode=SIMULATION').json()['routes'][0]
    session=c.post(root+'/meter-workflow',json={'basis_id':package['id'],'mode':'SIMULATION','edge_id':route['edge_id'],'acknowledged':True,'operator':'TEST','reference':'SIM ONLY'}).json()
    sid=session['id']
    for step in ['selfcheck','route','identity','quality','reference','stability','complete']:
        r=c.post(root+'/meter-workflow/'+sid+'/run',json={'step':step})
        assert r.status_code==200,r.text
    body={'session_id':sid,'mode':'SIMULATION','acknowledged':True,'request_id':'sim-chain'}
    for endpoint in ['pv-communication','bess-communication','configuration-readback','pv-control','bess-control','zero-export','dynamic-response','degradation','continuous-observation']:
        args={**body}
        if endpoint=='degradation':args['recovery_mode']='relapse'
        if endpoint=='continuous-observation':args.update(scenario='meter_loss',pattern='repeat')
        response=c.post(root+'/'+endpoint,json=args)
        assert response.status_code==200,response.text
        result=response.json()
        assert result['source']=='SIMULATOR' and result['field_result'] is None
        assert not result.get('physical_control_allowed',False)
        assert c.post(root+'/'+endpoint,json={**args,'mode':'REAL'}).status_code==503
        if endpoint=='continuous-observation':
            assert result['status']=='COMPLETE' and result['reset_count']==2
            assert result['window_start']==25 and result['completed_at']==45
            assert next(d for d in result['devices'] if d['node_id']=='PV_01')['parameters'][0]['key']=='address'
    assert db.record(package['id'])==package and db.record(b['id'])==b
    report=c.get(root+'/sat-report',params={'session_id':sid,'mode':'SIMULATION'}).json()['report']
    assert not report['sat_passed'] and report['field_result'] is None
    assert all(step['status']=='SIM_PASS' for step in report['steps'] if 7<=step['number']<=12)
