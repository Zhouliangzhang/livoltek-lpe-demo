from datetime import datetime
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field

class Demand(BaseModel):
    revision:int
    expected_id:str|None=None
    epc_contact:str=Field(min_length=1,max_length=150)
    requested_time:datetime
    support_mode:Literal['REMOTE','SITE','DOCUMENT']
    target_ids:list[str]=Field(min_length=1,max_length=200)
    subject:str=Field(min_length=1,max_length=200)
    details:str=Field(min_length=1,max_length=4000)
class Arrangement(BaseModel):
    request_id:str
    decision:Literal['CONFIRMED','NEEDS_INFO']
    manufacturer_contact:str=Field(min_length=1,max_length=150)
    agreed_time:datetime|None=None
    support_mode:Literal['REMOTE','SITE','DOCUMENT']
    note:str=Field(min_length=1,max_length=4000)

def register_coordination(app,db):
    def current(id):
        try:return db.get(id)
        except KeyError:raise HTTPException(404,'项目不存在')
    @app.get('/api/projects/{id}/coordination')
    def get(id:str):
        current(id)
        return {'requests':db.records('coordination_request',id),'arrangements':db.records('coordination_arrangement',id),'mode':'SIMULATION'}
    @app.post('/api/projects/{id}/coordination/requests')
    def request(id:str,body:Demand):
        p=current(id);records=db.records('coordination_request',id)
        if p['revision']!=body.revision:raise HTTPException(409,'工程版本已变化，请重新载入')
        if (records[0]['id'] if records else None)!=body.expected_id:raise HTTPException(409,'协同需求已更新，请刷新后重试')
        valid={n['node_id'] for n in p['model']['nodes']}|{e['edge_id'] for e in p['model']['edges']}
        if not set(body.target_ids)<=valid:raise HTTPException(422,'协同对象不属于本项目')
        if not all(v.strip() for v in (body.epc_contact,body.subject,body.details)):raise HTTPException(422,'请完整填写需求')
        return db.add('coordination_request',id,{**body.model_dump(mode='json',exclude={'expected_id'}),'version':len(records)+1,'mode':'SIMULATION'})
    @app.post('/api/projects/{id}/coordination/arrangements')
    def arrange(id:str,body:Arrangement):
        p=current(id);requests=db.records('coordination_request',id)
        if not requests or requests[0]['id']!=body.request_id or requests[0]['revision']!=p['revision']:
            raise HTTPException(409,'需求或工程版本已变化，请由 EPC 更新需求后再确认')
        if not body.manufacturer_contact.strip() or not body.note.strip():raise HTTPException(422,'请填写厂家联系人和安排说明')
        if body.decision=='CONFIRMED' and not body.agreed_time:raise HTTPException(422,'确认安排必须填写协同时间')
        return db.add('coordination_arrangement',id,{**body.model_dump(mode='json'),'mode':'SIMULATION','scope':'TECHNICAL_SUPPORT_ONLY'})
