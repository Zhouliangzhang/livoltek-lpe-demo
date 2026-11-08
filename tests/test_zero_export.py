from test_bess_control import setup8


def test_zero_export_gates_and_balance(tmp_path):
 c,m,bess,pv,cfg,meter,s,body=setup8(tmp_path);url=bess.replace('bess-control','zero-export')
 assert c.post(url,json=body).status_code==409
 assert c.post(bess,json=body).status_code==200
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert r['status']=='PASS' and r['restored']
 assert all(x['status']=='PASS' for x in r['stages'])
 assert r['field_result'] is None and not r['physical_control_allowed']
 for x in r['samples']:
  assert abs(x['pcc_kw']-(x['load_kw']-x['pv_kw']-x['bess_kw']))<0.02
  for d in x['devices']:
   if d['kind']=='BESS':assert -d['charge_bound_kw']<=d['power_kw']<=d['discharge_bound_kw']
 assert any(x['bess_kw']<0 for x in r['samples']) and any(x['bess_kw']>0 for x in r['samples'])
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'meter_lost'}).status_code==409
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert not c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']
 c.post(bess,json={**body,'request_id':'new08'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']


def test_zero_export_faults_and_recovery(tmp_path):
 c,m,bess,pv,cfg,meter,s,body=setup8(tmp_path);c.post(bess,json=body);url=bess.replace('bess-control','zero-export')
 for scenario,node in [('no_permission','EMS_MASTER'),('missing_basis','EMS_MASTER'),('meter_lost','METER_PCC'),('pv_reject','PV_03'),('bess_reject','BESS_03'),('restore_failed','PV_03')]:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario,'fault_node':node});assert r.status_code==200,r.text
  r=r.json();assert r['status']!='PASS' and r['issues']
  assert r['issues'][0]['node_id']==node
  if scenario in ('no_permission','missing_basis'):assert not r['samples'] and not r['commands']
  if scenario=='meter_lost':assert any(x['feedback_kw'] is None for x in r['samples'])
  if r['alarm_latched']:
   assert c.post(url,json={**body,'request_id':'blocked'}).status_code==409
   assert c.post(url+'/'+r['id']+'/recover',json=body).status_code==200
 c.post(bess,json={**body,'request_id':'low08','scenario':'soc_low','fault_node':'BESS_03'})
 assert c.post(url,json={**body,'request_id':'blocked08'}).status_code==409
