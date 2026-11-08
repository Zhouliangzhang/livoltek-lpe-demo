import pytest
from test_fleet import setup,ready

@pytest.mark.parametrize('scenario',['load_step','pv_fluctuation','charge_limited'])
def test_dynamic_power_balance_events_metrics(tmp_path,scenario):
    c,m,pid,url=setup(tmp_path);url=url.replace('/fleet','/dynamic-tests');ready(c,pid)
    response=c.post(url,json={'mode':'SIMULATION','scenario':scenario})
    assert response.status_code==200,response.text
    r=response.json();assert len(r['trace'])==81 and r['source']=='SIMULATOR'
    assert [e['time'] for e in r['events']]==[10,24]
    for s in r['trace']:
        assert abs(s['grid']-(s['load']+s['bess']-s['pv']))<0.02
        assert abs(sum(d['actual'] for d in s['devices'] if d['kind']=='PV')-s['pv'])<0.02
    expected=max(0,-min(s['grid'] for s in r['trace']))
    assert r['metrics']['peak_export_kw']==pytest.approx(expected)
    duration=sum(0.5 for s in r['trace'][:-1] if s['grid']<0)
    assert r['metrics']['export_duration_s']==duration
    assert r['metrics']['events'][0]['response_delay_s']>=1
    assert abs(r['trace'][-1]['grid']-25)<=5

def test_dynamic_guards_and_specific_fault(tmp_path):
    c,m,pid,url=setup(tmp_path);url=url.replace('/fleet','/dynamic-tests')
    command={'mode':'SIMULATION','scenario':'charge_limited','fault':'bess_block','fault_node':'BESS_03'}
    assert c.post(url,json=command).status_code==409
    ready(c,pid)
    r=c.post(url,json=command).json()
    assert r['issues'][0]['node_id']=='BESS_03'
    assert any(d['status']=='FAULT' for s in r['trace'] if s['time']>=10 for d in s['devices'] if d['node_id']=='BESS_03')
    assert all(d['status']!='FAULT' for s in r['trace'] if s['time']<10 for d in s['devices'])
    count=len(c.get(url).json()['records'])
    assert c.post(url,json={**command,'mode':'REAL'}).status_code==503
    assert c.post(url,json={**command,'fault_node':'PV_01'}).status_code==422
    assert c.post(url,json={**command,'delay_s':0}).status_code==422
    assert len(c.get(url).json()['records'])==count
    m['project']['name']+=' new';c.post('/api/projects',json={'model':m,'expected_revision':1})
    assert c.post(url,json=command).status_code==409

def test_dynamic_missing_model_path(tmp_path):
    c,m,pid,url=setup(tmp_path,True);ready(c,pid)
    r=c.post(url.replace('/fleet','/dynamic-tests'),json={'mode':'SIMULATION','scenario':'load_step'}).json()
    assert r['status']=='BLOCKED' and r['trace']==[]
    assert any(i['node_id']=='PV_01' for i in r['issues'])
