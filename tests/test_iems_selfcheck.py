from concurrent.futures import ThreadPoolExecutor
from test_fleet import setup
from test_meter_workflow import create


def test_selfcheck_detail_failures_and_readonly(tmp_path):
 c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow');s=create(c,url).json();base=url+'/'+s['id']
 def run(scenario,key):return c.post(base+'/run',json={'step':'selfcheck','scenario':scenario,'request_id':key})
 r=run('normal','initial').json()
 assert len(r['checks'])>=10
 assert r['capabilities']['read_only'] and not r['capabilities']['power_control']
 assert r['initial_snapshot']['controller_sn']=='SIM-IEMS-001'
 assert r['interfaces'] and r['basis_pending']
 for scenario in ['controller_mismatch','configuration_mismatch','driver_mismatch','engine_restart','clock_unsynced','log_unwritable','storage_fault','interface_conflict','owner_lost','strategy_conflict']:
  response=run(scenario,scenario);assert response.status_code==200,response.text
  r=response.json();assert r['status']=='FAIL' and not r['capabilities']['read_only']
  assert any(x['reason'] and x['action'] for x in r['checks'] if not x['passed'])
  assert c.post(base+'/run',json={'step':'route'}).status_code==409
  if scenario=='log_unwritable':assert next(x for x in r['checks'] if x['key']=='interfaces')['severity']=='SKIPPED'
 r=run('readonly_only','readonly').json();assert r['status']=='PASS' and r['capabilities']['read_only']
 assert not r['capabilities']['power_control']
 r=run('unknown_device','candidate').json();assert r['candidates'][0]['admitted'] is False
 assert len(c.get('/api/projects/'+pid).json()['model']['nodes'])==len(m['nodes'])
 real=create(c,url,'REAL').json()
 assert c.post(url+'/'+real['id']+'/run',json={'step':'selfcheck'}).status_code==503


def test_selfcheck_idempotency_and_recovery(tmp_path):
 c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow');s=create(c,url).json();base=url+'/'+s['id']
 body={'step':'selfcheck','scenario':'normal','request_id':'reconnect-001'}
 with ThreadPoolExecutor(max_workers=3) as pool:
  results=list(pool.map(lambda _:c.post(base+'/run',json=body),range(3)))
 assert all(r.status_code==200 for r in results)
 assert len({r.json()['id'] for r in results})==1
 assert len(c.get(url).json()['attempts'][s['id']])==1
 assert c.get(base+'/runs/reconnect-001').json()['id']==results[0].json()['id']
 assert c.post(base+'/run',json={**body,'scenario':'clock_unsynced'}).status_code==409
 assert c.get(base+'/runs/missing').status_code==404
