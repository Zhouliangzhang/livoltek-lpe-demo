from test_step14_handover import setup14


def setup_tracking(tmp_path):
 c,base,s,body,r=setup14(tmp_path)
 pack=c.post(base+'/handover',json={**body,'report_id':r['id'],'prepared_by':'EPC','acknowledged':True}).json()
 url=f"/api/projects/{pack['project']}/handovers/{pack['id']}/tracking"
 return c,base,s,body,pack,url


def test_tracking_retest_version_and_original_retained(tmp_path):
 c,base,s,body,pack,url=setup_tracking(tmp_path)
 response=c.get(url);assert response.status_code==200,response.text
 data=response.json();task=next(t for t in data['items'] if t['kind']=='ISSUE' and t['node_id']=='PV_03')
 event={'item_id':task['id'],'action':'SUBMIT','actor':'EPC工程师','note':'已核对PV_03通信并完成模拟处理','reference':'SIM-WORK-01','request_id':'submit1','expected_event_id':''}
 res=c.post(url,json=event);assert res.status_code==200,res.text
 assert c.post(url,json=event).json()['id']==res.json()['id']
 assert c.post(url,json={**event,'request_id':'stale-edit'}).status_code==409
 run=c.post(base+'/continuous-observation',json={**body,'request_id':'retest-m3'}).json()
 report=c.post(base+'/sat-report',json={**body,'request_id':'report-m3'}).json()
 link={**event,'action':'LINK_RETEST','request_id':'link1','expected_event_id':res.json()['id'],'report_id':report['id'],'evidence_id':run['id']}
 saved=c.post(url,json=link);assert saved.status_code==200,saved.text
 d=c.get(url).json();task=next(t for t in d['items'] if t['id']==task['id']);assert task['status']=='SIM_VERIFIED'
 rev=c.post(url.replace('/tracking','/revisions'),json={'mode':'SIMULATION','report_id':report['id'],'prepared_by':'EPC','acknowledged':True,'request_id':'revision1','expected_tracking_hash':d['tracking_hash']});assert rev.status_code==200,rev.text
 child=rev.json();assert child['parent_package_id']==pack['id'] and child['root_package_id']==pack['id'] and child['handover_version']==2
 assert child['tracking_snapshot']['items'] and not child['field_accepted']
 child_state=c.get(url.replace(pack['id'],child['id'])).json();assert child_state['tracking_hash']==child_state['frozen_tracking_hash']
 assert c.get(url.replace('/tracking','')).json()['package']['seal_hash']==pack['seal_hash']
 assert c.post(url.replace('/tracking','/revisions'),json={'mode':'SIMULATION','report_id':report['id'],'prepared_by':'EPC','acknowledged':True,'request_id':'revision1','expected_tracking_hash':d['tracking_hash']}).json()['id']==child['id']
 c.post(base+'/continuous-observation',json={**body,'request_id':'new-failure','scenario':'pv_loss','fault_node':'PV_03','pattern':'persistent'})
 assert next(t for t in c.get(url).json()['items'] if t['id']==task['id'])['status']=='RETEST_STALE'


def test_manufacturer_and_wrong_evidence_cannot_close(tmp_path):
 c,base,s,body,pack,url=setup_tracking(tmp_path)
 data=c.get(url);assert data.status_code==200,data.text
 t=next(t for t in data.json()['items'] if t['party']=='MANUFACTURER' and t['step']==6)
 event={'item_id':t['id'],'action':'SUBMIT','actor':'资料编制人','note':'已登记厂家文档引用，尚待适用性确认','reference':'DOC-DRAFT-01','request_id':'mfr1','expected_event_id':''}
 r=c.post(url,json=event);assert r.status_code==200,r.text
 assert next(x for x in c.get(url).json()['items'] if x['id']==t['id'])['status']=='WAIT_MANUFACTURER'
 # Different-step and old evidence cannot be attached as successful retest.
 old=pack['test_results'][11]['latest_id']
 assert c.post(url,json={**event,'action':'LINK_RETEST','report_id':pack['report_id'],'evidence_id':old,'request_id':'bad','expected_event_id':r.json()['id']}).status_code==409
 assert c.get(url,params={'mode':'REAL'}).status_code==404
 assert c.post(url,json={**event,'mode':'REAL','request_id':'cross'}).status_code==404

def test_failed_retest_and_manufacturer_reference_remain_open(tmp_path):
 c,base,s,body,pack,url=setup_tracking(tmp_path)
 items=c.get(url).json()['items'];fault=next(x for x in items if x['kind']=='ISSUE')
 event={'item_id':fault['id'],'action':'SUBMIT','actor':'EPC','note':'提交模拟处理','reference':'SIM-01','request_id':'start','expected_event_id':''}
 submit=c.post(url,json=event).json()
 run=c.post(base+'/continuous-observation',json={**body,'request_id':'still-fault','scenario':'pv_loss','fault_node':'PV_03','pattern':'persistent'}).json()
 report=c.post(base+'/sat-report',json={**body,'request_id':'still-report'}).json()
 r=c.post(url,json={**event,'action':'LINK_RETEST','request_id':'fail-link','expected_event_id':submit['id'],'report_id':report['id'],'evidence_id':run['id']})
 assert r.status_code==200 and r.json()['status']=='RETEST_BLOCKED'
 mfr=next(x for x in items if x['kind']=='PENDING' and x['party']=='MANUFACTURER' and x['step']==6)
 event={**event,'item_id':mfr['id'],'request_id':'mfr-submit','note':'厂家草稿引用，尚未核验'}
 sub=c.post(url,json=event).json()
 run=c.post(base+'/configuration-readback',json={**body,'request_id':'mfr-readback'}).json()
 report=c.post(base+'/sat-report',json={**body,'request_id':'mfr-report'}).json()
 r=c.post(url,json={**event,'action':'LINK_RETEST','request_id':'mfr-link','expected_event_id':sub['id'],'report_id':report['id'],'evidence_id':run['id']})
 assert r.status_code==200,r.text
 assert r.json()['status']=='WAIT_MANUFACTURER' and r.json()['field_accepted'] is False
