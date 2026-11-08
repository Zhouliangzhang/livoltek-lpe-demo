"""Immutable after-sales cases and synthetic, sequential meter-loss diagnostics."""
from typing import Literal
from copy import deepcopy
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .m1_inheritance import environment_model

Mode=Literal['SIMULATION','REAL','OFFLINE']
SCENARIOS={'configuration':('CONFIGURATION','系统配置问题','模拟iEMS地址与表计地址不一致；按匹配地址只读探测后收到有效响应','EPC / 配置维护方','核对变更授权与批准点表；确认配置修正方案后再进入通信和计量复测'),
'installation':('INSTALLATION','安装 / 接线问题','模拟RS485线路断路；端口本地测试正常，线路连续性证据定位到通信电缆','EPC / 安装维护方','由有资质人员按适用规程检查通信接线；修复后复测通信、计量及受影响联动'),
'product':('PRODUCT_SUSPECTED','疑似产品故障','供电、线路和通信配置模拟正常，表计通信接口自检异常；疑似设备接口故障，需厂家进一步确认','该设备供货方 / 厂家技术支持','提供型号、SN、固件及接口测试证据；厂家确认适用性并决定进一步检测或维修'),
'operating':('OPERATING_CONDITION','运行条件问题','模拟记录显示辅助电源被外部停用，设备无供电；不是仅凭离线报警判断产品损坏','业主 / 授权运维方','核对供电停用原因与现场作业状态；由授权人员决定恢复条件'),
'unknown':('UNCONFIRMED','根因未确认','只有通信超时，供电和线路证据缺失；不能区分配置、安装或产品故障','EPC / 厂家联合排查','补充辅助电源、线路检查及本地设备日志；不因重启暂时恢复关闭问题')}
TITLES=['保全故障证据','确认供电与影响范围','检查通信路径','核对配置及后续变化','验证根因与处理分工']

class Intake(BaseModel):
    mode:Mode
    package_id:str
    device_id:str
    reporter:str=Field(min_length=1,max_length=100)
    symptom:str=Field(min_length=1,max_length=2000)
    occurred_at:str=Field(min_length=1,max_length=100)
    scenario:Literal['configuration','installation','product','operating','unknown']='configuration'
    safe_readonly:bool=False
    request_id:str=Field(min_length=1,max_length=100)

class Step(BaseModel):
    mode:Mode
    step:int=Field(ge=1,le=5)

class Support(BaseModel):
    mode:Mode


def changes(before,after):
    def flatten(v,path=''):
        if isinstance(v,dict):
            return {k2:v2 for k,x in sorted(v.items()) if k not in ('baseline',) for k2,v2 in flatten(x,path+'/'+k).items()}
        if isinstance(v,list):
            return {k2:v2 for i,x in enumerate(v) for k2,v2 in flatten(x,path+'/'+str(next((x[k] for k in ('node_id','port_id','edge_id','asset_id','model_id','parameter_id') if isinstance(x,dict) and k in x),i))).items()}
        return {path:v}
    a,b=flatten(before),flatten(after)
    return [dict(path=k,before=a.get(k),after=b.get(k),status='待核验，不能据此认定根因') for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)]


def register_field_service(app,db):
    def package(project,pid,mode):
        try:p=db.record(pid)
        except KeyError:raise HTTPException(404,'交接包不存在')
        if p['kind']!='handover_package' or p['project']!=project or p['mode']!=mode:raise HTTPException(409,'必须选择本项目同环境交接包；模拟包不能作为现场依据')
        if digest(p['baseline'])!=p['model_hash']:raise HTTPException(409,'交接基线完整性校验失败')
        return p
    def get_case(project,cid,mode):
        try:c=db.record(cid)
        except KeyError:raise HTTPException(404,'服务单不存在')
        if c['kind']!='service_case' or c['project']!=project or c['mode']!=mode:raise HTTPException(404,'本项目当前环境没有该服务单')
        return c
    def records(c):return sorted(db.records('service_diagnosis',c['id']),key=lambda r:r['step'])

    @app.get('/api/projects/{project}/service')
    def listing(project:str,mode:Mode='SIMULATION'):
        packs=[p for p in db.records('handover_package',project) if p['mode']==mode]
        return dict(packages=[dict(id=p['id'],created=p['created'],revision=p['revision'],title=p['title'],devices=[dict(id=n['node_id'],name=n['name']) for n in p['baseline']['nodes'] if n['node_type']=='METER']) for p in packs],cases=[{k:c[k] for k in ('id','created','device_id','symptom','mode')} for c in db.records('service_case',project) if c['mode']==mode],field_connected=False)

    @app.post('/api/projects/{project}/service')
    def intake(project:str,body:Intake):
        signature=digest(body.model_dump());cid=digest(dict(kind='service-case',project=project,mode=body.mode,request=body.request_id))
        try:
            old=get_case(project,cid,body.mode)
            if old['request_signature']!=signature:raise HTTPException(409,'请求ID已用于不同服务单')
            return old
        except HTTPException as e:
            if e.status_code!=404:raise
        p=package(project,body.package_id,body.mode)
        if not body.reporter.strip() or not body.symptom.strip() or not body.safe_readonly:raise HTTPException(422,'填写报障信息并确认只读采集范围；紧急情况先按现场规程处置')
        baseline=environment_model(p['baseline'],body.mode);current=db.get(project)
        nodes={n['node_id']:n for n in baseline['nodes']};n=nodes.get(body.device_id)
        if not n or n['node_type']!='METER':raise HTTPException(422,'本阶段支持交接范围内的零馈表失联诊断')
        ports={x['port_id']:x for x in baseline['ports']};routes=[e for e in baseline['edges'] if e['edge_type']=='COMMUNICATION' and body.device_id in [ports[e['from_port_id']]['node_id'],ports[e['to_port_id']]['node_id']]]
        asset=next((a for a in baseline['device_assets'] if a['asset_id']==n.get('device_asset_id')),{})
        model=next((m for m in baseline['device_models'] if m['model_id']==asset.get('model_id')),{})
        revisions=[h for h in db.history(project) if h['revision']>p['revision']]
        body_data=dict(**body.model_dump(),request_signature=signature,baseline_hash=p['model_hash'],baseline_revision=p['revision'],package_hash=p['seal_hash'],baseline=deepcopy(baseline),current_model=deepcopy(current['model']),current_revision=current['revision'],changes=changes(p['baseline'],current['model']),subsequent_revisions=revisions,device=dict(id=body.device_id,name=n['name'],manufacturer=model.get('manufacturer'),model=model.get('model_name'),sn=asset.get('serial_number'),firmware=asset.get('firmware_version')),routes=routes,followup=deepcopy(p['followup']),historical_evidence=p['report']['manifest'],field_result=None,physical_actions=False,root_cause='UNCONFIRMED',warranty='未判定',manufacturer_basis='PENDING',source='SIMULATOR' if body.mode=='SIMULATION' else 'FIELD_PREPARATION')
        return db.add_once('service_case',project,body_data,cid)

    @app.get('/api/projects/{project}/service/{cid}')
    def detail(project:str,cid:str,mode:Mode='SIMULATION'):
        c=get_case(project,cid,mode)
        return dict(case=c,steps=records(c),support=db.records('service_support',cid),stale=db.get(project)['revision']!=c['current_revision'],field_connected=False)

    @app.post('/api/projects/{project}/service/{cid}/diagnose')
    def diagnose(project:str,cid:str,body:Step):
        c=get_case(project,cid,body.mode)
        if body.mode!='SIMULATION':raise HTTPException(503,'真实iEMS诊断接口未连接；不生成现场测量、结论或控制动作')
        if db.get(project)['revision']!=c['current_revision']:raise HTTPException(409,'工程版本已变化；保留本次记录，重新建立诊断上下文')
        rs=records(c);existing=next((r for r in rs if r['step']==body.step),None)
        if existing:return existing
        if body.step!=len(rs)+1:raise HTTPException(409,'先完成前一项检查，不能跳步确认根因')
        scenario=c['scenario'];unknown=scenario=='unknown'
        observations=[
            '保存通信超时、最后有效值和故障时间线；PCC反馈无效，不把缓存值当作当前功率。设备、端口及交接版本来自封存资料。',
            '模拟辅助电源被停用；无有效供电。需核对外部停用原因。' if scenario=='operating' else '辅助电源与本地状态证据未取得。' if unknown else '模拟辅助电源与设备本地运行正常；同控制器其他设备在线，缩小到表计及其路径。',
            '模拟线路连续性检查发现电缆断路，两端接口本地测试正常。' if scenario=='installation' else '未取得线路检查证据。' if unknown else '无供电，通信测试不具备条件，不将超时判为接口损坏。' if scenario=='operating' else '模拟链路连续性正常，未发现共享总线冲突；后续核验配置和接口。',
            '演练夹具：iEMS目标地址2、表计地址1；仅为故障注入，不写入M1。当前工程相对交接的真实保存差异另列。' if scenario=='configuration' else '当前工程差异与现场实际状态分列；演练配置匹配。' if not unknown else '未取得设备实际参数；不能凭计划值排除配置错误。',
            SCENARIOS[scenario][2]]
        result=dict(step=body.step,title=TITLES[body.step-1],observation=observations[body.step-1],status='证据不足' if unknown and body.step>1 else '模拟已记录',source='SIMULATOR',field_result=None,physical_actions=False,manufacturer_basis='PENDING',evidence=dict(case_id=cid,package_id=c['package_id'],baseline_hash=c['baseline_hash'],device_id=c['device_id'],routes=c['routes'],fixture='SIM-M4-METER-1',scenario=scenario,prior_evidence_ids=[r['id'] for r in rs]),conclusion=None)
        if body.step==5:
            category,label,reason,owner,action=SCENARIOS[scenario]
            result['conclusion']=dict(category=category,label=label,reason=reason,owner=owner,action=action,confidence='待验证' if scenario in ('product','unknown') else '模拟因果链验证满足',field_root_cause='未确认',quality_liability='未判定',warranty='未判定',restored=False,next='本阶段未执行维修或现场恢复，转处置方案与受影响范围复测')
        return db.add_once('service_diagnosis',cid,result,digest(dict(case=cid,step=body.step)))

    @app.post('/api/projects/{project}/service/{cid}/support')
    def support(project:str,cid:str,body:Support):
        c=get_case(project,cid,body.mode);rs=records(c)
        if not rs:raise HTTPException(409,'先完成证据保全；证据不足也可发起协同草稿')
        last=rs[-1]
        return db.add_once('service_support',cid,dict(mode=body.mode,source=c['source'],sent=False,status='本地协同草稿 · 未发送',device=c['device'],package_id=c['package_id'],baseline_hash=c['baseline_hash'],changes=c['changes'],evidence_ids=[r['id'] for r in rs],observations=[r['observation'] for r in rs],conclusion=last['conclusion'],questions=['请确认该型号/固件的通信点表、端子定义及只读诊断方法','请评估现有证据是否足以定位根因，并列出缺少的验证','如涉及产品缺陷，请明确进一步检测与处置方案；保修责任另行核验'],field_result=None,warranty='未判定'),digest(dict(case=cid,evidence=[r['id'] for r in rs])))
