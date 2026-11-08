"""Synthetic loss-of-PCC-feedback exercise. No hardware control or certified policy."""
from .system_tests import participants


def simulate_meter(model, body, preflight):
    from .dynamic_tests import approach, DT, SCENARIOS
    from fastapi import HTTPException
    if body.fault_node and body.fault_node != preflight['meter']:
        raise HTTPException(422, '故障目标必须是当前控制域的零馈表')
    p = participants(model)
    np, nb = len(p['pv']), len(p['bess'])
    detected, fresh, resume = 10 + body.delay_s + 1, 28 + body.delay_s, 31 + body.delay_s
    pv = [min(1250, 125*np, 800+30*nb-25)/np]*np
    bess = [min(30, max(-70, (min(1250,125*np)-800+25)/nb))]*nb
    trace = []
    last_pv, last_bess = sum(pv), sum(bess)
    last_valid = 0.0
    for k in range(121):
        t = k*DT
        middle = 10 <= t < 24
        load = (400 if middle else 1200 if t >= 24 else 800) if body.scenario == 'load_step' else 800
        available = min(650 if middle and body.scenario == 'pv_fluctuation' else 1250, 125*np)
        cap = (5 if middle and body.scenario == 'charge_limited' else 30)*nb
        previous = trace[max(0,k-int(body.delay_s/DT))] if trace else dict(grid=800+sum(bess)-sum(pv),pv=sum(pv),bess=sum(bess),charge_cap=30*nb,available=min(1250,125*np))
        valid = t < 10 or (body.recover and t >= fresh)
        meter = previous['grid'] if valid else None
        quality = 'GOOD' if valid else 'TIMEOUT' if body.fault == 'meter_comm_loss' else 'OUT_OF_RANGE'
        if valid:
            last_valid = max(0,t-body.delay_s)
        degraded = body.mitigation and t >= detected and (not body.recover or t < resume)
        if degraded:
            # Conservative demonstration only: no guessed load, last good value,
            # or hidden simulated PCC power enters the failover controller.
            cp, cb = 0.0, 0.0
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
            pv[i] = min(available/np,approach(pv[i],cp/np,8))
            devices.append(dict(node_id=d['node_id'],kind='PV',command=round(cp/np,4),actual=round(pv[i],4),status='TRACKING' if abs(cp/np-pv[i])>.5 else 'MATCHED'))
        for i,d in enumerate(p['bess']):
            bess[i] = max(-70,min(cap/nb,approach(bess[i],cb/nb,10)))
            devices.append(dict(node_id=d['node_id'],kind='BESS',command=round(cb/nb,4),actual=round(bess[i],4),status='TRACKING' if abs(cb/nb-bess[i])>.5 else 'MATCHED'))
        grid = load+sum(bess)-sum(pv)
        trace.append(dict(time=t,load=load,available=available,charge_cap=cap,pv=round(sum(pv),4),bess=round(sum(bess),4),grid=round(grid,4),meter=meter,meter_raw=meter if valid else None if body.fault=='meter_comm_loss' else 1e9,meter_quality=quality,meter_age_s=round(t-last_valid,2),feedback_state=state,closed_loop=valid and not degraded,pv_command=round(cp,4),bess_command=round(cb,4),eligible_bess=nb,devices=devices))
    settled_at = next((trace[i+6]['time'] for i in range(len(trace)-6) if trace[i]['time'] >= resume and all(s['closed_loop'] and abs(s['grid']-25)<=5 for s in trace[i:])),None) if body.recover else None
    if settled_at is not None:
        for s in trace:
            if s['time'] >= settled_at:s['feedback_state']='NORMAL'
    events=[dict(time=10,label='零馈表通信中断' if body.fault=='meter_comm_loss' else '零馈表异常值 1×10⁹ kW（合成越界样本）')]
    stages=[dict(time=10,phase='FAULT',label='反馈失效',detail='无效样本不参与计算；等待演练检测时限。')]
    if body.mitigation:
        stages.append(dict(time=detected,phase='DERATED',label='退出零馈闭环',detail='光伏目标降至 0；储能目标回到 0，禁止放电。设备按演练速率响应。'))
    if body.recover:
        stages.extend([dict(time=fresh,phase='QUALIFYING',label='反馈恢复观察',detail='重新收到新鲜有效样本；连续观察 3 秒，期间保持降级。'),dict(time=resume,phase='RAMPING',label='恢复闭环调节',detail='有效反馈重新参与分配；光伏、储能按演练斜率恢复。')])
        if settled_at is not None:stages.append(dict(time=settled_at,phase='NORMAL',label='模拟恢复完成',detail='并网点模型功率连续 3 秒位于目标带，且余下观察窗保持。'))
    meter_id=preflight['meter']
    ports={v['port_id']:v for v in model['ports']}
    route=[dict(edge_id=e['edge_id'],**{'from':e['from_port_id'],'to':e['to_port_id']}) for e in model['edges'] if e['edge_type']=='COMMUNICATION' and meter_id in (ports[e['from_port_id']]['node_id'],ports[e['to_port_id']]['node_id'])]
    return dict(scenario=body.scenario,title=SCENARIOS[body.scenario]+' · '+events[0]['label'],mode='SIMULATION',source='SIMULATOR',version='M2-METER-DEGRADATION-1',field_result=None,manufacturer_basis='PENDING',status='ANOMALY',ems=preflight['ems'],meter=meter_id,trace=trace,events=events,control_events=stages,
        issues=[dict(node_id=meter_id,time=10,code='METER_COMMUNICATION_LOSS' if body.fault=='meter_comm_loss' else 'METER_INVALID_DATA',layer='L4',reason='无有效并网点反馈，不能确认实际馈网。演练策略为光伏降至零、储能回零且不放电；保持通信的设备假设接受指令。异常阈值、持续时间、联锁、设备拒令处置与恢复授权待厂家确认。历史异常在恢复后保留。',route=route)],
        settings=dict(delay_s=body.delay_s,duration_s=60,mitigation=body.mitigation,recover=body.recover,fault=body.fault,fault_node=meter_id,policy_basis='PENDING',note='独立合成模型；计量失效期间不用真实模型功率或最后有效值继续闭环。失联无接收值；异常值注入 1×10⁹ kW 并拒用。降级仅是假设光伏可限至零、储能接受零功率指令；没有 SOC / BMS 或保护联锁模型。检测时限、3 秒观察、调节斜率均待厂家确认。'),
        recovery=dict(state='RECOVERED' if settled_at is not None else 'FEEDBACK_UNAVAILABLE' if not body.recover else 'UNSETTLED',node_id=meter_id,final_eligible_bess=nb,final_grid_kw=trace[-1]['grid'],basis='PENDING',note='恢复仅为模拟判定；失去反馈时现场馈网未知。'),
        metrics=dict(peak_export_kw=max(0,-min(s['grid'] for s in trace)),export_duration_s=sum(DT for s in trace[:-1] if s['grid']<0),export_energy_kwh=round(sum(max(0,-s['grid'])*DT/3600 for s in trace[:-1]),4),final_grid_kw=trace[-1]['grid'],events=[dict(time=10,response_delay_s=detected-10 if body.mitigation else None,settling_s=settled_at-10 if settled_at is not None else None)]))
