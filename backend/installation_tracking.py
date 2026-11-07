"""Plan-bound installation records and bounded local photo storage."""
import base64
from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import Literal
from .domain import digest

def targets(model, task):
    nodes={n['node_id']:n for n in model['nodes']}
    ports={p['port_id']:p for p in model['ports']}
    tid=task['task_id']
    def node(n):
        return {'id':n['node_id'],'name':n['name'],'kind':'设备' if n.get('device_asset_id') else '电气结构','detail':n.get('device_asset_id') or n['node_type']}
    if tid in ('INSTALL-POWER','INSTALL-COMMS','RULE-METER-COMM'):
        kinds=['ELECTRICAL'] if tid=='INSTALL-POWER' else ['COMMUNICATION']
        result=[]
        for e in model['edges']:
            if e['edge_type'] not in kinds: continue
            a,b=ports[e['from_port_id']],ports[e['to_port_id']]
            if tid=='RULE-METER-COMM' and not any(nodes[p['node_id']]['node_type']=='METER' for p in (a,b)): continue
            result.append({'id':e['edge_id'],'name':nodes[a['node_id']]['name']+' → '+nodes[b['node_id']]['name'],'kind':'回路','detail':a['port_id']+' → '+b['port_id']})
        return result
    if tid.startswith('BOUNDARY-'):
        return [node(n) for n in model['nodes'] if n['node_id']==tid[9:]]
    if tid.startswith('INTERFACE-'):
        return [node(n) for n in model['nodes'] if n.get('device_asset_id')==tid[10:]]
    return [node(n) for n in model['nodes'] if n.get('device_asset_id') and (tid!='RULE-BESS-PREP' or n['node_type']=='BESS')]

class InstallationRecord(BaseModel):
    task_id: str
    target_id: str
    feedback_type: Literal['OBSERVATION','QUESTION','ADDITIONAL']
    recorder: str = Field(min_length=1,max_length=100)
    note: str = Field(min_length=1,max_length=4000)
    photo_ids: list[str] = Field(default_factory=list,max_length=10)

def register_tracking(app,db):
    def plan_context(id,task_id=None,target_id=None,write=False):
        try: plan=db.record(id)
        except KeyError: raise HTTPException(404,'技术指引快照不存在')
        if plan['kind']!='plan': raise HTTPException(404,'技术指引快照不存在')
        if write and digest(db.get(plan['project'])['model'])!=plan['engineering_hash']:
            raise HTTPException(409,'工程模型已变化，请更新技术指引快照；历史记录仍保留')
        if task_id is not None:
            task=next((t for t in plan['tasks'] if t['task_id']==task_id),None)
            if not task or not any(t['id']==target_id for t in targets(plan['system_context_baseline'],task)):
                raise HTTPException(422,'设备或回路不属于该技术指引')
        return plan

    @app.get('/api/plans/{id}/installation')
    def listing(id:str):
        plan=plan_context(id)
        return {'targets':{t['task_id']:targets(plan['system_context_baseline'],t) for t in plan['tasks']},
                'records':db.records('feedback',id)+[{**r,'feedback_type':'LEGACY'} for r in db.records('installation',id)]}

    @app.post('/api/plans/{id}/feedback')
    def save(id:str,body:InstallationRecord):
        plan_context(id,body.task_id,body.target_id,True)
        if not body.recorder.strip(): raise HTTPException(422,'请填写记录人')
        for pid in body.photo_ids:
            try: p=db.record(pid)
            except KeyError: raise HTTPException(422,'照片不存在')
            if p['kind']!='installation_photo' or p['project']!=id or p['task_id']!=body.task_id or p['target_id']!=body.target_id:
                raise HTTPException(422,'照片必须属于本技术指引和对象')
        if not body.note.strip(): raise HTTPException(422,'请填写现场反馈')
        return db.add('feedback',id,{**body.model_dump(),'mode':'SIMULATION','approval':'NOT_APPROVED'})

    @app.post('/api/plans/{id}/installation/photos')
    async def upload(id:str,request:Request,task_id:str,target_id:str,filename:str):
        plan_context(id,task_id,target_id,True)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>5*1024*1024: raise HTTPException(413,'单张照片不能超过 5 MB')
            chunks.append(chunk)
        data=b''.join(chunks)
        mime='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
        if not mime: raise HTTPException(415,'请上传 PNG 或 JPEG 照片')
        saved=db.add('installation_photo',id,{'task_id':task_id,'target_id':target_id,'filename':filename[:150],
            'mime':mime,'data':base64.b64encode(data).decode()})
        return {'id':saved['id'],'filename':saved['filename']}

    @app.get('/api/installation/photos/{id}')
    def photo(id:str):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'照片不存在')
        if p['kind']!='installation_photo':raise HTTPException(404,'照片不存在')
        return Response(base64.b64decode(p['data']),media_type=p['mime'],headers={'X-Content-Type-Options':'nosniff'})
