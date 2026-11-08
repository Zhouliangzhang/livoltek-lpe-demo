"""Sequential commissioning, immutable evidence; no physical driver is implemented."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from .domain import digest
from .session_scope import preflight, freeze
from .iems_selfcheck import selfcheck, SCENARIOS
from .meter_detail import enrich, EXTRA

ORDER=['selfcheck','route','identity','quality','reference','stability','complete']
TITLES=['iEMS 自检与控制权','连接与通信配置','目标电表识别','计量数据质量','方向倍率与独立参照','连续有效计量','结束验证与证据封存']
BASIS=[
 {'title':'端子与接线','missing':'两端实物端子、极性、线缆、屏蔽和终端要求','owner':'表计与 iEMS 厂家','layer':'L4'},
 {'title':'驱动与身份','missing':'型号 / 固件适配、身份寄存器、协议版本和错误码','owner':'表计与 iEMS 厂家','layer':'L3'},
 {'title':'计量点表','missing':'功率单位、倍率、符号、数据刷新及质量定义','owner':'表计厂家','layer':'L5'},
 {'title':'有效性判据','missing':'允许误差、最大数据年龄、连续观察窗和采样间隔','owner':'iEMS 厂家与项目授权方','layer':'L5'},
 {'title':'现场独立参照','missing':'PCC覆盖范围、CT/PT实物确认、参考仪表及同期读数记录','owner':'EPC 现场工程师','layer':'L5'}]

class Start(BaseModel):
    mode:Literal['SIMULATION','REAL']
    edge_id:str
    acknowledged:bool=False
    operator:str=Field(min_length=1,max_length=100)
    reference:str=Field(min_length=1,max_length=1000)
    scope:Literal['READ_ONLY','METER_VALIDATION']='METER_VALIDATION'
    witness_requirement:Literal['NONE','EPC_WITNESS','JOINT_WITNESS']='NONE'
    witness_name:str=Field(default='',max_length=200)
    installation_ref:str=Field(default='',max_length=1000)
    energization_ref:str=Field(default='',max_length=1000)
    authorization_ref:str=Field(default='',max_length=1000)
    procedure_ref:str=Field(default='',max_length=1000)
class Run(BaseModel):
    step:Literal['selfcheck','route','identity','quality','reference','stability','complete']
    scenario:str=Field(default='normal',max_length=60)
    request_id:str|None=Field(default=None,min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')

ALLOWED={'selfcheck':SCENARIOS,'route':['normal'],'identity':['normal','timeout','wrong_identity'],'quality':['normal','stale','frozen','bad','scale'],'reference':['normal','reverse','scale'],'stability':['normal','gap','stale'],'complete':['normal']}

for step,scenarios in EXTRA.items():ALLOWED[step]+=scenarios

def states(records):
    output=[];parent=None;valid=True
    for key,title in zip(ORDER,TITLES):
        r=next((r for r in records if r['step']==key),None)
        current=bool(r and valid and r['predecessor_id']==parent)
        output.append(dict(key=key,title=title,record=r,current=current,unlocked=valid))
        valid=bool(current and r['status']=='PASS');parent=r['id'] if r else None
    return output

def simulate(step,scenario,route):
    checks=[];samples=[]
    def check(label,actual,expected,passed=True):
        checks.append(dict(label=label,actual=str(actual),expected=expected,passed=passed))
    if step=='selfcheck':
        for label in ['模拟引擎与日志','演练时钟','单一指令所有者']:
            check(label,'演练夹具就绪','独立模拟环境；不是现场自检')
    elif step=='route':
        check('M1 通信路径',route['edge_id']+' / '+route['domain'],'模型中存在电表与 iEMS 直接通信连接')
        check('通信协议与地址','演练驱动 / 地址 1','模拟专用；不覆盖 M1 待确认参数')
        check('实物接线','模拟前提已声明','仅演练假定；不证明端子、极性或实物接线正确')
    elif step=='identity':
        check('通信应答','无响应' if scenario=='timeout' else '收到模拟应答','必须收到有效应答',scenario!='timeout')
        check('目标身份','其他设备' if scenario=='wrong_identity' else 'SIM-METER-001','模拟身份 SIM-METER-001；非现场 SN',scenario not in ['wrong_identity','timeout'])
    elif step in ['quality','stability']:
        for t in range(7):
            power=25000+t*10 if scenario=='scale' else 25+t*0.01
            source=t-10 if scenario=='stale' else 0 if scenario=='frozen' else t
            quality='MISSING' if scenario=='gap' and t==3 else 'BAD' if scenario=='bad' else 'GOOD'
            samples.append(dict(time=t,source_time=source,age=t-source,sequence=0 if scenario=='frozen' else t+1,quality=quality,meter_kw=None if quality=='MISSING' else round(power,2),iems_kw=None if quality=='MISSING' else round(power,2),voltage_v=400,frequency_hz=50))
        check('采样完整性',f"{sum(s['quality']!='MISSING' for s in samples)} / 7 个样本",'演练：每秒1点，不允许缺测',all(s['quality']!='MISSING' for s in samples))
        check('数据质量',','.join(sorted({s['quality'] for s in samples})),'演练：全部 GOOD',all(s['quality']=='GOOD' for s in samples))
        check('数据新鲜度',f"最大年龄 {max(s['age'] for s in samples)} s",'演练：数据年龄不超过2秒',all(0<=s['age']<=2 for s in samples))
        check('更新连续性',f"{len({s['sequence'] for s in samples})} 个不同序号",'演练：源序号持续更新；恒定功率本身不是冻结',len({s['sequence'] for s in samples})==7)
        check('单位与合理范围',f"{samples[-1]['meter_kw']} kW",'演练夹具：0至100 kW，非现场额定范围',all(s['meter_kw'] is None or 0<=s['meter_kw']<=100 for s in samples))
        if step=='stability':check('连续观察', '6秒完整窗口' if all(c['passed'] for c in checks) else '窗口中断，未形成连续证据','演练：6秒连续有效；真实窗口待厂家确认',all(c['passed'] for c in checks))
    elif step=='reference':
        measured=-25 if scenario=='reverse' else 250 if scenario=='scale' else 25
        check('独立参照来源','SIM-REFERENCE-001 / 25.0 kW 购电','独立生成的演练参照；不是现场仪表或实测记录')
        check('PCC方向',f'{measured} kW','演练：正号为购电，参考值+25 kW',measured>0)
        check('倍率与偏差',f'{abs(measured-25):.2f} kW','演练：相对独立参考偏差≤0.5 kW',abs(measured-25)<=0.5)
        check('现场映射确认','演练假设 CT/PT 1:1','实际 CT/PT 铭牌、计量覆盖范围及位置仍需 EPC 确认')
    else:
        check('退出状态','仅执行合成读取，无设备写入','没有现场动作或遗留强制值')
        check('证据范围','仅零馈表与 iEMS 模拟验证','不证明系统零馈控制有效，不形成 SAT 结论')
    passed=all(c['passed'] for c in checks)
    return dict(status='PASS' if passed else 'FAIL',checks=checks,samples=samples,code='SIM_CRITERIA_MET' if passed else {'timeout':'METER_TIMEOUT','wrong_identity':'IDENTITY_MISMATCH','stale':'DATA_STALE','frozen':'DATA_FROZEN','bad':'BAD_QUALITY','scale':'SCALING_MISMATCH','reverse':'DIRECTION_MISMATCH','gap':'SAMPLE_GAP'}[scenario],source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',criteria_version='SIM-METER-SEQ-1',exit_state='NO_PHYSICAL_ACTION')

def register_meter_workflow(app,db):
    def context(id):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        if p['kind']!='plan':raise HTTPException(404,'调试依据不存在')
        m=p['system_context_baseline'];nodes={n['node_id']:n for n in m['nodes']};ports={x['port_id']:x for x in m['ports']};routes=[]
        for e in m['edges']:
            a,b=ports[e['from_port_id']],ports[e['to_port_id']]
            if e['edge_type']!='COMMUNICATION' or {nodes[a['node_id']]['node_type'],nodes[b['node_id']]['node_type']}!={'METER','EMS'}:continue
            meter,ems=(a,b) if nodes[a['node_id']]['node_type']=='METER' else (b,a)
            routes.append(dict(edge_id=e['edge_id'],meter=meter,ems=ems,domain=meter['domain']))
        return p,m,routes,digest(db.get(p['project'])['model'])!=p['engineering_hash']
    @app.get('/api/plans/{id}/meter-workflow')
    def listing(id:str,mode:Literal['SIMULATION','REAL']='SIMULATION'):
        p,m,routes,stale=context(id)
        sessions=[s for s in db.records('meter_session',id) if s['mode']==mode]
        attempts={s['id']:db.records('meter_run',s['id']) for s in sessions}
        results={sid:states(records) for sid,records in attempts.items()}
        return dict(model=m,routes=routes,stale=stale,sessions=sessions,progress=results,attempts=attempts,basis=BASIS,preflights={r['edge_id']:preflight(m,r) for r in routes},real_connected=False,version='M2-SEQUENCE-1')
    @app.post('/api/plans/{id}/meter-workflow')
    def start(id:str,body:Start):
        p,m,routes,stale=context(id)
        if stale:raise HTTPException(409,'模型已变化，请先更新调试依据')
        if not body.acknowledged or not body.operator.strip() or not body.reference.strip():raise HTTPException(422,'请填写责任人、条件依据并确认本次范围')
        if body.witness_requirement!='NONE' and not body.witness_name.strip():raise HTTPException(422,'请填写见证人或见证组织')
        route=next((r for r in routes if r['edge_id']==body.edge_id),None)
        if route is None:raise HTTPException(422,'缺少零馈表与 iEMS 直接通信连接，请在 M1 补充')
        if route['meter']['domain']!=route['ems']['domain']:raise HTTPException(422,'两端通信域不一致，请在 M1 修正')
        return db.add('meter_session',id,{**body.model_dump(), **freeze(p,m,route,body), 'model_hash':p['engineering_hash'],'revision':p['revision'],'route':route,'source':'SIMULATOR' if body.mode=='SIMULATION' else 'FIELD_PREPARATION','binding_status':'SIMULATED' if body.mode=='SIMULATION' else 'UNVERIFIED','manufacturer_basis':'PENDING','version':'M2-SEQUENCE-1'})
    def run_id(session_id,request_id):
        return digest({'session':session_id,'request':request_id})
    @app.get('/api/plans/{id}/meter-workflow/{session_id}/runs/{request_id}')
    def query_run(id:str,session_id:str,request_id:str):
        try:
            session=db.record(session_id)
            if session['kind']!='meter_session' or session['project']!=id:raise KeyError(session_id)
            return db.record(run_id(session_id,request_id))
        except KeyError:raise HTTPException(404,'原运行尚无持久化记录；未自动重新启动')
    @app.post('/api/plans/{id}/meter-workflow/{session_id}/run')
    def run(id:str,session_id:str,body:Run):
        p,m,routes,stale=context(id)
        try:s=db.record(session_id)
        except KeyError:raise HTTPException(404,'调试会话不存在')
        if s['kind']!='meter_session' or s['project']!=id:raise HTTPException(404,'调试会话不属于当前项目依据')
        if body.request_id:
            try:previous=db.record(run_id(session_id,body.request_id))
            except KeyError:previous=None
            if previous:
                if previous['step']!=body.step or previous['scenario']!=body.scenario:raise HTTPException(409,'该运行ID已用于不同动作')
                return previous
        if stale or s['model_hash']!=p['engineering_hash']:raise HTTPException(409,'配置基线已变化，需重新验证')
        if s['mode']!='SIMULATION':raise HTTPException(503,'真实 iEMS 未连接，厂家判据未批准；未执行现场测试')
        if s.get('scope')=='READ_ONLY' and body.step in ['reference','stability','complete']:raise HTTPException(409,'本次为只读诊断范围；完整计量验证需重新建立对应范围的会话')
        if body.scenario not in ALLOWED[body.step]:raise HTTPException(422,'此故障场景不适用于本步骤')
        progress=states(db.records('meter_run',s['id']));idx=ORDER.index(body.step)
        if not progress[idx]['unlocked']:raise HTTPException(409,'前置步骤未通过或已失效，请按调试顺序执行')
        result=selfcheck(s,body.scenario) if body.step=='selfcheck' else simulate(body.step,'normal' if body.scenario in EXTRA.get(body.step,[]) else body.scenario,s['route'])
        if body.step!='selfcheck':result=enrich(result,body.step,body.scenario,m,s['route'])
        if body.step=='complete':result['evidence_ids']=[state['record']['id'] for state in progress[:idx]]
        record={**result,**body.model_dump(),'model_hash':s['model_hash'],'edge_id':s['edge_id'],'predecessor_id':progress[idx-1]['record']['id'] if idx else None}
        if body.request_id:
            saved=db.add_once('meter_run',s['id'],record,run_id(s['id'],body.request_id))
            if saved['step']!=body.step or saved['scenario']!=body.scenario:raise HTTPException(409,'该运行ID已用于不同动作，请查询原运行或明确重新执行')
            return saved
        return db.add('meter_run',s['id'],record)
