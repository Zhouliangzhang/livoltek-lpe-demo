from backend.domain import pilot,validate

def test_boundary_references_and_draft_status():
    model=pilot()
    model['project']['system_boundary']={'timezone':'Africa/Johannesburg','scope':'PCC domain','reference':'DRAFT-01','status':'DRAFT','domains':[{'id':'D1','pcc_id':'','controller_id':'','scope':''}]}
    assert validate(model)['valid']
    model['project']['system_boundary']['domains'][0]['pcc_id']='NOT_A_PCC'
    assert not validate(model)['valid']
    model['project']['system_boundary']['domains'][0]['pcc_id']=''
    model['project']['system_boundary']['status']='APPROVED'
    assert not validate(model)['valid']

def test_boundary_unique_domains_and_timezone():
    model=pilot()
    d={'id':'D1','pcc_id':'','controller_id':'','scope':''}
    model['project']['system_boundary']={'timezone':'Invalid/Zone','scope':'scope','reference':'ref','status':'DRAFT','domains':[d,dict(d)]}
    errors=validate(model)['errors']
    assert any('控制域编号' in e for e in errors)
    assert any('时区' in e for e in errors)
