from test_fleet import setup
from test_meter_workflow import create


def test_meter_detailed_evidence_and_faults(tmp_path):
 c,m,pid,old=setup(tmp_path);url=old.replace('/fleet','/meter-workflow');s=create(c,url).json();base=url+'/'+s['id']+'/run'
 def run(step,scenario='normal'):
  r=c.post(base,json={'step':step,'scenario':scenario});assert r.status_code==200,r.text;return r.json()
 run('selfcheck');run('route')
 for fault in ['duplicate_address','bad_frames','parameter_mismatch','model_mismatch']:
  r=run('identity',fault);assert r['status']=='FAIL';assert r['diagnosis']['action'] and r['diagnosis']['owner']
  assert c.post(base,json={'step':'quality'}).status_code==409
 run('identity')
 for fault in ['time_reverse','phase_sum','jump','duplicate','quality_unknown']:
  r=run('quality',fault);assert r['status']=='FAIL'
 r=run('quality');assert len(r['samples'][0]['phases'])==3
 assert r['samples'][0]['quality_source']=='SIMULATED_DEVICE_FLAG'
 assert r['m1_evidence']['meter']['node_id']=='METER_PCC'
 for fault in ['no_reference','ct_ratio','pt_ratio']:
  r=run('reference',fault);assert r['status']=='FAIL'
  assert r['reference_evidence']['source']=='INDEPENDENT_SIMULATOR'
 assert c.post(base,json={'step':'stability'}).status_code==409
 r=run('reference');assert r['reference_evidence']['reference_kw']==25
 assert r['manufacturer_basis']=='PENDING' and r['field_result'] is None
 run('stability');r=run('complete');assert len(r['evidence_ids'])==6
 assert c.get('/api/projects/'+pid).json()['model']['nodes']==m['nodes']
