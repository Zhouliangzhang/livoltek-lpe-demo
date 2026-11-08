import pytest
from test_fleet import setup,ready

@pytest.mark.parametrize('fault',['bess_block','bess_comm_loss'])
def test_degradation_reallocates_and_qualified_recovery(tmp_path,fault):
    c,m,pid,url=setup(tmp_path);ready(c,pid);url=url.replace('/fleet','/dynamic-tests')
    body={'mode':'SIMULATION','scenario':'charge_limited','fault':fault,'fault_node':'BESS_03','mitigation':True,'recover':True}
    r=c.post(url,json=body);assert r.status_code==200,r.text
    r=r.json();assert r['recovery']['state']=='RECOVERED'
    def device(s):return next(d for d in s['devices'] if d['node_id']=='BESS_03')
    assert all(device(s)['command']==0 for s in r['trace'] if 12<=s['time']<=32)
    assert device(r['trace'][56])['control_state']=='QUALIFYING'
    assert device(r['trace'][-1])['control_state']=='NORMAL'
    assert all(abs(s['grid']-25)<=5 for s in r['trace'] if 18<=s['time']<24)
    assert abs(r['trace'][-1]['grid']-25)<=5
    assert any(e['phase']=='DERATED' for e in r['control_events'])
    if fault=='bess_comm_loss':
        assert all(device(s)['feedback'] is None for s in r['trace'] if 10<=s['time']<28)
        assert all(device(s)['sent_command'] is None for s in r['trace'] if 10<=s['time']<28)
    baseline=c.post(url,json={**body,'mitigation':False}).json()
    # A short fault can end before the next export interval; do not promise
    # a strictly shorter export duration for every scenario.
    assert r['metrics']['export_energy_kwh']<=baseline['metrics']['export_energy_kwh']
    assert sum(abs(s['grid']-25) for s in r['trace'][36:48])<sum(abs(s['grid']-25) for s in baseline['trace'][36:48])

def test_persistent_fault_remains_derated_not_recovered(tmp_path):
    c,m,pid,url=setup(tmp_path);ready(c,pid)
    r=c.post(url.replace('/fleet','/dynamic-tests'),json={'mode':'SIMULATION','scenario':'charge_limited','fault':'bess_comm_loss','fault_node':'BESS_01','mitigation':True,'recover':False}).json()
    assert r['recovery']['state']=='DERATED'
    assert abs(r['trace'][-1]['grid']-25)<=5
    assert next(d for d in r['trace'][-1]['devices'] if d['node_id']=='BESS_01')['feedback'] is None
    baseline=c.post(url.replace('/fleet','/dynamic-tests'),json={'mode':'SIMULATION','scenario':'charge_limited','fault':'bess_comm_loss','fault_node':'BESS_01','mitigation':False,'recover':False}).json()
    assert baseline['trace'][-1]['grid']<0
    assert r['metrics']['export_duration_s']<baseline['metrics']['export_duration_s']
