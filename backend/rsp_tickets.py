"""Local RSP ticket simulation; never connects to a manufacturer platform."""
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Literal
from .domain import digest
from .field_service import Intake

class TicketAction(BaseModel):
 mode:Literal['SIMULATION','REAL','OFFLINE']
 package_id:str=''

def register_rsp_tickets(app,db):
 intake=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/api/projects/{project}/service' and 'POST' in getattr(r,'methods',set()))
 def eligible(project,mode):
  result=[]
  for p in db.records('handover_package',project):
   if p['mode']!=mode:continue
   receipt=next((r for r in db.records('delivery_manufacturer',p['id']) if r['action']=='receipt' and r['mode']==mode),None)
   if receipt:result.append(dict(id=p['id'],revision=p['revision'],receipt_id=receipt['id'],site_id=receipt['site_id']))
  return result
 @app.get('/api/projects/{project}/rsp-tickets')
 def listing(project:str,mode:str='SIMULATION'):
  return dict(packages=eligible(project,mode),tickets=[dict(**t,case_id=next((c['id'] for c in db.records('service_case',project) if c['request_id']==t['id'] and c['mode']==mode),None)) for t in db.records('rsp_ticket',project) if t['mode']==mode],platform_connected=False)
 @app.post('/api/projects/{project}/rsp-tickets')
 def create(project:str,body:TicketAction):
  if body.mode!='SIMULATION':raise HTTPException(503,'真实RSP未接入；不能生成现场工单')
  p=next((p for p in eligible(project,body.mode) if p['id']==body.package_id),None)
  if not p:raise HTTPException(409,'先完成本项目同环境的厂家服务建档模拟回执')
  pack=db.record(p['id']);meter=next((n for n in pack['baseline']['nodes'] if n['node_type']=='METER'),None)
  if not meter:raise HTTPException(409,'交接范围内没有零馈表')
  return db.add_once('rsp_ticket',project,dict(mode=body.mode,package_id=p['id'],receipt_id=p['receipt_id'],site_id=p['site_id'],device_id=meter['node_id'],symptom='模拟RSP报障：零馈表失联，PCC功率反馈无效',source='SIM-RSP',scenario='configuration',field_result=None),digest(dict(project=project,package=p['id'],fixture='RSP-METER-1')))
 @app.post('/api/projects/{project}/rsp-tickets/{tid}/accept')
 def accept(project:str,tid:str,body:TicketAction):
  try:t=db.record(tid)
  except KeyError:raise HTTPException(404,'工单不存在')
  if t['kind']!='rsp_ticket' or t['project']!=project or t['mode']!=body.mode:raise HTTPException(404,'当前项目和环境没有该工单')
  if body.mode!='SIMULATION':raise HTTPException(503,'真实RSP身份认证与派单接口未接入')
  c=intake(project,Intake(mode=body.mode,package_id=t['package_id'],device_id=t['device_id'],reporter='模拟RSP派单',symptom=t['symptom'],occurred_at=t['created'],scenario=t['scenario'],safe_readonly=True,request_id=tid))
  db.add_once('rsp_ticket_link',c['id'],dict(ticket_id=tid,receipt_id=t['receipt_id'],site_id=t['site_id'],mode=body.mode,source='SIM-RSP',external_sent=False),digest(dict(ticket=tid,case=c['id'])))
  return c
