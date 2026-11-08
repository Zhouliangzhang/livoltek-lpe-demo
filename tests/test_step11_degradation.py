from test_dynamic_response import setup10


def setup11(tmp_path):
 c,dynamic,zero,s,body=setup10(tmp_path);url=dynamic.replace('dynamic-response','degradation')
 assert c.post(url,json=body).status_code==409
 assert c.post(dynamic,json=body).status_code==200
 return c,url,dynamic,s,body


def test_degradation_three_cases_gates_and_recovery(tmp_path):
 c,url,dynamic,s,body=setup11(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert len(r['cases'])==3 and r['status']=='PASS' and not r['alarm_latched']
 for case in r['cases']:
  assert case['restored'] and case['stable_verified']
  assert all(x['alarm_latched'] for x in case['samples'] if 5<=x['t']<case['cleared_at'])
  assert all(x['stable_count']>=5 for x in case['samples'] if x['t']==case['cleared_at'])
  assert abs(case['samples'][-1]['pcc_kw']-100)<.1
  for x in case['samples']:assert abs(x['pcc_kw']-(x['load_kw']-x['pv_kw']-x['bess_kw']))<.02
 meter=r['cases'][0];assert any(x['feedback_kw'] is None and x['alarm_latched'] for x in meter['samples'])
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert not c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']
 c.post(dynamic,json={**body,'request_id':'new10'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']


def test_persistent_fault_requires_evidenced_recovery(tmp_path):
 c,url,dynamic,s,body=setup11(tmp_path)
 r=c.post(url,json={**body,'scenario':'meter_lost','recovery_mode':'hold'}).json()
 assert r['alarm_latched'] and r['status']=='FAIL'
 assert c.post(url,json={**body,'request_id':'blocked'}).status_code==409
 endpoint=url+'/'+r['id']+'/recover'
 bad=c.post(endpoint,json={**body,'request_id':'still-bad','recovery_mode':'hold'});assert bad.status_code==200,bad.text
 assert not bad.json()['verified']
 assert c.get(url,params={'session_id':s['id']}).json()['alarm_latched']
 good=c.post(endpoint,json={**body,'request_id':'fixed','recovery_mode':'normal'}).json()
 assert good['verified'] and all(x['stable_verified'] and x['restored'] for x in good['cases'])
 assert not c.get(url,params={'session_id':s['id']}).json()['alarm_latched']
 assert c.post(endpoint,json={**body,'request_id':'fixed','recovery_mode':'normal'}).json()['id']==good['id']


def test_recurrence_resets_stable_counter():
 from backend.degradation import simulate_case
 cap=[dict(node_id='BESS_03',capability=dict(charge_kw=80,discharge_kw=100))]
 r=simulate_case('bess_reject',['PV_03'],cap,'METER','EMS','BESS_03','relapse','r')
 assert r['status']=='PASS' and r['stable_verified']
 assert any(x['t']>=19 and x['stable_count']>0 for x in r['samples'][:25])
 assert r['samples'][25]['stable_count']==0 and r['samples'][25]['alarm_latched']
 assert r['cleared_at']>29


def test_degradation_reject_commands_and_bounds():
 from backend.degradation import simulate_case
 cap=[dict(node_id='BESS_03',capability=dict(charge_kw=12,discharge_kw=15))]
 for kind,fault in [('pv_reject','PV_03'),('bess_reject','BESS_03')]:
  r=simulate_case(kind,['PV_03'],cap,'METER','EMS',fault,'normal','r')
  assert r['status']=='PASS'
  rejected=[c for c in r['commands'] if c['node_id']==fault and c['ack']=='REJECTED']
  assert rejected and all(c['value_kw']<100 for c in rejected)
  if kind=='bess_reject':assert all(c['value_kw']<0 for c in rejected)
  for s in r['samples']:
   d=next(d for d in s['devices'] if d['node_id']=='BESS_03')
   assert -d['charge_bound_kw']-.001<=d['power_kw']<=d['discharge_bound_kw']+.001
 failed=simulate_case('pv_reject',['PV_03'],cap,'METER','EMS','PV_03','restore_failed','r')
 assert failed['alarm_latched'] and not failed['restored'] and failed['cleared_at'] is None


def test_permission_and_incomplete_step10_block(tmp_path):
 c,url,dynamic,s,body=setup11(tmp_path)
 for scenario in ['no_permission','missing_basis']:
  r=c.post(url,json={**body,'scenario':scenario,'request_id':scenario}).json()
  assert r['status']=='FAIL' and not r['cases']
 c.post(dynamic,json={**body,'request_id':'onecase','scenario':'load_step'})
 assert c.post(url,json={**body,'request_id':'blocked'}).status_code==409
