import pytest
from test_fleet import setup,ready

@pytest.mark.parametrize('order',['meter_first','pv_first','meter_only','pv_only'])
def test_independent_recovery_alarm_requires_both_and_stability(tmp_path,order):
    c,m,pid,url=setup(tmp_path);ready(c,pid)
    r=c.post(url.replace('/fleet','/dynamic-tests'),json=dict(mode='SIMULATION',scenario='load_step',fault='meter_pv_reject',fault_node='PV_03',mitigation=True,recover=True,recovery_order=order)).json()
    trace=r['trace'];mid=trace[50] # 25 seconds, between independent restores.
    assert mid['alarm_active'] and not mid['closed_loop']
    if order.startswith('meter'):
        assert mid['meter'] is not None and mid['pv_recovery_state']=='REFUSING'
    else:
        assert mid['meter'] is None and mid['pv_recovery_state']!='REFUSING'
    for i,s in enumerate(trace):
        if s['time']<10:continue
        if not s['meter_recovered'] or not s['pv_recovered']:assert s['alarm_active']
        if not s['alarm_active']:
            window=trace[i-6:i+1]
            assert len(window)==7
            assert all(v['meter_recovered'] and v['pv_recovered'] and v['closed_loop'] and abs(v['meter']-25)<=5 and abs(v['grid']-25)<=5 for v in window)
    if order.endswith('only'):
        assert r['alarm']['active'] and r['alarm']['cleared_at_s'] is None
        assert r['recovery']['state']!='RECOVERED'
    else:
        assert not r['alarm']['active'] and r['recovery']['state']=='RECOVERED'
        assert r['alarm']['cleared_at_s']>39
    assert r['field_result'] is None and r['manufacturer_basis']=='PENDING'
