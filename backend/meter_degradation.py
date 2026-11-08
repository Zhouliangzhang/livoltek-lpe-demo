"""Synthetic loss-of-PCC-feedback exercise. No hardware control or certified policy."""
from .system_tests import participants


def simulate_meter(model, body, preflight):
    from .dynamic_tests import approach, DT, SCENARIOS
    from fastapi import HTTPException
    compound = body.fault == 'meter_pv_reject'
    if not compound and body.fault_node and body.fault_node != preflight['meter']:
        raise HTTPException(422, '故障目标必须是当前控制域的零馈表')
    p = participants(model)
    np, nb = len(p['pv']), len(p['bess'])
    reject_id = (body.fault_node or p['pv'][0]['node_id']) if compound else None
    if compound and reject_id not in [d['node_id'] for d in p['pv']]:
        raise HTTPException(422, '复合异常的拒令设备必须是本控制域的光伏设备')
    detected, fresh, resume = 10 + body.delay_s + 1, 28 + body.delay_s, 31 + body.delay_s
    meter_restore, pv_restore = (28,28)
    if compound:
        meter_restore, pv_restore = {'simultaneous':(28,28),'meter_first':(20,36),'pv_first':(36,20),'meter_only':(20,float('inf')),'pv_only':(float('inf'),20)}[body.recovery_order]
    if not body.recover:meter_restore = pv_restore = float('inf')
    fresh = meter_restore + body.delay_s
    duration = 80 if compound else 60
    ready_since = None
    compound_resume = None
    relapse_start = relapse_end = None
    relapse_power = 0.0
    observation_events = []
    pv = [min(1250, 125*np, 800+30*nb-25)/np]*np
    bess = [min(30, max(-70, (min(1250,125*np)-800+25)/nb))]*nb
    stuck_power = pv[0]
    trace = []
    last_pv, last_bess = sum(pv), sum(bess)
    last_valid = 0.0
    for k in range(int(duration/DT)+1):
        t = k*DT
        middle = 10 <= t < 24
        load = (400 if middle else 1200 if t >= 24 else 800) if body.scenario == 'load_step' else 800
        available = min(650 if middle and body.scenario == 'pv_fluctuation' else 1250, 125*np)
        cap = (5 if middle and body.scenario == 'charge_limited' else 30)*nb
        if compound and t >= 10:
            load = 20  # Explicit low-load stress fixture, never a controller input.
            cap = (5 if body.support_capacity == 'limited' else 30)*nb
        reject_active = compound and t >= 10 and t < pv_restore
        relapse_meter = relapse_start is not None and body.relapse=='meter' and relapse_start <= t < relapse_end+body.delay_s
        relapse_pv = relapse_start is not None and body.relapse=='pv' and relapse_start <= t < relapse_end
        reject_active = reject_active or relapse_pv
        previous = trace[max(0,k-int(body.delay_s/DT))] if trace else dict(grid=800+sum(bess)-sum(pv),pv=sum(pv),bess=sum(bess),charge_cap=30*nb,available=min(1250,125*np))
        valid = (t < 10 or (body.recover and t >= fresh)) and not relapse_meter
        meter = previous['grid'] if valid else None
        quality = 'GOOD' if valid else 'TIMEOUT' if body.fault in ('meter_comm_loss','meter_pv_reject') else 'OUT_OF_RANGE'
        if valid:
            last_valid = max(0,t-body.delay_s)
        pv_observation = next((d for d in previous.get('devices',[]) if d['node_id']==reject_id),None)
        pv_verified = compound and not reject_active and t >= pv_restore+body.delay_s and pv_observation is not None and pv_observation['status']=='MATCHED'
        if compound and body.relapse!='none' and relapse_start is None:
            anchor = ready_since if body.relapse_window=='qualification' else compound_resume
            if anchor is not None and t-anchor >= 1:
                relapse_start, relapse_end = t, t+4
                relapse_power = pv[next(i for i,d in enumerate(p['pv']) if d['node_id']==reject_id)]
                relapse_meter = body.relapse=='meter'
                relapse_pv = body.relapse=='pv'
                if relapse_meter:
                    valid=False;meter=None;quality='TIMEOUT'
                    last_valid = max((s['time']-body.delay_s for s in trace if s['meter'] is not None),default=0)
                if relapse_pv:reject_active=True;pv_verified=False
                observation_events.append(dict(time=t,phase='RELAPSE',label='零馈表再次失联' if relapse_meter else '光伏再次拒令',detail='重新降级；双项观察和闭环稳定计时清零，告警保持。'))
        if compound and t >= 10:
            if not valid or reject_active:
                ready_since=None
                compound_resume=None
            if compound_resume is None and valid and pv_verified:
                if ready_since is None:
                    ready_since=t
                    observation_events.append(dict(time=t,phase='OBSERVING_'+str(t),label='重新开始双项观察' if relapse_start is not None else '双项恢复观察',detail='从 0 秒开始；需连续 3 秒有效，任何复发都会重置。'))
                if t-ready_since >= 3 and compound_resume is None:
                    compound_resume=t
                    observation_events.append(dict(time=t,phase='RAMPING_'+str(t),label='恢复闭环 · 告警保持',detail='重新满足双项观察；还须完成闭环稳定计时。'))
            elif compound_resume is None:ready_since=None
        degraded = body.mitigation and t >= detected and ((compound_resume is None) if compound else (not body.recover or t < resume))
        observed_reject = next((d['actual'] for d in previous.get('devices',[]) if d['node_id']==reject_id),0) if reject_active else 0
        if degraded:
            # Conservative demonstration only: no guessed load, last good value,
            # or hidden simulated PCC power enters the failover controller.
            cp, cb = 0.0, min(previous['charge_cap'],observed_reject) if compound else 0.0
        elif valid:
            estimated_load = meter + previous['pv'] - previous['bess']
            cb = max(-70*nb,min(previous['charge_cap'],previous['available']-estimated_load+25))
            cp = min(previous['available'],max(0,estimated_load+cb-25))
        else:
            cp, cb = last_pv, last_bess
        last_pv, last_bess = cp, cb
        state = 'DETECTING' if not valid and t < detected else 'FEEDBACK_LOST' if not valid else 'QUALIFYING' if degraded else 'RAMPING' if body.recover and t >= resume else 'NORMAL'
        devices = []
        for i,d in enumerate(p['pv']):
            refused = reject_active and d['node_id']==reject_id
            pv[i] = min(available/np,(relapse_power if relapse_pv else stuck_power) if refused else approach(pv[i],cp/np,8))
            devices.append(dict(node_id=d['node_id'],kind='PV',command=round(cp/np,4),actual=round(pv[i],4),status='FAULT' if refused else 'TRACKING' if abs(cp/np-pv[i])>.5 else 'MATCHED'))
        for i,d in enumerate(p['bess']):
            bess[i] = max(-70,min(cap/nb,approach(bess[i],cb/nb,10)))
            devices.append(dict(node_id=d['node_id'],kind='BESS',command=round(cb/nb,4),actual=round(bess[i],4),status='TRACKING' if abs(cb/nb-bess[i])>.5 else 'MATCHED'))
        grid = load+sum(bess)-sum(pv)
        recovery_gate = ('WAIT_METER' if not valid else 'WAIT_PV' if not pv_verified else 'OBSERVING' if compound_resume is None else 'RESTORING') if compound and t>=10 else 'NORMAL'
        trace.append(dict(meter_recovered=valid,pv_recovered=pv_verified,pv_recovery_state='REFUSING' if reject_active else 'VERIFIED' if pv_verified else 'VERIFYING',recovery_gate=recovery_gate,relapse_active=relapse_meter or relapse_pv,timer_reset=relapse_start==t,qualification_elapsed_s=round(min(3,t-ready_since),2) if ready_since is not None else 0,time=t,load=load,available=available,charge_cap=cap,pv=round(sum(pv),4),bess=round(sum(bess),4),grid=round(grid,4),meter=meter,meter_raw=meter if valid else None if body.fault in ('meter_comm_loss','meter_pv_reject') else 1e9,meter_quality=quality,meter_age_s=round(t-last_valid,2),feedback_state=state,closed_loop=valid and not degraded,pv_command=round(cp,4),bess_command=round(cb,4),eligible_bess=nb,devices=devices,compound=compound,rejected_pv_kw=round(observed_reject,4),support_gap_kw=round(max(0,observed_reject-previous['charge_cap']),4) if degraded else 0,control_alarm=('FEEDBACK_AND_CONTROL_LOST' if not valid and reject_active else 'FEEDBACK_UNAVAILABLE' if not valid else 'RECOVERY_OBSERVATION' if degraded else 'NONE') if compound else None))
    settled_at = next((trace[i+6]['time'] for i in range(len(trace)-6) if trace[i]['time'] >= resume and all(s['closed_loop'] and abs(s['grid']-25)<=5 for s in trace[i:])),None) if body.recover else None
    if compound:
        # Alarm qualification uses only samples available at each time, never future data.
        stable_since=None
        for i,sample in enumerate(trace):
            window=trace[max(0,i-6):i+1]
            stable=len(window)==7 and all(v['closed_loop'] and v['meter_recovered'] and v['pv_recovered'] and abs(v['grid']-25)<=5 and v['meter'] is not None and abs(v['meter']-25)<=5 and all(d['status']=='MATCHED' for d in v['devices']) for v in window)
            current_ok=sample['closed_loop'] and sample['meter_recovered'] and sample['pv_recovered'] and abs(sample['grid']-25)<=5 and sample['meter'] is not None and abs(sample['meter']-25)<=5 and all(d['status']=='MATCHED' for d in sample['devices'])
            stable_since=(sample['time'] if stable_since is None else stable_since) if current_ok else None
            sample['stability_elapsed_s']=min(3,round(sample['time']-stable_since,2)) if stable_since is not None else 0
            sample['alarm_active']=sample['time']>=10 and not stable
            if sample['time']>=10 and stable:sample['recovery_gate']='STABLE'
        settled_at=next((s['time'] for s in trace if s['time']>=10 and not s['alarm_active']),None) if not trace[-1]['alarm_active'] else None
    if settled_at is not None:
        for s in trace:
            if s['time'] >= settled_at:s['feedback_state']='NORMAL'
    events=[dict(time=10,label='零馈表通信中断' if body.fault in ('meter_comm_loss','meter_pv_reject') else '零馈表异常值 1×10⁹ kW（合成越界样本）')]
    stages=[dict(time=10,phase='FAULT',label='反馈失效',detail='无效样本不参与计算；等待演练检测时限。')]
    if body.mitigation:
        stages.append(dict(time=detected,phase='DERATED',label='退出零馈闭环',detail='光伏目标降至 0；储能目标回到 0，禁止放电。设备按演练速率响应。'))
    if body.recover:
        stages.extend([dict(time=fresh,phase='QUALIFYING',label='反馈恢复观察',detail='重新收到新鲜有效样本；连续观察 3 秒，期间保持降级。'),dict(time=resume,phase='RAMPING',label='恢复闭环调节',detail='有效反馈重新参与分配；光伏、储能按演练斜率恢复。')])
        if settled_at is not None:stages.append(dict(time=settled_at,phase='NORMAL',label='模拟恢复完成',detail='并网点模型功率连续 3 秒位于目标带，且余下观察窗保持。'))
    meter_id=preflight['meter']
    ports={v['port_id']:v for v in model['ports']}
    route=[dict(edge_id=e['edge_id'],**{'from':e['from_port_id'],'to':e['to_port_id']}) for e in model['edges'] if e['edge_type']=='COMMUNICATION' and meter_id in (ports[e['from_port_id']]['node_id'],ports[e['to_port_id']]['node_id'])]
    result = dict(scenario=body.scenario,title=SCENARIOS[body.scenario]+' · '+events[0]['label'],mode='SIMULATION',source='SIMULATOR',version='M2-METER-DEGRADATION-1',field_result=None,manufacturer_basis='PENDING',status='ANOMALY',ems=preflight['ems'],meter=meter_id,trace=trace,events=events,control_events=stages,
        issues=[dict(node_id=meter_id,time=10,code='METER_COMMUNICATION_LOSS' if body.fault in ('meter_comm_loss','meter_pv_reject') else 'METER_INVALID_DATA',layer='L4',reason='无有效并网点反馈，不能确认实际馈网。演练策略为光伏降至零、储能回零且不放电；保持通信的设备假设接受指令。异常阈值、持续时间、联锁、设备拒令处置与恢复授权待厂家确认。历史异常在恢复后保留。',route=route)],
        settings=dict(delay_s=body.delay_s,duration_s=duration,mitigation=body.mitigation,recover=body.recover,fault=body.fault,fault_node=meter_id,policy_basis='PENDING',note='独立合成模型；计量失效期间不用真实模型功率或最后有效值继续闭环。失联无接收值；异常值注入 1×10⁹ kW 并拒用。降级仅是假设光伏可限至零、储能接受零功率指令；没有 SOC / BMS 或保护联锁模型。检测时限、3 秒观察、调节斜率均待厂家确认。'),
        recovery=dict(state='RECOVERED' if settled_at is not None else 'FEEDBACK_UNAVAILABLE' if not body.recover else 'UNSETTLED',node_id=meter_id,final_eligible_bess=nb,final_grid_kw=trace[-1]['grid'],basis='PENDING',note='恢复仅为模拟判定；失去反馈时现场馈网未知。'),
        metrics=dict(peak_export_kw=max(0,-min(s['grid'] for s in trace)),export_duration_s=sum(DT for s in trace[:-1] if s['grid']<0),export_energy_kwh=round(sum(max(0,-s['grid'])*DT/3600 for s in trace[:-1]),4),final_grid_kw=trace[-1]['grid'],events=[dict(time=10,response_delay_s=detected-10 if body.mitigation else None,settling_s=settled_at-10 if settled_at is not None else None)]))

    if compound:
        result['title'] = '复合异常：零馈表失联 + ' + reject_id + ' 拒绝限功率'
        result['version'] = 'M2-COMPOUND-3'
        result['settings'].update(relapse=body.relapse,relapse_window=body.relapse_window,relapse_start_s=relapse_start,relapse_end_s=relapse_end,reject_node=reject_id,support_capacity=body.support_capacity,recovery_order=body.recovery_order,meter_restore_s=meter_restore if meter_restore!=float('inf') else None,pv_restore_s=pv_restore if pv_restore!=float('inf') else None)
        result['settings']['recovery_basis']='独立注入恢复不等于验证通过。需新鲜计量、光伏指令反馈一致并同时观察 3 秒，再恢复闭环；计量与功率进入目标带且全部设备反馈一致持续 3 秒才解除模拟告警。时间、容差、联锁与授权均待厂家确认。'
        result['settings']['note'] = '独立合成模型；零馈表失联期间无有效计量。指定光伏拒绝降功率，其余光伏接受降零指令；储能按合成可用容量协助充电。检测与恢复时序待厂家确认。 复合演练在 10 秒后将负载设为 20 kW；储能每台充电上限为 5 kW（受限）或 30 kW（充足）。负载为模型真值，不进入失联控制算法。储能仅按延迟的拒令光伏设备输出及可用充电上限尝试吸收，不放电，不推定 SOC 无限可用。'
        result['events'][0]['label'] = '零馈表失联 + 光伏拒令 + 低负载 20 kW'
        result['issues'][0]['reason'] = '零馈表失联，实际馈网无法确认；正常光伏降零，储能依据仍有效的设备反馈尝试吸收拒令光伏输出。该开环配合不能保证零馈，策略及 BMS / SOC 联锁待厂家确认。'
        result['issues'].append(dict(node_id=reject_id,time=detected,code='PV_LIMIT_REJECTED_WITH_METER_LOSS',layer='L5',reason='模拟光伏拒绝限功率，保持故障前输出。核对远程控制权限、指令确认及设备故障；必要的停机 / 隔离处置须由现场按批准程序执行，本工具不自动跳闸。',route=next(d['route'] for d in p['pv'] if d['node_id']==reject_id)))
        result['control_events'][0]['label'] = '计量失联 + 光伏拒令'
        for event in result['control_events']:
            if event['phase']=='DERATED':
                event.update(label='限光伏 + 储能协助',detail='正常光伏降零；按拒令设备反馈尝试充电，受可用容量约束；告警保持，不宣告零馈。')
        result['control_events']=[e for e in result['control_events'] if e['phase'] in ('FAULT','DERATED')]
        if meter_restore!=float('inf'):
            result['control_events'].append(dict(time=fresh,phase='METER_RESTORED',label='零馈表反馈恢复',detail='新鲜计量可用；仍需独立验证光伏执行，单项恢复不解除告警。'))
        if pv_restore!=float('inf'):
            result['control_events'].append(dict(time=pv_restore,phase='PV_RESTORED',label='光伏接受指令',detail='解除拒令注入，实际功率逐步跟随；等待反馈一致，单项恢复不解除告警。'))
        result['control_events'].extend(observation_events)
        if relapse_start is not None:
            result['control_events'].append(dict(time=relapse_end+(body.delay_s if body.relapse=='meter' else 0),phase='RELAPSE_ENDED',label='复发故障解除 · 待重新验证',detail='故障注入结束不等于恢复通过；从头完成观察与稳定验证。'))
            result['issues'].append(dict(node_id=meter_id if body.relapse=='meter' else reject_id,time=relapse_start,code='RECOVERY_RELAPSE',layer='L4' if body.relapse=='meter' else 'L5',reason='恢复观察期间模拟复发，已重新降级并清零两个稳定计时。需要重新验证；复发检测、观察时间与解除权限待厂家确认。',route=[]))
            result['settings']['recovery_basis'] += ' 本次复发在首次观察或闭环恢复 1 秒后触发、持续 4 秒；计量还计入演练延迟。两个计时均重置，重新降级；光伏再次拒令保持复发时输出。仅为演练假设。'
        if settled_at is not None:result['control_events'].append(dict(time=settled_at,phase='NORMAL',label='解除模拟告警',detail='两项恢复并完成稳定观察；历史异常保留，非现场 SAT。'))
        result['control_events'].sort(key=lambda e:e['time'])
        result['alarm'] = dict(severity='CRITICAL',active=trace[-1]['alarm_active'],cleared_at_s=settled_at,code='ZERO_EXPORT_NOT_ASSURED',meter_id=meter_id,pv_id=reject_id,final_model_export_kw=max(0,-trace[-1]['grid']),peak_support_gap_kw=max(s['support_gap_kw'] for s in trace),note='计量与控制能力同时受损，零馈无法保证；失联期间实际馈网未知。模型曲线仅展示演练后果，厂家协同尚未发送。')
        result['recovery']['node_id']=meter_id+' + '+reject_id
        if trace[-1]['alarm_active']:result['recovery']['state']='CONTROL_UNAVAILABLE'
    return result
