from backend.domain import pilot,validate

def test_structure_metadata_remains_pending_and_references_structure():
    m=pilot();n=next(n for n in m['nodes'] if n['node_type']=='PCC')
    n['attributes']['engineering']={'circuit_id':'PCC-C01','voltage_level':'LV','phase_system':'','purpose':'','epc_drawing_ref':'','manufacturer_ref':'','structure_role':'STRUCTURE','basis_status':'PENDING'}
    assert validate(m)['valid']
    n['attributes']['engineering']['basis_status']='APPROVED'
    assert not validate(m)['valid']
