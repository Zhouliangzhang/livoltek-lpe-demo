"""Read-only projection of M1 environment-specific planning data for M2."""
from copy import deepcopy
from .m1_baseline import effective_edges

def environment_model(model,mode):
    m=deepcopy(model)
    assets={a['asset_id']:a for a in m['device_assets']}
    models={d['model_id']:d for d in m['device_models']}
    for n in m['nodes']:
        records=n.get('attributes',{}).get('identity_records',{})
        if not records:continue
        r=records.get(mode,{})
        a=assets.get(n.get('device_asset_id'))
        if not a:continue
        a['serial_number']=r.get('sn') or (a.get('serial_number') if mode=='REAL' else None)
        a['firmware_version']=r.get('firmware') or (a.get('firmware_version') if mode=='REAL' else None)
        a['installed_location']=r.get('location') or (a.get('installed_location') if mode=='REAL' else None)
        if r.get('structure'):n['parent_node_id']=r['structure']
        if r.get('third_party'):
            original=models.get(a['model_id'],{})
            d={**original,'model_id':a['model_id']+'@'+n['node_id']+'@'+mode,'manufacturer':r['third_party'].get('manufacturer') or original.get('manufacturer'),'model_name':r['third_party'].get('model') or original.get('model_name')}
            m['device_models'].append(d);a['model_id']=d['model_id']
    m['edges']=effective_edges(m,mode)
    return m
