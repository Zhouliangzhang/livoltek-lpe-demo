"""Draft electrical connections are scoped to an environment, never approved wiring."""
DRAFT_SCHEMA={'type':'array','maxItems':2000,'items':{'type':'object','additionalProperties':False,'required':['id','base_edge_id','environment','from_port_id','to_port_id','circuit_id','epc_ref','manufacturer_ref','status'],'properties':{**{k:{'type':'string','maxLength':1000} for k in ['id','base_edge_id','from_port_id','to_port_id','circuit_id','epc_ref','manufacturer_ref']},'environment':{'enum':['OFFLINE','SIMULATION','REAL']},'status':{'const':'PENDING'}}}}

def electrical_errors(m):
    errors=[];ports={p['port_id']:p for p in m['ports']};nodes={n['node_id']:n for n in m['nodes']};base={e['edge_id']:e for e in m['edges'] if e['edge_type']=='ELECTRICAL'};rows=m['project'].get('electrical_drafts',[])
    ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids):errors.append('电气连接草案编号重复')
    for env in ('OFFLINE','SIMULATION','REAL'):
        drafts=[r for r in rows if r['environment']==env];overrides=[r['base_edge_id'] for r in drafts if r['base_edge_id']]
        if len(set(overrides))!=len(overrides):errors.append('同环境不能重复修订同一连接')
        pairs=set()
        for e in list(e for k,e in base.items() if k not in overrides)+drafts:
            a,b=ports.get(e['from_port_id']),ports.get(e['to_port_id'])
            if not a or not b:errors.append('电气端口不存在');continue
            if a['node_id']==b['node_id'] or a['domain'] not in ('AC','DC') or a['domain']!=b['domain']:errors.append('电气连接需连接不同对象的同域 AC/DC 端口')
            if a['role']=='IN' or b['role']=='OUT':errors.append('电气连接端口方向不兼容')
            for key in ('voltage','phases'):
                av=a.get('attributes',{}).get(key);bv=b.get('attributes',{}).get(key)
                if av is not None and bv is not None and av!=bv:errors.append('电气连接电压或相制不兼容')
            pair=tuple(sorted((e['from_port_id'],e['to_port_id'])))
            if pair in pairs:errors.append('同环境电气连接重复')
            pairs.add(pair)
        for r in drafts:
            if r['base_edge_id'] and r['base_edge_id'] not in base:errors.append('被修订的规划连接不存在')
            c=nodes.get(r['circuit_id'])
            if not c or c.get('device_asset_id') or (c['node_type'] not in ('FEEDER','BREAKER') and not c.get('attributes',{}).get('engineering',{}).get('circuit_id')):errors.append('请引用步骤03的有效回路')
    return errors
