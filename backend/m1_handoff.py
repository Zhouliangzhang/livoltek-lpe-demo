"""Immutable M1 -> M2 evidence references; never a commissioning approval."""
import copy
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from .m1_baseline import content_hash
from .m1_delivery import baseline
from .store import now

class HandoffRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    baseline_id:str
    task_id:str=''
    environment:Literal['OFFLINE','SIMULATION','REAL']

def checked_package(db,project,package_id,environment,current=True):
    try:r=db.record(package_id)
    except KeyError:raise HTTPException(404,'配置引用包不存在')
    if r['kind']!='m1_commissioning_basis' or r['project']!=project or r['environment']!=environment:raise HTTPException(409,'引用包不属于本项目当前环境')
    if content_hash({k:v for k,v in r.items() if k!='archive_hash'})!=r['archive_hash']:raise HTTPException(409,'引用包完整性核验失败')
    if current and db.get(project)['revision']!=r['source_revision']:raise HTTPException(409,'M1 已产生新版本，请重新冻结、读回并生成引用包；原会话保留')
    return r

def prepare(db,project,req):
    b=baseline(db,project,req.baseline_id)
    if b['environment']!=req.environment:raise HTTPException(409,'冻结基线环境不一致')
    if db.get(project)['revision']!=b['source_revision']:raise HTTPException(409,'冻结基线已过期，请回步骤10更新')
    task=None
    if req.task_id:
        try:task=db.record(req.task_id)
        except KeyError:raise HTTPException(404,'下发任务不存在')
        if task['kind']!='m1_delivery_task' or task['project']!=project or task['environment']!=req.environment or task['baseline_id']!=b['id'] or task['baseline_hash']!=b['content_hash']:raise HTTPException(409,'任务与本次冻结基线不匹配')
    issues=copy.deepcopy(b['findings'])
    if not task:issues.append(dict(step=11,owner='EPC 补充',message='尚未关联下发与读回证据；现场配置状态未知',objects=[],status='PENDING'))
    elif task['status']=='BLOCKED':issues.append(dict(step=11,owner='EPC / 厂家',message='配置下发已阻断，未执行设备动作',objects=[],status='PENDING'))
    else:
        for d in task['devices']:
            if d['status']!='SIM_CANDIDATE_MATCH':issues.append(dict(step=11,owner='EPC / 厂家',message=d['reason'],objects=[d['node_id']],status=d['status']))
    issues.append(dict(step=11,owner='厂家确认',message='未取得现场实际配置生效证据；模拟读回一致不等于现场生效或调试通过',objects=[],status='PENDING'))
    for i,row in enumerate(issues):
        row['id']=f'item-{i+1}';row['category']='共同处理' if '/' in row['owner'] else '厂家确认' if '厂家' in row['owner'] else 'EPC / 项目补充'
        row['blocks']='依赖该依据的控制测试；只读诊断由 M2 按所选范围重新核验'
    return dict(environment=req.environment,baseline_id=b['id'],baseline_hash=b['content_hash'],source_revision=b['source_revision'],baseline=b,task=task,issues=issues,control_allowed=False,commissioning_passed=False,sat_passed=False,field_result=None,strategy_activation='NOT_ACTIVATED',status='OFFLINE_PREPARATION' if req.environment=='OFFLINE' else 'SIMULATION_REFERENCE' if req.environment=='SIMULATION' else 'FIELD_PREPARATION',diagnostics='M2 必须重新核验身份、路径、驱动与本次范围；移交本身不放行诊断')

def register_m1_handoff(app,db):
    @app.post('/api/projects/{project}/commissioning-basis/preview')
    def preview(project:str,body:HandoffRequest):return prepare(db,project,body)
    @app.get('/api/projects/{project}/commissioning-basis')
    def listing(project:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        return [dict(id=r['id'],created=r['created'],source_revision=r['source_revision'],status=r['status']) for r in db.records('m1_commissioning_basis',project) if r['environment']==environment]
    @app.get('/api/projects/{project}/commissioning-basis/{package_id}')
    def detail(project:str,package_id:str,environment:Literal['OFFLINE','SIMULATION','REAL']):
        r=checked_package(db,project,package_id,environment,False)
        return {**r,'stale':db.get(project)['revision']!=r['source_revision']}
    @app.post('/api/projects/{project}/commissioning-basis')
    def create(project:str,body:HandoffRequest):
        import json
        payload=prepare(db,project,body);rid='m1basis-'+content_hash(dict(project=project,**body.model_dump()))
        with db.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT revision FROM projects WHERE id=?',(project,)).fetchone()['revision']!=payload['source_revision']:raise HTTPException(409,'工程版本变化，请重新核验')
            old=c.execute('SELECT body FROM records WHERE id=?',(rid,)).fetchone()
            if old:return json.loads(old['body'])
            r=dict(id=rid,kind='m1_commissioning_basis',project=project,created=now(),**payload)
            r['archive_hash']=content_hash(r)
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(rid,r['kind'],project,json.dumps(r),r['created']))
            return r
