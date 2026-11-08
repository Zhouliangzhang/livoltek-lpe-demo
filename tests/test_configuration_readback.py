from test_bess_communication import prepare


def test_configuration_readback_gates_and_modes(tmp_path):
 c,m,bess,pv,meter,s,body=prepare(tmp_path);url=bess.replace('bess-communication','configuration-readback')
 assert c.post(url,json=body).status_code==409
 assert c.post(bess,json=body).status_code==200
 inv=c.get(url,params={'session_id':s['id']}).json()
 assert len(inv['devices'])==22 and inv['prerequisite_ready']
 row=next(r for d in inv['devices'] if d['node_id']=='PV_03' for r in d['parameters'] if r['key']=='station_address')
 req={**body,'scenario':'difference','fault_parameter':row['id']}
 r=c.post(url,json=req);assert r.status_code==200,r.text
 r=r.json();assert r['counts']['DIFFERENCE']==1 and r['counts']['MATCH']==0
 assert len(r['devices'])==22 and not r['power_control_allowed'] and r['field_result'] is None
 assert c.post(url,json=req).json()['id']==r['id']
 assert c.post(url,json=body).status_code==409
 assert c.get(url,params={'session_id':s['id'],'mode':'REAL'}).json()['records']==[]
 assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
 c.post(bess,json={**body,'request_id':'bess-again'})
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 c.post(meter+'/'+s['id']+'/run',json={'step':'identity','scenario':'timeout'})
 assert c.post(url,json={**body,'request_id':'new'}).status_code==409


def test_readback_approved_not_candidate_and_units(tmp_path):
 from backend.configuration_readback import inventory,compare
 c,m,bess,pv,meter,s,body=prepare(tmp_path)
 d=next(d for d in inventory(m) if d['node_id']=='PV_03')
 r=next(r for r in d['parameters'] if r['key']=='station_address')
 assert r['approved'] is None and compare(r,'normal')['status']=='CANDIDATE_MATCH'
 m['parameters'].append(dict(parameter_id='approved-pv03',scope='NODE',owner_id='PV_03',name='station_address',planned=None,actual=None,approved=dict(value='3',unit=r['unit'],source='MANUFACTURER',status='APPROVED',source_ref='TEST-APPROVAL'),review_status='APPROVED',reference_doc='TEST-APPROVAL',criticality='NORMAL'))
 r=next(r for d in inventory(m) if d['node_id']=='PV_03' for r in d['parameters'] if r['key']=='station_address')
 assert r['approved']=='3' and compare(r,'normal')['status']=='MATCH'
 assert compare(r,'difference')['status']=='DIFFERENCE'
 assert compare(r,'unreadable')['status']=='UNREAD'
 assert compare(r,'unit_mismatch')['status']=='UNIT_MISMATCH'
 assert compare(r,'type_mismatch')['status']=='TYPE_MISMATCH'
 assert compare(r,'normal')['manufacturer_basis']=='PENDING'
 m['parameters'][-1]['review_status']='DRAFT'
 assert next(r for d in inventory(m) if d['node_id']=='PV_03' for r in d['parameters'] if r['key']=='station_address')['approved'] is None
 m['parameters'][-1]['review_status']='APPROVED';m['parameters'][-1]['approved']['unit']='invalid'
 assert next(r for d in inventory(m) if d['node_id']=='PV_03' for r in d['parameters'] if r['key']=='station_address')['approved'] is None


def test_readback_blank_is_missing_and_model_change_invalidates(tmp_path):
 from backend.configuration_readback import inventory,compare
 c,m,bess,pv,meter,s,body=prepare(tmp_path)
 row=next(r for d in inventory(m) for r in d['parameters'])
 row.update(approved=None,planned='')
 assert compare(row,'normal')['status']=='PENDING'
 row.update(approved=0,planned=1)
 assert compare(row,'normal')['actual']==0 and compare(row,'normal')['status']=='MATCH'
 url=bess.replace('bess-communication','configuration-readback')
 c.post(bess,json=body);assert c.post(url,json=body).status_code==200
 m['project']['name']+=' revised';assert c.post('/api/projects',json={'model':m,'expected_revision':1}).status_code==200
 assert not c.get(url,params={'session_id':s['id']}).json()['current']
 assert c.post(url,json={**body,'request_id':'changed'}).status_code==409
