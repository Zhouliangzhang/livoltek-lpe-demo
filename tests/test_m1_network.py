from backend.domain import pilot,validate

def draft(m):
 e=next(e for e in m['edges'] if e['edge_type']=='COMMUNICATION')
 r={'id':'NC_TEST','base_edge_id':e['edge_id'],'environment':'SIMULATION','edge_type':'COMMUNICATION','from_port_id':e['from_port_id'],'to_port_id':e['to_port_id'],'purpose':'计量反馈','manufacturer_ref':'','cable_note':'','status':'PENDING'}
 m['project']['network_drafts']=[r];return r

def test_network_drafts_scope_and_ports():
 m=pilot();r=draft(m);assert validate(m)['valid']
 r['to_port_id']=r['from_port_id'];assert not validate(m)['valid']

def test_network_drafts_do_not_approve_or_mislabel_controls():
 m=pilot();r=draft(m);r['status']='APPROVED';assert not validate(m)['valid']
 r['status']='PENDING';r['edge_type']='CONTROL';assert not validate(m)['valid']

def test_network_duplicate_override_rejected():
 m=pilot();r=draft(m);m['project']['network_drafts'].append(dict(r,id='NC_OTHER'));assert not validate(m)['valid']
