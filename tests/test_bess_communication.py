from test_fleet import setup
from test_meter_workflow import create


def prepare(tmp_path):
 c,m,pid,old=setup(tmp_path);meter=old.replace('/fleet','/meter-workflow');url=old.replace('/fleet','/bess-communication');s=create(c,meter).json()
 body={'session_id':s['id'],'acknowledged':True,'request_id':'bess-1'}
 assert c.post(url,json=body).status_code==409
 for step in ['selfcheck','route','identity','quality','reference','stability','complete']:
  assert c.post(meter+'/'+s['id']+'/run',json={'step':step}).status_code==200
 assert c.post(url,json=body).status_code==409
 pv=old.replace('/fleet','/pv-communication')
 assert c.post(pv,json={**body,'request_id':'pv-1'}).status_code==200
 return c,m,url,pv,meter,s,body


def test_bess_gates_snapshot_and_invalidation(tmp_path):
 c,m,url,pv,meter,s,body=prepare(tmp_path)
 r=c.post(url,json={**body,'scenario':'timeout','fault_node':'BESS_03'});assert r.status_code==200,r.text
 r=r.json();assert r['passed']==9 and r['failed']==1 and len(r['devices'])==10
 bad=next(d for d in r['devices'] if d['node_id']=='BESS_03')
 assert not bad['capability']['eligible'] and bad['capability']['charge_kw']==0
 assert r['totals']['charge_kw']==9*80 and r['totals']['discharge_kw']==9*100
 assert not r['power_control_allowed'] and r['field_result'] is None
 assert c.post(url,json={**body,'scenario':'timeout','fault_node':'BESS_03'}).json()['id']==r['id']
 assert c.post(url,json=body).status_code==409
 assert c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']==[]
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 assert c.get(url,params={'session_id':s['id']}).json()['current']
 c.post(pv,json={**body,'request_id':'pv-2'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 c.post(meter+'/'+s['id']+'/run',json={'step':'identity','scenario':'timeout'})
 assert c.post(url,json={**body,'request_id':'bess-2'}).status_code==409


def test_bess_capability_conditions_not_device_fault(tmp_path):
 from backend.bess_communication import inventory,simulate_device
 c,m,pid,old=setup(tmp_path)
 groups=inventory(m,'EMS_MASTER');assert sum(len(g['devices']) for g in groups)==10
 d=groups[0]['devices'][0]
 for scenario in ['timeout','driver_mismatch','bms_unknown','device_fault','unknown','stale','unit_mismatch','wrong_identity']:
  r=simulate_device(d,scenario);assert r['status']=='FAIL',scenario
  assert not r['capability']['eligible'] and r['capability']['charge_kw']==r['capability']['discharge_kw']==0
  assert r['diagnosis']['action']
 for scenario,charge,discharge in [('normal',80,100),('soc_low',80,0),('soc_high',0,100),('bms_forbid',0,100),('charge_only',80,0),('discharge_only',0,100)]:
  r=simulate_device(d,scenario)
  assert r['capability']['charge_kw']==charge and r['capability']['discharge_kw']==discharge
  assert r['status']==('PASS' if scenario=='normal' else 'CONDITION')
  assert r['action_tests']=={'charge':'NOT_TESTED','discharge':'NOT_TESTED'}
  assert r['manufacturer_basis']=='PENDING' and not r['power_control_allowed']
 assert simulate_device(d,'normal')['readings']['soc_pct']==55


def test_bess_mapping_and_model_change(tmp_path):
 from backend.bess_communication import inventory,simulate_device
 c,m,url,pv,meter,s,body=prepare(tmp_path)
 r=c.post(url,json=body);assert r.status_code==200
 m['project']['name']+=' changed'
 assert c.post('/api/projects',json={'model':m,'expected_revision':1}).status_code==200
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 assert c.post(url,json={**body,'request_id':'new'}).status_code==409
 b=[n for n in m['nodes'] if n['node_type']=='BESS'];a={a['asset_id']:a for a in m['device_assets']}
 a[b[0]['device_asset_id']]['firmware_version']='OTHER'
 a[b[1]['device_asset_id']]['serial_number']='DUP';a[b[2]['device_asset_id']]['serial_number']='DUP'
 g=inventory(m,'EMS_MASTER');assert len(g)==2
 d=next(d for g in g for d in g['devices'] if d['node_id']==b[1]['node_id'])
 assert simulate_device(d,'normal')['status']=='FAIL'
 assert d['components']['pcs_sn'] is None and d['components']['bms_sn'] is None


def test_bess_keeps_completed_evidence_after_bms_failure(tmp_path):
 from backend.bess_communication import inventory,simulate_device
 c,m,pid,old=setup(tmp_path)
 d=inventory(m,'EMS_MASTER')[0]['devices'][0]
 r=simulate_device(d,'bms_unknown')
 assert r['readings']['observed_sn']=='SIM-'+d['node_id']
 assert r['readings']['quality']=='GOOD'
 assert not r['capability']['eligible']
