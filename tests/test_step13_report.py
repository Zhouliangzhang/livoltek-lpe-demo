from test_step12_observation import setup12


def test_report_snapshot_mode_and_evidence(tmp_path):
 c,obs,deg,s,body=setup12(tmp_path)
 run=c.post(obs,json=body).json();url=obs.replace('continuous-observation','sat-report');params={'session_id':s['id']}
 res=c.get(url,params=params);assert res.status_code==200,res.text
 report=res.json()['report'];assert len(report['steps'])==12
 assert report['steps'][11]['status']=='SIM_PASS'
 assert report['sat_status']=='NOT_FIELD_SAT' and not report['sat_passed']
 assert report['pending'] and report['steps'][5]['status']=='PENDING'
 saved=c.post(url,json=body);assert saved.status_code==200,saved.text
 snap=saved.json();assert c.post(url,json=body).json()['id']==snap['id']
 raw=c.get(url+'/evidence/'+run['id'],params=params);assert raw.status_code==200 and raw.json()['samples']
 assert c.get(url+'/evidence/'+run['id'],params={**params,'mode':'REAL'}).status_code==404
 assert c.get(url,params={**params,'mode':'REAL'}).json()['report']['steps'][11]['status']=='NOT_RUN'
 exported=c.get(url+'/'+snap['id']+'/export',params={'format':'json'}).json()
 assert exported['sat_passed'] is False and run['id'] in exported['raw_evidence']
 html=c.get(url+'/'+snap['id']+'/export',params={'format':'html'});assert '非现场 SAT' in html.text
 c.post(obs,json={**body,'request_id':'fault13','scenario':'pv_loss','fault_node':'PV_03','pattern':'persistent'})
 new=c.get(url,params=params).json();assert new['report']['steps'][11]['status']=='INCOMPLETE'
 assert any(i['node_id']=='PV_03' and not i['resolved'] for i in new['report']['issues'])
 assert not new['snapshots'][0]['current']
 assert c.get(url+'/'+snap['id']+'/export',params={'format':'json'}).json()['snapshot_hash']==snap['snapshot_hash']


def test_report_never_reuses_stale_or_missing_steps(tmp_path):
 c,obs,deg,s,body=setup12(tmp_path);url=obs.replace('continuous-observation','sat-report');params={'session_id':s['id']}
 r=c.get(url,params=params);assert r.status_code==200
 assert r.json()['report']['steps'][11]['status']=='NOT_RUN'
 c.post(obs,json=body)
 c.post(deg,json={**body,'request_id':'rerun13'})
 report=c.get(url,params=params).json()['report']
 assert report['steps'][11]['status']=='STALE' and report['incomplete']
 assert c.get(url,params={'session_id':'invalid'}).status_code==404
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==409

def test_report_selfcheck_fault_and_session_isolation(tmp_path):
 c,obs,deg,s,body=setup12(tmp_path);base=obs.rsplit('/',1)[0];url=base+'/sat-report'
 fault=c.post(base+'/meter-workflow/'+s['id']+'/run',json={'step':'selfcheck','scenario':'clock_unsynced'}).json()
 r=c.get(url,params={'session_id':s['id']}).json()['report']
 assert any(x['step']==2 and x['node_id']=='EMS_MASTER' and '2500' in x['reason'] for x in r['issues'])
 assert r['steps'][1]['status']=='FAIL' and r['steps'][2]['status']=='STALE'
 other=c.post(base+'/meter-workflow',json={'mode':'SIMULATION','edge_id':'CI-072','acknowledged':True,'operator':'other','reference':'sim'}).json()
 assert c.get(url+'/evidence/'+fault['id'],params={'session_id':other['id']}).status_code==404
 assert all(x['status']=='NOT_RUN' for x in c.get(url,params={'session_id':other['id']}).json()['report']['steps'][1:])
