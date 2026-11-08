from tests.test_m1_delivery import setup
from backend.configuration_readback import session_inventory,compare

def test_readback_uses_frozen_new_m1_configuration(setup):
    c,db,p,b=setup
    rows=session_inventory({}, {'m1_basis':{'environment':'SIMULATION','baseline':b}}, 'SIMULATION')
    pv=next(d for d in rows if d['node_id']=='PV_01')
    assert len(pv['parameters'])==1
    r=pv['parameters'][0]
    assert r['planned']=='1' and r['m1_step']==7 and r['focus_label']=='PV_01.RS485 address'
    assert compare(r,'difference')['status']=='DIFFERENCE'
    assert compare(r,'normal')['status']=='CANDIDATE_MATCH'
    missing=next(d for d in rows if d['node_id']=='BESS_01')['parameters'][0]
    assert compare(missing,'normal')['status']=='PENDING'
    assert all(r['approved'] is None and r['m1_actual'] is None for d in rows for r in d['parameters'])
