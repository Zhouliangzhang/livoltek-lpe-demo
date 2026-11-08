"""Server-built, immutable configuration draft snapshots. No deployment capability."""
import copy
import hashlib
import json
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from .store import now, uid
from .m1_strategy import scope_devices, strategy_checks
from .m1_metering import metering_checks
from .m1_communication_settings import settings_checks

class ScopeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=1)
    environment: Literal['OFFLINE','SIMULATION','REAL']
    domain_id: str = Field(min_length=1,max_length=128)
    scope_type: Literal['READ_ONLY','PARTIAL','FULL']
    selected_ids: list[str] = Field(default_factory=list,max_length=1000)

class FreezeRequest(ScopeRequest):
    author: str = Field(min_length=1,max_length=100)
    authorization_ref: str = Field(default='',max_length=1000)
    expected_hash: str = Field(min_length=64,max_length=64)

def content_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def effective_edges(model,env):
    drafts=[r for key in ('electrical_drafts','network_drafts') for r in model['project'].get(key,[]) if r['environment']==env]
    overrides={r['base_edge_id'] for r in drafts if r.get('base_edge_id')}
    return [e for e in model['edges'] if e['edge_id'] not in overrides]+[{**r,'edge_id':r['id'],'edge_type':r.get('edge_type','ELECTRICAL')} for r in drafts]

def network_plan_edges(model,env):
    """Match the saved M1 step06 planning representation for stale-basis checks."""
    drafts=[r for r in model['project'].get('network_drafts',[]) if r['environment']==env]
    overrides={r['base_edge_id']:r for r in drafts if r['base_edge_id']}
    edges=[]
    for e in model['edges']:
        r=overrides.get(e['edge_id'])
        edges.append({**e,'from_port_id':r['from_port_id'],'to_port_id':r['to_port_id']} if r else e)
    edges.extend({'edge_id':r['id'],'edge_type':r['edge_type'],'from_port_id':r['from_port_id'],'to_port_id':r['to_port_id'],'review_status':'DRAFT'} for r in drafts if not r['base_edge_id'])
    return edges

def json_signature_matches(signature,value):
    try:return json.loads(signature)==value
    except (ValueError,TypeError):return False

def compare(old,new,path=''):
    """Field-level changes with stable object IDs; no false deletion outside a scope."""
    rows=[]
    if isinstance(old,dict) and isinstance(new,dict):
        for key in sorted(set(old)|set(new)):
            p=path+'/'+str(key)
            if key not in old:rows.append({'path':p,'kind':'ADD','before':None,'after':new[key]})
            elif key not in new:rows.append({'path':p,'kind':'REMOVE','before':old[key],'after':None})
            else:rows.extend(compare(old[key],new[key],p))
    elif old!=new:rows.append({'path':path,'kind':'CHANGE','before':old,'after':new})
    return rows

def build_preview(model,revision,request):
    env=request.environment;project=model['project']
    domain=next((d for d in project.get('system_boundary',{}).get('domains',[]) if d['id']==request.domain_id),None)
    if not domain:raise HTTPException(422,'控制域不存在，请回步骤02确认')
    nodes={n['node_id']:n for n in model['nodes']};ports={p['port_id']:p for p in model['ports']}
    controller=domain.get('controller_id');pcc=domain.get('pcc_id')
    if controller not in nodes or nodes[controller]['node_type']!='EMS' or pcc not in nodes or nodes[pcc]['node_type']!='PCC':raise HTTPException(422,'控制域必须关联有效 iEMS 与 PCC')
    controlled,conflicting_owners=scope_devices(model,env,controller)
    allowed={n['node_id'] for n in controlled}
    if set(request.selected_ids)-allowed:raise HTTPException(422,'选择的设备不在本控制域步骤06控制范围内')
    if len(set(request.selected_ids))!=len(request.selected_ids):raise HTTPException(422,'设备选择重复')
    if request.scope_type=='PARTIAL' and not request.selected_ids:raise HTTPException(422,'部分设备范围至少选择一台设备')
    targets=set(request.selected_ids) if request.scope_type=='PARTIAL' else allowed
    seeds=targets|{controller,pcc}
    meters=[r for r in project.get('metering_settings',{}).get(env,[]) if r['pcc_id']==pcc]
    seeds.update(r['meter_id'] for r in meters if r['meter_id'] in nodes)
    edges=effective_edges(model,env)
    # Conservative connected electrical/communication context, never an implicit write list.
    included=set(seeds)
    changed=True
    while changed:
        changed=False
        for e in edges:
            a=ports.get(e['from_port_id'],{}).get('node_id');b=ports.get(e['to_port_id'],{}).get('node_id')
            if e['edge_type'] in ('ELECTRICAL','COMMUNICATION') and (a in included or b in included):
                for nid in (a,b):
                    if nid in nodes and nid not in included:included.add(nid);changed=True
        for nid in list(included):
            parent=nodes[nid].get('parent_node_id')
            if parent in nodes and parent not in included:included.add(parent);changed=True
    assets={a['asset_id']:a for a in model['device_assets']};models={d['model_id']:d for d in model['device_models']}
    selected_nodes={};devices={}
    for nid in sorted(included):
        n=copy.deepcopy(nodes[nid]);records=n.get('attributes',{}).pop('identity_records',{})
        identity=records.get(env,{})
        a=assets.get(n.get('device_asset_id'))
        if a:
            dm=models.get(a['model_id'],{})
            devices[nid]={'name':n['name'],'model_id':a['model_id'],'model_name':dm.get('model_name'),'manufacturer':dm.get('manufacturer'),'master_data_version':dm.get('master_data_version'),'serial_number':identity.get('sn') or (a.get('serial_number') if env=='REAL' else None),'firmware':identity.get('firmware') or (a.get('firmware_version') if env=='REAL' else None),'identity':identity,'role':'TARGET' if nid in targets else 'DEPENDENCY'}
        selected_nodes[nid]=n
    scoped_ports={pid:copy.deepcopy(p) for pid,p in ports.items() if p['node_id'] in included}
    scoped_edges={e['edge_id']:copy.deepcopy(e) for e in edges if e['from_port_id'] in scoped_ports and e['to_port_id'] in scoped_ports}
    communication={r['id']:copy.deepcopy(r) for r in project.get('communication_settings',{}).get(env,[]) if any(pid in scoped_ports for pid in r['ports'])}
    metering={r['meter_id']:copy.deepcopy(r) for r in meters}
    strategies={r['domain_id']:copy.deepcopy(r) for r in project.get('operating_strategies',{}).get(env,[]) if r['domain_id']==domain['id']}
    # The UI change fingerprints are not deployment metadata; retain them as recorded draft provenance.
    snapshot={'project':{'project_id':project['project_id'],'name':project['name'],'operation_modes':project.get('operation_modes',[]),'boundary':copy.deepcopy(project.get('system_boundary',{}))},'scope':{'environment':env,'domain':copy.deepcopy(domain),'type':request.scope_type,'target_ids':sorted(targets),'dependency_ids':sorted(included-targets),'write_intent':'NONE' if request.scope_type=='READ_ONLY' else 'REVIEW_REQUIRED','outside_scope_action':'PRESERVE'},'devices':devices,'structure':selected_nodes,'models':{mid:copy.deepcopy(models[mid]) for mid in {d['model_id'] for d in devices.values()} if mid in models},'ports':scoped_ports,'connections':scoped_edges,'communication':communication,'metering':metering,'strategies':strategies,'versions':{'schema_version':model['schema_version'],'driver_package':None,'rule_package':None,'baseline_checker':'M1-10-DRAFT-1'},'approvals':{'manufacturer':'PENDING','project':'PENDING','verified_records':[]}}
    findings=[]
    def finding(step,owner,message,ids=None):findings.append({'step':step,'owner':owner,'message':message,'objects':ids or [],'status':'PENDING'})
    if conflicting_owners:finding(6,'EPC / 厂家','本控制域设备存在其他指令来源，需明确控制归属',sorted(conflicting_owners))
    required_identity=targets|{controller}
    if request.scope_type=='FULL':required_identity.update(metering)
    gaps=[nid for nid in sorted(required_identity) if nid not in devices or not devices[nid]['serial_number'] or not devices[nid]['firmware']]
    if gaps:finding(4,'EPC 补充','本次目标的 SN 或固件缺失；型号不等于现场身份',gaps)
    serials={}
    for nid in sorted(required_identity):
        serial=devices.get(nid,{}).get('serial_number')
        if serial:serials.setdefault(serial,[]).append(nid)
    for ids in serials.values():
        if len(ids)>1:finding(4,'EPC / 厂家','同一设备 SN 映射到多个目标，需核对身份',ids)
    if not communication:finding(7,'EPC / 厂家','本次依赖的通信设置尚未保存')
    connected_ports={pid for e in edges if e['edge_type']=='COMMUNICATION' for pid in (e['from_port_id'],e['to_port_id']) if pid in scoped_ports and scoped_ports[pid]['domain'] in ('RS485','CAN','ETHERNET')}
    recorded_ports={pid for r in communication.values() for pid in r['ports']}
    missing_ports=sorted(connected_ports-recorded_ports)
    if missing_ports:finding(7,'EPC / 厂家','部分通信路径尚无当前环境的总线设置',missing_ports)
    planned_edges=network_plan_edges(model,env)
    for row in communication.values():
        port_ids=row['ports']
        signature_parts=[e['from_port_id']+'>'+e['to_port_id'] for e in planned_edges if e['edge_type']=='COMMUNICATION' and (e['from_port_id'] in port_ids or e['to_port_id'] in port_ids)]
        for pid in port_ids:
            a=assets.get(nodes.get(ports.get(pid,{}).get('node_id'),{}).get('device_asset_id'),{})
            dm=models.get(a.get('model_id'),{})
            signature_parts.append(pid+':'+dm.get('model_id','')+':'+dm.get('master_data_version',''))
        if row['signature']!='|'.join(sorted(signature_parts)):finding(7,'EPC / 厂家','通信设置与当前路径或型号依据不一致，需重新核对',port_ids)
        shared={'RS485':['protocol','baud_rate','data_bits','parity','stop_bits'],'CAN':['can_bitrate','can_protocol'],'ETHERNET':[]}[row['domain']]
        empty=[k for k in shared if not row['shared'].get(k)]
        if empty:finding(7,'厂家确认','总线公共参数待补：'+', '.join(empty),row['ports'])
        for pid,values in row['devices'].items():
            required=['ip_address','subnet_mask','protocol'] if row['domain']=='ETHERNET' else ['role'] if row['domain']=='RS485' else ['address']
            if row['domain']=='RS485' and values.get('role')!='MASTER':required+=['address']
            if any(not values.get(k) for k in required):finding(7,'EPC / 厂家','设备通信参数缺项',[pid])
    filtered=copy.deepcopy(model);filtered['project']['communication_settings']={env:list(communication.values())};filtered['project']['metering_settings']={env:list(metering.values())};filtered['project']['operating_strategies']={env:list(strategies.values())}
    for err in settings_checks(filtered)[0]:finding(7,'EPC / 厂家',err)
    if request.scope_type=='FULL':
        if len(metering)!=1:finding(8,'EPC / 厂家','完整控制范围必须有唯一 PCC 零馈计量映射')
        if not strategies:finding(9,'厂家确认','完整控制范围尚无运行策略草案')
        for r in metering.values():
            n=nodes.get(r['meter_id'],{});a=assets.get(n.get('device_asset_id'));dm=models.get(a.get('model_id')) if a else None
            ids={pid for pid,p in ports.items() if p['node_id']==r['meter_id']}
            expected=[a,dm,[p for p in model['ports'] if p['port_id'] in ids],[e for e in planned_edges if e['from_port_id'] in ids or e['to_port_id'] in ids],n.get('attributes',{}).get('identity_records')]
            if not json_signature_matches(r['signature'],expected):finding(8,'EPC / 厂家','计量草案与当前身份、型号或路径不一致，需重新核对',[r['meter_id']])
        device_ids={n['node_id'] for n in controlled}
        asset_ids={n.get('device_asset_id') for n in controlled}
        expected_strategy=[project.get('system_boundary'),project.get('operation_modes'),project.get('network_drafts'),[n for n in model['nodes'] if n['node_id'] in device_ids],[a for a in model['device_assets'] if a['asset_id'] in asset_ids],model['device_models'],[e for e in planned_edges if e['edge_type']=='CONTROL'],meters]
        for r in strategies.values():
            if not json_signature_matches(r['signature'],expected_strategy):finding(9,'EPC / 厂家','运行策略的边界、设备或计量依据已变化，需重新核对',[r['domain_id']])
        for fn,step in ((metering_checks,8),(strategy_checks,9)):
            errors,warnings=fn(filtered)
            for text in errors+warnings:finding(step,'EPC / 厂家',text)
        if not any(r.get('zero_enabled') or r.get('pv_enabled') or r.get('bess_enabled') for r in strategies.values()):finding(9,'EPC / 厂家','完整控制范围尚未明确拟启用目标')
    finding(7,'厂家确认','驱动、点表、型号 / 固件适用性及规则包版本未取得受控确认')
    finding(10,'厂家确认','厂家适用性确认尚未核验；文档引用不能代替批准')
    finding(10,'项目授权人','项目变更授权尚未核验；填写记录不授予权限')
    if env=='REAL':finding(1,'现场接入','真实 iEMS 尚未连接，身份与当前生效配置未知')
    return {'source_revision':revision,'source_model_hash':content_hash(model),'environment':env,'domain_id':domain['id'],'scope_type':request.scope_type,'snapshot':snapshot,'content_hash':content_hash(snapshot),'findings':findings,'status':'DRAFT_REVIEW_REQUIRED','deployable':False,'approved':False,'applied':False,'scope_candidates':[{'id':n['node_id'],'name':n['name']} for n in controlled]}

def register_baselines(app,db):
    kind='m1_config_baseline'
    def current(project,request):
        try:p=db.get(project)
        except KeyError:raise HTTPException(404,'项目不存在')
        if p['revision']!=request.expected_revision:raise HTTPException(409,'工程版本已变化，请保存或重新载入后预览')
        return p
    def with_diff(project,payload):
        previous=next((r for r in db.records(kind,project) if r['environment']==payload['environment'] and r['domain_id']==payload['domain_id'] and r['scope_type']==payload['scope_type']),None)
        old=previous['snapshot'] if previous else {}
        diff=compare(old,payload['snapshot'])
        payload.update(comparison_id=previous['id'] if previous else None,comparison_revision=previous['source_revision'] if previous else None,diff=diff)
        return payload
    @app.post('/api/projects/{project}/config-baselines/preview')
    def preview(project:str,request:ScopeRequest):
        p=current(project,request);return with_diff(project,build_preview(p['model'],p['revision'],request))
    @app.get('/api/projects/{project}/config-baselines')
    def history(project:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        return [{k:v for k,v in r.items() if k not in ('snapshot','diff')} for r in db.records(kind,project) if r['environment']==environment]
    @app.get('/api/projects/{project}/config-baselines/{record_id}')
    def detail(project:str,record_id:str):
        try:r=db.record(record_id)
        except KeyError:raise HTTPException(404,'基线不存在')
        if r['kind']!=kind or r['project']!=project:raise HTTPException(404,'基线不存在')
        return r
    @app.post('/api/projects/{project}/config-baselines/freeze')
    def freeze(project:str,request:FreezeRequest):
        if not request.author.strip():raise HTTPException(422,'请记录冻结操作人')
        p=current(project,request);payload=with_diff(project,build_preview(p['model'],p['revision'],request))
        if payload['content_hash']!=request.expected_hash:raise HTTPException(409,'范围或内容与预览不一致，请重新预览')
        record={'id':uid(),'kind':kind,'project':project,'created':now(),**payload,'status':'FROZEN_DRAFT','author':request.author.strip(),'authorization_ref':request.authorization_ref,'authorization_status':'UNVERIFIED'}
        record['archive_hash']=content_hash({k:v for k,v in record.items() if k!='archive_hash'})
        # Serialize against project saves: never freeze a stale source after preview.
        with db.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()
            if not row or row['revision']!=request.expected_revision:raise HTTPException(409,'冻结期间工程版本变化，请重新预览')
            connection.execute('INSERT INTO records VALUES(?,?,?,?,?)',(record['id'],kind,project,json.dumps(record),record['created']))
        return record
