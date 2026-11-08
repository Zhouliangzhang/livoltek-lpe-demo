"""Step07 synthetic sequential control engine. Never performs physical device I/O."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .meter_workflow import states
from .pv_communication import inventory

PENDING=['现场控制租约、唯一指令所有者及EPC作业授权','型号/固件/驱动适用的批准控制测试规程','限功率点表、单位、确认语义与生效条件','功率响应容差/时限、光照条件与恢复/退出策略','M1批准配置与真实配置读回一致证据']


def control_inventory(model,controller):
    groups=inventory(model,controller);ports={p['port_id']:p for p in model['ports']}
    for g in groups:
        for d in g['devices']:
            d['control_valid']=any(e['edge_type']=='CONTROL' and ports[e['from_port_id']]['node_id']==controller and ports[e['to_port_id']]['node_id']==d['node_id'] for e in model['edges'])
    return groups


def simulate(d,scenario,run_id,permission=True):
    stages=[];commands=[];samples=[];diagnosis=None;restored=False
    def stage(key,label,status,evidence):stages.append(dict(key=key,label=label,status=status,evidence=evidence))
    def issue(reason,action,layer='L5'):
        nonlocal diagnosis
        diagnosis=dict(reason=reason,action=action,layer=layer,owner='EPC / 厂家技术支持')
    pre=d['path_valid'] and d['control_valid'] and not d['duplicate_sn'] and permission and scenario not in ('no_permission','missing_basis','low_available')
    if not pre:
        condition=scenario=='low_available'
        reason='可用功率20kW低于演练目标50kW，不能证明限功率响应' if condition else '演练批准测试包缺失' if scenario=='missing_basis' else '控制权限或设备映射不满足'
        issue(reason,'等待足够可用功率后复测，不判设备故障' if condition else '核对唯一所有者、写权限、通信映射及批准规程；不绕过限制')
        stage('preflight','控制前核验','CONDITION' if condition else 'FAIL',reason)
        for key,label in [('command','指令与确认'),('response','功率响应'),('restore','撤销测试与恢复')]:stage(key,label,'SKIPPED','未下发测试指令')
        return dict(node_id=d['node_id'],status='CONDITION' if condition else 'FAIL',stages=stages,commands=[],samples=[],diagnosis=diagnosis,restored=False,restore_required=False,original_limit_kw=None,target_kw=50,source='SIMULATOR')
    stage('preflight','控制前核验','PASS','独立SIM控制范围 / 单一SIM所有者 / 写权限 / SIM-PV-CONTROL-1演练包；现场依据仍待确认')
    original=125;target=50
    commands.append(dict(id=run_id+'-'+d['node_id']+'-limit',kind='LIMIT',value_kw=target,ack='UNKNOWN' if scenario=='ack_timeout' else 'REJECTED' if scenario=='rejected' else 'ACCEPTED',source='SIMULATOR'))
    stage('command','指令与确认','FAIL' if scenario in ('ack_timeout','rejected') else 'PASS','确认超时：不能推断指令未生效' if scenario=='ack_timeout' else '设备明确拒绝限功率指令' if scenario=='rejected' else '命令ID匹配，模拟回执接受50kW限值；仍需功率证据')
    response_ok=scenario not in ('ack_timeout','rejected','no_response','owner_lost')
    if scenario=='owner_lost':
        stage('response','功率响应','FAIL','运行中控制所有者丢失，停止发出新测试动作')
        stage('restore','撤销测试与恢复','UNCONFIRMED','未再发送恢复指令；退出策略待执行方确认，禁止自动抢回控制权')
        issue('指令所有权丢失，恢复未确认','停止后续测试并联系厂家；协调当前所有者，按批准退出策略核验状态')
        samples=[dict(t=0,power_kw=80,limit_kw=125,available_kw=100),dict(t=1,power_kw=70,limit_kw=50,available_kw=100)]
    else:
        stage('response','功率响应','SKIPPED' if scenario in ('ack_timeout','rejected') else 'PASS' if response_ok else 'FAIL','未取得可靠确认，不判定响应通过' if scenario in ('ack_timeout','rejected') else '80→65→50kW，末3点稳定；演练容差±2kW / 5s，非厂家判据' if response_ok else '回执接受，但功率维持80kW，超出演练响应时限')
        restored=scenario!='restore_failed'
        commands.append(dict(id=run_id+'-'+d['node_id']+'-restore',kind='RESTORE',value_kw=original,ack='ACCEPTED',source='SIMULATOR'))
        stage('restore','撤销测试与恢复','PASS' if restored else 'UNCONFIRMED','原限值125kW读回一致；功率恢复80kW，未超过当时可用100kW' if restored else '恢复指令已确认，但限值仍为50kW；恢复未确认')
        powers=[80,65,50,50,50,65,80,80] if response_ok else [80]*8
        if not restored:powers=[80,65,50,50,50,50,50,50]
        samples=[dict(t=i,power_kw=p,limit_kw=125 if i==0 or i>=5 and restored else 50,available_kw=100) for i,p in enumerate(powers)]
        if not restored:issue('恢复限值读回不符，告警保持','停止后续设备测试；保留原限值与命令证据，请厂家核对恢复及生效条件')
        elif not response_ok:issue('指令确认超时' if scenario=='ack_timeout' else '设备拒令' if scenario=='rejected' else '指令已接受但功率未响应','核对该台控制模式、点表、当前可用功率及限制原因；原限值已模拟恢复，需处理后重新验证')
    return dict(node_id=d['node_id'],status='PASS' if response_ok and restored else 'FAIL',stages=stages,commands=commands,samples=samples,diagnosis=diagnosis,restored=restored,restore_required=True,original_limit_kw=original,target_kw=target,source='SIMULATOR')


class Command(BaseModel):
    session_id:str
    mode:Literal['SIMULATION','REAL']='SIMULATION'
    acknowledged:bool=False
    request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    scenario:Literal['normal','no_permission','missing_basis','ack_timeout','rejected','no_response','low_available','restore_failed','owner_lost']='normal'
    fault_node:str=''


def register_pv_control(app,db):
    def context(id,sid,mode):
        try:
            p=db.record(id)
            if p['kind']!='plan':raise KeyError(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        s=None;cfg=None;pv=None
        if sid:
            try:s=db.record(sid)
            except KeyError:raise HTTPException(404,'会话不存在')
            if s['kind']!='meter_session' or s['project']!=id:raise HTTPException(404,'会话不属于本项目')
            if s['mode']==mode:
                complete=states(db.records('meter_run',sid))[6]
                def latest(kind):return next((r for r in db.records(kind,sid) if r['mode']==mode),None)
                pv=latest('pv_communication');bess=latest('bess_communication');candidate=latest('configuration_readback')
                if complete['current'] and complete['record']['status']=='PASS' and pv and bess and candidate and not pv['failed'] and not bess['failed'] and pv['pcc_evidence_id']==complete['record']['id'] and bess['pv_evidence_id']==pv['id'] and candidate['bess_evidence_id']==bess['id'] and pv['model_hash']==bess['model_hash']==candidate['model_hash']==p['engineering_hash'] and not any(candidate['counts'].get(k,0) for k in ('DIFFERENCE','UNREAD','UNIT_MISMATCH','TYPE_MISMATCH')):cfg=candidate
        stale=digest(db.get(p['project'])['model'])!=p['engineering_hash']
        groups=control_inventory(p['system_context_baseline'],s['route']['ems']['node_id'] if s else None)
        return p,s,groups,cfg,pv,stale
    def recovered(run):return bool(db.records('pv_control_recovery',run['id']))

    @app.get('/api/plans/{id}/pv-control')
    def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,s,groups,cfg,pv,stale=context(id,session_id,mode)
        records=[r for r in db.records('pv_control',session_id) if r['mode']==mode] if session_id else []
        last=records[0] if records else None
        return dict(groups=groups,records=records,prerequisite_ready=bool(cfg and not stale),current=bool(last and cfg and not stale and last['configuration_id']==cfg['id']),alarm_latched=bool(last and last['alarm_latched'] and not recovered(last)),recovery=db.records('pv_control_recovery',last['id']) if last else [],basis_pending=PENDING,physical_control_allowed=False,field_connected=False)

    @app.post('/api/plans/{id}/pv-control')
    def execute(id:str,body:Command):
        if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；缺少有效现场权限、控制租约和批准依据，未下发指令')
        p,s,groups,cfg,pv,stale=context(id,body.session_id,body.mode)
        if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
        rid=digest(dict(kind='pv-control',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
        try:old=db.record(rid)
        except KeyError:old=None
        if old:
            if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同场景')
            return old
        if stale or not cfg:raise HTTPException(409,'请完成当前基线步骤03至06，处理配置差异后再测试')
        last=next(iter(db.records('pv_control',s['id'])),None)
        if last and last['alarm_latched'] and not recovered(last):raise HTTPException(409,'原运行恢复未确认，先复核模拟恢复；禁止启动新测试')
        if not body.acknowledged:raise HTTPException(422,'须明确确认独立PV控制演练范围；只读权限不自动扩展')
        devices=[d for g in groups for d in g['devices']]
        if not devices:raise HTTPException(422,'缺少光伏设备')
        if body.scenario!='normal' and body.fault_node not in [d['node_id'] for d in devices]:raise HTTPException(422,'请选择本次范围内设备')
        permissions={d['node_id']:d['readings'].get('remote_write') is True for d in pv['devices']}
        results=[];stopped=False
        for i,d in enumerate(devices):
            if stopped:r=dict(node_id=d['node_id'],status='SKIPPED',stages=[],commands=[],samples=[],diagnosis=None,restored=False,restore_required=False,original_limit_kw=None,target_kw=50,source='SIMULATOR')
            else:r=simulate(d,body.scenario if d['node_id']==body.fault_node else 'normal',rid,permissions.get(d['node_id'],False))
            results.append(dict(**r,execution_order=i+1))
            if r['status']!='PASS':stopped=True
        scope=dict(kind='SIM_PV_CONTROL',node_ids=[d['node_id'] for d in devices],controller=s['route']['ems']['node_id'],model_hash=p['engineering_hash'],configuration_id=cfg['id'],allowed_actions=['SIM_LIMIT','SIM_RESTORE'],physical_lease=False,owner='SIM-CONTROL-ENGINE',test_pack='SIM-PV-CONTROL-1')
        result=dict(mode=body.mode,request_id=body.request_id,request_signature=signature,scope=scope,scope_hash=digest(scope),configuration_id=cfg['id'],devices=results,passed=sum(d['status']=='PASS' for d in results),failed=sum(d['status']=='FAIL' for d in results),conditional=sum(d['status']=='CONDITION' for d in results),skipped=sum(d['status']=='SKIPPED' for d in results),alarm_latched=any(d['restore_required'] and not d['restored'] for d in results),manufacturer_basis='PENDING',basis_pending=PENDING,physical_control_allowed=False,source='SIMULATOR',field_result=None)
        saved=db.add_once('pv_control',s['id'],result,rid)
        if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
        return saved

    @app.post('/api/plans/{id}/pv-control/{run_id}/recover')
    def recover(id:str,run_id:str,body:Command):
        if body.mode!='SIMULATION':raise HTTPException(503,'未执行现场恢复')
        p,s,groups,cfg,pv,stale=context(id,body.session_id,body.mode)
        try:r=db.record(run_id)
        except KeyError:raise HTTPException(404,'运行不存在')
        if not s or r['kind']!='pv_control' or r['project']!=s['id'] or r['mode']!='SIMULATION':raise HTTPException(404,'运行不属于本会话')
        if not body.acknowledged or not r['alarm_latched']:raise HTTPException(409,'需明确确认模拟恢复范围')
        if stale or not cfg or cfg['id']!=r['configuration_id']:raise HTTPException(409,'依据已变化，不能用新上下文确认原运行恢复')
        return db.add_once('pv_control_recovery',run_id,dict(mode='SIMULATION',source='SIMULATOR',status='SIM_RECOVERY_VERIFIED',evidence='独立演练重新确认SIM所有者，原限值125kW读回、功率80kW及可用100kW一致；不重启测试，不改写原失败记录',field_result=None,physical_control_allowed=False),digest(dict(kind='pv-control-recovery',run=run_id)))
