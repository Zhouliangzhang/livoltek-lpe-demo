"""Explicit simulator configuration delivery; real iEMS adapter is not connected."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel
from .domain import digest
class ConfigurationCommand(BaseModel):
    mode:Literal['SIMULATION','REAL']
    revision:int
    action:Literal['send','readback']
    mismatch:bool=False

def register_workbench(app,db):
    @app.get('/api/projects/{id}/iems-configuration')
    def state(id:str):
        try:project=db.get(id)
        except KeyError:raise HTTPException(404,'项目不存在')
        records=db.records('iems_configuration',id)
        return {'records':records,'revision':project['revision'],'model_hash':digest(project['model']),'real_connected':False}
    @app.post('/api/projects/{id}/iems-configuration')
    def command(id:str,body:ConfigurationCommand):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 尚未接入，未下发任何配置')
        try:p=db.get(id)
        except KeyError:raise HTTPException(404,'项目不存在')
        if p['revision']!=body.revision:raise HTTPException(409,'配置版本已变化，请重新加载')
        records=db.records('iems_configuration',id)
        sent=next((r for r in records if r['action']=='send'),None)
        model_hash=digest(p['model'])
        if body.action=='send':
            return db.add('iems_configuration',id,{'mode':'SIMULATION','action':'send','revision':p['revision'],'model_hash':model_hash,'status':'SENT','source':'SIMULATOR','snapshot':p['model']})
        if not sent or sent['model_hash']!=model_hash:raise HTTPException(409,'请先下发当前配置到模拟 iEMS')
        return db.add('iems_configuration',id,{'mode':'SIMULATION','action':'readback','revision':p['revision'],'model_hash':model_hash,'send_id':sent['id'],'status':'MISMATCH' if body.mismatch else 'MATCHED','source':'SIMULATOR','note':'模拟读回存在差异，禁止进入自动测试' if body.mismatch else '模拟读回与下发快照一致；不代表现场生效'})
