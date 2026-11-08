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
    current=c.app.state.store.get(pack['project']);c.app.state.store.save(current['model'],current['revision'])
    assert c.post(url+'/remedy',json=req).status_code==409
