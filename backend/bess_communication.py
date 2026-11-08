from .m1_inheritance import environment_model
"""Step05 read-only BESS capability snapshots. Synthetic fixtures, never hardware I/O."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .pv_communication import inventory as device_inventory
from .meter_workflow import states


def inventory(model,controller):
    groups=device_inventory(model,controller,'BESS')
    nodes={n['node_id']:n for n in model['nodes']}
    for group in groups:
        for d in group['devices']:
            a=nodes[d['node_id']].get('attributes',{})
            d['components']={key:a.get(key) for key in ['pcs_sn','pcs_firmware','bms_sn','bms_firmware']}
            d['pending']+=['PCS/BMS身份关系及固件适配','SOC范围/充放电实时边界/接触器和互锁定义','充放电符号/时序/本地保护依据']
    return groups


def simulate_device(d,scenario):
    node=d['node_id'];checks=[];diagnosis=None
    definitions=[
        ('path','通信路径与应答',d['path_valid'] and scenario!='timeout','收到合成通信帧','通信不可达','核对该台两端端口、总线、地址及供电条件；不自动改址','L4'),
        ('identity','BESS / PCS / BMS身份关系',not d['duplicate_sn'] and scenario!='wrong_identity',f'SIM-{node} → SIM-PCS-{node} / SIM-BMS-{node}；合成唯一关系','身份关系不符或SN重复','核对BESS及内部PCS/BMS身份关系；换机回到M1确认','L3'),
        ('driver','点表与驱动适用性',scenario!='driver_mismatch','SIM-BESS-DRIVER/1，适配演练夹具','点表不兼容','厂家提供型号、固件、PCS/BMS点表及驱动适配矩阵','L3'),
        ('quality','更新时序及数据质量',scenario!='stale','源序号1→2→3，GOOD，年龄0s；仅演练2s阈值','源数据陈旧，不能计入可调容量','核对源时间、序号及缓存；取得厂家刷新时序依据','L5'),
        ('units','充放电符号及单位',scenario!='unit_mismatch','演练：充电负、放电正；80000W ÷ 1000 = 80kW','充放电符号或单位不一致','厂家确认符号、倍率及单位；不能凭显示值推断方向','L3'),
        ('bms','BMS状态及保护有效性',scenario!='bms_unknown','合成BMS状态已知；接触器闭合、互锁正常','BMS状态未知','保留本地保护；核对BMS通信及状态定义，未知设备排除容量','L3'),
        ('health','运行模式与告警',scenario not in ('device_fault','unknown'),'模拟待机 / 无设备故障','设备故障告警：SIM-FAULT' if scenario=='device_fault' else '未知原因，未取得可靠限制码','保存告警及快照并请厂家确认；不绕过保护或猜测复位步骤','L3')]
    stopped=False
    for key,label,ok,evidence,reason,action,layer in definitions:
        checks.append(dict(key=key,label=label,status='SKIPPED' if stopped else 'PASS' if ok else 'FAIL',actual='前置失败，未取得有效证据' if stopped else evidence if ok else reason))
        if not stopped and not ok:
            diagnosis=dict(reason=reason,action=action,owner='EPC / 厂家技术支持',layer=layer,edge_id=d['route'][0]['edge_id'] if d['route'] else None)
            stopped=True
    completed={c['key']:c['status']=='PASS' for c in checks}
    valid=not stopped
    soc=5 if scenario=='soc_low' else 98 if scenario=='soc_high' else 55
    charge_allowed=scenario not in ('soc_high','bms_forbid','discharge_only')
    discharge_allowed=scenario not in ('soc_low','charge_only')
    reasons={'soc_low':('SOC条件不足：暂不具备放电条件','等待SOC满足批准范围后重新采集；不判设备故障、不绕过BMS'),
             'soc_high':('SOC条件不足：暂不具备充电条件','按批准SOC范围选择可用方向，条件变化后复核'),
             'bms_forbid':('BMS禁止充电，放电反馈允许','保存BMS限制码，请厂家确认原因；禁止覆盖电池保护'),
             'charge_only':('仅允许充电方向','后续只生成充电候选范围；放电动作保持未测试'),
             'discharge_only':('仅允许放电方向','后续只生成放电候选范围；充电动作保持未测试')}
    condition=valid and scenario in reasons
    if condition:
        reason,action=reasons[scenario]
        diagnosis=dict(reason=reason,action=action,owner='EPC / 厂家技术支持',layer='L5',edge_id=None)
    # Effective limits are min(feedback, explicit simulation constraint), never nameplate power.
    charge=min(90,80) if valid and charge_allowed else 0
    discharge=min(110,100) if valid and discharge_allowed else 0
    if valid:
        checks.append(dict(key='capacity',label='SOC与实时充放电边界',status='CONDITION' if condition else 'PASS',actual=f'SOC {soc}% / 演练范围10–90%；反馈上限90/110kW，演练约束80/100kW → 可用充电{charge}/放电{discharge}kW'))
    readings=dict(soc_pct=soc if valid else None,soh_pct=98 if valid else None,temperature_c=26 if valid else None,operating_state='STANDBY' if valid else None,
        charge_allowed=charge_allowed if valid else None,discharge_allowed=discharge_allowed if valid else None,
        feedback_charge_kw=90 if valid else None,feedback_discharge_kw=110 if valid else None,
        alarms=['SIM-FAULT'] if scenario=='device_fault' else [] if valid else None,
        contactor='CLOSED' if valid else None,interlock='OK' if valid else None,bms_state='KNOWN' if valid else 'UNKNOWN',
        quality='GOOD' if completed['quality'] else 'UNKNOWN',source_age_s=0 if completed['quality'] else None,
        observed_sn='SIM-'+node if completed['identity'] else None,pcs_sn='SIM-PCS-'+node if completed['identity'] else None,bms_sn='SIM-BMS-'+node if completed['identity'] else None)
    return dict(node_id=node,status='FAIL' if not valid else 'CONDITION' if condition else 'PASS',checks=checks,diagnosis=diagnosis,readings=readings,route=d['route'],
        capability=dict(eligible=valid,charge_kw=charge,discharge_kw=discharge,directions=([ 'charge'] if charge else [])+(['discharge'] if discharge else []),
            reason=diagnosis['reason'] if diagnosis else '按合成有效反馈与演练约束取小值',soc_min=10,soc_max=90,constraint_source='SIMULATION_ONLY',requires_action_recheck=True),
        action_tests=dict(charge='NOT_TESTED',discharge='NOT_TESTED'),source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',power_control_allowed=False,scenario=scenario)


class Scan(BaseModel):
    session_id:str
    mode:Literal['SIMULATION','REAL']='SIMULATION'
    acknowledged:bool=False
    request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    scenario:Literal['normal','timeout','wrong_identity','driver_mismatch','stale','unit_mismatch','bms_unknown','device_fault','unknown','soc_low','soc_high','bms_forbid','charge_only','discharge_only']='normal'
    fault_node:str=''


def register_bess_communication(app,db):
    def context(id,sid,mode):
        try:
            p=db.record(id)
            if p['kind']!='plan':raise KeyError(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        s=None;pcc=None;pv=None
        if sid:
            try:s=db.record(sid)
            except KeyError:raise HTTPException(404,'会话不存在')
            if s['kind']!='meter_session' or s['project']!=id:raise HTTPException(404,'会话不属于本项目')
            if s['mode']==mode:
                state=states(db.records('meter_run',sid))[6]
                if state['current'] and state['record']['status']=='PASS':pcc=state['record']
                records=[r for r in db.records('pv_communication',sid) if r['mode']==mode]
                candidate=records[0] if records else None
                if candidate and pcc and candidate['pcc_evidence_id']==pcc['id'] and candidate['model_hash']==p['engineering_hash'] and candidate['failed']==0:pv=candidate
        stale=digest(db.get(p['project'])['model'])!=p['engineering_hash']
        controller=s['route']['ems']['node_id'] if s else next((n['node_id'] for n in p['system_context_baseline']['nodes'] if n['node_type']=='EMS'),None)
        return p,s,inventory(environment_model(p['system_context_baseline'],mode),controller),pv,stale

    @app.get('/api/plans/{id}/bess-communication')
    def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,s,groups,pv,stale=context(id,session_id,mode)
        records=[r for r in db.records('bess_communication',session_id) if r['mode']==mode] if session_id else []
        latest=records[0] if records else None
        current=bool(latest and pv and not stale and latest['pv_evidence_id']==pv['id'] and latest['model_hash']==p['engineering_hash'])
        return dict(groups=groups,records=records,current=current,prerequisite_ready=bool(pv and not stale),stale=stale,field_connected=False,power_control_allowed=False)

    @app.post('/api/plans/{id}/bess-communication')
    def execute(id:str,body:Scan):
        if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；未执行储能现场验证')
        p,s,groups,pv,stale=context(id,body.session_id,body.mode)
        if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境的调试会话')
        rid=digest(dict(kind='bess-read',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
        try:prior=db.record(rid)
        except KeyError:prior=None
        if prior:
            if prior['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同场景')
            return prior
        if stale or not pv:raise HTTPException(409,'请先完成当前模型的步骤03及步骤04；前置重测后须重新验证')
        if not body.acknowledged:raise HTTPException(422,'请确认全体储能只读范围')
        devices=[d for g in groups for d in g['devices']]
        if not devices:raise HTTPException(422,'M1未定义储能设备')
        if body.scenario!='normal' and body.fault_node not in [d['node_id'] for d in devices]:raise HTTPException(422,'请选择范围内设备')
        results=[dict(**simulate_device(d,body.scenario if d['node_id']==body.fault_node else 'normal'),execution_order=i+1) for i,d in enumerate(devices)]
        scope=dict(kind='BESS_READ_ONLY',node_ids=[d['node_id'] for d in devices],groups=groups,controller=s['route']['ems']['node_id'],model_hash=p['engineering_hash'],pv_evidence_id=pv['id'])
        snapshot_at=datetime.now(timezone.utc).isoformat()
        record=dict(mode=body.mode,request_id=body.request_id,request_signature=signature,scope=scope,scope_hash=digest(scope),model_hash=p['engineering_hash'],pv_evidence_id=pv['id'],devices=results,
            passed=sum(d['status']=='PASS' for d in results),failed=sum(d['status']=='FAIL' for d in results),conditional=sum(d['status']=='CONDITION' for d in results),
            totals={k:sum(d['capability'][k] for d in results) for k in ['charge_kw','discharge_kw']},snapshot_at=snapshot_at,requires_action_recheck=True,
            power_control_allowed=False,field_result=None,manufacturer_basis='PENDING',source='SIMULATOR',version='SIM-BESS-COMM-1')
        saved=db.add_once('bess_communication',s['id'],record,rid)
        if saved['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同场景')
        return saved
