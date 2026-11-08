import pytest
from test_fleet import setup, ready


@pytest.mark.parametrize('fault',['meter_comm_loss','meter_invalid'])
@pytest.mark.parametrize('recover',[True,False])
def test_meter_loss_no_hidden_feedback_and_recovery(tmp_path,fault,recover):
    c,m,pid,url=setup(tmp_path);ready(c,pid)
    url=url.replace('/fleet','/dynamic-tests')
    body=dict(mode='SIMULATION',scenario='load_step',fault=fault,mitigation=True,recover=recover)
    response=c.post(url,json=body)
    assert response.status_code==200,response.text
    r=response.json();trace=r['trace']
    assert r['source']=='SIMULATOR' and r['field_result'] is None
    assert r['manufacturer_basis']=='PENDING'
    bad=[s for s in trace if s['time']>=10 and (not recover or s['time']<29)]
    assert all(s['meter'] is None and not s['closed_loop'] for s in bad)
    assert all(s['meter_raw'] is None for s in bad) if fault=='meter_comm_loss' else all(s['meter_raw']==1e9 for s in bad)
    for s in trace:
        assert abs(s['grid']-(s['load']+s['bess']-s['pv']))<.01
        if s['time']>=12 and (not recover or s['time']<32):
            assert s['pv_command']==0 and s['bess_command']==0
    # Baseline must also lose feedback: it holds commands, never sees model truth.
    b=c.post(url,json={**body,'mitigation':False}).json()
    assert all(s['pv_command']==b['trace'][19]['pv_command'] for s in b['trace'] if 10<=s['time']<29)
    if recover:
        assert trace[58]['feedback_state']=='QUALIFYING'
        assert r['recovery']['state']=='RECOVERED'
        assert abs(trace[-1]['grid']-25)<=5
    else:
        assert r['recovery']['state']=='FEEDBACK_UNAVAILABLE'
        assert trace[-1]['meter'] is None
        assert trace[-1]['pv']==0 and trace[-1]['bess']==0
    assert c.post(url,json={**body,'mode':'REAL'}).status_code==503
    assert c.post(url,json={**body,'fault_node':'BESS_03'}).status_code==422
