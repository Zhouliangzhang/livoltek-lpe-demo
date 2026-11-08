"""Ordered step04: full frozen PV read-only scope; no network or hardware writes."""
from collections import Counter
from copy import deepcopy
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .fleet import groups_for
from .meter_workflow import states


def inventory(model,controller,kind='PV_INVERTER'):
    nodes={n['node_id']:n for n in model['nodes']};ports={p['port_id']:p for p in model['ports']}
    assets={a['asset_id']:a for a in model['device_assets']};models={d['model_id']:d for d in model['device_models']}
    sns=Counter(assets.get(n.get('device_asset_id'),{}).get('serial_number') for n in nodes.values() if n['node_type']==kind)
    groups={}
    for old in groups_for(model):
        if old['kind']!=kind:continue
        for device in old['devices']:
            node=nodes[device['node_id']];asset=assets.get(node.get('device_asset_id'),{});dm=models.get(asset.get('model_id'),{})
            firmware=asset.get('firmware_version') or None
            driver=str(node.get('attributes',{}).get('driver_version') or '待厂家确认')
            key=digest(dict(model=dm.get('model_id'),version=dm.get('master_data_version'),firmware=firmware,driver=driver))
            g=groups.setdefault(key,dict(id=key,model=dm.get('model_name','型号待补'),model_id=dm.get('model_id'),manufacturer=dm.get('manufacturer'),firmware=firmware,driver=driver,master_data_version=dm.get('master_data_version'),devices=[]))
            path=device['route'];target=ports[path[-1]['to']]['node_id'] if path else None
            port_ids={p for e in path for p in [e['from'],e['to']]}
            configs=[dict(owner=node['node_id'],values=deepcopy(node.get('attributes',{}).get('l5_settings',{})))]
            configs += [dict(owner=p,values=deepcopy(ports[p].get('attributes',{}).get('l5_settings',{}))) for p in sorted(port_ids)]
            missing=[]
            if not asset.get('serial_number'):missing.append('现场SN')
            if not firmware:missing.append('现场固件')
            missing+=['型号/固件/驱动适配依据','能力点表与单位换算','刷新/失联行为和远程权限定义']
            g['devices'].append(dict(node_id=node['node_id'],name=node['name'],model=g['model'],model_id=g['model_id'],sn=asset.get('serial_number'),firmware=firmware,driver=driver,location=asset.get('installed_location'),logical_position=node.get('parent_node_id'),route=path,controller=controller,path_valid=bool(path and target==controller),duplicate_sn=bool(asset.get('serial_number') and sns[asset['serial_number']]>1),configuration=configs,pending=missing))
    return list(groups.values())


def simulate_device(device,scenario):
    node=device['node_id'];checks=[];diagnosis=None
    definitions=[
      ('path','路径与通信应答',device['path_valid'] and scenario!='timeout','收到模拟通信帧；非 Ping 判定','未取得有效路径或通信应答','核对该台总线、两端端口及通信条件；不自动改址','L4'),
      ('identity','型号、SN、固件与逻辑位置',not device['duplicate_sn'] and scenario!='wrong_identity','SIM-'+node+' · SIM-FW-1 · 逻辑映射唯一','身份不符或 M1 SN 重复，不能确认唯一映射','核对型号、SN、固件及逻辑位置；换机须回 M1 确认','L3'),
      ('driver','适用驱动',scenario!='driver_mismatch','SIM-PV-DRIVER/1 适配演练夹具','模拟驱动与目标固件不适配','请厂家提供型号/固件适配矩阵和批准驱动版本','L3'),
      ('fields','功率、状态、限值与能力',scenario!='capability_missing','有功80kW / 可用100kW / 当前限值125kW / RUNNING','可用功率字段不可读，也无批准的替代证据','请厂家确认能力点表或批准替代证据；依赖该能力的控制测试保持阻断','L3'),
      ('freshness','数据刷新与质量',scenario!='stale','源序号1→2→3 / GOOD / 最大年龄0s','源数据年龄30s，超出演练2s阈值','核对源更新时间、缓存与刷新定义；轮询成功不代表更新','L5'),
      ('units','单位转换',scenario!='unit_mismatch','80000 W ÷ 1000 = 80 kW','原始80000W被解析为80000kW，单位不一致','核对点表单位、倍率及驱动换算依据','L3'),
      ('permissions','权限、告警与本地失联设置',True,'无远程写权限；只读仍可用' if scenario=='readonly' else '模拟远程写允许 / 无告警 / 失联停用测试指令（仅演练设定）','','','L5')]
    stopped=False
    for key,label,passed,actual,reason,action,layer in definitions:
        status='SKIPPED' if stopped else 'PASS' if passed else 'FAIL'
        checks.append(dict(key=key,label=label,status=status,actual='前置失败，本项未取得证据' if stopped else actual if passed else reason,expected='仅演练判据；现场依据待厂家确认'))
        if not stopped and not passed:
            diagnosis=dict(reason=reason,action=action,owner='EPC / 厂家技术支持',layer=layer,node_id=node,edge_id=device['route'][0]['edge_id'] if device['route'] else None)
            stopped=True
    valid={c['key']:c['status']=='PASS' for c in checks}
    readings=dict(active_kw=80 if valid['fields'] else None,available_kw=100 if valid['fields'] else None,power_limit_kw=125 if valid['fields'] else None,operating_state='RUNNING' if valid['fields'] else None,remote_write=(scenario!='readonly') if valid['permissions'] else None,alarms=[] if valid['permissions'] else None,local_loss_policy='SIM-STOP-TEST-COMMANDS' if valid['permissions'] else None,raw_active_w=80000 if valid['fields'] else None,source_age_s=30 if scenario=='stale' else 0 if valid['freshness'] else None,quality='GOOD' if valid['freshness'] else 'UNKNOWN',observed_sn='SIM-OTHER' if scenario=='wrong_identity' else 'SIM-'+node if valid['identity'] else None)
    return dict(node_id=node,status='FAIL' if stopped else 'PASS',checks=checks,diagnosis=diagnosis,readings=readings,route=device['route'],source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',power_control_allowed=False,scenario=scenario)


class Scan(BaseModel):
    session_id:str
    mode:Literal['SIMULATION','REAL']='SIMULATION'
    acknowledged:bool=False
    request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    scenario:Literal['normal','timeout','wrong_identity','driver_mismatch','stale','unit_mismatch','capability_missing','readonly']='normal'
    fault_node:str=''


def register_pv_communication(app,db):
    def context(id,session_id,mode):
        try:
            plan=db.record(id)
            if plan['kind']!='plan':raise KeyError(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        model=plan['system_context_baseline'];session=None;complete=None
        if session_id:
            try:session=db.record(session_id)
            except KeyError:raise HTTPException(404,'调试会话不存在')
            if session['kind']!='meter_session' or session['project']!=id:raise HTTPException(404,'会话不属于本项目')
            if session['mode']==mode:
                progress=states(db.records('meter_run',session_id))
                if progress[6]['current'] and progress[6]['record']['status']=='PASS':complete=progress[6]['record']
        controller=session['route']['ems']['node_id'] if session else next((n['node_id'] for n in model['nodes'] if n['node_type']=='EMS'),None)
        stale=digest(db.get(plan['project'])['model'])!=plan['engineering_hash']
        return plan,session,inventory(model,controller),complete,stale

    @app.get('/api/plans/{id}/pv-communication')
    def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,s,groups,pcc,stale=context(id,session_id,mode)
        records=[r for r in db.records('pv_communication',session_id) if r['mode']==mode] if session_id else []
        latest=records[0] if records else None
        current=bool(latest and pcc and not stale and latest['pcc_evidence_id']==pcc['id'] and latest['model_hash']==p['engineering_hash'])
        return dict(groups=groups,records=records,current=current,pcc_ready=bool(pcc and not stale),stale=stale,field_connected=False,power_control_allowed=False)

    @app.post('/api/plans/{id}/pv-communication')
    def execute(id:str,body:Scan):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 未接入；未执行光伏现场验证')
        p,s,groups,pcc,stale=context(id,body.session_id,body.mode)
        if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境的调试会话')
        rid=digest(dict(kind='pv-read',session=s['id'],request=body.request_id))
        signature=digest(body.model_dump())
        try:previous=db.record(rid)
        except KeyError:previous=None
        if previous:
            if previous['request_signature']!=signature:raise HTTPException(409,'该运行ID已用于不同范围或场景')
            return previous
        if stale or not pcc:raise HTTPException(409,'必须先完成当前模型的步骤03 PCC计量验证；前置重测后须重新验证')
        if not body.acknowledged:raise HTTPException(422,'请确认冻结本次全体光伏只读验证范围')
        devices=[d for g in groups for d in g['devices']]
        if not devices:raise HTTPException(422,'M1未定义光伏逆变器')
        if body.scenario!='normal' and body.fault_node not in [d['node_id'] for d in devices]:raise HTTPException(422,'请选择本次范围内的异常设备')
        result=[dict(**simulate_device(d,body.scenario if body.fault_node==d['node_id'] else 'normal'),execution_order=i+1) for i,d in enumerate(devices)]
        scope=dict(kind='PV_READ_ONLY',node_ids=[d['node_id'] for d in devices],controller=s['route']['ems']['node_id'],groups=groups,model_hash=p['engineering_hash'],pcc_evidence_id=pcc['id'])
        record=dict(mode=body.mode,request_signature=signature,request_id=body.request_id,scope=scope,scope_hash=digest(scope),model_hash=p['engineering_hash'],pcc_evidence_id=pcc['id'],devices=result,passed=sum(d['status']=='PASS' for d in result),failed=sum(d['status']=='FAIL' for d in result),power_control_allowed=False,field_result=None,manufacturer_basis='PENDING',source='SIMULATOR',version='SIM-PV-COMM-1')
        saved=db.add_once('pv_communication',s['id'],record,rid)
        if saved['request_signature']!=signature:raise HTTPException(409,'该运行ID已用于不同场景')
        return saved

