from test_step14_handover import setup14


def test_m4_case_diagnosis_and_environment_isolation(tmp_path):
    c,base,s,body,report=setup14(tmp_path)
    pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json()
    project=pack['project'];root=f'/api/projects/{project}/service'
    response=c.get(root+'?mode=SIMULATION');assert response.status_code==200,response.text
    assert response.json()['packages'][0]['id']==pack['id']
    request=dict(mode='SIMULATION',package_id=pack['id'],device_id='METER_PCC',reporter='EPC',symptom='零馈表失联',occurred_at='2026-11-09T09:00',scenario='configuration',safe_readonly=True,request_id='case-1')
    case=c.post(root,json=request);assert case.status_code==200,case.text
    case=case.json();url=root+'/'+case['id']
    assert c.post(root,json=request).json()['id']==case['id']
    assert c.get(url+'?mode=REAL').status_code==404
    assert c.post(root,json={**request,'mode':'REAL','request_id':'real'}).status_code==409
    assert c.post(url+'/diagnose',json={'mode':'SIMULATION','step':2}).status_code==409
    for step in range(1,6):
        result=c.post(url+'/diagnose',json={'mode':'SIMULATION','step':step})
        assert result.status_code==200,result.text
    result=result.json()
    assert result['conclusion']['category']=='CONFIGURATION'
    assert result['field_result'] is None and not result['physical_actions']
    draft=c.post(url+'/support',json={'mode':'SIMULATION'}).json()
    assert draft['sent'] is False and len(draft['evidence_ids'])==5
    assert c.get(url+'?mode=SIMULATION').json()['case']['baseline_hash']==pack['model_hash']
    assert c.get(f'/api/projects/{project}/handovers/{pack["id"]}').json()['package']==pack


def test_m4_categories_changes_and_stale_context(tmp_path):
    c,base,s,body,report=setup14(tmp_path)
    pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json()
    project=pack['project'];root=f'/api/projects/{project}/service';db=c.app.state.store
    current=db.get(project);model=current['model'];model['project']['name']='changed after handover';db.save(model,current['revision'])
    for scenario,category in [('installation','INSTALLATION'),('product','PRODUCT_SUSPECTED'),('operating','OPERATING_CONDITION'),('unknown','UNCONFIRMED')]:
        case=c.post(root,json=dict(mode='SIMULATION',package_id=pack['id'],device_id='METER_PCC',reporter='EPC',symptom='失联',occurred_at='2026-11-09',scenario=scenario,safe_readonly=True,request_id=scenario)).json()
        assert case['changes'] and case['subsequent_revisions']
        url=root+'/'+case['id']
        for step in range(1,6):
            r=c.post(url+'/diagnose',json={'mode':'SIMULATION','step':step});assert r.status_code==200,r.text
        result=r.json();assert result['conclusion']['category']==category
        assert result['conclusion']['quality_liability']=='未判定' and not result['conclusion']['restored']
        assert c.post(url+'/diagnose',json={'mode':'SIMULATION','step':5}).json()['id']==result['id']
    current=db.get(project);model=current['model'];model['project']['name']='changed again';db.save(model,current['revision'])
    assert c.get(url+'?mode=SIMULATION').json()['stale']
    assert c.post(url+'/diagnose',json={'mode':'SIMULATION','step':5}).status_code==409
    assert db.record(pack['id'])==pack


def test_m4_remedy_requires_approval_and_preserves_evidence(tmp_path):
    c,base,s,body,report=setup14(tmp_path)
    pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json()
    root=f'/api/projects/{pack["project"]}/service'
    case=c.post(root,json=dict(mode='SIMULATION',package_id=pack['id'],device_id='METER_PCC',reporter='EPC',symptom='失联',occurred_at='2026-11-09',safe_readonly=True,request_id='remedy')).json()
    url=root+'/'+case['id']; req=dict(mode='SIMULATION',step=1)
    assert c.post(url+'/remedy',json=req).status_code==409
    for i in range(1,6):assert c.post(url+'/diagnose',json=dict(mode='SIMULATION',step=i)).status_code==200
    original=c.get(url+'?mode=SIMULATION').json()['steps']
    preview=c.get(url+'/report?mode=SIMULATION');assert preview.status_code==200,preview.text
    assert not preview.json()['current']['can_close']
    first=c.post(url+'/report',json={'mode':'SIMULATION'}).json()
    assert c.post(url+'/close',json={'mode':'SIMULATION'}).status_code==409
    assert c.post(url+'/remedy',json=req).status_code==200
    assert c.post(url+'/remedy',json={**req,'step':3}).status_code==409
    assert c.post(url+'/remedy',json={**req,'step':2}).status_code==422
    for i in range(2,7):
        r=c.post(url+'/remedy',json={**req,'step':i,'actor':'EPC demo','acknowledged':True})
        assert r.status_code==200,r.text
    final=r.json(); assert final['simulation_recovered'] and final['field_repaired'] is False
    assert final['manufacturer_basis']=='PENDING' and len(final['evidence']['samples'])==6
    assert c.post(url+'/remedy',json={**req,'step':6,'actor':'EPC demo','acknowledged':True}).json()['id']==final['id']
    d=c.get(url+'?mode=SIMULATION').json(); assert d['steps']==original and len(d['remedy'])==6
    assert c.post(url+'/remedy',json={**req,'mode':'REAL'}).status_code==404
    assert c.app.state.store.record(pack['id'])==pack
    report=c.post(url+'/report',json={'mode':'SIMULATION'}).json()
    assert report['id']!=first['id'] and report['simulation_recovered'] and not report['field_repaired']
    assert len(report['evidence'])==11 and report['pending'] and not report['can_close']
    assert c.post(url+'/report',json={'mode':'SIMULATION'}).json()['id']==report['id']
    assert c.app.state.store.record(first['id'])==first
    assert len(c.get(url+'/report?mode=SIMULATION').json()['versions'])==2
    assert c.get(url+'/report?mode=REAL').status_code==404
    assert c.post(url+'/close',json={'mode':'SIMULATION'}).status_code==409
    current=c.app.state.store.get(pack['project']);c.app.state.store.save(current['model'],current['revision'])
    assert c.post(url+'/remedy',json=req).status_code==409


def test_m4_followup_resolution_and_simulation_closure(tmp_path):
    c,base,s,body,report=setup14(tmp_path)
    pack=c.post(base+'/handover',json={**body,'report_id':report['id'],'prepared_by':'EPC','acknowledged':True}).json()
    project=pack['project']; root=f'/api/projects/{project}/service'
    case=c.post(root,json=dict(mode='SIMULATION',package_id=pack['id'],device_id='METER_PCC',reporter='EPC',symptom='失联',occurred_at='2026-11-09',safe_readonly=True,request_id='followup')).json()
    url=root+'/'+case['id']
    for i in range(1,6): c.post(url+'/diagnose',json=dict(mode='SIMULATION',step=i))
    for i in range(1,7): c.post(url+'/remedy',json=dict(mode='SIMULATION',step=i,actor='Demo',acknowledged=True))
    original=c.post(url+'/report',json={'mode':'SIMULATION'}).json()
    evidence=[r['id'] for r in c.get(url+'?mode=SIMULATION').json()['remedy'] if r['step']>=4]
    request=dict(mode='SIMULATION',item_id='manufacturer-1',role='MANUFACTURER',actor='模拟厂家工程师',note='演练依据核对完成',document_ref='SIM-BASIS-01 v1',evidence_ids=evidence,acknowledged=True)
    assert c.post(url+'/followup',json={**request,'evidence_ids':['fake']}).status_code==422
    assert c.post(url+'/followup',json={**request,'role':'EPC'}).status_code==422
    assert c.post(url+'/close',json={'mode':'SIMULATION'}).status_code==409
    for item in ['manufacturer-1','manufacturer-2','manufacturer-3','manufacturer-4','field-repair']:
        r=c.post(url+'/followup',json={**request,'item_id':item,'role':'EPC' if item=='field-repair' else 'MANUFACTURER'})
        assert r.status_code==200,r.text
    current=c.get(url+'/report?mode=SIMULATION').json()
    assert current['current']['can_close'] and len(current['current']['resolved'])==5
    assert len(current['versions'])==6
    closed=c.post(url+'/close',json={'mode':'SIMULATION'});assert closed.status_code==200,closed.text
    assert closed.json()['service_status']=='SIMULATION_CLOSED' and not closed.json()['field_repaired']
    assert c.post(url+'/close',json={'mode':'SIMULATION'}).json()['id']==closed.json()['id']
    assert c.post(url+'/followup',json=request).status_code==409
    assert c.post(url+'/close',json={'mode':'REAL'}).status_code==404
    assert c.app.state.store.record(original['id'])==original
    assert c.app.state.store.record(pack['id'])==pack
