"""Step09 synthetic plant/control loop. No network/device write capability."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .pv_control import control_context

PENDING=['EPC整站测试授权、唯一控制所有者与有效控制租约','型号/固件适用的批准联动测试包及M1批准配置','PCC范围、计量方向/倍率、质量与数据时效要求','SOC/BMS实时边界、光伏限功率与储能分配策略','零馈目标/容差/稳定窗口、退出与恢复确认规程']

class Command(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 acknowledged:bool=False
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 scenario:Literal['normal','no_permission','missing_basis','meter_lost','pv_reject','bess_reject','restore_failed']='normal'
 fault_node:str=''


def simulate(pvs,bess,meter,ems,scenario,fault,rid):
 stages=[];samples=[];commands=[];issues=[]
 def stage(key,label,status,evidence):stages.append(dict(key=key,label=label,status=status,evidence=evidence))
 def issue(node,reason,action,layer='L5'):issues.append(dict(node_id=node,reason=reason,action=action,layer=layer,owner='EPC / 厂家技术支持'))
 def result(restored=False):return dict(original_state=dict(pv_limit_kw=125,pv_available_kw=100,bess_setpoint_kw=0,bess_mode='STANDBY',source='SIMULATOR'),status='FAIL' if issues else 'PASS',stages=stages,samples=samples,commands=commands,issues=issues,restored=restored,alarm_latched=bool(samples and not restored))
 if scenario in ('no_permission','missing_basis'):
  issue(ems,'整站控制权限不足' if scenario=='no_permission' else '批准演练包缺失','补齐整站控制范围、唯一所有者和适用规程；不下发功率指令')
  stage('preflight','权限与批准依据','FAIL',issues[0]['reason'])
  for key,label in [('charge','富余光伏：充电与限功率'),('discharge','功率缺口：储能放电配合'),('restore','退出并恢复原状态')]:stage(key,label,'SKIPPED','未下发指令')
  return result()
 stage('preflight','权限与批准依据','PASS','SIM整站范围、单一所有者、演练包已核验；真实权限/厂家批准仍待确认')
 np=len(pvs);available=100*np;target=10
 # All plant values are synthetic. Actual M1 identity and Step05 capability limits bound allocations.
 pv={d:100.0 for d in pvs};bp={d['node_id']:0.0 for d in bess}
 cb={d['node_id']:min(40,max(0,d['capability']['charge_kw'])) for d in bess}
 dbound={d['node_id']:min(40,max(0,d['capability']['discharge_kw'])) for d in bess}
 load=available+100;t=0;failed=False;feedback_ok=True
 def record(phase,pvt,bt):
  nonlocal t
  power=load-sum(pv.values())-sum(bp.values())
  devices=[dict(node_id=d,kind='PV',power_kw=round(v,3),target_kw=round(pvt[d],3),available_kw=100) for d,v in pv.items()]
  devices += [dict(node_id=d,kind='BESS',power_kw=round(v,3),target_kw=round(bt[d],3),charge_bound_kw=cb[d],discharge_bound_kw=dbound[d],soc_pct=55,bms_allowed=True) for d,v in bp.items()]
  samples.append(dict(t=t,phase=phase,pcc_kw=round(power,3),feedback_kw=round(power,3) if feedback_ok else None,quality='GOOD' if feedback_ok else 'INVALID',age_s=0 if feedback_ok else None,sequence=t if feedback_ok else None,pv_kw=round(sum(pv.values()),3),bess_kw=round(sum(bp.values()),3),load_kw=load,target_kw=target,devices=devices));t+=1
 def send(phase,pvt,bt):
  for node,value in {**pvt,**bt}.items():
   rejected=phase=='charge' and node==fault and scenario in ('pv_reject','bess_reject')
   commands.append(dict(id=f'{rid}-{phase}-{node}',node_id=node,phase=phase,value_kw=125 if phase=='restore' and node in pv else round(value,3),ack='REJECTED' if rejected else 'ACCEPTED',source='SIMULATOR'))
 record('initial',pv,bp)
 for phase in ('charge','discharge'):
  label='富余光伏：充电与限功率' if phase=='charge' else '功率缺口：储能放电配合'
  if failed:
   stage(phase,label,'SKIPPED','上一阶段异常，未启动本阶段');continue
  load=round(available*.4) if phase=='charge' else available+min(sum(dbound.values())*.5,200)
  for tick in range(10):
   if scenario=='meter_lost' and phase=='charge' and tick==3:
    feedback_ok=False;failed=True
    issue(meter,'并网点功率反馈失效，零馈状态不可判定','停止闭环测试；检查零馈表供电、通信路径、时间戳和数据质量；按厂家批准的退出策略处理','L4')
    pvt={d:0 for d in pv};bt={d:0 for d in bp};send('feedback_exit',pvt,bt)
   elif not feedback_ok:pvt={d:0 for d in pv};bt={d:0 for d in bp}
   else:
    # Feedback plus measured generation reconstructs demand; no stale PCC used.
    feedback=load-sum(pv.values())-sum(bp.values())
    demand=feedback+sum(pv.values())+sum(bp.values())
    desired=demand-available-target
    capacity=sum(cb.values()) if desired<0 else sum(dbound.values())
    bounded=max(-sum(cb.values()),min(sum(dbound.values()),desired))
    weights=cb if desired<0 else dbound
    bt={d:bounded*weights[d]/capacity if capacity else 0 for d in bp}
    pv_total=max(0,min(available,demand-sum(bt.values())-target))
    pvt={d:pv_total/np for d in pv}
    if tick==0:send(phase,pvt,bt)
   for d in pv:
    pv[d]=pv[d]+.7*(pvt[d]-pv[d]) if not (scenario=='pv_reject' and d==fault and phase=='charge') else 100
   for d in bp:
    bp[d]=bp[d]+.7*(bt[d]-bp[d]) if not (scenario=='bess_reject' and d==fault and phase=='charge') else 0
   record(phase,pvt,bt)
  if phase=='charge' and scenario in ('pv_reject','bess_reject'):
   failed=True;issue(fault,'光伏拒绝限功率' if scenario=='pv_reject' else '储能拒绝充电，分配功率未执行','停止下一测试段；核对设备远程控制模式、回执、BMS允许与点表，保留逐台功率证据；请厂家协同')
  window=samples[-3:];ok=not failed and all(x['quality']=='GOOD' and 0<=x['feedback_kw'] and abs(x['feedback_kw']-target)<=2 for x in window)
  if not ok and not failed:
   failed=True;issue(ems,'并网点未在演练窗口内稳定到目标','检查设备可用边界、控制响应、功率分配及PCC覆盖范围')
  stage(phase,label,'PASS' if ok else 'FAIL',f'购电目标10kW；末3点：'+ ' / '.join('反馈无效' if x['feedback_kw'] is None else str(x['feedback_kw'])+'kW' for x in window)+f'；PV {window[-1]["pv_kw"]}kW / BESS {window[-1]["bess_kw"]}kW；演练窗口非厂家判据')
 # Withdraw temporary control; simulator restores original PV availability / BESS standby.
 load=available+100;pvt={d:100 for d in pv};bt={d:0 for d in bp};send('restore',pvt,bt)
 for tick in range(8):
  for d in pv:pv[d]=pv[d]+.7*(100-pv[d]) if not (scenario=='restore_failed' and d==fault) else 50
  for d in bp:bp[d]+=.7*(0-bp[d])
  record('restore',pvt,bt)
 restored=feedback_ok and all(abs(v-100)<.1 for v in pv.values()) and all(abs(v)<.1 for v in bp.values())
 if scenario=='restore_failed':issue(fault,'原光伏限值/功率恢复未确认','保持告警，停止新测试；核对原限值、实际功率及模式，按批准规程复核退出状态')
 stage('restore','退出并恢复原状态','PASS' if restored else 'UNCONFIRMED','原PV限值125kW、可用100kW/台、BESS 0kW待机模拟读回一致；原状态购电100kW' if restored else '恢复未确认；缺少有效PCC反馈或设备原状态未恢复，保持告警')
 return result(restored)


def register_zero_export(app,db):
 def context(id,sid,mode):
  p,s,groups,cfg,_,stale=control_context(db,id,sid,mode)
  def latest(kind):return next((r for r in db.records(kind,sid) if r['mode']==mode),None) if s and s['mode']==mode else None
  pv=latest('pv_control');bess=latest('bess_control');cap=latest('bess_communication')
  ready=bool(cfg and not stale and pv and bess and cap and pv['configuration_id']==cfg['id'] and bess['pv_control_id']==pv['id'] and pv['passed']==len(pv['devices']) and bess['passed']==len(bess['devices']) and len(pv['devices'])>0 and len(bess['devices'])>0 and not pv['alarm_latched'] and not bess['alarm_latched'])
  return p,s,groups,bess,cap,ready
 def recovered(r):return db.records('zero_export_recovery',r['id'])
 @app.get('/api/plans/{id}/zero-export')
 def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,s,groups,bess,cap,ready=context(id,session_id,mode)
  records=[r for r in db.records('zero_export',session_id) if r['mode']==mode] if s and s['mode']==mode else []
  last=records[0] if records else None
  return dict(records=records,prerequisite_ready=ready,current=bool(last and ready and last['bess_control_id']==bess['id']),basis_pending=PENDING,alarm_latched=bool(last and last['alarm_latched'] and not recovered(last)),recovery=recovered(last) if last else [],pv_ids=[d['node_id'] for g in groups for d in g['devices']],bess_ids=[d['node_id'] for d in cap['devices']] if cap else [],meter=s['route']['meter']['node_id'] if s else None,ems=s['route']['ems']['node_id'] if s else None,physical_control_allowed=False)
 @app.post('/api/plans/{id}/zero-export')
 def execute(id:str,body:Command):
  if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；现场控制权限及厂家批准依据未齐备，未下发指令')
  p,s,groups,bess,cap,ready=context(id,body.session_id,body.mode)
  if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
  rid=digest(dict(kind='zero-export',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:old=db.record(rid)
  except KeyError:old=None
  if old:
   if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同请求')
   return old
  if not ready:raise HTTPException(409,'请完成当前步骤03–08全部设备及双向控制验证；前置重测后重新验证')
  last=next(iter(db.records('zero_export',s['id'])),None)
  if last and last['alarm_latched'] and not recovered(last):raise HTTPException(409,'原运行恢复未确认，禁止新测试')
  if not body.acknowledged:raise HTTPException(422,'请确认独立整站演练范围和退出策略')
  pvs=[d['node_id'] for g in groups for d in g['devices']];bs=cap['devices'];meter=s['route']['meter']['node_id'];ems=s['route']['ems']['node_id']
  allowed=pvs if body.scenario in ('pv_reject','restore_failed') else [d['node_id'] for d in bs] if body.scenario=='bess_reject' else [meter] if body.scenario=='meter_lost' else [ems]
  fault=body.fault_node or allowed[0]
  if body.scenario!='normal' and fault not in allowed:raise HTTPException(422,'异常设备不属于所选场景范围')
  r=simulate(pvs,bs,meter,ems,body.scenario,fault,rid)
  scope=dict(model_hash=p['engineering_hash'],controller=ems,meter=meter,pv=pvs,bess=[d['node_id'] for d in bs],test_pack='SIM-ZERO-EXPORT-1',physical_lease=False)
  r.update(mode=body.mode,source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',physical_control_allowed=False,scope=scope,scope_hash=digest(scope),bess_control_id=bess['id'],request_id=body.request_id,request_signature=signature,scenario=body.scenario)
  saved=db.add_once('zero_export',s['id'],r,rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
  return saved
 @app.post('/api/plans/{id}/zero-export/{run_id}/recover')
 def recover(id:str,run_id:str,body:Command):
  if body.mode!='SIMULATION':raise HTTPException(503,'未执行现场恢复')
  p,s,groups,bess,cap,ready=context(id,body.session_id,body.mode)
  try:r=db.record(run_id)
  except KeyError:raise HTTPException(404,'运行不存在')
  if not s or r['kind']!='zero_export' or r['project']!=s['id'] or r['mode']!='SIMULATION':raise HTTPException(404,'运行不属于本会话')
  if not body.acknowledged or not r['alarm_latched'] or not ready or r['bess_control_id']!=bess['id']:raise HTTPException(409,'恢复范围或依据不满足')
  return db.add_once('zero_export_recovery',run_id,dict(mode='SIMULATION',source='SIMULATOR',field_result=None,evidence='独立合成复核：PCC连续3点购电100kW/质量GOOD、PV原限值125kW与功率100kW/台、BESS 0kW待机、控制所有者一致；原失败记录保留。',samples=[dict(t=i,pcc_kw=100,quality='GOOD') for i in range(3)],physical_control_allowed=False),digest(dict(kind='zero-recovery',run=run_id)))
