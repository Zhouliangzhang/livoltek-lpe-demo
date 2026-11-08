"""Persisted mock-iEMS tasks bound to immutable M1 step10 draft baselines.

Real writes are deliberately unavailable. Rehearsal results never populate actual values.
"""
import copy
import hashlib
import json
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from .m1_baseline import content_hash
from .store import now

class TaskRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    baseline_id:str=Field(min_length=1,max_length=128)
    environment:Literal['OFFLINE','SIMULATION','REAL']
    request_id:str=Field(min_length=8,max_length=128)
    action:Literal['DEPLOY','REHEARSE']
    scenario:Literal['MATCH','DIFFERENCE','READ_FAILED','UNSUPPORTED','REJECTED','ACK_LOST','INTERRUPTED']='MATCH'
    fault_device:str=Field(default='',max_length=128)

LABELS={'protocol':'协议','baud_rate':'波特率','data_bits':'数据位','parity':'校验方式','stop_bits':'停止位','address':'站号','role':'接口角色','ip_address':'IP地址','subnet_mask':'子网掩码','gateway':'网关','tcp_port':'服务端口','meter_ct_ratio':'仪表CT倍率','meter_pt_ratio':'仪表PT倍率','read_side':'读数侧别','input_unit':'输入单位','raw_sign':'功率符号','driver_scale':'驱动缩放','power_field':'功率字段','refresh_seconds':'刷新周期','stale_seconds':'过期判定','time_source':'时间来源','quality_field':'质量字段','import_target':'购电目标','export_limit':'允许送电上限','cycle_seconds':'控制周期','response_seconds':'响应判据','pv_mode':'光伏限值表达','pv_limit':'站级光伏限值','pv_allocation':'光伏分配规则','pv_ramp':'光伏爬坡','pv_ack_seconds':'确认时限','pv_restore':'光伏恢复方式','charge_limit':'站级充电上限','discharge_limit':'站级放电上限','soc_min':'SOC下限','soc_max':'SOC上限','reserve_kwh':'预约容量','bess_mode':'储能模式','enable_conditions':'启用条件','priority':'目标优先级','meter_loss':'计量失效方案','pv_reject':'光伏拒令方案','bess_unavailable':'储能不可用方案','recovery_conditions':'恢复条件','stable_seconds':'稳定观察时间'}
UNITS={'baud_rate':'bit/s','refresh_seconds':'s','stale_seconds':'s','import_target':'kW','export_limit':'kW','cycle_seconds':'s','response_seconds':'s','pv_ramp':'kW/s','pv_ack_seconds':'s','charge_limit':'kW','discharge_limit':'kW','soc_min':'%','soc_max':'%','reserve_kwh':'kWh','stable_seconds':'s'}

def baseline(db,project,id):
    try:b=db.record(id)
    except KeyError:raise HTTPException(404,'冻结基线不存在')
    if b['kind']!='m1_config_baseline' or b['project']!=project:raise HTTPException(404,'冻结基线不存在')
    if b.get('status')!='FROZEN_DRAFT' or content_hash(b['snapshot'])!=b.get('content_hash') or content_hash({k:v for k,v in b.items() if k!='archive_hash'})!=b.get('archive_hash'):
        raise HTTPException(409,'冻结基线完整性校验失败，不能创建配置任务')
    return b

def inventory(b):
    s=b['snapshot'];controller=s['scope']['domain']['controller_id'];ids=set(s['scope']['target_ids'])
    if b['scope_type']!='PARTIAL':ids|={controller}|set(s['metering'])
    result=[]
    for nid in sorted(ids,key=lambda id:(id!=controller,id)):
        d=s['devices'].get(nid)
        if not d:continue
        rows=[]
        def add(key,value,owner,step,unit=None):
            if value is None or value=='':return
            rows.append({'id':owner+'::'+key,'label':LABELS.get(key,key),'key':key,'owner':owner,'planned':value,'unit':unit if unit is not None else UNITS.get(key,''),'approved':None,'actual':None,'actual_time':None,'step':step,'basis':'PENDING','mapping':'UNVERIFIED'})
        for bus in s['communication'].values():
            for pid,values in bus['devices'].items():
                if s['ports'].get(pid,{}).get('node_id')!=nid:continue
                for key,value in {**bus['shared'],**values}.items():add(key,value,pid,7)
        for meter,r in s['metering'].items():
            if nid==meter:
                for key in ('meter_ct_ratio','meter_pt_ratio'):add(key,r.get(key),meter,8)
            if nid==controller:
                for key in ('read_side','input_unit','raw_sign','driver_scale','power_field','refresh_seconds','stale_seconds','time_source','quality_field'):add(key,r.get(key),'计量映射/'+meter,8)
        if nid==controller and b['scope_type']!='PARTIAL':
            for domain,r in s['strategies'].items():
                keys=[]
                if r.get('zero_enabled'):keys+=['import_target','export_limit','cycle_seconds','response_seconds']
                if r.get('pv_enabled'):keys+=['pv_mode','pv_limit','pv_allocation','pv_ramp','pv_ack_seconds','pv_restore']
                if r.get('bess_enabled'):keys+=['bess_mode','charge_limit','discharge_limit','soc_min','soc_max','reserve_kwh']
                if keys:keys+=['enable_conditions','priority','meter_loss','pv_reject','bess_unavailable','recovery_conditions','stable_seconds']
                for key in keys:add(key,r.get(key),'站级策略/'+domain,9,('%' if r.get('pv_mode')=='PERCENT' else 'kW') if key=='pv_limit' else None)
        result.append({'node_id':nid,'name':d['name'],'model':d.get('model_name'),'firmware':d.get('firmware'),'serial_number':d.get('serial_number'),'group_key':'|'.join(str(d.get(k) or '待确认') for k in ('model_id','master_data_version','firmware')),'parameters':rows})
    return result

def preflight(db,project,b,env):
    if b['environment']!=env:raise HTTPException(409,'冻结基线环境不匹配，禁止跨环境沿用')
    current=db.get(project)['revision'];stale=current!=b['source_revision']
    gates=[{'key':'revision','label':'当前工程版本','ok':not stale,'reason':'与冻结版本一致' if not stale else '工程已变化，需返回步骤10重新核对并冻结','step':10},
           {'key':'manufacturer','label':'厂家批准依据','ok':False,'reason':'适用型号、固件、点表、读回规则与批准程序尚未核验','step':10},
           {'key':'authorization','label':'项目授权与写权限','ok':False,'reason':'操作人或授权引用不等于可信写权限；尚无核验记录','step':10},
           {'key':'identity','label':'iEMS身份与现场状态','ok':False,'reason':'真实接口未连接；未核验SN、当前版本、控制所有权及现场条件','step':1}]
    if b['findings']:gates.append({'key':'findings','label':'冻结范围待办','ok':False,'reason':f'冻结时保留 {len(b["findings"])} 条待办；不得按完整已批准配置执行','step':10})
    if b['scope_type']=='READ_ONLY':gates.append({'key':'readonly','label':'只读配置范围','ok':False,'reason':'本冻结范围没有写入意图；不能启动配置下发','step':10})
    return {'baseline_id':b['id'],'source_revision':b['source_revision'],'content_hash':b['content_hash'],'environment':env,'current_revision':current,'stale':stale,'gates':gates,'can_deploy':False,'can_rehearse':env=='SIMULATION' and not stale,'devices':inventory(b),'actual_state':'UNKNOWN','strategy_activation':'NOT_ACTIVATED'}

def simulate(b,devices,scenario,fault_device):
    events=[];results=[];interrupted=False;readonly=b['scope_type']=='READ_ONLY'
    def event(device,stage,message):events.append({'time':now(),'device':device,'stage':stage,'message':message,'source':'MOCK_IEMS'})
    event(b['snapshot']['scope']['domain']['controller_id'],'PREPARE','后端模拟器装载冻结候选配置；批准值与现场值保持未知，策略不激活')
    for d in devices:
        target=d['node_id']==fault_device and scenario!='MATCH';fault=scenario if target else 'MATCH'
        row=copy.deepcopy(d);row.update(command='NOT_REQUESTED',readback='NOT_READ',status='NO_PLAN',reason='',action='',before_snapshot={r['id']:None for r in d['parameters']},after_snapshot={},actual_state='UNKNOWN')
        if interrupted:
            row.update(status='NOT_ATTEMPTED',reason='模拟执行中断后停止后续动作',action='查询原任务ID与已知状态，不重复发起写入')
        elif not d['parameters']:
            row.update(reason='冻结范围内尚无可核对的已填参数；不能把站级功率值复制到每台设备',action='回步骤07补充设备通信配置；厂家确认逐台映射和适用依据')
        else:
            event(d['node_id'],'BEFORE','现场修改前值未知；仅创建模拟记录，不伪造现场前快照')
            if fault=='INTERRUPTED':
                interrupted=True;row.update(status='INTERRUPTED',command='UNKNOWN',reason='演练：执行中断，指令是否被设备处理未知',action='按任务ID查询状态；未经核对不重发、不宣称已回退');event(d['node_id'],'INTERRUPTED',row['reason'])
            elif fault=='REJECTED' and not readonly:
                row.update(status='REJECTED',command='REJECTED',reason='演练：设备拒绝配置指令',action='核对该设备权限、模式和型号/固件适用依据');event(d['node_id'],'COMMAND_REJECTED',row['reason'])
            elif fault=='ACK_LOST' and not readonly:
                interrupted=True
                row.update(status='ACK_UNKNOWN',command='UNKNOWN',reason='演练：指令确认丢失；不能判定设备未执行',action='查询原任务与设备实际值；禁止盲目重发或假定回滚');event(d['node_id'],'ACK_UNKNOWN',row['reason'])
            else:
                row['command']='NOT_REQUESTED' if readonly else 'SIM_ACK'
                event(d['node_id'],'READ_ONLY' if readonly else 'ACK','只读模拟，不发配置指令' if readonly else '模拟指令确认；尚不代表配置生效')
                status={'DIFFERENCE':'SIM_DIFFERENCE','READ_FAILED':'SIM_READ_FAILED','UNSUPPORTED':'SIM_UNSUPPORTED'}.get(fault,'SIM_CANDIDATE_MATCH')
                for index,r in enumerate(row['parameters']):
                    actual=copy.deepcopy(r['planned']);state='SIM_CANDIDATE_MATCH'
                    if fault in ('READ_FAILED','UNSUPPORTED'):actual=None;state=status
                    elif fault=='DIFFERENCE' and index==0:
                        try:actual=str(float(actual)+1)
                        except (TypeError,ValueError):actual=str(actual)+' [模拟差异]'
                        state=status
                    r.update(simulated_readback=actual,simulated_time=now(),status=state,source='MOCK_IEMS')
                    row['after_snapshot'][r['id']]=actual
                row.update(status=status,readback=status,reason={'SIM_DIFFERENCE':'演练：设备读回与冻结候选值不一致','SIM_READ_FAILED':'演练：未取得有效读回','SIM_UNSUPPORTED':'演练：驱动不支持该项读回'}.get(status,'合成读回与候选值相同；批准与现场适用性仍未确认'),action='核对表中参数、权限、点表及生效条件；必要时回原步骤修改并冻结新基线，不能覆盖原基线')
                event(d['node_id'],'READBACK',row['reason'])
        for r in row['parameters']:
            r.setdefault('status',row['status']);r.setdefault('simulated_readback',None);r.setdefault('simulated_time',None);r['source']='MOCK_IEMS'
        results.append(row)
    status='SIMULATION_INTERRUPTED' if interrupted else 'SIMULATION_INCOMPLETE' if any(d['status']!='SIM_CANDIDATE_MATCH' for d in results) else 'SIMULATION_CANDIDATE_MATCH'
    return results,events,status

def register_delivery(app,db):
    kind='m1_delivery_task'
    @app.get('/api/projects/{project}/config-tasks/preflight/{baseline_id}')
    def check(project:str,baseline_id:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        return preflight(db,project,baseline(db,project,baseline_id),environment)
    @app.get('/api/projects/{project}/config-tasks')
    def history(project:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        return [{k:v for k,v in r.items() if k not in ('devices','events','preflight')} for r in db.records(kind,project) if r['environment']==environment][:100]
    @app.get('/api/projects/{project}/config-tasks/{task_id}')
    def detail(project:str,task_id:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        try:r=db.record(task_id)
        except KeyError:raise HTTPException(404,'任务不存在')
        if r['kind']!=kind or r['project']!=project or r['environment']!=environment:raise HTTPException(404,'本项目当前环境没有该任务')
        return r
    @app.post('/api/projects/{project}/config-tasks')
    def execute(project:str,request:TaskRequest):
        payload=request.model_dump();fingerprint=content_hash(payload)
        task_id='m1task-'+hashlib.sha256((project+'|'+request.environment+'|'+request.request_id).encode()).hexdigest()
        try:
            existing=db.record(task_id)
            if existing.get('request_hash')!=fingerprint:raise HTTPException(409,'同一请求ID不能对应不同动作')
            return existing
        except KeyError:pass
        b=baseline(db,project,request.baseline_id);checks=preflight(db,project,b,request.environment)
        if request.action=='REHEARSE' and not checks['can_rehearse']:raise HTTPException(409,'仅当前版本的模拟环境可进行独立演练；现场/离线不能沿用模拟任务')
        candidates={d['node_id'] for d in checks['devices'] if d['parameters']}
        if request.scenario!='MATCH' and request.fault_device not in candidates:raise HTTPException(422,'请选择本范围中有候选参数的异常设备')
        if b['scope_type']=='READ_ONLY' and request.scenario in ('REJECTED','ACK_LOST'):raise HTTPException(422,'只读范围没有配置指令确认，不支持该写入故障场景')
        if request.action=='DEPLOY':
            results=[];events=[{'time':now(),'device':None,'stage':'BLOCKED','message':'批准依据、可信权限和设备适配器未就绪，未发出任何配置动作','source':'WORKBENCH'}];status='BLOCKED'
        else:results,events,status=simulate(b,checks['devices'],request.scenario,request.fault_device)
        record={'id':task_id,'kind':kind,'project':project,'created':now(),'request_id':request.request_id,'request_hash':fingerprint,'baseline_id':b['id'],'baseline_hash':b['content_hash'],'source_revision':b['source_revision'],'environment':request.environment,'action':request.action,'scenario':request.scenario,'fault_device':request.fault_device,'engine':'MOCK_IEMS_11_V1' if request.action=='REHEARSE' else 'NO_EXECUTION','status':status,'preflight':checks,'devices':results,'events':events,'actual_state':'UNKNOWN','approved':False,'applied':False,'strategy_activation':'NOT_ACTIVATED','rollback':'NOT_ATTEMPTED','controller_config':'SIMULATED_CANDIDATE_ONLY' if request.action=='REHEARSE' else 'NOT_SENT'}
        with db.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT body FROM records WHERE id=?',(task_id,)).fetchone()
            if old:
                existing=json.loads(old['body'])
                if existing.get('request_hash')!=fingerprint:raise HTTPException(409,'请求ID冲突')
                return existing
            current=c.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()
            if not current or current['revision']!=checks['current_revision']:raise HTTPException(409,'执行准备期间工程版本变化；请重新核验')
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(task_id,kind,project,json.dumps(record),record['created']))
        return record
