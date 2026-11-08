"""Step10 deterministic synthetic dynamic plant. Never connects to physical hardware."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .zero_export import zero_context,PENDING as ZERO_PENDING

PENDING=ZERO_PENDING+['扰动幅度、采样周期、时间质量、响应时限、馈网峰值/能量限值与稳定观察窗口']
CASE_NAMES={'load_step':'负载突变','pv_fluctuation':'光伏波动','charge_limited':'储能充电受限'}

class Command(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 acknowledged:bool=False
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 scenario:Literal['normal','load_step','pv_fluctuation','charge_limited','slow_response','meter_lost','pv_reject','restore_failed','no_permission','missing_basis']='normal'
 fault_node:str=''


def measure(samples,start,end):
 window=[s for s in samples if start<=s['t']<end]
 valid=lambda s:s['feedback_kw'] is not None and s['quality']=='GOOD' and 0<=s['feedback_kw'] and abs(s['feedback_kw']-10)<=2
 settling=None;confirmed=None
 for i in range(len(window)-2):
  if all(valid(x) for x in window[i:i+3]) and all(valid(x) for x in window[i:]):
   settling=window[i]['t']-start;confirmed=settling+2;break
 good=[s for s in window if s['feedback_kw'] is not None and s['quality']=='GOOD']
 complete=len(good)==len(window)
 return dict(start_s=start,end_s=end,settling_s=settling,confirmed_s=confirmed,status='PASS' if complete and settling is not None and settling<=8 else 'FAIL',peak_export_kw=round(max([max(0,-s['feedback_kw']) for s in good],default=0),3) if complete else None,export_duration_s=sum(s['feedback_kw']<0 for s in good) if complete else None,export_energy_kwh=round(sum(max(0,-s['feedback_kw']) for s in good)/3600,5) if complete else None,quality_complete=complete)


def simulate_case(kind,pvs,bess,meter,ems,fault,scenario,rid):
 samples=[];commands=[];issues=[];notes=[];n=len(pvs);base_available=100*n
 charge={d['node_id']:min(40,max(0,d['capability']['charge_kw'])) for d in bess}
 discharge={d['node_id']:min(40,max(0,d['capability']['discharge_kw'])) for d in bess}
 pv={d:100. for d in pvs};bp={d:0. for d in charge};pvt=dict(pv);bt=dict(bp)
 limited=fault if fault in charge else next(iter(charge));target=10
 def issue(node,reason,action,layer='L5'):issues.append(dict(node_id=node,reason=reason,action=action,layer=layer))
 for t in range(56):
  phase='prepare' if t<12 else 'disturbance' if t<28 else 'return' if t<44 else 'restore'
  load=base_available+100 if phase=='restore' else round(base_available*.6)
  avail={d:100. for d in pv};cb=dict(charge)
  if phase=='disturbance':
   if kind=='load_step':load=round(base_available*.35)
   if kind=='pv_fluctuation':avail={d:50. for d in pv}
   if kind=='charge_limited':cb[limited]=0
  quality=not (scenario=='meter_lost' and t>=12)
  # Apply prior command with first-order synthetic response; BMS local bounds always win.
  speed=.15 if scenario=='slow_response' and 12<t<44 else .65
  if t:
   for d in pv:
    pv[d]=min(avail[d],pv[d]+speed*(pvt[d]-pv[d]))
    if scenario=='pv_reject' and d==fault and 12<=t<44:pv[d]=avail[d]
    if scenario=='restore_failed' and d==fault and t>=44:pv[d]=50
   for d in bp:bp[d]=max(-cb[d],min(discharge[d],bp[d]+speed*(bt[d]-bp[d])))
  pcc=load-sum(pv.values())-sum(bp.values())
  # Compute command only from fresh synthetic PCC + aggregate measured production.
  if phase=='restore':pvt={d:100 for d in pv};bt={d:0 for d in bp}
  elif not quality:pvt={d:0 for d in pv};bt={d:0 for d in bp}
  else:
   demand=pcc+sum(pv.values())+sum(bp.values());desired=demand-sum(avail.values())-target
   bound=max(-sum(cb.values()),min(sum(discharge.values()),desired));weights=cb if desired<0 else discharge;total=sum(weights.values())
   bt={d:bound*weights[d]/total if total else 0 for d in bp}
   desired_pv=max(0,min(sum(avail.values()),demand-sum(bt.values())-target))
   pvt={d:desired_pv/n for d in pv}
  if t in (0,12,28,44):
   for node,value in {**pvt,**bt}.items():commands.append(dict(id=f'{rid}-{kind}-{t}-{node}',node_id=node,t=t,phase=phase,value_kw=125 if phase=='restore' and node in pv else round(value,3),ack='REJECTED' if scenario=='pv_reject' and node==fault and t in (12,28) else 'ACCEPTED'))
  devices=[dict(node_id=d,kind='PV',power_kw=round(v,3),target_kw=round(pvt[d],3),available_kw=avail[d]) for d,v in pv.items()]
  devices += [dict(node_id=d,kind='BESS',power_kw=round(v,3),target_kw=round(bt[d],3),charge_bound_kw=cb[d],discharge_bound_kw=discharge[d],soc_pct=55,bms_allowed=cb[d]>0,bms_discharge_allowed=discharge[d]>0) for d,v in bp.items()]
  samples.append(dict(t=t,phase=phase,pcc_kw=round(pcc,3),feedback_kw=round(pcc,3) if quality else None,quality='GOOD' if quality else 'INVALID',age_s=0 if quality else None,sequence=t if quality else None,load_kw=load,pv_kw=round(sum(pv.values()),3),bess_kw=round(sum(bp.values()),3),target_kw=10,devices=devices))
 events=[dict(label='扰动后的收敛',**measure(samples,12,28)),dict(label='撤销扰动后的收敛',**measure(samples,28,44))]
 prepared=all(s['quality']=='GOOD' and abs(s['feedback_kw']-10)<=2 and s['feedback_kw']>=0 for s in samples[9:12])
 restored=all(s['quality']=='GOOD' and abs(s['pcc_kw']-100)<.2 and all(abs(d['power_kw']-(100 if d['kind']=='PV' else 0))<.1 for d in s['devices']) for s in samples[-3:])
 if scenario=='meter_lost':issue(meter,'零馈表反馈失效，响应时间及馈网指标不可判定','暂停闭环测试；核对端口、通信质量、时间戳及供电；按厂家批准退出策略复核恢复','L4')
 elif scenario=='pv_reject':issue(fault,'光伏拒绝限功率，协调指令未执行','核对该台远程模式、限功率点表和回执；保留曲线，请厂家协同')
 elif scenario=='restore_failed':issue(fault,'撤销测试后原光伏限值/功率未恢复','保持告警，核对原限值与功率读回；不得开始新测试')
 elif any(e['status']=='FAIL' for e in events):issue(ems,'动态响应未满足演练时限或稳定窗口','核对控制周期、驱动延迟、设备响应及实时功率边界；以厂家批准时限复核，不能凭最终功率达标判通过')
 if not prepared:issue(ems,'扰动前未建立稳定工况','重新建立有效基线，不能据此放行动态测试')
 if not restored and not issues:issue(ems,'退出状态未确认','保持告警并逐台核验原模式、设定和PCC反馈')
 if kind=='charge_limited':notes.append(dict(node_id=limited,reason='BMS模拟充电允许变为禁止，可用充电功率降为0；这是一项边界条件，不判设备故障',action='iEMS移除该台充电容量，按其余有效边界重新分配；不足部分通过光伏限功率消纳，不覆盖BMS保护',layer='L5'))
 return dict(key=kind,title=CASE_NAMES[kind],status='FAIL' if issues else 'PASS',prepared=prepared,restored=restored,events=events,samples=samples,commands=commands,issues=issues,notes=notes,source='SIMULATOR',original_state=dict(pv_limit_kw=125,bess_setpoint_kw=0,bess_mode='STANDBY',pcc_kw=100))


def register_dynamic_response(app,db):
 def context(id,sid,mode):
  p,s,groups,bess,cap,ready=zero_context(db,id,sid,mode)
  prior=next((r for r in db.records('zero_export',sid) if r['mode']==mode),None) if s and s['mode']==mode else None
  ready=bool(ready and prior and prior['status']=='PASS' and prior['restored'] and not prior['alarm_latched'] and prior['bess_control_id']==bess['id'])
  return p,s,groups,prior,cap,ready
 def recovered(r):return db.records('dynamic_response_recovery',r['id'])
 @app.get('/api/plans/{id}/dynamic-response')
 def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,s,groups,prior,cap,ready=context(id,session_id,mode)
  records=[r for r in db.records('dynamic_response',session_id) if r['mode']==mode] if s and s['mode']==mode else []
  last=records[0] if records else None
  return dict(records=records,prerequisite_ready=ready,current=bool(last and ready and last['zero_export_id']==prior['id']),basis_pending=PENDING,alarm_latched=bool(last and last['alarm_latched'] and not recovered(last)),recovery=recovered(last) if last else [],pv_ids=[d['node_id'] for g in groups for d in g['devices']],bess_ids=[d['node_id'] for d in cap['devices']] if cap else [],meter=s['route']['meter']['node_id'] if s else None,ems=s['route']['ems']['node_id'] if s else None,physical_control_allowed=False)
 @app.post('/api/plans/{id}/dynamic-response')
 def execute(id:str,body:Command):
  if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；现场权限、扰动规程与厂家判据未齐备，未下发指令')
  p,s,groups,prior,cap,ready=context(id,body.session_id,body.mode)
  if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
  rid=digest(dict(kind='dynamic-response',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:old=db.record(rid)
  except KeyError:old=None
  if old:
   if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同请求')
   return old
  if not ready:raise HTTPException(409,'请先完成当前步骤09联动及恢复；模型或前置变化后须重测')
  last=next(iter(db.records('dynamic_response',s['id'])),None)
  if last and last['alarm_latched'] and not recovered(last):raise HTTPException(409,'原运行恢复未确认，禁止新测试')
  if not body.acknowledged:raise HTTPException(422,'请确认独立动态演练范围、扰动及退出策略')
  pvs=[d['node_id'] for g in groups for d in g['devices']];bs=cap['devices'];meter=s['route']['meter']['node_id'];ems=s['route']['ems']['node_id']
  allowed=pvs if body.scenario in ('pv_reject','restore_failed') else [d['node_id'] for d in bs] if body.scenario in ('normal','charge_limited') else [meter] if body.scenario=='meter_lost' else [ems]
  fault=body.fault_node or allowed[0]
  if fault not in allowed:raise HTTPException(422,'异常或受限设备不属于所选场景范围')
  cases=[];issues=[]
  if body.scenario in ('no_permission','missing_basis'):
   issues=[dict(node_id=ems,reason='独立控制权限不足' if body.scenario=='no_permission' else '批准演练包缺失',action='补齐本次控制域、权限与适用规程；未施加扰动',layer='L5')]
  else:
   kinds=list(CASE_NAMES) if body.scenario=='normal' else [body.scenario] if body.scenario in CASE_NAMES else ['load_step']
   for k in kinds:
    r=simulate_case(k,pvs,bs,meter,ems,fault,body.scenario,rid);cases.append(r);issues+=r['issues']
    if r['status']=='FAIL':break
  scope=dict(model_hash=p['engineering_hash'],controller=ems,meter=meter,pv=pvs,bess=[d['node_id'] for d in bs],test_pack='SIM-DYNAMIC-1',physical_lease=False,zero_export_id=prior['id'])
  result=dict(mode=body.mode,source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',physical_control_allowed=False,scope=scope,scope_hash=digest(scope),zero_export_id=prior['id'],request_id=body.request_id,request_signature=signature,scenario=body.scenario,cases=cases,issues=issues,status='FAIL' if issues else 'PASS',restored=bool(cases and all(c['restored'] for c in cases)),alarm_latched=any(not c['restored'] for c in cases),criteria=dict(target_import_kw=10,tolerance_kw=2,consecutive_samples=3,sample_period_s=1,settling_limit_s=8,source='SIMULATION_ONLY'))
  saved=db.add_once('dynamic_response',s['id'],result,rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
  return saved
 @app.post('/api/plans/{id}/dynamic-response/{run_id}/recover')
 def recover(id:str,run_id:str,body:Command):
  if body.mode!='SIMULATION':raise HTTPException(503,'未执行现场恢复')
  p,s,groups,prior,cap,ready=context(id,body.session_id,body.mode)
  try:r=db.record(run_id)
  except KeyError:raise HTTPException(404,'运行不存在')
  if not s or r['kind']!='dynamic_response' or r['project']!=s['id'] or r['mode']!='SIMULATION':raise HTTPException(404,'运行不属于本会话')
  if not body.acknowledged or not r['alarm_latched'] or not ready or r['zero_export_id']!=prior['id']:raise HTTPException(409,'恢复范围或依据不满足')
  snapshots=[dict(t=i,pcc_kw=100,quality='GOOD',pv_limit_kw=125,bess_setpoint_kw=0,bess_mode='STANDBY',source='SIMULATOR') for i in range(3)]
  return db.add_once('dynamic_response_recovery',run_id,dict(mode='SIMULATION',source='SIMULATOR',field_result=None,evidence='独立合成复核：连续3点PCC购电100kW、质量GOOD、PV原限值125kW与BESS 0kW待机一致；原失败结果保留，不自动重启测试。',samples=snapshots,physical_control_allowed=False),digest(dict(kind='dynamic-recovery',run=run_id)))
