"""Append-only M3 follow-up log. SIM verification never grants manufacturer or field approval."""
import json
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .handover import content_hash
from .store import now

class Action(BaseModel):
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 item_id:str
 action:Literal['PROGRESS','SUBMIT','LINK_RETEST','REOPEN']
 actor:str=Field(min_length=1,max_length=100)
 note:str=Field(min_length=1,max_length=3000)
 reference:str=Field(default='',max_length=1000)
 report_id:str=''
 evidence_id:str=''
 expected_event_id:str=''
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')

class Revision(BaseModel):
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 report_id:str
 prepared_by:str=Field(min_length=1,max_length=100)
 acknowledged:bool=False
 expected_tracking_hash:str
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


def tasks_from(followup):
 items={}
 def add(kind,step,title,owner,node=None,row=None,layer=None,action='',evidence_id=None):
  key=dict(kind=kind,step=step,title=title,node_id=node,row_id=row)
  iid=content_hash(key);party='EPC' if owner.startswith('EPC') else 'MANUFACTURER'
  items[iid]=dict(id=iid,**key,owner=owner,party=party,layer=layer,action=action,evidence_id=evidence_id,group_id=content_hash(dict(kind=kind,step=step,title=title,party=party)))
 for x in followup['issues']:
  if not x['resolved']:add('ISSUE',x['step'],x['reason'],x['owner'],x['node_id'],x.get('row_id'),x.get('layer'),x['action'],x['evidence_id'])
 for x in followup['incomplete']:add('STEP',x['number'],x['title'],'EPC / 厂家技术支持',action='处理缺项后按当前依据重新执行本步骤',evidence_id=x['latest_id'])
 for g in followup['pending']:
  for t in g['targets']:add('PENDING',g['step'],g['title'],g['owner'],t['node_id'],t['row_id'],g['layer'],g['action'],t['evidence_id'])
 return items


def register_m3_tracking(app,db):
 report_query=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/plans/{id}/sat-report' and 'GET' in r.methods)
 report_export=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/plans/{id}/sat-report/{report_id}/export' and 'GET' in r.methods)
 def get_package(project,pid,mode):
  try:
   p=db.record(pid)
   if p['kind']!='handover_package' or p['project']!=project or p['mode']!=mode:raise KeyError(pid)
   return p
  except KeyError:raise HTTPException(404,'交接包不属于本项目或环境')
 def root_id(p):return p.get('root_package_id',p['id'])
 def lineage(p):return [x for x in db.records('handover_package',p['project']) if x['mode']==p['mode'] and root_id(x)==root_id(p)]
 def report_current(r,cache):
  key=(r['plan_id'],r['project'],r['mode'])
  if key not in cache:cache[key]=report_query(id=key[0],session_id=key[1],mode=key[2])['report']
  live=cache[key]
  return not live['model_stale'] and live['snapshot_hash']==r['snapshot_hash']
 def valid_report(p,rid,cache):
  try:
   r=db.record(rid)
   if r['kind']!='sat_report' or r['identity']['project']!=p['project'] or r['mode']!=p['mode']:raise KeyError(rid)
  except KeyError:raise HTTPException(404,'报告不属于本项目及环境')
  if not report_current(r,cache):raise HTTPException(409,'报告已失效，请先完成复测并在步骤13保存当前报告')
  return r
 def coverage(record,node):
  if not node:return True
  ids=set(record.get('scope',{}).get('node_ids',[])) if isinstance(record.get('scope'),dict) else set()
  ids.update(d['node_id'] for d in record.get('devices',[]) if 'node_id' in d)
  ids.update(record.get('lease',{}).get('devices',[]))
  for sample in record.get('samples',[]):ids.update(d['node_id'] for d in sample.get('devices',[]) if 'node_id' in d)
  for side in ('meter','ems'):
   if record.get('route',{}).get(side):ids.add(record['route'][side]['node_id'])
  # Meter evidence is a run on the explicitly frozen route.
  if record.get('kind')=='meter_run':
   session=db.record(record['project']);ids.update(session['route'][x]['node_id'] for x in ('meter','ems'))
  return node in ids
 def evaluate(item,r,evidence):
  step=r['steps'][item['step']-1]
  remaining=item['id'] in tasks_from({k:r[k] for k in ('issues','incomplete','pending')})
  if item['party']=='MANUFACTURER' and remaining:return 'WAIT_MANUFACTURER','已关联复测；适用厂家依据仍待确认，引用文档不能自动批准'
  if remaining or not step['current'] or step['status']!='SIM_PASS':return 'RETEST_BLOCKED','对应缺项或步骤判据仍未满足，保留待处理'
  if r['mode']!='SIMULATION' or evidence.get('source')!='SIMULATOR':return 'FIELD_PENDING','现场证据真实性及授权尚未核验，不能自动关闭或形成验收结论'
  return 'SIM_VERIFIED','对应当前模拟复测满足，原缺项未再出现；仅为模拟闭环，非现场验收'
 def state(p,cache=None):
  cache={} if cache is None else cache
  packages=lineage(p);tasks={}
  for pack in reversed(packages):tasks.update(tasks_from(pack['followup']))
  events=db.records('handover_action',root_id(p));items=[]
  for item in tasks.values():
   logs=[x for x in events if x['item_id']==item['id']];last=logs[0] if logs else None
   status='OPEN';reason='尚无处理记录'
   if last:
    status=last['status'];reason=last['reason']
    if last['action']=='LINK_RETEST':
     r=db.record(last['report_id'])
     if not report_current(r,cache):status='RETEST_STALE';reason='配置或前置结果变化，已关联复测失效，需重新复测'
   items.append(dict(**item,status=status,status_reason=reason,latest_event_id=last['id'] if last else '',actor=last['actor'] if last else '',updated=last['created'] if last else None,events=logs))
  body=dict(root_package_id=root_id(p),items=items,event_ids=[x['id'] for x in events],mode=p['mode'])
  return dict(**body,tracking_hash=content_hash(body))
 def reports(p,cache):
  out=[]
  for plan in db.records('plan',p['project']):
   for session in db.records('meter_session',plan['id']):
    if session['mode']!=p['mode']:continue
    saved=[r for r in db.records('sat_report',session['id']) if r['mode']==p['mode']]
    if not saved or not report_current(saved[0],cache):continue
    r=saved[0];runs=[]
    for step in r['steps']:
     for eid in step['evidence_ids']:
      e=r['raw_evidence'][eid]
      runs.append(dict(id=eid,step=step['number'],title=step['title'],created=e['created'],status=step['label']))
    out.append(dict(id=r['id'],created=r['created'],revision=r['identity']['revision'],plan_id=r['plan_id'],session_id=r['project'],runs=runs))
  return out

 @app.get('/api/projects/{id}/handovers/{package_id}/tracking')
 def listing(id:str,package_id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p=get_package(id,package_id,mode);cache={};s=state(p,cache);chain=lineage(p)
  return dict(**s,reports=reports(p,cache),latest_package_id=chain[0]['id'],can_revise=chain[0]['id']==p['id'],frozen_tracking_hash=p.get('tracking_snapshot',{}).get('tracking_hash'),field_accepted=False)

 @app.post('/api/projects/{id}/handovers/{package_id}/tracking')
 def action(id:str,package_id:str,body:Action):
  p=get_package(id,package_id,body.mode);root=root_id(p);rid=content_hash(dict(kind='handover_action',root=root,request=body.request_id));signature=content_hash(body.model_dump())
  try:
   old=db.record(rid)
   if old['request_signature']!=signature:raise HTTPException(409,'请求ID已用于不同处理内容')
   return old
  except KeyError:pass
  s=state(p);item=next((x for x in s['items'] if x['id']==body.item_id),None)
  if not item:raise HTTPException(404,'事项不属于本交接清单')
  if not body.actor.strip() or not body.note.strip():raise HTTPException(422,'请填写处理人和具体处理记录')
  if body.action=='SUBMIT' and not body.reference.strip():raise HTTPException(422,'请填写处理资料或厂家文档引用；引用本身不代表批准')
  status={'PROGRESS':'IN_PROGRESS','SUBMIT':'WAIT_MANUFACTURER' if item['party']=='MANUFACTURER' else 'READY_RETEST','REOPEN':'OPEN','LINK_RETEST':'RETEST_BLOCKED'}[body.action]
  reason={'PROGRESS':'已记录处理，等待补充与复测','SUBMIT':'厂家引用已登记，适用性和批准状态待确认' if item['party']=='MANUFACTURER' else '处理资料已提交，等待对应范围的新复测','REOPEN':'已重新打开，保留原处理及证据','LINK_RETEST':''}[body.action]
  evidence=None;report_hash=None
  if body.action=='LINK_RETEST':
   submit=next((x for x in item['events'] if x['action']=='SUBMIT'),None)
   latest_reset=next((x for x in item['events'] if x['action'] in ('PROGRESS','REOPEN')),None)
   if not submit or latest_reset and latest_reset['created']>submit['created']:raise HTTPException(409,'请先提交本次处理资料，再执行并关联复测')
   r=valid_report(p,body.report_id,{})
   step=r['steps'][item['step']-1]
   if body.evidence_id not in step['evidence_ids']:raise HTTPException(409,'证据不属于该事项的对应步骤')
   evidence=r['raw_evidence'][body.evidence_id]
   if evidence['created']<=submit['created'] or evidence['created']<=p['created']:raise HTTPException(409,'必须关联本次处理提交后产生的新复测证据')
   if not coverage(evidence,item['node_id']):raise HTTPException(409,'复测证据未覆盖该设备')
   status,reason=evaluate(item,r,evidence);report_hash=r['snapshot_hash']
  entry=dict(id=rid,kind='handover_action',project=root,created=now(),**body.model_dump(),package_id=p['id'],status=status,reason=reason,source='SIMULATOR' if body.mode=='SIMULATION' else 'FIELD_PREPARATION',evidence_snapshot=evidence,report_hash=report_hash,field_accepted=False,request_signature=signature)
  # Compare-and-append under SQLite lock: simultaneous updates never silently overwrite.
  with db.db() as c:
   c.execute('BEGIN IMMEDIATE')
   existing=c.execute('SELECT body FROM records WHERE id=?',(rid,)).fetchone()
   if existing:
    old=json.loads(existing['body'])
    if old['request_signature']!=signature:raise HTTPException(409,'请求ID冲突')
    return old
   logs=[json.loads(x['body']) for x in c.execute('SELECT body FROM records WHERE kind=? AND project=? ORDER BY rowid DESC',('handover_action',root))]
   last=next((x['id'] for x in logs if x['item_id']==body.item_id),'')
   if last!=body.expected_event_id:raise HTTPException(409,'该事项已有更新，请刷新后继续；原记录不会覆盖')
   c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(rid,'handover_action',root,json.dumps(entry),entry['created']))
  return entry

 @app.get('/api/projects/{id}/handovers/{package_id}/tracking/evidence/{event_id}')
 def evidence(id:str,package_id:str,event_id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p=get_package(id,package_id,mode)
  try:
   e=db.record(event_id)
   if e['kind']!='handover_action' or e['project']!=root_id(p) or e['mode']!=mode or not e.get('evidence_snapshot'):raise KeyError(event_id)
  except KeyError:raise HTTPException(404,'复测证据不属于此交接链及环境')
  return e['evidence_snapshot']

 @app.post('/api/projects/{id}/handovers/{package_id}/revisions')
 def revise(id:str,package_id:str,body:Revision):
  p=get_package(id,package_id,body.mode);root=root_id(p);rid=content_hash(dict(kind='handover_revision',root=root,request=body.request_id));signature=content_hash(dict(parent=package_id,**body.model_dump()))
  try:
   old=db.record(rid)
   if old['request_signature']!=signature:raise HTTPException(409,'新版封存请求ID冲突')
   return old
  except KeyError:pass
  if not body.acknowledged or not body.prepared_by.strip():raise HTTPException(422,'请确认遗留事项随新版保留并填写编制人')
  chain=lineage(p)
  if chain[0]['id']!=p['id']:raise HTTPException(409,'请从交接链的最新版本生成新版，避免覆盖或分叉')
  r=valid_report(p,body.report_id,{})
  if r['created']<=p['created']:raise HTTPException(409,'请先保存处理后的新SAT报告快照')
  tracking=state(p)
  if not tracking['event_ids']:raise HTTPException(409,'尚无处理记录')
  if tracking['tracking_hash']!=body.expected_tracking_hash:raise HTTPException(409,'处理清单已更新，请刷新后封存')
  plan=db.record(r['plan_id']);baseline=plan['system_context_baseline']
  if digest(baseline)!=r['identity']['model_hash'] or any(m['id'] not in r['raw_evidence'] or digest(r['raw_evidence'][m['id']])!=m['hash'] for m in r['manifest']):raise HTTPException(409,'基线或证据校验不一致')
  # Include new report gaps too; removed original tasks remain in the log, never disappear silently.
  byid={x['id']:x for x in tracking['items']}
  f={k:r[k] for k in ('incomplete','issues','historical_issues','pending')}
  for task in tasks_from(f).values():
   if task['id'] not in byid:byid[task['id']]=dict(**task,status='OPEN',status_reason='尚无处理记录',latest_event_id='',actor='',updated=None,events=[])
   else:byid[task['id']].update(task)
  tracking['items']=list(byid.values());tracking.pop('tracking_hash');tracking['tracking_hash']=content_hash(tracking)
  html=report_export(id=r['plan_id'],report_id=r['id'],format='html').body.decode('utf-8')
  components=dict(baseline=baseline,test_results=r['steps'],sat_report=r,original_evidence=r['raw_evidence'],followup=f,sat_report_html=html,tracking=tracking)
  pack=dict(version='M2-M3-HANDOVER-2',title='模拟交接包 · 非现场验收' if body.mode=='SIMULATION' else '现场交接资料草稿 · 未执行现场交接',mode=body.mode,status=p['status'],source=p['source'],plan_id=r['plan_id'],session_id=r['project'],report_id=r['id'],revision=plan['revision'],model_hash=plan['engineering_hash'],prepared_by=body.prepared_by.strip(),baseline=baseline,test_results=r['steps'],report=r,sat_report_html=html,followup=f,manifest=[dict(key=k,hash=content_hash(v)) for k,v in components.items()],sat_passed=False,field_accepted=False,signature_status='UNSIGNED',handover_boundary=p['handover_boundary'],limitations=r['limitations'],parent_package_id=p['id'],root_package_id=root,handover_version=p.get('handover_version',1)+1,tracking_snapshot=tracking)
  pack['seal_hash']=content_hash(pack)
  record=dict(id=rid,kind='handover_package',project=id,created=now(),**pack,request_signature=signature,request_id=body.request_id)
  with db.db() as c:
   c.execute('BEGIN IMMEDIATE')
   exists=c.execute('SELECT body FROM records WHERE id=?',(rid,)).fetchone()
   if exists:
    old=json.loads(exists['body'])
    if old['request_signature']!=signature:raise HTTPException(409,'新版封存请求ID冲突')
    return old
   heads=[json.loads(x['body']) for x in c.execute('SELECT body FROM records WHERE kind=? AND project=? ORDER BY rowid DESC',('handover_package',id))]
   head=next(x for x in heads if root_id(x)==root and x['mode']==body.mode)
   if head['id']!=p['id']:raise HTTPException(409,'交接链已有新版，请刷新')
   logids=[x['id'] for x in c.execute('SELECT id FROM records WHERE kind=? AND project=? ORDER BY rowid DESC',('handover_action',root))]
   if logids!=tracking['event_ids']:raise HTTPException(409,'处理记录在封存时发生变化，请刷新')
   c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(rid,'handover_package',id,json.dumps(record),record['created']))
  return record
