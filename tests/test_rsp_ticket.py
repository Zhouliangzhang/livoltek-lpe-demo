from test_step14_handover import setup14

def test_rsp_ticket_to_m4_keeps_origin_and_is_idempotent(tmp_path):
 c,base,s,body,report=setup14(tmp_path)
 pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json(); project=pack['project']
 d=f'/api/projects/{project}/handovers/{pack["id"]}/delivery/manufacturer'
 for action in ['prepare','receipt']:assert c.post(d,json=dict(mode='SIMULATION',action=action,actor='Demo',acknowledged=True)).status_code==200
 root=f'/api/projects/{project}/rsp-tickets'
 r=c.post(root,json={'mode':'SIMULATION','package_id':pack['id']});assert r.status_code==200,r.text
 ticket=r.json(); url=root+'/'+ticket['id']+'/accept'
 accepted=c.post(url,json={'mode':'SIMULATION'});assert accepted.status_code==200,accepted.text
 case=accepted.json();assert c.post(url,json={'mode':'SIMULATION'}).json()['id']==case['id']
 detail=c.get(f'/api/projects/{project}/service/{case["id"]}?mode=SIMULATION').json()
 assert detail['origin'][0]['ticket_id']==ticket['id'] and detail['case']['package_id']==pack['id']
 assert c.post(url,json={'mode':'REAL'}).status_code==404

 assert c.get(root+'?mode=SIMULATION').json()['tickets'][0]['case_id']==case['id']
 assert c.get(root+'?mode=REAL').json()['tickets']==[]
 assert c.post(root,json={'mode':'REAL','package_id':pack['id']}).status_code==503
 service=f'/api/projects/{project}/service/{case["id"]}'
 for step in range(1,6):assert c.post(service+'/diagnose',json={'mode':'SIMULATION','step':step}).status_code==200
 for step in range(1,7):assert c.post(service+'/remedy',json={'mode':'SIMULATION','step':step,'actor':'Demo','acknowledged':True}).status_code==200
 first=c.post(service+'/report',json={'mode':'SIMULATION'}).json()
 assert first['origin'][0]['ticket_id']==ticket['id'] and first['simulation_recovered'] and not first['field_repaired']
 assert c.post(service+'/close',json={'mode':'SIMULATION'}).status_code==409
 assert c.app.state.store.record(pack['id'])==pack
