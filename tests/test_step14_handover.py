from test_step12_observation import setup12
import io,json,zipfile


def setup14(tmp_path):
 c,obs,deg,s,body=setup12(tmp_path)
 c.post(obs,json={**body,'scenario':'pv_loss','fault_node':'PV_03','pattern':'persistent'})
 base=obs.rsplit('/',1)[0];report=c.post(base+'/sat-report',json=body).json()
 return c,base,s,body,report


def test_archive_carries_open_items_and_immutable_evidence(tmp_path):
 c,base,s,body,report=setup14(tmp_path);url=base+'/handover'
 payload={**body,'report_id':report['id'],'prepared_by':'EPC演练工程师','acknowledged':True}
 response=c.post(url,json=payload);assert response.status_code==200,response.text
 pack=response.json();pid=report['identity']['project'];purl=f'/api/projects/{pid}/handovers'
 assert pack['mode']=='SIMULATION' and pack['status']=='SIMULATION_ARCHIVED'
 assert not pack['field_accepted'] and not pack['sat_passed']
 assert pack['baseline']['project']['project_id']==pid
 assert any(x['node_id']=='PV_03' and not x['resolved'] for x in pack['followup']['issues'])
 assert pack['followup']['pending'] and pack['followup']['incomplete']
 assert pack['report']['raw_evidence'] and pack['report']['id']==report['id']
 assert c.post(url,json=payload).json()['id']==pack['id']
 assert c.post(url,json={**payload,'prepared_by':'changed'}).status_code==409
 listed=c.get(purl).json();assert listed['packages'][0]['id']==pack['id']
 assert not c.get(purl,params={'mode':'REAL'}).json()['packages']
 assert c.get(purl+'/'+pack['id'],params={'mode':'REAL'}).status_code==404
 downloaded=c.get(purl+'/'+pack['id']+'/export');assert downloaded.status_code==200
 z=zipfile.ZipFile(io.BytesIO(downloaded.content));assert {'baseline.json','test-results.json','sat-report.json','sat-report.html','evidence.json','followup.json','manifest.json'}<=set(z.namelist())
 assert not json.loads(z.read('manifest.json'))['field_accepted']
 c.post(base+'/continuous-observation',json={**body,'request_id':'later14'})
 assert not c.get(purl).json()['packages'][0]['current']
 assert c.get(purl+'/'+pack['id']).json()['package']['seal_hash']==pack['seal_hash']
 assert c.post(url,json={**payload,'request_id':'stale14'}).status_code==409


def test_handover_requires_matching_report_and_ack(tmp_path):
 c,base,s,body,report=setup14(tmp_path);url=base+'/handover'
 payload={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':False}
 assert c.post(url,json=payload).status_code==422
 assert c.post(url,json={**payload,'acknowledged':True,'mode':'REAL'}).status_code==409
 assert c.post(url,json={**payload,'acknowledged':True,'report_id':s['id']}).status_code==404
 other=c.post(base+'/meter-workflow',json={'mode':'SIMULATION','edge_id':'CI-072','acknowledged':True,'operator':'other','reference':'sim'}).json()
 assert c.post(url,json={**payload,'acknowledged':True,'session_id':other['id']}).status_code==404

def test_field_draft_cannot_inherit_sim_and_seal_is_complete(tmp_path):
 from backend.handover import content_hash
 c,base,s,body,report=setup14(tmp_path)
 real=c.post(base+'/meter-workflow',json={'mode':'REAL','edge_id':'CI-072','acknowledged':True,'operator':'现场资料编制','reference':'尚未核验'}).json()
 real_body={'mode':'REAL','session_id':real['id'],'request_id':'real-report'}
 draft=c.post(base+'/sat-report',json=real_body).json()
 payload={**real_body,'prepared_by':'现场资料编制','acknowledged':True,'report_id':draft['id']}
 res=c.post(base+'/handover',json=payload);assert res.status_code==200,res.text
 pack=res.json();assert pack['status']=='FIELD_DRAFT_ARCHIVED' and not pack['field_accepted'] and not pack['sat_passed']
 assert len(pack['test_results'])==12 and all(x['status']!='SIM_PASS' for x in pack['test_results'])
 assert all(x['source']!='SIMULATOR' for x in pack['report']['raw_evidence'].values())
 sealed={k:v for k,v in pack.items() if k not in ('seal_hash','id','kind','project','created','request_signature','request_id')}
 assert content_hash(sealed)==pack['seal_hash']
 sealed['baseline']['view_layout']={};assert content_hash(sealed)!=pack['seal_hash']
 model=c.get('/api/projects/'+pack['project']).json()
 model['model']['project']['name']='变更后的工程名称'
 assert c.post('/api/projects',json={'model':model['model'],'expected_revision':model['revision']}).status_code==200
 assert c.post(base+'/handover',json={**payload,'request_id':'stale-model'}).status_code==409
 assert c.post(base+'/handover',json=payload).json()['id']==pack['id']
