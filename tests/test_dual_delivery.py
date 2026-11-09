from test_step14_handover import setup14
import io,zipfile,json

def test_dual_delivery_paths_are_independent_and_environment_bound(tmp_path):
 c,base,s,body,report=setup14(tmp_path)
 pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json()
 root=f'/api/projects/{pack["project"]}/handovers/{pack["id"]}/delivery'
 assert c.get(root+'?mode=SIMULATION').status_code==200
 req=dict(mode='SIMULATION',action='prepare',actor='Demo',acknowledged=True)
 a=c.post(root+'/epc',json=req);assert a.status_code==200,a.text
 assert c.post(root+'/epc',json={**req,'action':'receipt','acknowledged':False}).status_code==422
 epc=c.post(root+'/epc',json={**req,'action':'receipt'}).json()
 assert epc['audience']=='epc' and epc['simulated'] and not epc['field_accepted']
 assert not c.get(root+'?mode=SIMULATION').json()['manufacturer']['receipt']
 assert c.post(root+'/manufacturer',json={**req,'action':'receipt'}).status_code==409
 assert c.post(root+'/manufacturer',json=req).status_code==200
 receipt=c.post(root+'/manufacturer',json={**req,'action':'receipt'}).json()
 assert receipt['remote_control_enabled'] is False and receipt['platform']=='SIM-RSP'
 assert c.post(root+'/manufacturer',json={**req,'action':'receipt'}).json()['id']==receipt['id']
 export=c.get(root+'/epc/export?mode=SIMULATION');assert export.status_code==200
 with zipfile.ZipFile(io.BytesIO(export.content)) as z:
  manifest=json.loads(z.read('manifest.json'));assert manifest['baseline_id']==pack['id']
  assert 'technical-summary.html' in z.namelist()
 assert c.get(root+'?mode=REAL').status_code==404
 assert c.app.state.store.record(pack['id'])==pack
