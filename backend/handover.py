"""Step14 immutable handover packages. Archival is never field acceptance."""
import io
import hashlib
import json
import zipfile
from typing import Literal
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from .domain import digest

def content_hash(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()

class Seal(BaseModel):
 session_id:str
 mode:Literal['SIMULATION','REAL']='SIMULATION'
 report_id:str
 prepared_by:str=Field(min_length=1,max_length=100)
 acknowledged:bool=False
 request_id:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


def register_handover(app,db):
 report_query=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/plans/{id}/sat-report' and 'GET' in r.methods)
 report_export=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/plans/{id}/sat-report/{report_id}/export' and 'GET' in r.methods)
 def context(id,sid,mode):
  try:
   plan=db.record(id)
   if plan['kind']!='plan':raise KeyError(id)
   session=db.record(sid) if sid else None
   if session and (session['kind']!='meter_session' or session['project']!=id):raise KeyError(sid)
  except KeyError:raise HTTPException(404,'调试依据或所属会话不存在')
  return plan,session if session and session['mode']==mode else None
 def current(pack):
  data=report_query(id=pack['plan_id'],session_id=pack['session_id'],mode=pack['mode'])
  return not data['report']['model_stale'] and pack['report']['snapshot_hash']==data['report']['snapshot_hash']
 def brief(pack):
  f=pack['followup']
  return dict(handover_version=pack.get('handover_version',1),parent_package_id=pack.get('parent_package_id'),root_package_id=pack.get('root_package_id',pack['id']),id=pack['id'],mode=pack['mode'],created=pack['created'],title=pack['title'],status=pack['status'],revision=pack['revision'],plan_id=pack['plan_id'],session_id=pack['session_id'],report_id=pack['report_id'],prepared_by=pack['prepared_by'],seal_hash=pack['seal_hash'],request_id=pack['request_id'],current=current(pack),counts=dict(incomplete=len(f['incomplete']),pending=len(f['pending']),open_issues=sum(not i['resolved'] for i in f['issues']),historical=len(f['historical_issues'])),field_accepted=False)
 def get_pack(project,package_id,mode):
  try:
   pack=db.record(package_id)
   if pack['kind']!='handover_package' or pack['project']!=project or pack['mode']!=mode:raise KeyError(package_id)
  except KeyError:raise HTTPException(404,'交接包不属于本项目及环境')
  return pack

 @app.get('/api/plans/{id}/handover')
 def preview(id:str,session_id:str='',mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,s=context(id,session_id,mode);data=report_query(id=id,session_id=s['id'] if s else '',mode=mode)
  latest=data['snapshots'][0] if data['snapshots'] else None
  ready=bool(s and latest and latest['current'] and not data['report']['model_stale'])
  return dict(report=data['report'],snapshot=latest,ready=ready,reason='当前报告与基线一致，可封存资料并携带未完成项' if ready else '请先在步骤13保存与当前配置和测试结果一致的报告快照',packages=[brief(x) for x in db.records('handover_package',p['project']) if s and x['session_id']==s['id'] and x['mode']==mode],field_accepted=False)

 @app.post('/api/plans/{id}/handover')
 def seal(id:str,body:Seal):
  p,s=context(id,body.session_id,body.mode)
  if not s:raise HTTPException(409,'请先建立对应环境的调试会话')
  rid=digest(dict(kind='handover',session=s['id'],request=body.request_id));signature=digest(body.model_dump())
  try:
   old=db.record(rid)
   if old['request_signature']!=signature:raise HTTPException(409,'封存请求ID已用于不同内容')
   return old
  except KeyError:pass
  if not body.acknowledged or not body.prepared_by.strip():raise HTTPException(422,'请填写资料编制人并确认未完成项随包移交；此确认不是验收签署')
  try:
   report=db.record(body.report_id)
   if report['kind']!='sat_report' or report['plan_id']!=id or report['project']!=s['id'] or report['mode']!=body.mode:raise KeyError(body.report_id)
  except KeyError:raise HTTPException(404,'SAT报告不属于本依据、会话及环境')
  data=report_query(id=id,session_id=s['id'],mode=body.mode)
  if data['report']['model_stale'] or report['snapshot_hash']!=data['report']['snapshot_hash']:raise HTTPException(409,'报告或配置依据已变化，请先更新测试汇总并保存新的报告快照')
  baseline=p['system_context_baseline']
  if digest(baseline)!=report['identity']['model_hash']:raise HTTPException(409,'报告与封存模型校验不一致')
  if any(m['id'] not in report['raw_evidence'] or digest(report['raw_evidence'][m['id']])!=m['hash'] for m in report['manifest']):raise HTTPException(409,'原始证据校验不一致，不能封存')
  followup={k:report[k] for k in ('incomplete','issues','historical_issues','pending')}
  # Freeze all source content. Subsequent tests or M1 edits never rewrite these files.
  html=report_export(id=id,report_id=report['id'],format='html').body.decode('utf-8')
  components=dict(baseline=baseline,test_results=report['steps'],sat_report=report,original_evidence=report['raw_evidence'],followup=followup,sat_report_html=html)
  manifest=[dict(key=k,hash=content_hash(v)) for k,v in components.items()]
  package=dict(version='M2-M3-HANDOVER-1',title='模拟交接包 · 非现场验收' if body.mode=='SIMULATION' else '现场交接资料草稿 · 未执行现场交接',mode=body.mode,status='SIMULATION_ARCHIVED' if body.mode=='SIMULATION' else 'FIELD_DRAFT_ARCHIVED',source='SIMULATOR' if body.mode=='SIMULATION' else 'FIELD_PREPARATION',plan_id=id,session_id=s['id'],report_id=report['id'],revision=p['revision'],model_hash=p['engineering_hash'],prepared_by=body.prepared_by.strip(),baseline=baseline,test_results=report['steps'],report=report,sat_report_html=html,followup=followup,manifest=manifest,sat_passed=False,field_accepted=False,signature_status='UNSIGNED',handover_boundary='仅封存并移交工作台资料；不代表现场SAT通过、设备投运许可、接收方签署或合同验收',limitations=report['limitations'])
  package['seal_hash']=content_hash(package)
  saved=db.add_once('handover_package',p['project'],dict(**package,request_signature=signature,request_id=body.request_id),rid)
  if saved['request_signature']!=signature:raise HTTPException(409,'封存请求ID冲突')
  return saved

 @app.get('/api/projects/{id}/handovers')
 def listing(id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  try:db.get(id)
  except KeyError:raise HTTPException(404,'项目不存在')
  return dict(packages=[brief(p) for p in db.records('handover_package',id) if p['mode']==mode],mode=mode,field_accepted=False)

 @app.get('/api/projects/{id}/handovers/{package_id}')
 def detail(id:str,package_id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  pack=get_pack(id,package_id,mode)
  return dict(package=pack,current=current(pack))

 @app.get('/api/projects/{id}/handovers/{package_id}/export')
 def export(id:str,package_id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p=get_pack(id,package_id,mode);stream=io.BytesIO()
  manifest={k:p[k] for k in ('id','created','title','mode','status','revision','model_hash','prepared_by','seal_hash','manifest','plan_id','session_id','report_id','signature_status','field_accepted','sat_passed','handover_boundary')}
  files={'baseline.json':p['baseline'],'test-results.json':p['test_results'],'sat-report.json':p['report'],'evidence.json':p['report']['raw_evidence'],'followup.json':p['followup'],'manifest.json':manifest}
  if 'tracking_snapshot' in p:files['tracking.json']=p['tracking_snapshot'];manifest.update(parent_package_id=p['parent_package_id'],root_package_id=p['root_package_id'],handover_version=p['handover_version'])
  with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
   for name,content in files.items():z.writestr(name,json.dumps(content,ensure_ascii=False,indent=2))
   z.writestr('sat-report.html',p['sat_report_html'])
   z.writestr('README.txt',p['title']+'\n'+p['handover_boundary']+'\n这是冻结快照；后续变更需形成新包。manifest.json保存内容校验值，非数字签名。\n')
  return Response(stream.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="Handover-{mode}-{p["id"][:12]}.zip"'})
