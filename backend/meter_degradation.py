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
    pv = [min(1250, 125*np, 800+30*nb-25)/np]*np
    bess = [min(30, max(-70, (min(1250,125*np)-800+25)/nb))]*nb
    stuck_power = pv[0]
    trace = []
    last_pv, last_bess = sum(pv), sum(bess)
    last_valid = 0.0
    for k in range(121):
        t = k*DT
        middle = 10 <= t < 24
        load = (400 if middle else 1200 if t >= 24 else 800) if body.scenario == 'load_step' else 800
        available = min(650 if middle and body.scenario == 'pv_fluctuation' else 1250, 125*np)
        cap = (5 if middle and body.scenario == 'charge_limited' else 30)*nb
        if compound and t >= 10:
            load = 20  # Explicit low-load stress fixture, never a controller input.
            cap = (5 if body.support_capacity == 'limited' else 30)*nb
        reject_active = compound and t >= 10 and (not body.recover or t < 28)
        previous = trace[max(0,k-int(body.delay_s/DT))] if trace else dict(grid=800+sum(bess)-sum(pv),pv=sum(pv),bess=sum(bess),charge_cap=30*nb,available=min(1250,125*np))
        valid = t < 10 or (body.recover and t >= fresh)
        meter = previous['grid'] if valid else None
        quality = 'GOOD' if valid else 'TIMEOUT' if body.fault in ('meter_comm_loss','meter_pv_reject') else 'OUT_OF_RANGE'
        if valid:
            last_valid = max(0,t-body.delay_s)
        degraded = body.mitigation and t >= detected and (not body.recover or t < resume)
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
            pv[i] = min(available/np,stuck_power if refused else approach(pv[i],cp/np,8))
            devices.append(dict(node_id=d['node_id'],kind='PV',command=round(cp/np,4),actual=round(pv[i],4),status='FAULT' if refused else 'TRACKING' if abs(cp/np-pv[i])>.5 else 'MATCHED'))
        for i,d in enumerate(p['bess']):
            bess[i] = max(-70,min(cap/nb,approach(bess[i],cb/nb,10)))
            devices.append(dict(node_id=d['node_id'],kind='BESS',command=round(cb/nb,4),actual=round(bess[i],4),status='TRACKING' if abs(cb/nb-bess[i])>.5 else 'MATCHED'))
        grid = load+sum(bess)-sum(pv)
        trace.append(dict(time=t,load=load,available=available,charge_cap=cap,pv=round(sum(pv),4),bess=round(sum(bess),4),grid=round(grid,4),meter=meter,meter_raw=meter if valid else None if body.fault in ('meter_comm_loss','meter_pv_reject') else 1e9,meter_quality=quality,meter_age_s=round(t-last_valid,2),feedback_state=state,closed_loop=valid and not degraded,pv_command=round(cp,4),bess_command=round(cb,4),eligible_bess=nb,devices=devices,compound=compound,rejected_pv_kw=round(observed_reject,4),support_gap_kw=round(max(0,observed_reject-previous['charge_cap']),4) if degraded else 0,control_alarm=('FEEDBACK_AND_CONTROL_LOST' if not valid and reject_active else 'FEEDBACK_UNAVAILABLE' if not valid else 'RECOVERY_OBSERVATION' if degraded else 'NONE') if compound else None))
    settled_at = next((trace[i+6]['time'] for i in range(len(trace)-6) if trace[i]['time'] >= resume and all(s['closed_loop'] and abs(s['grid']-25)<=5 for s in trace[i:])),None) if body.recover else None
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
        settings=dict(delay_s=body.delay_s,duration_s=60,mitigation=body.mitigation,recover=body.recover,fault=body.fault,fault_node=meter_id,policy_basis='PENDING',note='独立合成模型；计量失效期间不用真实模型功率或最后有效值继续闭环。失联无接收值；异常值注入 1×10⁹ kW 并拒用。降级仅是假设光伏可限至零、储能接受零功率指令；没有 SOC / BMS 或保护联锁模型。检测时限、3 秒观察、调节斜率均待厂家确认。'),
        recovery=dict(state='RECOVERED' if settled_at is not None else 'FEEDBACK_UNAVAILABLE' if not body.recover else 'UNSETTLED',node_id=meter_id,final_eligible_bess=nb,final_grid_kw=trace[-1]['grid'],basis='PENDING',note='恢复仅为模拟判定；失去反馈时现场馈网未知。'),
        metrics=dict(peak_export_kw=max(0,-min(s['grid'] for s in trace)),export_duration_s=sum(DT for s in trace[:-1] if s['grid']<0),export_energy_kwh=round(sum(max(0,-s['grid'])*DT/3600 for s in trace[:-1]),4),final_grid_kw=trace[-1]['grid'],events=[dict(time=10,response_delay_s=detected-10 if body.mitigation else None,settling_s=settled_at-10 if settled_at is not None else None)]))

    if compound:
        result['title'] = '复合异常：零馈表失联 + ' + reject_id + ' 拒绝限功率'
        result['version'] = 'M2-COMPOUND-1'
        result['settings'].update(reject_node=reject_id,support_capacity=body.support_capacity)
        result['settings']['note'] = '独立合成模型；零馈表失联期间无有效计量。指定光伏拒绝降功率，其余光伏接受降零指令；储能按合成可用容量协助充电。检测与恢复时序待厂家确认。 复合演练在 10 秒后将负载设为 20 kW；储能每台充电上限为 5 kW（受限）或 30 kW（充足）。负载为模型真值，不进入失联控制算法。储能仅按延迟的拒令光伏设备输出及可用充电上限尝试吸收，不放电，不推定 SOC 无限可用。'
        result['events'][0]['label'] = '零馈表失联 + 光伏拒令 + 低负载 20 kW'
        result['issues'][0]['reason'] = '零馈表失联，实际馈网无法确认；正常光伏降零，储能依据仍有效的设备反馈尝试吸收拒令光伏输出。该开环配合不能保证零馈，策略及 BMS / SOC 联锁待厂家确认。'
        result['issues'].append(dict(node_id=reject_id,time=detected,code='PV_LIMIT_REJECTED_WITH_METER_LOSS',layer='L5',reason='模拟光伏拒绝限功率，保持故障前输出。核对远程控制权限、指令确认及设备故障；必要的停机 / 隔离处置须由现场按批准程序执行，本工具不自动跳闸。',route=next(d['route'] for d in p['pv'] if d['node_id']==reject_id)))
        result['control_events'][0]['label'] = '计量失联 + 光伏拒令'
        for event in result['control_events']:
            if event['phase']=='DERATED':
                event.update(label='限光伏 + 储能协助',detail='正常光伏降零；按拒令设备反馈尝试充电，受可用容量约束；告警保持，不宣告零馈。')
        result['alarm'] = dict(severity='CRITICAL',active=settled_at is None,code='ZERO_EXPORT_NOT_ASSURED',meter_id=meter_id,pv_id=reject_id,final_model_export_kw=max(0,-trace[-1]['grid']),peak_support_gap_kw=max(s['support_gap_kw'] for s in trace),note='计量与控制能力同时受损，零馈无法保证；失联期间实际馈网未知。模型曲线仅展示演练后果，厂家协同尚未发送。')
        result['recovery']['node_id']=meter_id+' + '+reject_id
        if not body.recover:result['recovery']['state']='CONTROL_UNAVAILABLE'
    return result
