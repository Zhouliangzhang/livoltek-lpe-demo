import pytest
from test_fleet import setup, ready


@pytest.mark.parametrize('capacity,export',[('limited',37.5),('available',0)])
def test_compound_fault_no_false_feedback_or_recovery(tmp_path,capacity,export):
    c,m,pid,url=setup(tmp_path);ready(c,pid);url=url.replace('/fleet','/dynamic-tests')
    body=dict(mode='SIMULATION',scenario='load_step',fault='meter_pv_reject',fault_node='PV_03',mitigation=True,recover=False,support_capacity=capacity)
    response=c.post(url,json=body);assert response.status_code==200,response.text
    r=response.json();end=r['trace'][-1]
    assert r['alarm']['active'] and r['alarm']['final_model_export_kw']==export
    assert r['recovery']['state']=='CONTROL_UNAVAILABLE'
    assert end['meter'] is None and not end['closed_loop']
    assert end['pv_command']==0 and end['pv']==107.5
    assert end['bess']==(50 if capacity=='limited' else 107.5)
    assert next(d for d in end['devices'] if d['node_id']=='PV_03')['status']=='FAULT'
    assert all(d['actual']==0 for d in end['devices'] if d['kind']=='PV' and d['node_id']!='PV_03')
    for s in r['trace']:
        assert abs(s['grid']-(s['load']+s['bess']-s['pv']))<.01
        if s['time']>=12:assert 0<=s['bess_command']<=s['charge_cap']
    assert r['manufacturer_basis']=='PENDING' and r['field_result'] is None
    assert c.post(url,json={**body,'fault_node':'BESS_03'}).status_code==422
    assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
    recovered=c.post(url,json={**body,'recover':True}).json()
    assert recovered['recovery']['state']=='RECOVERED'
    assert not recovered['alarm']['active']
    assert len(recovered['issues'])==2
    assert abs(recovered['trace'][-1]['grid']-25)<=5
