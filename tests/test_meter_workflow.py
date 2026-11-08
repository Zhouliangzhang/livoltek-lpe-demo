from test_fleet import setup

def create(c,url,mode='SIMULATION'):
    return c.post(url,json={'mode':mode,'edge_id':'CI-072','acknowledged':True,'operator':'EPC Demo','reference':'演练前提确认'})

def test_meter_flow_dependencies_evidence_and_environment(tmp_path):
    c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow')
    assert c.get(url).status_code==200
    session=create(c,url).json();sid=session['id']
    action=lambda step,scenario='normal':c.post(url+'/'+sid+'/run',json={'step':step,'scenario':scenario})
    assert action('identity').status_code==409
    assert action('selfcheck').json()['status']=='PASS'
    for step in ['route','identity','quality','reference','stability','complete']:
        r=action(step);assert r.status_code==200,r.text
        assert r.json()['status']=='PASS'
        assert r.json()['source']=='SIMULATOR' and r.json()['field_result'] is None
    assert len(r.json()['evidence_ids'])==6
    assert len(c.get(url).json()['attempts'][sid])==7
    assert c.get(url+'?mode=REAL').json()['sessions']==[]
    real=create(c,url,'REAL').json()
    assert c.post(url+'/'+real['id']+'/run',json={'step':'selfcheck'}).status_code==503
    assert action('quality','stale').json()['status']=='FAIL'
    assert action('complete').status_code==409
    assert action('reference').status_code==409
    assert action('quality').json()['status']=='PASS'
    assert action('stability').status_code==409
    m['project']['name']+=' changed';c.post('/api/projects',json={'model':m,'expected_revision':1})
    assert action('reference').status_code==409

def test_meter_failures_and_missing_route(tmp_path):
    c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow')
    assert c.post(url,json={'mode':'SIMULATION','edge_id':'CI-072','acknowledged':False,'operator':'EPC','reference':'demo'}).status_code==422
    assert c.post(url,json={'mode':'SIMULATION','edge_id':'bad','acknowledged':True,'operator':'EPC','reference':'demo'}).status_code==422
    s=create(c,url).json();base=url+'/'+s['id']+'/run'
    for step in ['selfcheck','route']:assert c.post(base,json={'step':step}).json()['status']=='PASS'
    assert c.post(base,json={'step':'identity','scenario':'timeout'}).json()['status']=='FAIL'
    assert c.post(base,json={'step':'quality'}).status_code==409
    assert c.post(base,json={'step':'identity'}).json()['status']=='PASS'
    for fault in ['stale','frozen','bad','scale']:
        r=c.post(base,json={'step':'quality','scenario':fault});assert r.json()['status']=='FAIL'
    assert c.post(base,json={'step':'quality'}).json()['status']=='PASS'
    assert c.post(base,json={'step':'reference','scenario':'reverse'}).json()['status']=='FAIL'
    assert c.post(base,json={'step':'reference'}).json()['status']=='PASS'
    assert c.post(base,json={'step':'stability','scenario':'gap'}).json()['status']=='FAIL'
    assert c.post(base,json={'step':'complete'}).status_code==409

