from test_bess_control import setup8


def setup10(tmp_path):
 c,m,bess,pv,cfg,meter,s,body=setup8(tmp_path)
 c.post(bess,json=body);zero=bess.replace('bess-control','zero-export');url=bess.replace('bess-control','dynamic-response')
 assert c.post(url,json=body).status_code==409
 assert c.post(zero,json=body).status_code==200
 return c,url,zero,s,body


def test_dynamic_three_cases_and_evidence(tmp_path):
 c,url,zero,s,body=setup10(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert r['status']=='PASS' and r['restored'] and len(r['cases'])==3
 for case in r['cases']:
  assert case['status']=='PASS' and case['restored']
  assert all(e['settling_s'] is not None and e['settling_s']<=8 and e['confirmed_s']==e['settling_s']+2 for e in case['events'])
  assert len(case['samples'])==56
  for x in case['samples']:
   assert abs(x['pcc_kw']-(x['load_kw']-x['pv_kw']-x['bess_kw']))<.02
   for d in x['devices']:
    if d['kind']=='BESS':assert -d['charge_bound_kw']-.001<=d['power_kw']<=d['discharge_bound_kw']+.001
 assert r['field_result'] is None and r['manufacturer_basis']=='PENDING'
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'load_step'}).status_code==409
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert not c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']
 c.post(zero,json={**body,'request_id':'new09'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']


def test_dynamic_faults_and_recovery(tmp_path):
 c,url,zero,s,body=setup10(tmp_path)
 for scenario,node in [('no_permission','EMS_MASTER'),('missing_basis','EMS_MASTER'),('slow_response','EMS_MASTER'),('meter_lost','METER_PCC'),('pv_reject','PV_03'),('restore_failed','PV_03')]:
  r=c.post(url,json={**body,'scenario':scenario,'fault_node':node,'request_id':scenario});assert r.status_code==200,r.text
  r=r.json();assert r['status']=='FAIL' and r['issues'][0]['node_id']==node
  if scenario in ('no_permission','missing_basis'):assert not r['cases']
  if scenario=='slow_response':assert any(e['status']=='FAIL' for e in r['cases'][0]['events'])
  if scenario=='meter_lost':assert any(x['feedback_kw'] is None for x in r['cases'][0]['samples'])
  if r['alarm_latched']:
   assert c.post(url,json={**body,'request_id':'blocked'}).status_code==409
   assert c.post(url+'/'+r['id']+'/recover',json=body).status_code==200


def test_response_window_resets_and_invalid_data_is_not_success():
 from backend.dynamic_response import measure
 samples=[dict(t=i,feedback_kw=10,quality='GOOD') for i in range(12,28)]
 samples[3]['feedback_kw']=-5
 r=measure(samples,12,28)
 assert r['settling_s']==4 and r['confirmed_s']==6 and r['export_duration_s']==1
 samples[7]['feedback_kw']=None;samples[7]['quality']='INVALID'
 r=measure(samples,12,28)
 assert r['status']=='FAIL' and r['peak_export_kw'] is None and r['export_energy_kwh'] is None


def test_charge_limit_reallocation_and_restoration():
 from backend.dynamic_response import simulate_case
 bess=[dict(node_id='BESS_'+str(i),capability=dict(charge_kw=80,discharge_kw=100)) for i in range(10)]
 r=simulate_case('charge_limited',['PV_'+str(i) for i in range(10)],bess,'METER','EMS','BESS_3','normal','r')
 assert r['status']=='PASS' and len(r['notes'])==1 and not r['issues']
 restricted=[s for s in r['samples'] if 12<=s['t']<28]
 for s in restricted:
  d=next(d for d in s['devices'] if d['node_id']=='BESS_3')
  assert d['charge_bound_kw']==0 and not d['bms_allowed'] and d['power_kw']>=0 and d['target_kw']>=0
 assert restricted[-1]['pv_kw']<r['samples'][11]['pv_kw']
 assert next(d for d in r['samples'][36]['devices'] if d['node_id']=='BESS_3')['charge_bound_kw']==40
