from test_step11_degradation import setup11


def setup12(tmp_path):
 c,degrade,dynamic,s,body=setup11(tmp_path);url=degrade.replace('degradation','continuous-observation')
 assert c.post(url,json=body).status_code==409
 assert c.post(degrade,json=body).status_code==200
 return c,url,degrade,s,body


def test_continuous_clean_gate_and_evidence(tmp_path):
 c,url,degrade,s,body=setup12(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert r['status']=='COMPLETE' and r['stable_seconds']==20
 assert r['completed_at']-r['window_start']==20
 assert r['cleanup']['verified'] and len(r['devices'])==22 and len(r['samples'][-1]['devices'])==22
 assert r['field_result'] is None and not r['physical_control_allowed'] and r['manufacturer_basis']=='PENDING'
 assert r['configuration']['pending_count']>0
 assert all(x['stable_seconds']==0 for x in r['samples'] if x['t']<4)
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'meter_loss'}).status_code==409
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert not c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']
 c.post(degrade,json={**body,'request_id':'new11'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']


def test_continuous_resets_and_blocks(tmp_path):
 c,url,degrade,s,body=setup12(tmp_path)
 for scenario,node in [('meter_loss','METER_PCC'),('pv_loss','PV_03'),('bess_loss','BESS_03'),('iems_restart','EMS_MASTER'),('power_export','METER_PCC'),('config_drift','BESS_03'),('stale_data','METER_PCC')]:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario,'fault_node':node,'pattern':'repeat'});assert r.status_code==200,r.text
  r=r.json();assert r['status']=='COMPLETE' and r['reset_count']==2
  assert r['window_start']==25 and r['completed_at']==45
  assert all(x['stable_seconds']==0 for x in r['samples'] if x['t'] in (8,9,10,23,24))
  assert any(x['node_id']==node for x in r['issues'])
  if scenario=='pv_loss':assert not r['samples'][8]['power_ok']
  fail=c.post(url,json={**body,'request_id':scenario+'hold','scenario':scenario,'fault_node':node,'pattern':'persistent'}).json()
  assert fail['status']=='INCOMPLETE' and fail['completed_at'] is None
 for scenario in ['cleanup_failed','normal_config_mismatch']:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario}).json()
  assert r['status']=='BLOCKED' and not r['cleanup']['verified'] and not r['samples']


def test_window_is_elapsed_time_not_sample_count(tmp_path):
 c,url,degrade,s,body=setup12(tmp_path)
 r=c.post(url,json=body).json()
 assert r['window_start']==4 and r['completed_at']==24
 assert r['samples'][23]['stable_seconds']==19 and r['samples'][23]['state']=='OBSERVING'
 assert len([s for s in r['samples'] if s['window_start']==4])==21
 partial=c.post(degrade,json={**body,'request_id':'partial11','scenario':'meter_lost'}).json()
 assert partial['status']=='PASS'
 assert c.post(url,json={**body,'request_id':'missingcoverage'}).status_code==409
