from test_fleet import setup, ready

def test_system_scenarios_and_guards(tmp_path):
    c,m,pid,fleet=setup(tmp_path);url=fleet.replace('/fleet','/system-tests')
    assert c.get(url).status_code==200
    assert c.post(url,json={'mode':'SIMULATION','scenario':'surplus'}).status_code==409
    ready(c,pid)
    for scenario in ['surplus','deficit','charge_limit']:
        r=c.post(url,json={'mode':'SIMULATION','scenario':scenario}).json()
        assert r['status']=='PASS',r
        f=r['flow'];assert abs(f['grid']-(f['load']+f['charge']-f['pv']-f['discharge']))<0.01
        assert f['grid']==25
        assert len(r['devices'])==20
    r=c.post(url,json={'mode':'SIMULATION','scenario':'meter_stale'}).json()
    assert r['status']=='FAIL' and r['devices']==[] and r['flow'] is None
    assert r['issues'][0]['node_id']=='METER_PCC'
    for scenario,node in [('pv_reject','PV_03'),('bess_reject','BESS_04')]:
        r=c.post(url,json={'mode':'SIMULATION','scenario':scenario,'fault_node':node}).json()
        assert r['status']=='FAIL' and r['issues'][0]['node_id']==node
        assert r['flow']['grid']<0
        assert next(d for d in r['devices'] if d['node_id']==node)['status']=='FAIL'
    count=len(c.get(url).json()['records'])
    assert c.post(url,json={'mode':'REAL','scenario':'surplus'}).status_code==503
    assert c.post(url,json={'mode':'SIMULATION','scenario':'pv_reject','fault_node':'BESS_01'}).status_code==422
    assert len(c.get(url).json()['records'])==count
    m['project']['name']+=' changed';c.post('/api/projects',json={'model':m,'expected_revision':1})
    assert c.post(url,json={'mode':'SIMULATION','scenario':'surplus'}).status_code==409

def test_system_missing_route_blocks_control(tmp_path):
    c,m,pid,url=setup(tmp_path,True);ready(c,pid)
    r=c.post(url.replace('/fleet','/system-tests'),json={'mode':'SIMULATION','scenario':'surplus'}).json()
    assert r['status']=='BLOCKED' and r['devices']==[]
    assert any(i['node_id']=='PV_01' for i in r['issues'])
