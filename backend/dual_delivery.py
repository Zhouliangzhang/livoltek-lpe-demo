"""Two independent delivery records sharing an immutable M1/M2 baseline."""
import io,json,zipfile,csv,html,hashlib
from typing import Literal
from fastapi import HTTPException,Response
from pydantic import BaseModel,Field
from .domain import digest,SCHEMA
from jsonschema import Draft202012Validator

class DeliveryAction(BaseModel):
 mode:Literal['SIMULATION','REAL']
 action:Literal['prepare','receipt']
 actor:str=Field(min_length=1,max_length=100)
 acknowledged:bool=False

def clean(value):
 if isinstance(value,dict):return {k:('[REDACTED]' if any(x in k.lower() for x in ('password','secret','private_key','access_token','api_key')) else clean(v)) for k,v in value.items()}
 if isinstance(value,list):return [clean(v) for v in value]
 return value

def register_dual_delivery(app,db):
 detail=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/api/projects/{id}/handovers/{package_id}')
 def context(project,pid,mode):
  d=detail(id=project,package_id=pid,mode=mode);p=d['package']
  if list(Draft202012Validator(SCHEMA).iter_errors(p['baseline'])):raise HTTPException(409,'共同基线数据结构不符合Schema')
  ports={x['port_id'] for x in p['baseline']['ports']}
  if any(e['from_port_id'] not in ports or e['to_port_id'] not in ports for e in p['baseline']['edges']):raise HTTPException(409,'连接引用了不存在的端口')
  if digest(p['baseline'])!=p['model_hash']:raise HTTPException(409,'共同配置基线完整性校验失败')
  if any(x['id'] not in p['report']['raw_evidence'] or digest(p['report']['raw_evidence'][x['id']])!=x['hash'] for x in p['report']['manifest']):raise HTTPException(409,'M2证据校验失败')
  return p,d['current']
 def state(pid,audience):
  entries=db.records('delivery_'+audience,pid)
  return dict(package=next((r for r in entries if r['action']=='prepare'),None),receipt=next((r for r in entries if r['action']=='receipt'),None))
 def payload(p,audience):
  return clean(dict(baseline_id=p['id'],mode=p['mode'],audience=audience,model_hash=p['model_hash'],revision=p['revision'],m2_report_id=p['report_id'],baseline=p['baseline'],test_results=p['test_results'],sat_report=p['report'],followup=p['followup'],scope='技术资料及服务诊断上下文',field_accepted=False,remote_control_enabled=False))
 @app.get('/api/projects/{project}/handovers/{pid}/delivery')
 def overview(project:str,pid:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,current=context(project,pid,mode)
  counts=dict(incomplete=len(p['followup']['incomplete']),pending=len(p['followup']['pending']),issues=sum(not x.get('resolved') for x in p['followup']['issues']))
  return dict(baseline_id=pid,revision=p['revision'],report_id=p['report_id'],current=current,mode=mode,counts=counts,assets=len(p['baseline']['device_assets']),objects=len(p['baseline']['nodes']),connections=len(p['baseline']['edges']),evidence=len(p['report']['manifest']),epc=state(pid,'epc'),manufacturer=state(pid,'manufacturer'),platform_connected=False,field_accepted=False)
 @app.post('/api/projects/{project}/handovers/{pid}/delivery/{audience}')
 def action(project:str,pid:str,audience:Literal['epc','manufacturer'],body:DeliveryAction):
  p,current=context(project,pid,body.mode)
  if not current:raise HTTPException(409,'配置或测试已变化；请重新封存后生成交付包')
  if not body.actor.strip() or not body.acknowledged:raise HTTPException(422,'填写操作人并确认范围及环境')
  if body.action=='receipt' and body.mode!='SIMULATION':raise HTTPException(503,'正式接收认证及厂家平台未接入，不生成现场回执')
  existing=state(pid,audience)
  if existing['receipt' if body.action=='receipt' else 'package']:return existing['receipt' if body.action=='receipt' else 'package']
  data=payload(p,audience);content_hash=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
  if body.action=='receipt' and not existing['package']:raise HTTPException(409,'先生成该路径的交付包，再确认接收')
  result=dict(action=body.action,audience=audience,baseline_id=pid,mode=body.mode,simulated=body.mode=='SIMULATION',actor=body.actor.strip(),payload_hash=content_hash,field_accepted=False,remote_control_enabled=False,limitations=p['followup'],platform='SIM-RSP' if audience=='manufacturer' and body.mode=='SIMULATION' else '未接入',status=('模拟EPC已接收 · 随包限制保留' if audience=='epc' else '模拟平台已入库 · 技术依据仍待完善') if body.action=='receipt' else ('模拟技术资料包已生成' if body.mode=='SIMULATION' else '现场资料草稿已生成'),payload=data if body.action=='prepare' else None)
  if body.action=='receipt':result.update(delivery_package_id=existing['package']['id'],accepted_hash=existing['package']['payload_hash'],site_id='SIM-'+project if audience=='manufacturer' else None,validation=dict(schema=True,baseline_hash=True,evidence_hashes=True),data_scope_ack=True,service_baseline_confirmed=False)
  return db.add_once('delivery_'+audience,pid,result,digest(dict(baseline=pid,audience=audience,action=body.action,mode=body.mode)))
 @app.get('/api/projects/{project}/handovers/{pid}/delivery/{audience}/export')
 def export(project:str,pid:str,audience:Literal['epc','manufacturer'],mode:Literal['SIMULATION','REAL']='SIMULATION'):
  p,_=context(project,pid,mode);record=state(pid,audience)['package']
  if not record:raise HTTPException(409,'请先生成交付包')
  data=record['payload'];stream=io.BytesIO()
  files={'system-data.json':data,'original-evidence.json':clean(p['report']['raw_evidence']),'followup.json':clean(p['followup'])}
  text_files={}
  if audience=='epc':
   table=io.StringIO();writer=csv.writer(table);writer.writerow(['Asset','Model','SN','Firmware','Location'])
   for a in p['baseline']['device_assets']:
    vals=[a.get(k,'') for k in ('asset_id','model_id','serial_number','firmware_version','installed_location')]
    writer.writerow(["'"+str(v) if str(v).startswith(('=','+','-','@')) else v for v in vals])
   text_files['equipment.csv']='\ufeff'+table.getvalue()
   label='模拟EPC技术交付资料 · 非现场验收' if mode=='SIMULATION' else '现场技术资料草稿 · 未验收'
   text_files['technical-summary.html']='<meta charset="utf-8"><title>'+label+'</title><h1>'+label+'</h1><p>共同基线 '+html.escape(pid)+'</p><p>M1 R'+str(p['revision'])+' · M2报告 '+html.escape(p['report_id'])+'</p><p>供EPC整合进入业主交付资料。不是正式竣工图、完整EPC交付或合同验收。未完成事项见followup.json。</p><h2>测试结果</h2>'+''.join('<p>'+html.escape(str(x.get('title',''))+'：'+str(x.get('label','')))+'</p>' for x in p['test_results'])
  encoded={k:json.dumps(v,ensure_ascii=False,indent=2) for k,v in files.items()};encoded.update(text_files)
  manifest=dict(baseline_id=pid,delivery_package_id=record['id'],mode=mode,audience=audience,payload_hash=record['payload_hash'],files=[dict(name=k,hash=hashlib.sha256(v.encode("utf-8")).hexdigest()) for k,v in encoded.items()],hash_method='SHA256 of each file UTF-8 bytes',field_accepted=False)
  with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
   for k,v in encoded.items():z.writestr(k,v)
   z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
  return Response(stream.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{audience}-{mode}-{pid[:8]}.zip"'})

