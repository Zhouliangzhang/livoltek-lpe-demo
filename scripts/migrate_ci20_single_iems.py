"""Apply the user's single-iEMS correction as a new revision; retain unrelated edits."""
import copy
import json
import urllib.request
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_ci20_pilot import build, PROJECT_ID
from backend.domain import validate

def migrate(model):
    result=copy.deepcopy(model)
    fresh=build()
    removed={'EMS_PV','EMS_BESS'}
    assets={n['device_asset_id'] for n in result['nodes'] if n['node_id'] in removed}
    port_nodes={p['port_id']:p['node_id'] for p in result['ports']}
    remap={'EMS_PV.PV_RS485':'EMS_MASTER.PV_RS485'}
    for family in ('PV','BESS'):
        for i in range(1,11):remap[f'EMS_{family}.SETPOINT_{i}']=f'EMS_MASTER.{family}_SETPOINT_{i}'
    edges=[]
    for edge in result['edges']:
        a,b=edge['from_port_id'],edge['to_port_id']
        if any(port_nodes.get(p) in removed and p not in remap for p in (a,b)):continue
        edge['from_port_id']=remap.get(a,a);edge['to_port_id']=remap.get(b,b);edges.append(edge)
    result['edges']=edges
    result['nodes']=[n for n in result['nodes'] if n['node_id'] not in removed]
    result['device_assets']=[a for a in result['device_assets'] if a['asset_id'] not in assets]
    result['interface_bindings']=[b for b in result['interface_bindings'] if b['asset_id'] not in assets]
    obsolete={'EMS_MASTER.PV_DISPATCH','EMS_MASTER.BESS_DISPATCH'}|{f'{owner}.{id}' for owner in ['NET_01','UPS_01'] for id in removed}
    result['ports']=[p for p in result['ports'] if p['node_id'] not in removed and p['port_id'] not in obsolete]
    existing={p['port_id'] for p in result['ports']}
    result['ports'] += [p for p in fresh['ports'] if p['node_id']=='EMS_MASTER' and p['port_id'] not in existing]
    controller=next(n for n in result['nodes'] if n['node_id']=='EMS_MASTER')
    replacement=next(n for n in fresh['nodes'] if n['node_id']=='EMS_MASTER')
    controller['name']=replacement['name']
    controller['attributes']['scope']=replacement['attributes']['scope']
    controller['attributes']['configuration_basis']='User confirmed one iEMS controls all 20 devices; delivered model and protocol pending'
    # Keep existing parameter provenance so changed model identity requires reconfirmation.
    next(a for a in result['device_assets'] if a['asset_id']==controller['device_asset_id'])['model_id']='EMS-USER20'
    if not any(d['model_id']=='EMS-USER20' for d in result['device_models']):result['device_models'].append(next(d for d in fresh['device_models'] if d['model_id']=='EMS-USER20'))
    used={a['model_id'] for a in result['device_assets']}
    result['device_models']=[d for d in result['device_models'] if d['model_id'] in used]
    zone=next(n for n in result['nodes'] if n['node_id']=='ZONE_01')
    zone['attributes']['open_questions']=[q for q in zone['attributes'].get('open_questions',[]) if '主从' not in q]
    zone['attributes']['controller_basis']='USER_CONFIRMED_SINGLE_IEMS_20_DEVICES'
    for id in removed:result['view_layout']['positions'].pop(id,None)
    check=validate(result)
    if not check['valid']:raise ValueError(check['errors'])
    return result

if __name__=='__main__':
    base='http://127.0.0.1:8000/api'
    current=json.load(urllib.request.urlopen(base+'/projects/'+PROJECT_ID))
    candidate=migrate(current['model'])
    request=urllib.request.Request(base+'/projects',data=json.dumps({'model':candidate,'expected_revision':current['revision']}).encode(),headers={'Content-Type':'application/json'})
    saved=json.load(urllib.request.urlopen(request))
    print(json.dumps({'revision':saved['revision'],'nodes':len(candidate['nodes']),'edges':len(candidate['edges']),'controllers':[n['node_id'] for n in candidate['nodes'] if n['node_type']=='EMS']}))
