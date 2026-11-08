"""Discrete-time demo controller and plant. All timings/limits are synthetic fixtures."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel
from .domain import digest
from .system_tests import participants,simulate,Command

SCENARIOS={'load_step':'负载突变','pv_fluctuation':'光伏波动','charge_limited':'储能充电受限'}
DT=0.5
class DynamicCommand(BaseModel):
    mode:Literal['SIMULATION','REAL']
    scenario:Literal['load_step','pv_fluctuation','charge_limited']
    delay_s:Literal[0.5,1,2,3]=1
    fault:Literal['none','pv_stuck','bess_block','bess_comm_loss','meter_comm_loss','meter_invalid','meter_pv_reject']='none'
    fault_node:str|None=None
    mitigation:bool=False
    recover:bool=False
    recovery_order:Literal['simultaneous','meter_first','pv_first','meter_only','pv_only']='simultaneous'
    support_capacity:Literal['limited','available']='limited'

def approach(actual,target,rate):
    return actual+max(-rate*DT,min(rate*DT,target-actual))

def dynamic_simulate(model,body):
    preflight=simulate(model,Command(mode='SIMULATION',scenario='surplus'))
    base={'scenario':body.scenario,'title':SCENARIOS[body.scenario],'mode':'SIMULATION','source':'SIMULATOR','version':'M2-DYNAMIC-1','field_result':None,'manufacturer_basis':'PENDING','trace':[],'events':[],'issues':[], 'metrics':None}
    if preflight['status']=='BLOCKED':return {**base,'status':'BLOCKED','issues':[{**i,'time':0,'route':[]} for i in preflight['issues']]}
    if body.fault in ('meter_comm_loss','meter_invalid','meter_pv_reject'):
        from .meter_degradation import simulate_meter
        return simulate_meter(model,body,preflight)
    p=participants(model);pv_nodes=p['pv'];bess_nodes=p['bess'];np=len(pv_nodes);nb=len(bess_nodes)
    targets=pv_nodes if body.fault=='pv_stuck' else bess_nodes if body.fault in ('bess_block','bess_comm_loss') else []
    if body.fault=='none' and body.fault_node:raise HTTPException(422,'未注入故障时不能指定故障设备')
    fault_node=body.fault_node or (targets[0]['node_id'] if targets else None)
    if targets and fault_node not in [d['node_id'] for d in targets]:raise HTTPException(422,'故障设备类型与注入场景不符')
    if body.mitigation and body.fault not in ('bess_block','bess_comm_loss'):raise HTTPException(422,'此降级策略仅用于储能拒充或储能通信中断演练')
    detected=10+body.delay_s+1
    reconnect=28+body.delay_s+3
    degradation=body.mitigation
    descriptions={'load_step':['负载 800 → 400 kW','负载 400 → 1200 kW'],'pv_fluctuation':['可用光伏 1250 → 650 kW（受台数上限约束）','可用光伏恢复至 1250 kW（受台数上限约束）'],'charge_limited':['每台储能可用充电功率 30 → 5 kW','每台储能可用充电功率恢复至 30 kW']}
    base['events']=[{'time':t,'label':descriptions[body.scenario][i]} for i,t in enumerate([10,24])]
    base['settings']={'dt_s':DT,'duration_s':40,'delay_s':body.delay_s,'pv_slew_kw_s_per_device':8,'bess_slew_kw_s_per_device':10,'target_kw':25,'band_kw':5,'hold_s':3,'fault':body.fault,'fault_node':fault_node,'note':'独立离散时间演练模型；全部延迟、速率、容量和判据是假设，不是厂家保证值。没有实际 SOC 积分、BMS、保护或网络模型。'}
    base['ems']=preflight['ems'];base['meter']=preflight['meter']
    base['version']='M2-DYNAMIC-2'
    base['settings'].update(mitigation=degradation,recover=body.recover,detection_s=detected,restore_s=28,qualification_s=3,ramp_s=5,policy_basis='PENDING',communication_loss_assumption='演练假设：失联储能本地进入 0 kW 待机；真实失联行为待厂家确认，不能由零遥测推断。')
    base['control_events']=[]
    if degradation:
        base['control_events']=[{'time':10,'phase':'FAULT','label':'故障注入','detail':'保留瞬态馈网，等待演练检测判据。'}, {'time':detected,'phase':'DERATED','label':'降级重分配','detail':'故障设备退出分配；按其余储能可用容量重分配，剩余富余通过限光伏消除。'}]
        if body.recover:
            base['control_events'] += [{'time':28,'phase':'QUALIFYING','label':'恢复待确认','detail':'合成通信/充电许可恢复；保持退出，等待新鲜状态与稳定观察。'}, {'time':reconnect,'phase':'RAMPING','label':'逐步重新接入','detail':'演练延迟及 3 秒观察结束，5 秒渐进恢复分配权重。'}, {'time':reconnect+5,'phase':'NORMAL','label':'接入完成','detail':'恢复分配完成；仍需核对并网点是否回到演练目标带。'}]
    if targets:
        base['issues']=[{'node_id':fault_node,'time':10,'code':'PV_COMMAND_STUCK' if body.fault=='pv_stuck' else 'BESS_CHARGE_BLOCKED','layer':'L5','reason':'t=10s 起注入光伏拒绝调节：保持初始输出上限，受可用光伏约束。核对控制权限及指令确认点。' if body.fault=='pv_stuck' else 't=10s 起注入储能拒绝充电；不禁止演练放电。核对 BMS 充电许可、SOC 与控制权限。','route':next(d['route'] for d in targets if d['node_id']==fault_node)}]
        if body.fault=='bess_comm_loss':base['issues'][0].update(code='BESS_COMMUNICATION_LOSS',reason='t=10s 注入通信中断：设备无新鲜反馈，不能把 0 当作实测值。仅在本演练假设本地待机 0 kW；失联安全策略待厂家确认。')
        if degradation:base['issues'][0]['reason']+=' 已启用模拟降级；记录保留为本次事件，不等于末时刻仍故障。'
    initial_avail=min(1250.,125.*np);initial_bess=max(-70.*nb,min(30.*nb,initial_avail-800+25))
    initial_pv=min(initial_avail,max(0,800+initial_bess-25))
    pv_actual=[initial_pv/np]*np;bess_actual=[initial_bess/nb]*nb
    trace=[];lag=int(body.delay_s/DT)
    for k in range(81):
        t=k*DT;middle=10<=t<24;load=(400. if middle else 1200. if t>=24 else 800.) if body.scenario=='load_step' else 800.
        available=min(650. if middle and body.scenario=='pv_fluctuation' else 1250.,125.*np)
        cap=(5. if middle and body.scenario=='charge_limited' else 30.)*nb
        previous=trace[max(0,k-lag)] if trace else {'grid':25,'pv':initial_pv,'bess':initial_bess,'available':initial_avail,'charge_cap':30.*nb}
        # Estimate net load only from the delayed meter/device observation, not future disturbances.
        estimated_load=previous['grid']+previous['pv']-previous['bess']
        desired_bess=max(-70.*nb,min(previous['charge_cap'],previous['available']-estimated_load+25))
        fault_active=t>=10 and (not body.recover or t<28)
        excluded=degradation and t>=detected and (not body.recover or t<reconnect)
        weight=0.0 if excluded else min(1.0,max(0.0,(t-reconnect)/5)) if degradation and body.recover and t>=reconnect else 1.0
        effective=nb-1+weight if degradation and t>=detected else nb
        if degradation and t>=detected:
            desired_bess=max(-70.*effective,min(previous['charge_cap']/nb*effective,previous['available']-estimated_load+25))
        desired_pv=min(previous['available'],max(0,estimated_load+desired_bess-25))
        devices=[]
        for i,d in enumerate(pv_nodes):
            command=desired_pv/np;faulted=fault_active and body.fault=='pv_stuck' and d['node_id']==fault_node
            pv_actual[i]=min(available/np,initial_pv/np if faulted else approach(pv_actual[i],command,8))
            devices.append({'node_id':d['node_id'],'kind':'PV','command':round(command,4),'actual':round(pv_actual[i],4),'status':'FAULT' if faulted else 'TRACKING' if abs(command-pv_actual[i])>0.5 else 'MATCHED'})
        for i,d in enumerate(bess_nodes):
            is_target=d['node_id']==fault_node
            command=desired_bess/(effective or 1)*(weight if is_target and degradation and t>=detected else 1)
            faulted=fault_active and body.fault in ('bess_block','bess_comm_loss') and is_target
            offline=faulted and body.fault=='bess_comm_loss'
            bess_actual[i]=0.0 if offline else max(-70,min(0 if faulted else cap/nb,approach(bess_actual[i],command,10)))
            state='DETECTING' if faulted and degradation and t<detected else 'DERATED' if is_target and excluded and fault_active else 'QUALIFYING' if is_target and excluded else 'RAMPING' if is_target and degradation and weight<1 else 'NORMAL'
            devices.append({'node_id':d['node_id'],'kind':'BESS','command':round(command,4),'sent_command':None if offline else round(command,4),'actual':round(bess_actual[i],4),'feedback':None if offline else round(bess_actual[i],4),'control_state':state,'status':'FAULT' if faulted else 'TRACKING' if abs(command-bess_actual[i])>0.5 else 'MATCHED'})
        pv=sum(pv_actual);bess=sum(bess_actual);grid=load+bess-pv
        trace.append({'time':t,'load':load,'available':available,'charge_cap':cap,'pv':round(pv,4),'bess':round(bess,4),'grid':round(grid,4),'meter':previous['grid'],'pv_command':round(desired_pv,4),'bess_command':round(desired_bess,4),'eligible_bess':round(effective,3),'devices':devices})
    events=[]
    for event,end in zip(base['events'],[24,40.5]):
        start=event['time'];window=[s for s in trace if start<=s['time']<end];before=trace[int(start/DT)-1]
        response=next((s['time']-start for s in window if abs(s['pv_command']-before['pv_command'])>0.01 or abs(s['bess_command']-before['bess_command'])>0.01),None)
        hold=int(3/DT)
        settled=next((window[i]['time']-start for i in range(max(0,len(window)-hold)) if all(abs(s['grid']-25)<=5 for s in window[i:i+hold+1]) and all(abs(s['grid']-25)<=5 for s in window[i:])),None)
        events.append({'time':start,'response_delay_s':response,'settling_s':settled})
    base['trace']=trace
    base['metrics']={'peak_export_kw':max(0,-min(s['grid'] for s in trace)),'export_duration_s':sum(DT for s in trace[:-1] if s['grid']<0),'export_energy_kwh':round(sum(max(0,-s['grid'])*DT/3600 for s in trace[:-1]),4),'final_grid_kw':trace[-1]['grid'],'events':events}
    # No PASS label: recovery in a toy model is not a zero-export/SAT certificate.
    base['status']='ANOMALY' if base['issues'] or any(e['settling_s'] is None for e in events) else 'COMPLETED'
    if degradation:
        settled=all(abs(s['grid']-25)<=5 for s in trace[-7:])
        recovered=body.recover and reconnect+5<=40 and settled
        base['recovery']={'state':'RECOVERED' if recovered else 'DERATED' if not body.recover and settled else 'UNSETTLED','node_id':fault_node,'final_eligible_bess':trace[-1]['eligible_bess'],'final_grid_kw':trace[-1]['grid'],'basis':'PENDING','note':'仅为演练恢复判定；历史故障仍保留。真实重连授权、联锁及失联本地行为待厂家确认。'}
    if any(e['settling_s'] is None for e in events):base['issues'].append({'node_id':preflight['ems'],'time':next(e['time'] for e in events if e['settling_s'] is None),'code':'TARGET_NOT_SETTLED','layer':'L5','reason':'至少一个观察区间未持续回到演练目标带；可能与已注入故障、演练功率容量或分配有关。不能据此认定现场 iEMS 故障。','route':[]})
    return base

def register_dynamic_tests(app,db):
    def context(id):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        if p['kind']!='plan':raise HTTPException(404,'调试依据不存在')
        return p
    @app.get('/api/plans/{id}/dynamic-tests')
    def listing(id:str):
        p=context(id)
        return {'participants':participants(p['system_context_baseline']),'scenarios':SCENARIOS,'records':db.records('dynamic_test',id),'stale':digest(db.get(p['project'])['model'])!=p['engineering_hash']}
    @app.post('/api/plans/{id}/dynamic-tests')
    def execute(id:str,body:DynamicCommand):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 动态测试接口未接入，未执行现场操作')
        p=context(id)
        if digest(db.get(p['project'])['model'])!=p['engineering_hash']:raise HTTPException(409,'模型已变化，请更新调试依据')
        configs=db.records('iems_configuration',p['project']);cfg=configs[0] if configs else None
        if not cfg or cfg['action']!='readback' or cfg['status']!='MATCHED' or cfg['model_hash']!=p['engineering_hash']:raise HTTPException(409,'请先在 M1 完成当前配置的模拟下发与读回一致性核对')
        result=dynamic_simulate(p['system_context_baseline'],body)
        if body.mitigation and result['trace']:
            baseline=dynamic_simulate(p['system_context_baseline'],body.model_copy(update={'mitigation':False}))
            result['comparison']={'label':'相同扰动及故障持续时间，不启用降级的反事实模拟','trace':[{'time':s['time'],'grid':s['grid']} for s in baseline['trace']],'metrics':baseline['metrics']}
        return db.add('dynamic_test',id,{**result,'model_hash':p['engineering_hash'],'configuration_id':cfg['id']})
