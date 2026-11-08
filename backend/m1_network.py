"""Environment-scoped communication and logical-control draft validation."""
NETWORK_SCHEMA={'type':'array','maxItems':2000,'items':{'type':'object','additionalProperties':False,'required':['id','base_edge_id','environment','edge_type','from_port_id','to_port_id','purpose','manufacturer_ref','cable_note','status'],'properties':{**{k:{'type':'string','maxLength':1000} for k in ['id','base_edge_id','from_port_id','to_port_id','purpose','manufacturer_ref','cable_note']},'environment':{'enum':['OFFLINE','SIMULATION','REAL']},'edge_type':{'enum':['COMMUNICATION','CONTROL']},'status':{'const':'PENDING'}}}}

def network_errors(m):
 errors=[];ports={p['port_id']:p for p in m['ports']};base={e['edge_id']:e for e in m['edges'] if e['edge_type'] in ('COMMUNICATION','CONTROL')};rows=m['project'].get('network_drafts',[])
 if len({r['id'] for r in rows})!=len(rows):errors.append('通信草案编号重复')
 for r in rows:
  if not r['purpose'].strip():errors.append('请说明通信或控制关系用途')
  if r['base_edge_id'] and (r['base_edge_id'] not in base or base[r['base_edge_id']]['edge_type']!=r['edge_type']):errors.append('原关系不存在或类型不匹配')
 for env in ('OFFLINE','SIMULATION','REAL'):
  drafts=[r for r in rows if r['environment']==env];overrides=[r['base_edge_id'] for r in drafts if r['base_edge_id']]
  if len(set(overrides))!=len(overrides):errors.append('同环境不能重复修订关系')
  pairs=set()
  for e in [e for k,e in base.items() if k not in overrides]+drafts:
   a,b=ports.get(e['from_port_id']),ports.get(e['to_port_id']);kind=e['edge_type']
   if not a or not b:errors.append('通信/控制端口不存在');continue
   domains=('CONTROL_LOGICAL',) if kind=='CONTROL' else ('ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO')
   if a['node_id']==b['node_id'] or a['domain'] not in domains or a['domain']!=b['domain']:errors.append('端口域不匹配；跨协议需显式网关')
   if a['role']=='IN' or b['role']=='OUT':errors.append('端口方向不匹配')
   ends=(e['from_port_id'],e['to_port_id']) if kind=='CONTROL' else tuple(sorted((e['from_port_id'],e['to_port_id'])))
   key=(kind,*ends)
   if key in pairs:errors.append('同环境通信/控制关系重复')
   pairs.add(key)
 return errors
