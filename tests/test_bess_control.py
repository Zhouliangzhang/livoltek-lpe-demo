from test_pv_control import ready


def setup8(tmp_path):
 c,m,pvctl,cfg,pv,meter,s,body=ready(tmp_path);url=pvctl.replace('pv-control','bess-control')
 assert c.post(url,json=body).status_code==409
 assert c.post(pvctl,json=body).status_code==200
 return c,m,url,pvctl,cfg,meter,s,body


def test_bess_control_normal_and_evidence_invalidation(tmp_path):
 c,m,url,pvctl,cfg,meter,s,body=setup8(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert r['passed']==10 and len(r['devices'])==10
 for d in r['devices']:
  assert [x['direction'] for x in d['directions']]==['charge','discharge']
  assert all(x['status']=='PASS' and x['restored'] for x in d['directions'])
  assert d['directions'][0]['target_kw']==-30 and d['directions'][1]['target_kw']==30
 assert r['field_result'] is None and not r['physical_control_allowed'] and r['manufacturer_basis']=='PENDING'
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'soc_low'}).status_code==409
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']==[]
 c.post(pvctl,json={**body,'request_id':'new-pv'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 c.post(meter+'/'+s['id']+'/run',json={'step':'identity','scenario':'timeout'})
 assert c.post(url,json={**body,'request_id':'new-bess'}).status_code==409


def test_bess_directions_conditions_and_failures(tmp_path):
 c,m,url,pvctl,cfg,meter,s,body=setup8(tmp_path)
 for scenario,blocked in [('soc_low','discharge'),('soc_high','charge'),('charge_forbidden','charge'),('discharge_forbidden','discharge')]:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario,'fault_node':'BESS_03'}).json()
  assert r['passed']==9 and r['conditional']==1 and r['skipped']==0
  d=next(d for d in r['devices'] if d['node_id']=='BESS_03')
  assert next(x for x in d['directions'] if x['direction']==blocked)['status']=='CONDITION'
  assert not next(x for x in d['directions'] if x['direction']==blocked)['commands']
  assert next(x for x in d['directions'] if x['direction']!=blocked)['status']=='PASS'
 for scenario in ['no_response','wrong_sign','boundary_drop','ack_timeout','rejected','bms_unknown','no_permission','missing_basis','restore_failed','owner_lost']:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario,'fault_node':'BESS_03','fault_direction':'charge'}).json()
  assert r['passed']==2 and r['failed']==1 and r['skipped']==7,scenario
  d=next(d for d in r['devices'] if d['node_id']=='BESS_03')
  assert d['directions'][1]['status']=='SKIPPED'
  if scenario=='boundary_drop':assert d['directions'][0]['restored'] and any(x['bound_kw']==0 for x in d['directions'][0]['samples'])
  if scenario=='owner_lost':assert len(d['directions'][0]['commands'])==1
  if r['alarm_latched']:
   assert c.post(url,json={**body,'request_id':'blocked'}).status_code==409
   assert c.post(url+'/'+r['id']+'/recover',json=body).status_code==200


def test_bess_control_honors_prior_direction_limits(tmp_path):
 c,m,url,pvctl,cfg,meter,s,body=setup8(tmp_path)
 bess=url.replace('bess-control','bess-communication')
 c.post(bess,json={**body,'request_id':'restricted','scenario':'charge_only','fault_node':'BESS_03'})
 c.post(cfg,json={**body,'request_id':'new-cfg'});c.post(pvctl,json={**body,'request_id':'new-pv'})
 r=c.post(url,json=body).json()
 d=next(d for d in r['devices'] if d['node_id']=='BESS_03')
 assert d['directions'][0]['status']=='PASS' and d['directions'][1]['status']=='CONDITION'

def test_bess_target_clamped_and_discharge_failure_preserves_charge():
 from backend.bess_control import direction_test
 d=dict(node_id='BESS_X',path_valid=True,control_valid=True,duplicate_sn=False)
 cap=dict(eligible=True,directions=['charge','discharge'],charge_kw=12,discharge_kw=15)
 charge=direction_test(d,'charge','normal','run',cap)
 discharge=direction_test(d,'discharge','no_response','run',cap)
 assert charge['target_kw']==-12 and charge['status']=='PASS'
 assert discharge['target_kw']==15 and discharge['status']=='FAIL' and discharge['restored']
 assert max(abs(s['power_kw']) for s in charge['samples'])<=12
 assert all(s['bound_kw']==12 for s in charge['samples'])
 assert charge['snapshot']['sequence']!=discharge['snapshot']['sequence']
