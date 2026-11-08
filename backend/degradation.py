"""Step11 synthetic degradation/recovery state machine. No physical I/O."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .dynamic_response import dynamic_context,PENDING as DYNAMIC_PENDING

NAMES={'meter_lost':'零馈表失联','pv_reject':'光伏拒绝限功率','bess_reject':'储能拒绝充电'}
PENDING=DYNAMIC_PENDING+['失去PCC反馈时的批准降级策略、失效设备隔离及恢复观察/告警解除规程']
class Command(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 acknowledged:bool=False
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 scenario:Literal['normal','meter_lost','pv_reject','bess_reject','no_permission','missing_basis']='normal'
 recovery_mode:Literal['normal','hold','relapse','restore_failed']='normal'
 fault_node:str=''


def simulate_case(kind,pvs,bess,meter,ems,fault,recovery_mode,rid):
 charge={d['node_id']:min(40,max(0,d['capability']['charge_kw'])) for d in bess}
 discharge={d['node_id']:min(40,max(0,d['capability']['discharge_kw'])) for d in bess}
 n=len(pvs);base=100*n;target=10;samples=[];commands=[];events=[]
 selected=meter if kind=='meter_lost' else fault if fault in (pvs if kind=='pv_reject' else charge) else (pvs[0] if kind=='pv_reject' else next(iter(charge)))
 def allocate(load,cb,fixed=None):
  fixed=fixed or {};desired=load-base-target;bound=max(-sum(cb.values()),min(sum(discharge.values()),desired));weights=cb if desired<0 else discharge;total=sum(weights.values())
  bt={d:bound*weights[d]/total if total else 0 for d in charge}
  free=[d for d in pvs if d not in fixed];pv_total=max(0,min(100*len(free),load-sum(bt.values())-target-sum(fixed.values())))
  pt={d:fixed[d] if d in fixed else pv_total/len(free) for d in pvs}
  return pt,bt
 pv,bp=allocate(round(base*.6),charge);pt=dict(pv);bt=dict(bp)
 stable=0;stable_verified=False;alarm=False;cleared_at=None;exit_started=False;exit_count=0;prior_state=None;prior_active=False
 for t in range(61):
  active=t>=5 and (recovery_mode=='hold' or t<19 or recovery_mode=='relapse' and 25<=t<29)
  quality=not(kind=='meter_lost' and active)
  cb=dict(charge)
  if kind=='bess_reject' and active:cb[selected]=0
  if t>=45 and stable_verified and not active:exit_started=True
  load=base+100 if exit_started else round(base*(.6 if t<5 else .35))
  if t:
   for d in pv:
    pv[d]+=.7*(pt[d]-pv[d])
    if kind=='pv_reject' and active and d==selected:pv[d]=100
    if recovery_mode=='restore_failed' and exit_started and d==pvs[0]:pv[d]=50
   for d in bp:
    bp[d]=max(-cb[d],min(discharge[d],bp[d]+.7*(bt[d]-bp[d])))
  pcc=load-sum(pv.values())-sum(bp.values())
  if t==5:alarm=True;events.append(dict(t=t,state='ALARM',message=f'{selected}异常触发，告警保持'))
  if active and not prior_active and t>5:
   stable=0;stable_verified=False;events.append(dict(t=t,state='RESET',message='观察期间异常复发，稳定计数清零，重新降级'))
  if exit_started:pt={d:100 for d in pv};bt={d:0 for d in bp}
  elif not quality:pt={d:0 for d in pv};bt={d:0 for d in bp}
  else:pt,bt=allocate(load,cb,{selected:pv[selected]} if kind=='pv_reject' and active else None)
  # Rejecting PV is measured as uncontrollable; only healthy nodes receive redistributed targets.
  response_ok=all(abs(pv[d]-pt[d])<=2 for d in pv) and all(abs(bp[d]-bt[d])<=2 for d in bp)
  valid=not active and quality and response_ok and 0<=pcc and abs(pcc-target)<=2
  if 19<=t and not exit_started:
   stable=min(5,stable+1) if valid else 0
   stable_verified=stable>=5
  if exit_started:
   original_ok=quality and not active and all(abs(v-100)<.1 for v in pv.values()) and all(abs(v)<.1 for v in bp.values()) and abs(pcc-100)<.2
   exit_count=exit_count+1 if original_ok else 0
   if exit_count>=3 and stable_verified and cleared_at is None:
    alarm=False;cleared_at=t;events.append(dict(t=t,state='CLEARED',message='异常已恢复、连续5点稳定及原状态连续3点恢复均核验，解除模拟告警'))
  state='BASELINE' if t<5 else 'CLEARED' if not alarm else 'EXIT_VERIFY' if exit_started else 'DEGRADED' if active else 'STABLE_WAIT' if stable_verified else 'OBSERVING'
  if state!=prior_state:events.append(dict(t=t,state=state,message={'BASELINE':'合成稳定工况：PCC购电10kW','DEGRADED':'失去反馈：PV限0、BESS归零；零馈不可判定' if not quality else '移除拒令设备可调能力，重新分配有效容量并限制光伏','OBSERVING':'异常信号已消失，核对回执/实际响应及有效PCC，开始稳定观察','STABLE_WAIT':'连续5点稳定；仍保持告警，等待退出原状态验证','EXIT_VERIFY':'撤销临时设置，核对PV原限值及BESS待机状态','CLEARED':'恢复证据完整，模拟告警已解除'}[state]))
  if t in (5,19,25,29,45) or state!=prior_state:
   for node,value in {**pt,**bt}.items():
    rejected=active and ((kind=='pv_reject' and node==selected) or(kind=='bess_reject' and node==selected))
    commands.append(dict(id=f'{rid}-{kind}-{t}-{node}',node_id=node,t=t,phase=state,value_kw=round((allocate(load,charge)[0 if node in pv else 1][node]) if rejected else 125 if exit_started and node in pv else value,3),ack='REJECTED' if rejected else 'ACCEPTED',purpose='降级隔离/响应核验' if rejected else '重新分配/恢复'))
  devices=[dict(node_id=d,kind='PV',power_kw=round(v,3),target_kw=round(pt[d],3),available_kw=100,controllable=not(active and kind=='pv_reject' and d==selected),original_limit_kw=125,readback_limit_kw=50 if recovery_mode=='restore_failed' and exit_started and d==pvs[0] else 125 if exit_started else round(pt[d],3)) for d,v in pv.items()]
  devices += [dict(node_id=d,kind='BESS',power_kw=round(v,3),target_kw=round(bt[d],3),charge_bound_kw=cb[d],discharge_bound_kw=discharge[d],soc_pct=55,bms_allowed=cb[d]>0,controllable=not(active and kind=='bess_reject' and d==selected),mode='STANDBY' if exit_started and abs(v)<.1 else 'CONTROL') for d,v in bp.items()]
  samples.append(dict(t=t,phase='prepare' if t<5 else 'degraded' if active else 'restore' if exit_started else 'observe',state=state,feedback_kw=round(pcc,3) if quality else None,pcc_kw=round(pcc,3),quality='GOOD' if quality else 'INVALID',sequence=t if quality else None,age_s=0 if quality else None,pv_kw=round(sum(pv.values()),3),bess_kw=round(sum(bp.values()),3),load_kw=load,target_kw=10,devices=devices,stable_count=stable,alarm_latched=alarm,fault_active=active,zero_export_state='UNKNOWN' if not quality else 'EXPORTING' if pcc<0 else 'IMPORTING'))
  prior_state=state;prior_active=active
 restored=exit_count>=3
 issue=dict(node_id=selected,reason=NAMES[kind],action={'meter_lost':'核对零馈表供电、通信路径、时间戳和质量；缺少有效反馈时不宣称零馈，降级策略需厂家批准','pv_reject':'核对该台远程控制权限、限功率点表、回执及实际功率；无法控制持续馈网时保持告警并请厂家协同','bess_reject':'核对该台BMS充电允许、SOC及实时充电边界；移除不可调容量，不绕过电池保护'}[kind],layer='L4' if kind=='meter_lost' else 'L5',resolved=cleared_at is not None)
 issues=[issue]
 if recovery_mode=='restore_failed':issues.append(dict(node_id=pvs[0],reason='退出时原光伏限值/功率未恢复',action='保持告警；核对原限值125kW及实际功率，完成原状态恢复验证后再解除',layer='L5',resolved=False))
 return dict(key=kind,title=NAMES[kind],fault_node=selected,status='PASS' if cleared_at is not None else 'FAIL',stable_verified=stable_verified,restored=restored,alarm_latched=alarm,cleared_at=cleared_at,samples=samples,commands=commands,events=events,issues=issues,source='SIMULATOR',recovery_mode=recovery_mode)


def degradation_context(db,id,sid,mode):
 p,s,groups,zero,cap,ready=dynamic_context(db,id,sid,mode)
 prior=next((r for r in db.records('dynamic_response',sid) if r['mode']==mode),None) if s and s['mode']==mode else None
 ready=bool(ready and prior and prior['zero_export_id']==zero['id'] and prior['status']=='PASS' and prior['restored'] and not prior['alarm_latched'] and {c['key'] for c in prior['cases']}=={'load_step','pv_fluctuation','charge_limited'})
 return p,s,groups,prior,cap,ready


def register_degradation(app,db):
 def context(id,sid,mode):return degradation_context(db,id,sid,mode)
 def recovery_records(r):return db.records('degradation_recovery',r['id'])
 def recovered(r):return any(x['verified'] for x in recovery_records(r))
 @app.get('/api/plans/{id}/degradation')
 def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,s,groups,prior,cap,ready=context(id,session_id,mode)
  records=[r for r in db.records('degradation',session_id) if r['mode']==mode] if s and s['mode']==mode else []
  last=records[0] if records else None
  return dict(records=records,current=bool(last and ready and last['dynamic_id']==prior['id']),prerequisite_ready=ready,alarm_latched=bool(last and last['alarm_latched'] and not recovered(last)),recovery=recovery_records(last) if last else [],basis_pending=PENDING,pv_ids=[d['node_id'] for g in groups for d in g['devices']],bess_ids=[d['node_id'] for d in cap['devices']] if cap else [],meter=s['route']['meter']['node_id'] if s else None,ems=s['route']['ems']['node_id'] if s else None,physical_control_allowed=False)
 @app.post('/api/plans/{id}/degradation')
 def execute(id:str,body:Command):
  if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；降级策略、权限与厂家批准依据未齐备，未下发指令')
  p,s,groups,prior,cap,ready=context(id,body.session_id,body.mode)
  if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
  rid=digest(dict(kind='degradation',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:old=db.record(rid)
  except KeyError:old=None
  if old:
   if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同请求')
   return old
  if not ready:raise HTTPException(409,'请先完成当前步骤10三类动态测试及恢复')
  last=next(iter(db.records('degradation',s['id'])),None)
  if last and last['alarm_latched'] and not recovered(last):raise HTTPException(409,'恢复未确认，禁止新测试；请继续原运行恢复验证')
  if not body.acknowledged:raise HTTPException(422,'请确认独立降级与恢复演练范围')
  pvs=[d['node_id'] for g in groups for d in g['devices']];bs=cap['devices'];meter=s['route']['meter']['node_id'];ems=s['route']['ems']['node_id']
  allowed=pvs if body.scenario=='pv_reject' else [d['node_id'] for d in bs] if body.scenario=='bess_reject' else [meter] if body.scenario=='meter_lost' else [ems]
  fault=body.fault_node or allowed[0]
  if fault not in allowed:raise HTTPException(422,'异常对象不属于本场景')
  cases=[];issues=[]
  if body.scenario in ('no_permission','missing_basis'):issues=[dict(node_id=ems,reason='控制权限不足' if body.scenario=='no_permission' else '批准演练包缺失',action='补齐控制范围、适用规程和退出策略；未下发指令',layer='L5',resolved=False)]
  else:
   for kind in (list(NAMES) if body.scenario=='normal' else [body.scenario]):
    c=simulate_case(kind,pvs,bs,meter,ems,fault,body.recovery_mode,rid);cases.append(c);issues+=c['issues']
    if c['alarm_latched']:break
  scope=dict(model_hash=p['engineering_hash'],controller=ems,meter=meter,pv=pvs,bess=[d['node_id'] for d in bs],dynamic_id=prior['id'],test_pack='SIM-DEGRADE-1',physical_lease=False)
  r=dict(mode=body.mode,source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',physical_control_allowed=False,scope=scope,scope_hash=digest(scope),dynamic_id=prior['id'],request_id=body.request_id,request_signature=signature,scenario=body.scenario,recovery_mode=body.recovery_mode,cases=cases,issues=issues,status='PASS' if cases and all(c['status']=='PASS' for c in cases) else 'FAIL',restored=bool(cases and all(c['restored'] for c in cases)),alarm_latched=any(c['alarm_latched'] for c in cases))
  saved=db.add_once('degradation',s['id'],r,rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
  return saved
 @app.post('/api/plans/{id}/degradation/{run_id}/recover')
 def recover(id:str,run_id:str,body:Command):
  if body.mode!='SIMULATION':raise HTTPException(503,'未执行现场恢复')
  p,s,groups,prior,cap,ready=context(id,body.session_id,body.mode)
  try:r=db.record(run_id)
  except KeyError:raise HTTPException(404,'运行不存在')
  if not s or r['kind']!='degradation' or r['project']!=s['id'] or r['mode']!='SIMULATION':raise HTTPException(404,'运行不属于本会话')
  signature=digest(body.model_dump());rid=digest(dict(kind='degradation-recovery',run=run_id,request=body.request_id))
  try:old=db.record(rid)
  except KeyError:old=None
  if old:
   if old['request_signature']!=signature:raise HTTPException(409,'恢复运行ID已用于不同请求')
   return old
  if not body.acknowledged or not r['alarm_latched'] or not ready or r['dynamic_id']!=prior['id'] or recovered(r):raise HTTPException(409,'恢复依据不满足或原运行已验证恢复')
  # Independent synthetic replay bound to the original fault/scope; no force-clear operation.
  cases=[simulate_case(c['key'],r['scope']['pv'],cap['devices'],r['scope']['meter'],r['scope']['controller'],c['fault_node'],body.recovery_mode,rid) for c in r['cases'] if c['alarm_latched']]
  verified=bool(cases and all(c['stable_verified'] and c['restored'] and not c['alarm_latched'] for c in cases))
  result=dict(request_signature=signature,request_id=body.request_id,mode='SIMULATION',source='SIMULATOR',field_result=None,physical_control_allowed=False,verified=verified,cases=cases,evidence='独立合成重演：恢复及稳定证据完整，解除模拟告警；原失败记录保留' if verified else '独立合成重演未满足恢复及稳定要求，告警保持；原失败记录保留')
  saved=db.add_once('degradation_recovery',run_id,result,rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'恢复运行ID冲突')
  return saved
