"""Step08 isolated synthetic charge/discharge engine; no physical device I/O."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .pv_control import control_context
from .pv_communication import inventory

PENDING=['现场写权限、唯一指令所有者、控制租约及EPC授权','BESS/PCS/BMS型号固件、控制点表与批准测试包','SOC允许范围、BMS互锁与实时充放电边界','功率正负符号、响应容差/时限与稳定窗口','撤销测试、原模式/设定值恢复及失去控制权时退出规程']


def direction_test(d,direction,scenario,run_id,capability):
    label='充电' if direction=='charge' else '放电';sign=-1 if direction=='charge' else 1
    soc=5 if scenario=='soc_low' else 98 if scenario=='soc_high' else 55
    bound=max(0,capability.get(direction+'_kw',0));allowed=direction in capability.get('directions',[])
    if scenario in ('soc_low','discharge_forbidden') and direction=='discharge':allowed=False
    if scenario in ('soc_high','charge_forbidden') and direction=='charge':allowed=False
    if not allowed:bound=0
    target=sign*min(30,bound);stages=[];commands=[];samples=[]
    snapshot=dict(soc_pct=soc,bms_known=scenario!='bms_unknown',bms_allowed=allowed,bound_kw=bound,source='SIMULATOR',age_s=0,sequence=1 if direction=='charge' else 2,original_mode='STANDBY',original_setpoint_kw=0)
    def stage(k,l,status,e):stages.append(dict(key=k,label=l,status=status,evidence=e))
    def result(status,reason=None,action=None,restored=False,required=False):
        return dict(direction=direction,label=label,status=status,snapshot=snapshot,target_kw=target,stages=stages,commands=commands,samples=samples,restored=restored,restore_required=required,diagnosis=dict(reason=reason,action=action,layer='L5',owner='EPC / 厂家技术支持') if reason else None,source='SIMULATOR')
    if not d['path_valid'] or not d['control_valid'] or d['duplicate_sn'] or not capability.get('eligible') or scenario in ('bms_unknown','no_permission','missing_basis'):
        reason='BMS状态未知，禁止计入可调容量' if scenario=='bms_unknown' else '控制权限、批准演练包或设备映射不满足'
        stage('preflight','方向条件与权限','FAIL',reason)
        return result('FAIL',reason,'核对身份、BMS反馈、控制域与批准规程；不得覆盖电池本地保护')
    if not allowed or bound<=0:
        reason=label+'条件未满足：'+('SOC不适合本方向' if scenario in ('soc_low','soc_high') else 'BMS/步骤05能力边界不允许')
        stage('preflight','方向条件与权限','CONDITION',f'SOC {soc}% · BMS允许={allowed} · 可用边界{bound}kW；无指令')
        return result('CONDITION',reason,'保留该方向未测试；等待SOC及BMS条件满足，取得有效实时反馈后复测')
    stage('preflight','方向条件与权限','PASS',f'SIM范围/所有者/写权限/演练包有效；本方向新采样序号{snapshot["sequence"]}，SOC {soc}%，BMS允许，可用{bound}kW；目标{target}kW不超边界')
    ack='UNKNOWN' if scenario=='ack_timeout' else 'REJECTED' if scenario=='rejected' else 'ACCEPTED'
    commands.append(dict(id=f'{run_id}-{d["node_id"]}-{direction}',kind=direction.upper(),value_kw=target,ack=ack))
    stage('command','指令与确认','PASS' if ack=='ACCEPTED' else 'FAIL','命令ID匹配，模拟确认接受；仍需功率证据' if ack=='ACCEPTED' else '确认超时，不能推断未执行' if ack=='UNKNOWN' else '设备明确拒令')
    response_ok=scenario not in ('ack_timeout','rejected','no_response','wrong_sign','boundary_drop','owner_lost')
    evidence='目标方向及末3点功率满足演练±2kW/5s；SOC、BMS允许及实时边界持续有效' if response_ok else '功率未响应' if scenario=='no_response' else '功率符号与测试方向相反' if scenario=='wrong_sign' else '运行中边界降为0，立即中止本方向' if scenario=='boundary_drop' else '指令所有者丢失，停止新动作' if scenario=='owner_lost' else '确认未取得，不判响应通过'
    stage('response','功率与实时边界','PASS' if response_ok else 'SKIPPED' if ack!='ACCEPTED' else 'FAIL',evidence)
    if scenario=='owner_lost':
        samples.extend([dict(t=0,power_kw=0,target_kw=target,bound_kw=bound,soc_pct=soc,bms_allowed=True),dict(t=1,power_kw=target/2,target_kw=target,bound_kw=bound,soc_pct=soc,bms_allowed=True)])
        stage('restore','归零并恢复原模式','UNCONFIRMED','未发新恢复指令；不抢回所有权，退出状态待执行方确认')
        return result('FAIL','所有权丢失，恢复未确认','停止后续动作，协调当前所有者并按厂家批准退出策略核验',required=True)
    commands.append(dict(id=f'{run_id}-{d["node_id"]}-{direction}-restore',kind='RESTORE',value_kw=0,ack='ACCEPTED'))
    restored=scenario!='restore_failed'
    stage('restore','归零并恢复原模式','PASS' if restored else 'UNCONFIRMED','模拟原设定0kW读回、实测0kW、STANDBY原模式一致' if restored else '归零回执接受，但功率/模式未恢复；不能启动另一方向')
    powers=[0,target/2,target,target,target,target/2,0,0]
    if scenario in ('no_response','rejected'):powers=[0]*8
    if scenario=='wrong_sign':powers=[0,-target/2,-target,-target,-target,-target/2,0,0]
    if scenario=='boundary_drop':powers=[0,target/2,target,0,0,0,0,0]
    if scenario=='restore_failed':powers=[0,target/2,target,target,target,target,target,target]
    for i,power in enumerate(powers):
        live_bound=0 if scenario=='boundary_drop' and i>=3 else bound
        samples.append(dict(t=i,power_kw=power,target_kw=target if 0<i<5 and live_bound else 0,bound_kw=live_bound,soc_pct=round(soc-sign*i*0.01,2),bms_allowed=live_bound>0))
    if not restored:return result('FAIL','恢复未确认，告警保持','停止另一方向及后续设备；保存回执、功率与模式证据，请厂家协同',required=True)
    if not response_ok:return result('FAIL',evidence,'原0kW及待机模式已模拟恢复；核对BMS限制、点表符号、权限和边界，禁止绕过保护',True,True)
    return result('PASS',restored=True,required=True)


def skipped(direction):return dict(direction=direction,label='充电' if direction=='charge' else '放电',status='SKIPPED',snapshot=None,target_kw=None,stages=[],commands=[],samples=[],restored=False,restore_required=False,diagnosis=None,source='SIMULATOR')


class Command(BaseModel):
    session_id:str
    mode:Literal['SIMULATION','REAL']='SIMULATION'
    acknowledged:bool=False
    request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    scenario:Literal['normal','soc_low','soc_high','charge_forbidden','discharge_forbidden','bms_unknown','no_permission','missing_basis','ack_timeout','rejected','no_response','wrong_sign','boundary_drop','restore_failed','owner_lost']='normal'
    fault_node:str=''
    fault_direction:Literal['charge','discharge']='charge'


def register_bess_control(app,db):
    def context(id,sid,mode):
        p,s,_,cfg,_,stale=control_context(db,id,sid,mode)
        prior=next((r for r in db.records('pv_control',sid) if r['mode']==mode),None) if s and s['mode']==mode else None
        if not (prior and cfg and prior['configuration_id']==cfg['id'] and prior['passed']==len(prior['devices']) and not prior['failed'] and not prior['conditional'] and not prior['alarm_latched']):prior=None
        bess=next((r for r in db.records('bess_communication',sid) if r['mode']==mode),None) if s and s['mode']==mode else None
        groups=inventory(p['system_context_baseline'],s['route']['ems']['node_id'] if s else None,'BESS');model=p['system_context_baseline'];ports={v['port_id']:v for v in model['ports']}
        for g in groups:
            for d in g['devices']:d['control_valid']=any(e['edge_type']=='CONTROL' and ports[e['from_port_id']]['node_id']==d['controller'] and ports[e['to_port_id']]['node_id']==d['node_id'] for e in model['edges'])
        return p,s,groups,prior,bess,stale
    def recovered(r):return bool(db.records('bess_control_recovery',r['id']))

    @app.get('/api/plans/{id}/bess-control')
    def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,s,groups,prior,bess,stale=context(id,session_id,mode)
        records=[r for r in db.records('bess_control',session_id) if r['mode']==mode] if s else []
        last=records[0] if records else None
        return dict(groups=groups,records=records,current=bool(last and prior and not stale and last['pv_control_id']==prior['id']),prerequisite_ready=bool(prior and not stale),alarm_latched=bool(last and last['alarm_latched'] and not recovered(last)),recovery=db.records('bess_control_recovery',last['id']) if last else [],basis_pending=PENDING,field_connected=False,physical_control_allowed=False)

    @app.post('/api/plans/{id}/bess-control')
    def execute(id:str,body:Command):
        if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；现场写权限、BMS边界及厂家批准依据未齐备，未下发指令')
        p,s,groups,prior,bess,stale=context(id,body.session_id,body.mode)
        if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
        rid=digest(dict(kind='bess-control',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
        try:old=db.record(rid)
        except KeyError:old=None
        if old:
            if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同场景')
            return old
        if stale or not prior:raise HTTPException(409,'请先完成当前模型步骤03至07；前置重测后需重新验证')
        last=next(iter(db.records('bess_control',s['id'])),None)
        if last and last['alarm_latched'] and not recovered(last):raise HTTPException(409,'原运行恢复未确认，禁止新测试')
        if not body.acknowledged:raise HTTPException(422,'请确认独立储能双向演练范围及退出策略')
        devices=[d for g in groups for d in g['devices']]
        if not devices:raise HTTPException(422,'缺少储能设备')
        if body.scenario!='normal' and body.fault_node not in [d['node_id'] for d in devices]:raise HTTPException(422,'异常设备不在范围')
        capabilities={d['node_id']:d['capability'] for d in bess['devices']};results=[];stopped=False
        for i,d in enumerate(devices):
            directions=[]
            for direction in ('charge','discharge'):
                scenario=body.scenario if d['node_id']==body.fault_node and (direction==body.fault_direction or body.scenario in ('soc_low','soc_high','charge_forbidden','discharge_forbidden')) else 'normal'
                r=skipped(direction) if stopped else direction_test(d,direction,scenario,rid,capabilities.get(d['node_id'],{}))
                directions.append(r)
                if r['status']=='FAIL':stopped=True
            status='FAIL' if any(r['status']=='FAIL' for r in directions) else 'SKIPPED' if all(r['status']=='SKIPPED' for r in directions) else 'CONDITION' if any(r['status']=='CONDITION' for r in directions) else 'PASS'
            results.append(dict(node_id=d['node_id'],execution_order=i+1,status=status,directions=directions))
        scope=dict(kind='SIM_BESS_BIDIRECTIONAL_CONTROL',model_hash=p['engineering_hash'],node_ids=[d['node_id'] for d in devices],pv_control_id=prior['id'],bess_capability_id=bess['id'],controller=s['route']['ems']['node_id'],test_pack='SIM-BESS-CONTROL-1',physical_lease=False)
        result=dict(mode=body.mode,request_id=body.request_id,request_signature=signature,scope=scope,scope_hash=digest(scope),pv_control_id=prior['id'],devices=results,passed=sum(d['status']=='PASS' for d in results),failed=sum(d['status']=='FAIL' for d in results),conditional=sum(d['status']=='CONDITION' for d in results),skipped=sum(d['status']=='SKIPPED' for d in results),direction_counts={key:sum(r['status']=='PASS' for d in results for r in d['directions'] if r['direction']==key) for key in ('charge','discharge')},alarm_latched=any(r['restore_required'] and not r['restored'] for d in results for r in d['directions']),source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',physical_control_allowed=False)
        saved=db.add_once('bess_control',s['id'],result,rid)
        if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
        return saved

    @app.post('/api/plans/{id}/bess-control/{run_id}/recover')
    def recover(id:str,run_id:str,body:Command):
        if body.mode!='SIMULATION':raise HTTPException(503,'未执行现场恢复')
        p,s,groups,prior,bess,stale=context(id,body.session_id,body.mode)
        try:r=db.record(run_id)
        except KeyError:raise HTTPException(404,'运行不存在')
        if not s or r['kind']!='bess_control' or r['project']!=s['id'] or r['mode']!='SIMULATION':raise HTTPException(404,'运行不属于本会话')
        if not body.acknowledged or not r['alarm_latched']:raise HTTPException(409,'需明确确认模拟恢复范围')
        if stale or not prior or r['pv_control_id']!=prior['id']:raise HTTPException(409,'原运行依据已变化，不能确认恢复')
        return db.add_once('bess_control_recovery',run_id,dict(mode='SIMULATION',source='SIMULATOR',status='SIM_RECOVERY_VERIFIED',evidence='独立演练重新确认控制所有者、BMS与互锁；原设定0kW、实际0kW及STANDBY原模式一致。不启动另一方向或新测试，原失败记录保留。',field_result=None,physical_control_allowed=False),digest(dict(kind='bess-recovery',run=run_id)))
