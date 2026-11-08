import pytest
from test_fleet import setup,ready

@pytest.mark.parametrize('relapse',['meter','pv'])
@pytest.mark.parametrize('window',['qualification','stabilization'])
def test_relapse_resets_timers_and_reenters_degraded_control(tmp_path,relapse,window):
    c,m,pid,url=setup(tmp_path);ready(c,pid)
    body=dict(mode='SIMULATION',scenario='load_step',fault='meter_pv_reject',fault_node='PV_03',mitigation=True,recover=True,recovery_order='pv_first',relapse=relapse,relapse_window=window)
    response=c.post(url.replace('/fleet','/dynamic-tests'),json=body)
    assert response.status_code==200,response.text
    r=response.json();trace=r['trace'];start=r['settings']['relapse_start_s'];end=r['settings']['relapse_end_s']
    assert start is not None
    reset=next(s for s in trace if s['time']==start)
    assert reset['timer_reset'] and reset['alarm_active'] and not reset['closed_loop']
    assert reset['qualification_elapsed_s']==reset['stability_elapsed_s']==0
    assert reset['pv_command']==0
    for s in trace:
        if start<=s['time']<end:
            assert s['alarm_active'] and not s['closed_loop']
            assert s['qualification_elapsed_s']==s['stability_elapsed_s']==0
            assert s['meter'] is None if relapse=='meter' else s['pv_recovery_state']=='REFUSING'
    clears=[s for i,s in enumerate(trace[1:],1) if trace[i-1]['alarm_active'] and not s['alarm_active']]
    assert len(clears)==1
    assert clears[0]['time']>=end+6
    assert r['recovery']['state']=='RECOVERED' and not r['alarm']['active']
    assert any(e['phase']=='RELAPSE' for e in r['control_events'])
    assert any(i['code']=='RECOVERY_RELAPSE' for i in r['issues'])
    assert r['manufacturer_basis']=='PENDING' and r['field_result'] is None
