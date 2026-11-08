from test_fleet import setup
from test_meter_workflow import create


def test_pv_scan_gates_all_devices_and_invalidates(tmp_path):
 c,m,pid,old=setup(tmp_path);meter=old.replace('/fleet','/meter-workflow');url=old.replace('/fleet','/pv-communication');s=create(c,meter).json()
 body={'session_id':s['id'],'mode':'SIMULATION','acknowledged':True,'request_id':'scan-1','scenario':'timeout','fault_node':'PV_03'}
 assert c.post(url,json=body).status_code==409
 for step in ['selfcheck','route','identity','quality','reference','stability','complete']:
  assert c.post(meter+'/'+s['id']+'/run',json={'step':step}).status_code==200
 r=c.post(url,json=body);assert r.status_code==200,r.text
 r=r.json();assert len(r['devices'])==10 and r['failed']==1 and r['passed']==9
 assert next(d for d in r['devices'] if d['node_id']=='PV_03')['diagnosis']['layer']=='L4'
 assert next(d for d in r['devices'] if d['node_id']=='PV_10')['status']=='PASS'
 assert not r['power_control_allowed'] and r['field_result'] is None
 assert r['scope']['kind']=='PV_READ_ONLY' and len(r['scope']['node_ids'])==10
 assert c.post(url,json=body).json()['id']==r['id']
 assert c.post(url,json={**body,'scenario':'normal'}).status_code==409
 d=c.get(url,params={'mode':'SIMULATION','session_id':s['id']}).json();assert d['current'] and d['pcc_ready']
 assert c.get(url,params={'mode':'REAL','session_id':s['id']}).json()['records']==[]
 assert c.post(url,json={**body,'mode':'REAL','request_id':'field'}).status_code==503
 c.post(meter+'/'+s['id']+'/run',json={'step':'identity','scenario':'timeout'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 assert c.post(url,json={**body,'request_id':'scan-2'}).status_code==409


def test_pv_inventory_groups_and_capability(tmp_path):
 from backend.pv_communication import inventory, simulate_device
 c,m,pid,old=setup(tmp_path)
 pv=[n for n in m['nodes'] if n['node_type']=='PV_INVERTER']
 a={a['asset_id']:a for a in m['device_assets']}
 a[pv[0]['device_asset_id']]['firmware_version']='FW-2'
 a[pv[1]['device_asset_id']]['serial_number']='DUP-SN';a[pv[2]['device_asset_id']]['serial_number']='DUP-SN'
 groups=inventory(m,'EMS_MASTER');assert len(groups)==2
 devices=[d for g in groups for d in g['devices']];assert len(devices)==10
 d=next(d for d in devices if d['node_id']==pv[1]['node_id'])
 assert simulate_device(d,'normal')['status']=='FAIL'
 d=next(d for d in devices if d['node_id']==pv[0]['node_id'])
 for fault in ['wrong_identity','driver_mismatch','stale','unit_mismatch','capability_missing']:
  r=simulate_device(d,fault);assert r['status']=='FAIL' and r['diagnosis']['action']
 r=simulate_device(d,'readonly');assert r['status']=='PASS' and not r['readings']['remote_write']
 assert r['manufacturer_basis']=='PENDING'

def test_pv_missing_path_and_model_change(tmp_path):
 from backend.pv_communication import inventory, simulate_device
 c,m,pid,old=setup(tmp_path,disconnected=True)
 d=next(d for g in inventory(m,'EMS_MASTER') for d in g['devices'] if d['node_id']=='PV_01')
 assert not d['path_valid'] and simulate_device(d,'normal')['status']=='FAIL'
 meter=old.replace('/fleet','/meter-workflow');url=old.replace('/fleet','/pv-communication');s=create(c,meter).json()
 for step in ['selfcheck','route','identity','quality','reference','stability','complete']:
  c.post(meter+'/'+s['id']+'/run',json={'step':step})
 body={'session_id':s['id'],'acknowledged':True,'request_id':'all'}
 r=c.post(url,json=body);assert r.status_code==200 and r.json()['failed']==1
 m['project']['name']+=' updated';assert c.post('/api/projects',json={'model':m,'expected_revision':1}).status_code==200
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 assert c.post(url,json={**body,'request_id':'new'}).status_code==409
