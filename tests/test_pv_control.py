from test_bess_communication import prepare


def ready(tmp_path):
 c,m,bess,pv,meter,s,body=prepare(tmp_path)
 c.post(bess,json=body)
 cfg=bess.replace('bess-communication','configuration-readback');url=bess.replace('bess-communication','pv-control')
 assert c.post(url,json=body).status_code==409
 assert c.post(cfg,json=body).status_code==200
 return c,m,url,cfg,pv,meter,s,body


def test_pv_control_gates_persistence_and_real(tmp_path):
 c,m,url,cfg,pv,meter,s,body=ready(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert len(r['devices'])==10 and r['passed']==10 and r['failed']==0
 assert all(d['restored'] for d in r['devices'])
 assert not r['physical_control_allowed'] and r['field_result'] is None
 assert r['scope']['kind']=='SIM_PV_CONTROL' and r['manufacturer_basis']=='PENDING'
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'no_permission'}).status_code==409
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']==[]
 c.post(cfg,json={**body,'request_id':'new-readback'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 c.post(meter+'/'+s['id']+'/run',json={'step':'identity','scenario':'timeout'})
 assert c.post(url,json={**body,'request_id':'new'}).status_code==409


def test_control_failure_stops_remaining_and_recovers(tmp_path):
 c,m,url,cfg,pv,meter,s,body=ready(tmp_path)
 for scenario in ['ack_timeout','rejected','no_response','restore_failed','owner_lost','low_available','no_permission','missing_basis']:
  r=c.post(url,json={**body,'request_id':scenario,'scenario':scenario,'fault_node':'PV_03'}).json()
  assert r['passed']==2 and r['skipped']==7
  d=next(d for d in r['devices'] if d['node_id']=='PV_03');assert d['diagnosis']['action']
  assert d['status']==('CONDITION' if scenario=='low_available' else 'FAIL')
  if scenario in ['no_permission','missing_basis','low_available']:assert not d['commands']
  if scenario in ['restore_failed','owner_lost']:assert not d['restored'] and r['alarm_latched']
  if scenario=='owner_lost':assert len(d['commands'])==1
  if r['alarm_latched']:
   assert c.post(url,json={**body,'request_id':'blocked-'+scenario}).status_code==409
   assert c.post(url+'/'+r['id']+'/recover',json=body).status_code==200
  if scenario=='no_response':assert d['stages'][1]['status']=='PASS' and d['stages'][2]['status']=='FAIL' and d['restored']
  if scenario=='ack_timeout':assert d['commands'][0]['ack']=='UNKNOWN' and d['restored']


def test_control_blocks_configuration_difference_and_readonly(tmp_path):
 c,m,url,cfg,pv,meter,s,body=ready(tmp_path)
 rows=c.get(cfg,params={'session_id':s['id']}).json()['devices']
 target=next(r for d in rows if d['node_id']=='PV_03' for r in d['parameters'] if r['key']=='station_address')
 c.post(cfg,json={**body,'request_id':'difference','scenario':'difference','fault_parameter':target['id']})
 assert c.post(url,json=body).status_code==409
 c.post(pv,json={**body,'request_id':'readonly','scenario':'readonly','fault_node':'PV_03'})
 bess=url.replace('pv-control','bess-communication');c.post(bess,json={**body,'request_id':'again'})
 c.post(cfg,json={**body,'request_id':'normal'})
 r=c.post(url,json={**body,'request_id':'readonly-run'}).json()
 d=next(d for d in r['devices'] if d['node_id']=='PV_03')
 assert d['status']=='FAIL' and not d['commands']


def test_control_requires_bound_iems_control_connection(tmp_path):
 from backend.pv_control import control_inventory,simulate
 from test_fleet import setup
 c,m,pid,url=setup(tmp_path)
 m['edges']=[e for e in m['edges'] if not (e['edge_type']=='CONTROL' and e['to_port_id']=='PV_03.SETPOINT')]
 d=next(d for g in control_inventory(m,'EMS_MASTER') for d in g['devices'] if d['node_id']=='PV_03')
 assert d['path_valid'] and not d['control_valid']
 r=simulate(d,'normal','test')
 assert r['status']=='FAIL' and not r['commands']
