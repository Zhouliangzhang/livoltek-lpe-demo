"""Meter commissioning: isolated simulation and field evidence, dependency-bound results."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest

STEPS=['conditions','wiring','settings','identity','data']
class Result(BaseModel):
    edge_id:str
    mode:Literal['SIMULATION','FIELD']
    step:Literal['conditions','wiring','settings','identity','data']
    scenario:Literal['normal','failure']='normal'
    status:Literal['PASS','FAIL','PENDING']='PENDING'
    recorder:str=Field(default='',max_length=100)
    observation:str=Field(default='',max_length=4000)
    reference:str=Field(default='',max_length=1500)

class AutomaticRun(BaseModel):
    edge_id:str
    mode:Literal['SIMULATION','REAL']
    failure_step:Literal['conditions','wiring','settings','identity','data'] | None=None

def progress(records,edge,mode):
    result=[];parent=None;valid=True
    for step in STEPS:
        r=next((r for r in records if r['edge_id']==edge and r['mode']==mode and r['step']==step),None)
        current=bool(r and valid and r.get('predecessor_id')==parent)
        result.append({'step':step,'record':r,'current':current,'unlocked':valid})
        valid=current and r['status']=='PASS'
        parent=r['id'] if r else None
    return result

def register_commissioning(app,db):
    def context(id):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        if p['kind']!='plan':raise HTTPException(404,'调试依据不存在')
        model=p['system_context_baseline'];nodes={n['node_id']:n for n in model['nodes']};ports={v['port_id']:v for v in model['ports']}
        edges=[e for e in model['edges'] if e['edge_type']=='COMMUNICATION' and {nodes[ports[e['from_port_id']]['node_id']]['node_type'],nodes[ports[e['to_port_id']]['node_id']]['node_type']}=={'METER','EMS'}]
        return p,model,edges
    @app.get('/api/plans/{id}/commissioning')
    def listing(id:str):
        p,model,edges=context(id)
        return {'model':model,'edges':edges,'records':db.records('commissioning',id),'version':'M3-METER-1','stale':digest(db.get(p['project'])['model'])!=p['engineering_hash']}
    @app.post('/api/plans/{id}/commissioning')
    def save(id:str,body:Result):
        p,model,edges=context(id)
        if not any(e['edge_id']==body.edge_id for e in edges):raise HTTPException(422,'请选择本依据中的电表与 iEMS 通信连接')
        if digest(db.get(p['project'])['model'])!=p['engineering_hash']:raise HTTPException(409,'模型已变化，请更新调试依据')
        records=db.records('commissioning',id);state=progress(records,body.edge_id,body.mode);idx=STEPS.index(body.step)
        if not state[idx]['unlocked']:raise HTTPException(409,'前置步骤未通过或结果已失效，请先验证前置步骤')
        values=body.model_dump()
        if body.mode=='SIMULATION':
            values.update(status='FAIL' if body.scenario=='failure' else 'PASS',recorder='模拟引擎',reference='M3-METER-1 / synthetic fixture',observation=(
                {'conditions':'模拟故障 PRECONDITION_MISSING：演练现场执行条件缺失，测试未启动。','wiring':'模拟故障 PORT_MAPPING_MISMATCH：演练线序与端口映射不一致，请检查双方接线图。','settings':'模拟故障 ADDRESS_MISMATCH：演练电表地址与 iEMS 目标地址不一致，请核对通信配置。','identity':'模拟故障 METER_TIMEOUT：演练目标电表无响应，请核对供电、接线、地址与驱动。','data':'模拟故障 STALE_DATA：演练功率点数据过期，不能作为零馈控制反馈。'}[body.step] if body.scenario=='failure' else {
                'conditions':'模拟现场许可与适用文件齐备。仅用于演练流程。',
                'wiring':'模拟两端端口和线序与演练图纸一致。',
                'settings':'模拟地址匹配，双方通信参数兼容；不使用或覆盖 M1 待确认值。',
                'identity':'模拟读到 TEST-METER-01，通信状态 OK；不是现场 SN。',
                'data':'模拟读数：电表 +25.0 kW，iEMS +25.0 kW，质量 GOOD；正号为演练购电约定。'}[body.step]))
        else:
            if not body.recorder.strip() or not body.observation.strip():raise HTTPException(422,'请填写现场记录人和实际结果')
            if body.step in ['identity','data'] and not body.reference.strip():raise HTTPException(422,'请提供现场测试条件与方法引用')
            if body.status=='PASS':
                if body.step!='conditions':raise HTTPException(422,'尚未接入受控厂家判据，现场功能不能判为通过')
                if not body.reference.strip():raise HTTPException(422,'请提供 EPC 现场执行条件确认记录')
        return db.add('commissioning',id,{**values,'version':'M3-METER-1','predecessor_id':state[idx-1]['record']['id'] if idx else None,'source':'SYNTHETIC' if body.mode=='SIMULATION' else 'MANUAL_FIELD_EVIDENCE'})

    @app.post('/api/plans/{id}/commissioning/auto')
    def automatic(id:str,body:AutomaticRun):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 测试接口未接入，未执行任何现场测试')
        p,model,edges=context(id)
        configs=db.records('iems_configuration',p['project'])
        current=configs[0] if configs else None
        if not current or current['action']!='readback' or current['status']!='MATCHED' or current['model_hash']!=p['engineering_hash']:
            raise HTTPException(409,'请先在 M1 完成当前配置的模拟下发与读回一致性核对')
        results=[]
        for step in STEPS:
            result=save(id,Result(edge_id=body.edge_id,mode='SIMULATION',step=step,scenario='failure' if body.failure_step==step else 'normal'))
            results.append(result)
            if result['status']!='PASS':break
        completed=len(results)==len(STEPS) and results[-1]['status']=='PASS'
        run=db.add('commissioning_run',id,{'source':'SIMULATOR','configuration_id':current['id'],'edge_id':body.edge_id,'result_ids':[r['id'] for r in results],'completed':completed})
        return {'run_id':run['id'],'source':'SIMULATOR','configuration_id':current['id'],'results':results,'completed':completed}
