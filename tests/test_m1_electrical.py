from backend.domain import pilot,validate

def test_electrical_drafts_validate_ports_circuits_and_environment():
    m=pilot();e=next(e for e in m['edges'] if e['edge_type']=='ELECTRICAL');c=next(n for n in m['nodes'] if n['node_type']=='BREAKER')
    r={'id':'DRAFT_1','base_edge_id':e['edge_id'],'environment':'SIMULATION','from_port_id':e['from_port_id'],'to_port_id':e['to_port_id'],'circuit_id':c['node_id'],'epc_ref':'','manufacturer_ref':'','status':'PENDING'}
    m['project']['electrical_drafts']=[r]
    assert validate(m)['valid']
    r['to_port_id']=r['from_port_id'];assert not validate(m)['valid']
    r['to_port_id']=e['to_port_id'];r['circuit_id']='MISSING';assert not validate(m)['valid']

def test_electrical_drafts_reject_duplicate_and_invalid_status():
    m=pilot();e=next(e for e in m['edges'] if e['edge_type']=='ELECTRICAL');c=next(n for n in m['nodes'] if n['node_type']=='BREAKER')
    r={'id':'DRAFT_1','base_edge_id':e['edge_id'],'environment':'OFFLINE','from_port_id':e['from_port_id'],'to_port_id':e['to_port_id'],'circuit_id':c['node_id'],'epc_ref':'','manufacturer_ref':'','status':'APPROVED'}
    m['project']['electrical_drafts']=[r];assert not validate(m)['valid']
    r['status']='PENDING';m['project']['electrical_drafts'].append(dict(r,id='DRAFT_2'));assert not validate(m)['valid']
