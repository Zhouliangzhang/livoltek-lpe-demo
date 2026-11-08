"""Step13 read-only evidence aggregation and immutable, explicitly unsigned reports."""
import json
from html import escape
from typing import Literal
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .domain import digest
from .store import now
from .configuration_readback import session_inventory
from .meter_workflow import states, BASIS

TITLES=['调试会话与冻结依据','iEMS自检与控制权','零馈表通信与计量','光伏通信与身份','储能通信与可用能力','配置读回','光伏限功率控制','储能充放电控制','零馈控制联动','动态响应','降级与恢复','连续观察']
ENDPOINTS=['pv-communication','bess-communication','configuration-readback','pv-control','bess-control','zero-export','dynamic-response','degradation','continuous-observation']
LABELS={'SIM_PASS':'模拟满足','PREPARED':'现场准备 · 未验证','NOT_RUN':'未执行','STALE':'依据变化 · 需重测','FAIL':'异常','INCOMPLETE':'未完成','PENDING':'依据待确认','BLOCKED':'阻断'}

class SaveReport(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


def result_status(r,step):
 if not r:return 'NOT_RUN'
 if r.get('status') in ('FAIL','BLOCKED','INCOMPLETE'):return r['status']
 if r.get('failed'):return 'FAIL'
 if r.get('conditional') or r.get('skipped'):return 'INCOMPLETE'
 if step==6:
  counts=r['counts']
  if any(counts.get(k,0) for k in ('DIFFERENCE','UNREAD','UNIT_MISMATCH','TYPE_MISMATCH')):return 'FAIL'
  if counts.get('PENDING',0)+counts.get('CANDIDATE_MATCH',0):return 'PENDING'
 if step in (10,11):
  expected={'load_step','pv_fluctuation','charge_limited'} if step==10 else {'meter_lost','pv_reject','bess_reject'}
  if {x['key'] for x in r.get('cases',[])}!=expected:return 'INCOMPLETE'
 if step==12 and r.get('status')!='COMPLETE':return 'INCOMPLETE'
 return 'SIM_PASS' if r.get('source')=='SIMULATOR' else 'PREPARED'


def register_sat_report(app,db):
 # Reuse the authoritative read-only step queries, including their dependency/current checks.
 getters={name:next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/plans/{id}/'+name and 'GET' in r.methods) for name in ENDPOINTS}
 def context(id,sid,mode):
  try:
   p=db.record(id)
   if p['kind']!='plan':raise KeyError(id)
   s=db.record(sid) if sid else None
   if s and (s['kind']!='meter_session' or s['project']!=id):raise KeyError(sid)
  except KeyError:raise HTTPException(404,'项目依据或所属会话不存在')
  return p,s if s and s['mode']==mode else None

 def build(id,sid,mode):
  p,s=context(id,sid,mode);model=p['system_context_baseline'];stale=digest(db.get(p['project'])['model'])!=p['engineering_hash']
  evidence={};steps=[];issues=[];pending=[];history=[]
  def add_pending(step,title,reason,owner='厂家技术支持',node=None,layer='L5',row=None,eid=None,m1_step=None,focus_label=None):
   pending.append(dict(m1_step=m1_step,focus_label=focus_label,step=step,title=title,reason=reason,owner=owner,node_id=node,layer=layer,row_id=row,evidence_id=eid,action='补充适用型号/固件依据并确认批准版本' if 'EPC' not in owner else '核对现场对象并补充资料'))
  def add_step(n,record,current,records=None,status=None):
   rs=records if records is not None else ([record] if record else [])
   for r in rs:evidence[r['id']]=r
   status=status or result_status(record,n)
   if record and not current:status='STALE'
   steps.append(dict(number=n,title=TITLES[n-1],status=status,label=LABELS[status],current=bool(current),evidence_ids=[r['id'] for r in rs],latest_id=record['id'] if record else None,created=record.get('created') if record else None,reason='模型或前置证据已变化，请返回本步骤重新验证' if status=='STALE' else '尚无本环境、本会话的有效执行证据' if status=='NOT_RUN' else '演练判据满足；现场结果仍未验证' if status=='SIM_PASS' else '按本步记录处理差异、未完成方向或缺失批准依据'))
  def faults(r,n,current,historical=False):
   found=[]
   def add(x,node=None):
    if not x:return
    reason=x.get('reason',x.get('message','未完成'))
    item=dict(step=n,node_id=x.get('node_id') or node,reason=reason,action=x.get('action','回到本步骤核对原始证据后处理'),layer=x.get('layer','L5'),row_id=x.get('row_id') or x.get('edge_id'),owner=x.get('owner','EPC / 厂家技术支持'),m1_step=x.get('m1_step'),focus_label=x.get('focus_label'),resolved=bool(x.get('resolved',False)),evidence_id=r['id'],current=current)
    if not any(y['node_id']==item['node_id'] and y['reason']==reason for y in found):found.append(item)
   add(r.get('diagnosis'),s['route']['meter']['node_id'] if s and n==3 else None)
   if n==2:
    for check in r.get('checks',[]):
     if check.get('severity')=='BLOCK':add(check,s['route']['ems']['node_id'] if s else None)
   for x in r.get('issues',[]):add(x)
   for d in r.get('devices',[]):
    node=d.get('node_id');add(d.get('diagnosis'),node)
    for direction in d.get('directions',[]):
     add(direction.get('diagnosis'),node)
     if direction.get('status')=='SKIPPED':add(dict(reason=direction.get('label','方向')+'未测试',action='满足适用边界与批准条件后重新验证该方向'),node)
    if d.get('status')=='SKIPPED':add(dict(reason='设备未测试',action='解决前置异常后逐台重新验证'),node)
    for row in d.get('parameters',[]):
     if row.get('status') in ('DIFFERENCE','UNREAD','UNIT_MISMATCH','TYPE_MISMATCH'):add(dict(reason=row['label']+'：'+row['reason'],action=row['action'],row_id=row['row_id'],m1_step=row.get('m1_step'),focus_label=row.get('focus_label')),node)
   for case in r.get('cases',[]):
    for x in case.get('issues',[]):add(x)
   (history if historical else issues).extend(found)
  meter=[]
  if s:
   evidence[s['id']]=s;meter=db.records('meter_run',s['id']);progress=states(meter)
   add_step(1,s,not stale,status='SIM_PASS' if mode=='SIMULATION' else 'PREPARED')
   add_step(2,progress[0]['record'],not stale and progress[0]['current'])
   # Retain all six selected meter substep records, even if the final substep is absent.
   selected=[x['record'] for x in progress[1:] if x['record']]
   current=not stale and all(x['current'] for x in progress[1:])
   status='NOT_RUN' if not selected else 'FAIL' if any(x['status']=='FAIL' for x in selected) else 'INCOMPLETE' if len(selected)<6 else None
   add_step(3,progress[-1]['record'],current,selected,status)
   if selected and not progress[-1]['record']:steps[-1]['status']=status;steps[-1]['label']=LABELS[status]
   for x in progress:
    if x['record']:faults(x['record'],2 if x['key']=='selfcheck' else 3,not stale and x['current'])
   active={x['record']['id'] for x in progress if x['record']}
   for r in meter:
    evidence[r['id']]=r
    if r['id'] not in active:faults(r,2 if r['step']=='selfcheck' else 3,False,True)
   for gap in s.get('gate',{}).get('gaps',[]):add_pending(1,gap['title'],gap['reason'],gap['owner'],gap.get('node_id'),gap.get('layer'),eid=s['id'])
  else:
   for n in range(1,4):add_step(n,None,False)
  for n,name in enumerate(ENDPOINTS,4):
   data=getters[name](id=id,session_id=s['id'] if s else '',mode=mode)
   records=data['records'];last=records[0] if records else None
   current=bool(data.get('current') and not stale and all(x['current'] for x in steps))
   add_step(n,last,current)
   for r in records:
    evidence[r['id']]=r;faults(r,n,current if r==last else False,r!=last)
    for recovery in db.records(name.replace('-','_')+'_recovery',r['id']):evidence[recovery['id']]=recovery
   for title in data.get('basis_pending',[]):add_pending(n,title,'缺少受控厂家依据，演练参数不能代替现场批准',eid=last['id'] if last else None)
   if n in (4,5):
    for group in data.get('groups',[]):
     for d in group['devices']:
      for title in [x for x in d.get('pending',[]) if x not in ('现场SN','现场固件')]:add_pending(n,title,'当前型号/固件的适用资料待补充',node=d['node_id'],layer='L3',eid=last['id'] if last else None)
  for b in BASIS:add_pending(3,b['title'],b['missing'],b['owner'],s['route']['meter']['node_id'] if s else None,b['layer'])
  for d in session_inventory(p,s,mode):
   for key,label in [('sn','SN'),('firmware','固件版本')]:
    if not d.get(key):add_pending(4 if d['kind']=='PV_INVERTER' else 5 if d['kind']=='BESS' else 1,'设备'+label+'待补充','无法完成实际设备身份核对','EPC 现场工程师',d['node_id'],'L3')
   for row in d['parameters']:
    if row['approved'] is None or row.get('pending') or row.get('stale'):
     add_pending(6,row['label'],'正常运行批准配置、厂家读回映射或适用依据待确认',node=d['node_id'],row=row['row_id'],m1_step=row.get('m1_step'),focus_label=row.get('focus_label'))
  # Same issue is grouped for display, preserving every affected object and parameter target.
  grouped={}
  for x in pending:
   key=digest({k:x[k] for k in ('step','title','reason','owner','layer')})
   g=grouped.setdefault(key,{**x,'id':key,'targets':[]})
   target={k:x[k] for k in ('node_id','row_id','evidence_id','m1_step','focus_label')}
   if target not in g['targets']:g['targets'].append(target)
  pending=list(grouped.values())
  incomplete=[x for x in steps if x['status'] not in ('SIM_PASS',)]
  identity=dict(project=p['project'],revision=p['revision'],model_hash=p['engineering_hash'],session_id=s['id'] if s else None,controller=s['snapshot'].get('controller_binding') if s else None,operator=s.get('operator') if s else None,scope=s.get('scope') if s else None,witness_requirement=s.get('witness_requirement') if s else None,witness_name=s.get('witness_name') if s else None)
  report=dict(version='M2-SAT-REPORT-1',mode=mode,source='SIMULATOR' if mode=='SIMULATION' else 'FIELD_PREPARATION',title='模拟调试汇总 · 非现场 SAT' if mode=='SIMULATION' else '现场 SAT 资料草稿 · 尚无现场结果',sat_status='NOT_FIELD_SAT' if mode=='SIMULATION' else 'FIELD_NOT_VERIFIED',sat_passed=False,field_result=None,signature_status='UNSIGNED',identity=identity,model_stale=stale,steps=steps,issues=issues,historical_issues=history,pending=pending,incomplete=incomplete,manifest=[dict(id=r['id'],kind=r['kind'],created=r['created'],source=r.get('source','UNKNOWN'),hash=digest(r)) for r in evidence.values()],limitations=['本报告仅汇总已保存证据，不自动作出现场SAT通过或合同验收结论','模拟结果不得用于现场SAT签署；真实iEMS适配器与现场证据尚未接入','待厂家确认项、未完成方向及失效结果均须处理；旧运行异常保留，不自动视作已解决'])
  report['snapshot_hash']=digest(report)
  return report,evidence

 @app.get('/api/plans/{id}/sat-report')
 def listing(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  report,_=build(id,session_id,mode)
  snapshots=db.records('sat_report',session_id) if report['identity']['session_id'] else []
  return dict(report=report,snapshots=[dict(id=r['id'],created=r['created'],snapshot_hash=r['snapshot_hash'],current=r['snapshot_hash']==report['snapshot_hash'],title=r['title']) for r in snapshots if r['mode']==mode])

 @app.get('/api/plans/{id}/sat-report/evidence/{evidence_id}')
 def evidence(id:str,evidence_id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  _,records=build(id,session_id,mode)
  if evidence_id not in records:raise HTTPException(404,'证据不属于本项目、会话及环境')
  return records[evidence_id]

 @app.post('/api/plans/{id}/sat-report')
 def save(id:str,body:SaveReport):
  p,s=context(id,body.session_id,body.mode)
  if not s:raise HTTPException(409,'请先建立对应环境的调试会话')
  rid=digest(dict(kind='sat-report',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:
   previous=db.record(rid)
   if previous['request_signature']!=signature:raise HTTPException(409,'报告请求ID冲突')
   return previous
  except KeyError:pass
  report,evidence=build(id,s['id'],body.mode)
  return db.add_once('sat_report',s['id'],dict(**report,raw_evidence=evidence,request_signature=signature,generated_at=now(),plan_id=id),rid)

 @app.get('/api/plans/{id}/sat-report/{report_id}/export')
 def export(id:str,report_id:str,format:Literal['json','html']='json'):
  try:
   r=db.record(report_id)
   if r['kind']!='sat_report' or r['plan_id']!=id:raise KeyError(report_id)
  except KeyError:raise HTTPException(404,'报告不属于本项目')
  if format=='json':return r
  e=lambda value:escape(str(value))
  rows=''.join('<tr><td>'+e(x['number'])+'</td><td>'+e(x['title'])+'</td><td>'+e(x['label'])+'</td><td>'+e(x['reason'])+'</td></tr>' for x in r['steps'])
  faults=''.join('<li>'+e(f"步骤{x['step']:02} · {x['node_id'] or '系统'} · {x['reason']} · {x['action']} · {'恢复证据已记录' if x['resolved'] else '未关闭 / 待核对'}")+'</li>' for x in r['issues'])
  gaps=''.join('<li>'+e(f"步骤{x['step']:02} · {x['owner']} · {x['title']}：{x['reason']} · "+', '.join(t['node_id'] or '系统' for t in x['targets']))+'</li>' for x in r['pending'])
  raw=''.join('<details><summary>'+e(key)+' · '+e(value['kind'])+'</summary><pre>'+e(json.dumps(value,ensure_ascii=False,indent=2))+'</pre></details>' for key,value in r['raw_evidence'].items())
  html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+e(r['title'])+'</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;color:#173c32}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd9d2;padding:10px;text-align:left}li{margin:10px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.notice{padding:20px;background:#fff4d7}@media print{details{break-inside:avoid}}</style><h1>'+e(r['title'])+'</h1><p class="notice">未签署 · 不构成现场 SAT 通过。冻结快照，后续变更不会改写本文件。</p><p>'+e(r['identity'])+'</p><p>报告编号 '+e(r['id'])+' · '+e(r['created'])+'<br>快照校验 '+e(r['snapshot_hash'])+'</p><h2>步骤结果</h2><table><tr><th>步骤</th><th>主题</th><th>结果</th><th>说明</th></tr>'+rows+'</table><h2>本轮设备异常与恢复记录</h2><ul>'+faults+'</ul><h2>待补充与待厂家确认</h2><ul>'+gaps+'</ul><h2>限制与签署状态</h2><p>'+e('；'.join(r['limitations']))+'</p><h2>原始证据（含历史运行）</h2>'+raw+'</html>'
  return HTMLResponse(html,headers={'Content-Disposition':f'attachment; filename="SAT-{r["mode"]}-{r["id"][:12]}.html"'})
