"""Step06 immutable per-parameter readback. SIMULATOR only; no device writes."""
from collections import Counter
from copy import deepcopy
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .l5_settings import applicable,CATALOG
from .meter_workflow import states

KINDS={'EMS':'iEMS','METER':'零馈表','PV_INVERTER':'光伏','BESS':'储能'}


def inventory(model):
    assets={a['asset_id']:a for a in model['device_assets']};models={m['model_id']:m for m in model['device_models']}
    connected={p for e in model['edges'] if e['edge_type']=='COMMUNICATION' for p in [e['from_port_id'],e['to_port_id']]}
    devices=[]
    for n in model['nodes']:
        if n['node_type'] not in KINDS:continue
        asset=assets.get(n.get('device_asset_id'),{});dm=models.get(asset.get('model_id'),{})
        rows=[];linked=[p for p in model['ports'] if p['node_id']==n['node_id'] and p['port_id'] in connected]
        used=set()
        for definition in applicable(model,n):
            matching=[p for p in linked if p['domain'] in definition['domains']]
            targets=matching if definition['group']=='通信' and definition['domains'] and definition['domains'][0]!='ETHERNET' else [None]
            for port in targets:
                multi=port and len(matching)>1
                owner=port['port_id'] if port else n['node_id'];key=definition['key']
                settings=(port or {}).get('attributes',{}).get('l5_settings',{}).get(key)
                if settings is None and not multi:settings=n.get('attributes',{}).get('l5_settings',{}).get(key)
                settings=settings or {}
                candidates=[p for p in model['parameters'] if p['name']==key and p['owner_id'] in [owner,n['node_id'],asset.get('asset_id')]]
                # Port-specific approval takes priority; a node-wide approval cannot disambiguate multiple ports.
                exact=[p for p in candidates if p['owner_id']==owner]
                candidates=exact or ([] if multi else candidates)
                used.update(p['parameter_id'] for p in candidates)
                approved=None;approval_ref=None
                if len(candidates)==1:
                    p=candidates[0];a=p.get('approved') or {}
                    if p.get('review_status')=='APPROVED' and a.get('status')=='APPROVED' and a.get('source_ref') and a.get('unit','')==definition['unit']:
                        approved=a.get('value') if a.get('value')!='' else None;approval_ref=a['source_ref'] if approved is not None else None
                stale=bool(settings) and (settings.get('model_id'),settings.get('master_data_version'),settings.get('template_version'))!=(dm.get('model_id'),dm.get('master_data_version'),CATALOG['version'])
                if stale:approved=None;approval_ref=None
                row_id=(port['port_id'] if multi else n['node_id'])+'.'+key
                rows.append(dict(id=n['node_id']+'::'+owner+'::'+key,row_id=row_id,key=key,label=definition['label'],unit=definition['unit'],type=definition['type'],owner=owner,
                    planned=settings.get('planned'),m1_actual=settings.get('actual'),approved=approved,approval_ref=approval_ref,reference=settings.get('reference_doc'),stale=stale,
                    pending='参数映射存在歧义' if len(candidates)>1 else '型号/模板版本变化' if stale else '缺少批准值或有效批准引用' if approved is None else '型号/固件点表、单位及读回生效规则待厂家确认',layer='L5'))
        # Keep additional explicitly scoped canonical parameters; never silently omit an approved device setting.
        owner_ids={n['node_id'],asset.get('asset_id')}|{p['port_id'] for p in linked}
        for p in model['parameters']:
            if p['parameter_id'] in used or p['owner_id'] not in owner_ids:continue
            a=p.get('approved') or {};planned=p.get('planned') or {};actual=p.get('actual') or {}
            approved=a.get('value') if p.get('review_status')=='APPROVED' and a.get('status')=='APPROVED' and a.get('source_ref') else None
            rows.append(dict(id=n['node_id']+'::'+p['parameter_id'],row_id=p['parameter_id'],key=p['name'],label=p['name'],unit=a.get('unit',planned.get('unit','')),type='canonical',owner=p['owner_id'],planned=planned.get('value'),m1_actual=actual.get('value'),approved=approved,approval_ref=a.get('source_ref') if approved is not None else None,reference=p.get('reference_doc'),stale=False,pending='厂家读回映射与适用依据待确认',layer='L5'))
        devices.append(dict(node_id=n['node_id'],name=n['name'],kind=n['node_type'],group=KINDS[n['node_type']],model=dm.get('model_name','待补'),sn=asset.get('serial_number'),firmware=asset.get('firmware_version'),parameters=rows))
    return devices


def session_inventory(plan,session,mode):
    package=(session or {}).get('m1_basis')
    if not package:return inventory(plan['system_context_baseline'])
    if package['environment']!=mode:raise HTTPException(409,'配置基线环境不匹配')
    from .m1_delivery import inventory as frozen_inventory
    b=package['baseline'];snapshot=b['snapshot'];result=[]
    for device in frozen_inventory(b):
        nid=device['node_id'];kind=snapshot['structure'][nid]['node_type']
        if kind not in KINDS:continue
        rows=[]
        for r in device['parameters']:
            label=(r['owner']+' '+r['key']) if r['step']==7 else (nid+' '+r['key']) if nid in snapshot['metering'] else ('策略 '+r['key']) if r['step']==9 else (r['owner'].split('/')[-1]+' '+r['key'])
            rows.append(dict(id=nid+'::'+r['id'],row_id=r['id'],key=r['key'],label=r['label'],unit=r['unit'],type='canonical',owner=r['owner'],planned=r['planned'],m1_actual=None,approved=None,approval_ref=None,reference=None,stale=False,pending='冻结候选值；厂家点表及批准依据待确认',layer='L5',m1_step=r['step'],focus_label=label))
        if not rows:
            rows.append(dict(id=nid+'::missing',row_id=nid,key='missing',label='设备配置待补充',unit='',type='canonical',owner=nid,planned=None,m1_actual=None,approved=None,approval_ref=None,reference=None,stale=False,pending='冻结范围未提供逐台配置；不能复制站级功率代替设备参数',layer='L5',m1_step=7,focus_label=''))
        identity=snapshot['devices'][nid].get('identity') or {}
        result.append(dict(node_id=nid,name=device['name'],kind=kind,group=KINDS[kind],model=(identity.get('third_party') or {}).get('model') or device['model'],sn=device['serial_number'],firmware=device['firmware'],parameters=rows))
    return result


def compare(row,scenario):
    expected=row['approved'] if row['approved'] not in (None,'') else row['planned']
    if expected=='':expected=None
    actual=deepcopy(expected);unit=row['unit'];reason='';action=''
    if scenario=='unreadable':actual=None
    elif scenario=='difference' and actual is not None:actual=actual+1 if type(actual) in (int,float) else str(int(actual)+1) if isinstance(actual,str) and actual.isdigit() else str(actual)+'-DIFF'
    elif scenario=='unit_mismatch':unit='SIM-WRONG-UNIT'
    elif scenario=='type_mismatch':actual=str(actual) if type(actual) in (int,float) else 999
    if row['stale']:status='PENDING';reason='基线型号或模板已变化';action='回M1重新确认配置及批准依据'
    elif scenario=='unreadable':status='UNREAD';reason='未取得该参数的有效读回';action='核对通信路径、只读权限和适用点表；不能用手录值替代'
    elif expected is None:status='PENDING';reason='缺少批准值和候选值';action='EPC补充参数；厂家确认适用范围与批准依据'
    elif unit!=row['unit']:status='UNIT_MISMATCH';reason='读回单位与基线不一致';action='厂家核对单位、倍率及转换规则；不猜测换算'
    elif type(actual)!=type(expected) and not (type(actual) in (int,float) and type(expected) in (int,float)):status='TYPE_MISMATCH';reason='参数类型不一致';action='厂家核对点表类型及枚举编码，不强制转换后放行'
    elif actual!=expected:status='DIFFERENCE';reason='读回值与'+('批准值' if row['approved'] is not None else '候选计划值')+'不同';action='EPC核对该设备参数；厂家确认生效/重启条件。需要变更基线时回M1批准，不自动覆盖'
    elif row['approved'] is None:status='CANDIDATE_MATCH';reason='与候选值相同，批准依据缺失';action='补齐批准值和厂家适用依据；不能作为批准一致'
    else:status='MATCH';reason='合成读回与批准值一致';action='仍需现场有效读回和厂家点表适用证据'
    return dict(**row,actual=actual,actual_unit=unit,status=status,reason=reason,action=action,source='SIMULATOR',manufacturer_basis='PENDING',field_result=None)


class Readback(BaseModel):
    session_id:str
    mode:Literal['SIMULATION','REAL']='SIMULATION'
    acknowledged:bool=False
    request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    scenario:Literal['normal','difference','unreadable','unit_mismatch','type_mismatch']='normal'
    fault_parameter:str=''


def register_configuration_readback(app,db):
    def context(id,sid,mode):
        try:
            p=db.record(id)
            if p['kind']!='plan':raise KeyError(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        s=None;prior=None
        if sid:
            try:s=db.record(sid)
            except KeyError:raise HTTPException(404,'会话不存在')
            if s['kind']!='meter_session' or s['project']!=id:raise HTTPException(404,'会话不属于本项目')
            if s['mode']==mode:
                complete=states(db.records('meter_run',sid))[6]
                pv=next((r for r in db.records('pv_communication',sid) if r['mode']==mode),None)
                bess=next((r for r in db.records('bess_communication',sid) if r['mode']==mode),None)
                if complete['current'] and complete['record']['status']=='PASS' and pv and bess and not pv['failed'] and not bess['failed'] and pv['pcc_evidence_id']==complete['record']['id'] and bess['pv_evidence_id']==pv['id'] and pv['model_hash']==bess['model_hash']==p['engineering_hash']:prior=bess
        stale=digest(db.get(p['project'])['model'])!=p['engineering_hash']
        return p,s,prior,stale

    @app.get('/api/plans/{id}/configuration-readback')
    def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,s,prior,stale=context(id,session_id,mode)
        records=[r for r in db.records('configuration_readback',session_id) if r['mode']==mode] if session_id else []
        latest=records[0] if records else None
        return dict(devices=session_inventory(p,s,mode),records=records,prerequisite_ready=bool(prior and not stale),current=bool(latest and prior and not stale and latest['bess_evidence_id']==prior['id'] and latest['model_hash']==p['engineering_hash']),stale=stale,field_connected=False)

    @app.post('/api/plans/{id}/configuration-readback')
    def execute(id:str,body:Readback):
        if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；未读取现场配置')
        p,s,prior,stale=context(id,body.session_id,body.mode)
        if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
        rid=digest(dict(kind='config-readback',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
        try:old=db.record(rid)
        except KeyError:old=None
        if old:
            if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同场景')
            return old
        if stale or not prior:raise HTTPException(409,'请完成当前基线的步骤03至05；前置变化须重验')
        if not body.acknowledged:raise HTTPException(422,'请确认只读范围')
        devices=session_inventory(p,s,body.mode);ids=[r['id'] for d in devices for r in d['parameters']]
        if body.scenario!='normal' and body.fault_parameter not in ids:raise HTTPException(422,'参数不在本次范围')
        for i,d in enumerate(devices):
            d['execution_order']=i+1;d['parameters']=[compare(r,body.scenario if r['id']==body.fault_parameter else 'normal') for r in d['parameters']]
        counts=Counter(r['status'] for d in devices for r in d['parameters'])
        scope=dict(model_hash=p['engineering_hash'],bess_evidence_id=prior['id'],node_ids=[d['node_id'] for d in devices],parameter_ids=ids)
        result=dict(mode=body.mode,request_id=body.request_id,request_signature=signature,devices=devices,counts={k:counts[k] for k in ['MATCH','CANDIDATE_MATCH','DIFFERENCE','UNREAD','PENDING','UNIT_MISMATCH','TYPE_MISMATCH']},scope=scope,scope_hash=digest(scope),model_hash=p['engineering_hash'],bess_evidence_id=prior['id'],source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',power_control_allowed=False)
        saved=db.add_once('configuration_readback',s['id'],result,rid)
        if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
        return saved
