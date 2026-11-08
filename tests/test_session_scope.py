from test_fleet import setup

def test_step01_freezes_scope_and_separates_pending_field(tmp_path):
 c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow')
 d=c.get(url).json();assert d['preflights']['CI-072']['devices']
 body={'mode':'SIMULATION','edge_id':'CI-072','acknowledged':True,'operator':'EPC','reference':'演练前提','witness_requirement':'EPC_WITNESS','witness_name':'演练见证人','scope':'METER_VALIDATION'}
 s=c.post(url,json=body).json();assert s['snapshot']['model_hash'] and len(s['snapshot']['devices'])==2
 assert s['gate']['next_step_allowed'] and not s['gate']['field_release']
 assert s['snapshot']['test_package']['version']=='SIM-METER-SEQ-1'
 body['mode']='REAL';s=c.post(url,json=body).json()
 assert not s['gate']['next_step_allowed'] and not s['gate']['field_release']
 assert s['snapshot']['controller_binding']['observed_sn'] is None
 assert any(g['owner']=='EPC 现场工程师' for g in s['gate']['gaps'])
 assert all(g['reason'] and g['action'] for g in s['gate']['gaps'])
 assert c.post(url,json={**body,'witness_name':''}).status_code==422

def test_read_only_scope_cannot_release_meter_validation(tmp_path):
 c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow')
 s=c.post(url,json={'mode':'SIMULATION','edge_id':'CI-072','acknowledged':True,'operator':'EPC','reference':'演练','scope':'READ_ONLY'}).json()
 action=url+'/'+s['id']+'/run'
 for step in ['selfcheck','route','identity','quality']:
  assert c.post(action,json={'step':step}).json()['status']=='PASS'
 for step in ['reference','stability','complete']:
  assert c.post(action,json={'step':step}).status_code==409
