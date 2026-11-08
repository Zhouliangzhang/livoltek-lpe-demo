"""Step12 accelerated synthetic observation, never physical device I/O."""
import math
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field
from .domain import digest
from .degradation import degradation_context
from .configuration_readback import inventory,compare,session_inventory

PENDING=['M1正常运行配置批准值、厂家点表与读回生效依据','撤销临时限值/充放电设定、测试租约及恢复正常控制所有者的规程','连续观察时长、采样间隔、数据时效与时钟质量判据','正常运行功率范围、SOC/BMS边界、告警及通信质量要求','现场iEMS身份、权限、日志持久化与现场见证记录']
class Command(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 acknowledged:bool=False
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 scenario:Literal['normal','meter_loss','pv_loss','bess_loss','iems_restart','stale_data','power_export','config_drift','cleanup_failed','normal_config_mismatch','no_permission','missing_basis']='normal'
 pattern:Literal['once','repeat','persistent']='once'
 fault_node:str=''


def observe(model,ems,meter,scenario,pattern,fault,rid,devices=None):
 devices=devices if devices is not None else inventory(model);rows=[dict(node_id=d['node_id'],**compare(r,'normal')) for d in devices for r in d['parameters']]
 configuration=dict(rows=rows,pending_count=sum(r['status'] in ('PENDING','CANDIDATE_MATCH') for r in rows),approved_match_count=sum(r['status']=='MATCH' for r in rows),basis='M1批准/候选对照；合成读回，缺失依据不升级为批准')
 profiles=[dict(node_id=d['node_id'],kind=d['kind'],expected='正常控制所有者 / 测试租约释放' if d['kind']=='EMS' else '正常计量模式 / 无测试覆盖' if d['kind']=='METER' else '原限值125kW / 无临时覆盖' if d['kind']=='PV_INVERTER' else '原0kW待机 / 无临时覆盖',actual=None,status='PENDING',source='SIMULATOR') for d in devices]
 steps=[dict(key='withdraw',label='撤销临时测试设置',status='PASS',evidence='合成撤销临时限功率、充放电设定与故障注入'),dict(key='owner',label='恢复正常控制权',status='PASS',evidence='合成测试租约已释放，正常SIM-iEMS拥有控制权'),dict(key='readback',label='正常配置读回',status='PASS',evidence='SIM-NORMAL-1正常配置读回一致；M1批准缺项另列待确认')]
 actions=[dict(id=f'{rid}-{d["node_id"]}-cleanup',node_id=d['node_id'],action='撤销临时覆盖并恢复SIM-NORMAL-1',ack='ACCEPTED') for d in devices]
 blocked=scenario in ('cleanup_failed','normal_config_mismatch','no_permission','missing_basis')
 issues=[];events=[];samples=[]
 if blocked:
  key='withdraw' if scenario=='cleanup_failed' else 'readback' if scenario=='normal_config_mismatch' else 'owner'
  reason={'cleanup_failed':'临时测试覆盖未撤销，不能开始连续观察','normal_config_mismatch':'正常配置读回不符，不能开始计时','no_permission':'缺少撤销测试设置的控制权限','missing_basis':'缺少适用演练包，不能执行撤销动作'}[scenario]
  for step in steps:
   step['status']='FAIL' if step['key']==key else 'SKIPPED'
   step['evidence']=reason if step['key']==key else '未取得本轮完整证据，不标为满足'
  issues=[dict(node_id=fault,reason=reason,action='核对临时覆盖、正常配置及批准依据，处理后重新发起；不能用勾选代替读回',layer='L5',first_t=0,last_t=0,resolved=False)]
  if scenario in ('no_permission','missing_basis'):actions=[]
  for a in actions:a['ack']='ACCEPTED_READBACK_MISMATCH' if a['node_id']==fault else 'ACCEPTED'
  for p in profiles:p.update(actual='临时覆盖仍存在' if scenario=='cleanup_failed' and p['node_id']==fault else '读回不符' if p['node_id']==fault else None,status='FAIL' if p['node_id']==fault else 'PENDING')
  return dict(status='BLOCKED',cleanup=dict(verified=False,steps=steps,actions=actions,profiles=profiles),configuration=configuration,devices=devices,samples=[],issues=issues,events=[],stable_seconds=0,window_start=None,completed_at=None,reset_count=0)
 for p in profiles:p.update(actual=p['expected'],status='SIM_MATCH')
 base_pv=sum(d['kind']=='PV_INVERTER' for d in devices)*100
 start=None;completed=None;elapsed=0;resets=0;episode=False;issue_index=None
 events.append(dict(t=3,kind='READY',message='撤销及正常读回完成；从下一有效样本开始计时'))
 for t in range(66):
  active=scenario!='normal' and t>=8 and (pattern=='persistent' or t<=10 or pattern=='repeat' and 23<=t<=24)
  readings=[]
  for d in devices:
   affected=active and d['node_id']==fault;comm=not(affected and scenario in ('meter_loss','pv_loss','bess_loss','iems_restart'))
   fresh=comm and not(affected and scenario=='stale_data');config_ok=not(affected and scenario=='config_drift')
   power=100+round(.05*math.sin(t/3),3) if d['kind']=='PV_INVERTER' else 15 if affected and scenario=='config_drift' and d['kind']=='BESS' else 0 if d['kind']=='BESS' else None
   readings.append(dict(node_id=d['node_id'],kind=d['kind'],communication='ONLINE' if comm else 'OFFLINE',quality='GOOD' if fresh else 'INVALID',age_s=0 if fresh else None,sequence=t if fresh else 7 if scenario=='stale_data' else None,power_kw=power if fresh else None,plant_power_kw=power,normal_config=config_ok,test_override=not config_ok,normal_owner=comm if d['kind']=='EMS' else None,log_persistent=comm if d['kind']=='EMS' else None,soc_pct=55 if d['kind']=='BESS' else None,bms_state='KNOWN' if fresh and d['kind']=='BESS' else None,state='RESTARTING' if affected and scenario=='iems_restart' else 'OFFLINE' if not comm else 'STALE' if not fresh else 'STANDBY' if d['kind']=='BESS' and config_ok else 'NORMAL' if config_ok else 'TEST_OVERRIDE'))
  pv=sum(d['plant_power_kw'] or 0 for d in readings if d['kind']=='PV_INVERTER');bess=sum(d['plant_power_kw'] or 0 for d in readings if d['kind']=='BESS')
  load=base_pv-25 if active and scenario=='power_export' else base_pv+100
  pcc=round(load-pv-bess,3);meter_data=next(d for d in readings if d['node_id']==meter);ems_data=next(d for d in readings if d['node_id']==ems)
  meter_good=meter_data['quality']=='GOOD';feedback=pcc if meter_good else None
  meter_data['power_kw']=feedback
  all_healthy=all(d['quality']=='GOOD' and d['normal_config'] for d in readings) and ems_data['normal_owner'] and ems_data['log_persistent']
  power_ok=feedback is not None and 95<=feedback<=105 and all((d['kind']!='BESS' or d['power_kw']==0) and (d['kind']!='PV_INVERTER' or d['power_kw'] is not None and 0<=d['power_kw']<=125) for d in readings)
  healthy=bool(all_healthy and power_ok)
  if t>=4:
   if not healthy:
    if not episode:
     resets+=1;reason={'meter_loss':'零馈表通信中断','pv_loss':'光伏通信中断','bess_loss':'储能通信中断','iems_restart':'iEMS重启，控制所有者及日志连续性中断','stale_data':'计量源序号冻结，数据无效','power_export':'并网点出现馈网，正常功率条件未满足（不直接判定电表故障）','config_drift':'观察期间正常配置漂移，发现临时测试覆盖'}[scenario]
     issues.append(dict(node_id=fault,reason=reason,action='核对通信路径、供电和数据质量；恢复新鲜有效反馈后从零计时' if scenario in ('meter_loss','pv_loss','bess_loss','stale_data') else '核对控制器身份、正常所有者、时钟和日志，重新读回正常配置后计时' if scenario=='iems_restart' else '核对负载/发电、正常控制策略与设备功率，必要时回步骤11处理，禁止手动完成' if scenario=='power_export' else '定位M1正常配置；确认测试覆盖撤销及读回一致后重新计时',layer='L4' if scenario in ('meter_loss','pv_loss','bess_loss','stale_data') else 'L5',first_t=t,last_t=t,resolved=False));issue_index=len(issues)-1
     events.append(dict(t=t,kind='RESET',message=f'{fault}：{reason}；连续计时清零'))
    else:issues[issue_index]['last_t']=t
    start=None;elapsed=0;episode=True
   else:
    if episode:
     issues[issue_index]['resolved']=True;events.append(dict(t=t,kind='RESTART',message='通信、正常配置及功率条件重新满足，从新鲜样本重新计时'))
    if start is None:start=t
    elapsed=t-start;episode=False
    if elapsed>=20:completed=t;events.append(dict(t=t,kind='COMPLETE',message='连续20秒所有对象通信/配置/功率满足演练要求，观察完成'))
  state='PREPARING' if t<4 else 'RESET' if not healthy else 'COMPLETE' if completed is not None else 'OBSERVING'
  samples.append(dict(t=t,phase='prepare' if t<4 else 'observe',state=state,quality='GOOD' if meter_good else 'INVALID',feedback_kw=feedback,pcc_kw=pcc,pv_kw=round(pv,3) if all(d['quality']=='GOOD' for d in readings if d['kind']=='PV_INVERTER') else None,bess_kw=round(bess,3) if all(d['quality']=='GOOD' for d in readings if d['kind']=='BESS') else None,load_kw=load,target_kw=100,devices=readings,stable_seconds=elapsed,window_start=start,online_count=sum(d['communication']=='ONLINE' for d in readings),fresh_count=sum(d['quality']=='GOOD' for d in readings),normal_config=all(d['normal_config'] for d in readings),power_ok=power_ok,all_healthy=healthy,test_lease_active=t<3))
  if completed is not None:break
 return dict(status='COMPLETE' if completed is not None else 'INCOMPLETE',cleanup=dict(verified=True,steps=steps,actions=actions,profiles=profiles),configuration=configuration,devices=devices,samples=samples,issues=issues,events=events,stable_seconds=elapsed,window_start=start,completed_at=completed,reset_count=resets)


def register_continuous_observation(app,db):
 def context(id,sid,mode):
  p,s,groups,dynamic,cap,ready=degradation_context(db,id,sid,mode)
  prior=next((r for r in db.records('degradation',sid) if r['mode']==mode),None) if s and s['mode']==mode else None
  ready=bool(ready and prior and prior['dynamic_id']==dynamic['id'] and prior['status']=='PASS' and prior['restored'] and not prior['alarm_latched'] and {c['key'] for c in prior['cases']}=={'meter_lost','pv_reject','bess_reject'})
  return p,s,prior,ready
 @app.get('/api/plans/{id}/continuous-observation')
 def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,s,prior,ready=context(id,session_id,mode)
  records=[r for r in db.records('continuous_observation',session_id) if r['mode']==mode] if s and s['mode']==mode else []
  last=records[0] if records else None
  return dict(records=records,current=bool(last and ready and last['degradation_id']==prior['id']),prerequisite_ready=ready,devices=session_inventory(p,s,mode),basis_pending=PENDING,physical_control_allowed=False)
 @app.post('/api/plans/{id}/continuous-observation')
 def execute(id:str,body:Command):
  if body.mode=='REAL':raise HTTPException(503,'真实iEMS未接入；未撤销现场设置、未取得现场连续观察证据，不能完成')
  p,s,prior,ready=context(id,body.session_id,body.mode)
  if not s or s['mode']!=body.mode:raise HTTPException(409,'缺少对应环境会话')
  rid=digest(dict(kind='continuous-observation',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:old=db.record(rid)
  except KeyError:old=None
  if old:
   if old['request_signature']!=signature:raise HTTPException(409,'运行ID已用于不同请求')
   return old
  if not ready:raise HTTPException(409,'请先完成当前步骤11三类降级测试及稳定恢复；模型或前置变化后重新验证')
  if not body.acknowledged:raise HTTPException(422,'请确认撤销临时测试设置并执行独立模拟连续观察')
  model=p['system_context_baseline'];devices=session_inventory(p,s,body.mode);ems=s['route']['ems']['node_id'];meter=s['route']['meter']['node_id']
  kind='PV_INVERTER' if body.scenario=='pv_loss' else 'BESS' if body.scenario in ('bess_loss','config_drift','normal_config_mismatch') else 'METER' if body.scenario in ('meter_loss','stale_data','power_export') else 'EMS'
  allowed=[d['node_id'] for d in devices if d['kind']==kind]
  if not allowed or ems not in {d['node_id'] for d in devices} or meter not in {d['node_id'] for d in devices}:raise HTTPException(409,'当前冻结范围缺少观察必需设备，请核对iEMS、零馈表及所选场景对象')
  fault=body.fault_node or allowed[0]
  if fault not in allowed:raise HTTPException(422,'异常设备不属于所选场景')
  result=observe(model,ems,meter,body.scenario,body.pattern,fault,rid,devices)
  scope=dict(model_hash=p['engineering_hash'],degradation_id=prior['id'],controller=ems,meter=meter,node_ids=[d['node_id'] for d in devices],test_pack='SIM-OBSERVE-1',normal_profile='SIM-NORMAL-1',physical_lease=False)
  result.update(mode=body.mode,source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',physical_control_allowed=False,scope=scope,scope_hash=digest(scope),degradation_id=prior['id'],request_id=body.request_id,request_signature=signature,scenario=body.scenario,pattern=body.pattern,criteria=dict(window_seconds=20,sample_period_s=1,normal_pcc_kw=100,tolerance_kw=5,source='SIMULATION_ONLY'))
  saved=db.add_once('continuous_observation',s['id'],result,rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'运行ID冲突')
  return saved
