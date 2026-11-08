from backend.domain import pilot, validate

def record(m):
    n=next(n for n in m['nodes'] if n.get('device_asset_id'))
    parent=next(n for n in m['nodes'] if not n.get('device_asset_id') and n['node_type']=='PCC')
    r={'sn':'SIM-TEST','firmware':'DEMO','factory_firmware':'','location':'演练位置','structure':parent['node_id'],'circuit':'','source':'SIMULATION_QR','raw_scan':'','basis_status':'PENDING','updated_at':'2026-11-08T12:00:00Z','replacement_reason':''}
    n.setdefault('attributes',{})['identity_records']={'SIMULATION':r}
    return n,r

def test_identity_rejects_duplicate_sn_in_environment():
    m=pilot();n,r=record(m)
    other=next(x for x in m['nodes'] if x.get('device_asset_id') and x!=n)
    other.setdefault('attributes',{})['identity_records']={'SIMULATION':dict(r)}
    assert not validate(m)['valid']

def test_identity_rejects_simulation_as_real_and_invalid_structure():
    m=pilot();n,r=record(m)
    assert validate(m)['valid']
    n['attributes']['identity_records']={'REAL':r}
    assert not validate(m)['valid']
    n['attributes']['identity_records']={'SIMULATION':dict(r,structure='MISSING')}
    assert not validate(m)['valid']

def test_identity_never_claims_approved_basis():
    m=pilot();n,r=record(m);r['basis_status']='APPROVED'
    assert not validate(m)['valid']
