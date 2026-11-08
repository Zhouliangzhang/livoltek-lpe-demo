"""Deterministic steady-state coordination fixtures; never sends hardware commands."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel
from .domain import digest
from .fleet import groups_for

SCENARIOS={'surplus':'光伏富余 · 储能吸收','charge_limit':'充电受限 · 光伏限功率','deficit':'负载增加 · 储能放电','meter_stale':'计量失效 · 阻断控制','pv_reject':'光伏拒绝限功率','bess_reject':'储能拒绝充电'}
class Command(BaseModel):
    mode:Literal['SIMULATION','REAL']
    scenario:Literal['surplus','charge_limit','deficit','meter_stale','pv_reject','bess_reject']
    fault_node:str|None=None

def participants(model):
    groups=groups_for(model)
    return {'pv':[d for g in groups if g['kind']=='PV_INVERTER' for d in g['devices']],
            'bess':[d for g in groups if g['kind']=='BESS' for d in g['devices']],
            'ems':[{'node_id':n['node_id'],'name':n['name']} for n in model['nodes'] if n['node_type']=='EMS'],
            'meters':[{'node_id':n['node_id'],'name':n['name']} for n in model['nodes'] if n['node_type']=='METER']}

def simulate(model,body):
    p=participants(model);ports={x['port_id']:x for x in model['ports']}
    issues=[];steps=[]
    def issue(node,code,reason,layer='L5'):
        issues.append({'node_id':node,'code':code,'reason':reason,'layer':layer})
    if len(p['ems'])!=1:issue(model['project']['project_id'],'EMS_SCOPE_UNCONFIRMED','此演练要求一个明确的 iEMS 控制域，请确认系统控制器归属。','L3')
    ems=p['ems'][0]['node_id'] if len(p['ems'])==1 else None
    if not p['pv'] or not p['bess']:issue(ems or model['project']['project_id'],'DEVICE_SCOPE_MISSING','缺少光伏或储能对象。','L3')
    meter_edges=[e for e in model['edges'] if e['edge_type']=='COMMUNICATION' and {ports[e['from_port_id']]['node_id'],ports[e['to_port_id']]['node_id']}=={ems,p['meters'][0]['node_id']}] if len(p['meters'])==1 else []
    meter=p['meters'][0]['node_id'] if len(p['meters'])==1 else model['project']['project_id']
    if not meter_edges:issue(meter,'METER_ROUTE_UNCONFIRMED','需唯一零馈表及其到该 iEMS 的通信连接。','L4')
    for d in p['pv']+p['bess']:
        if not d['route'] or ports[d['route'][-1]['to']]['node_id']!=ems:issue(d['node_id'],'DEVICE_ROUTE_MISSING','缺少到同一 iEMS 的通信路径。','L4')
        if not d['controls']:issue(d['node_id'],'CONTROL_ROUTE_MISSING','缺少该设备与 iEMS 的控制关系。','L4')
    base={'scenario':body.scenario,'title':SCENARIOS[body.scenario],'source':'SIMULATOR','mode':'SIMULATION','version':'M2-SYSTEM-1','manufacturer_basis':'PENDING','field_result':None,'issues':issues,'steps':steps,'devices':[],'flow':None,'ems':ems,'meter':meter}
    if issues:
        steps.append({'label':'模型与控制域核对','status':'BLOCKED','detail':'未执行联动控制，请处理列出的 M1 缺项。'})
        return {**base,'status':'BLOCKED'}
    steps.append({'label':'模型与控制域核对','status':'PASS','detail':f'{meter} → {ems} → {len(p["pv"])} 台光伏 + {len(p["bess"])} 台储能；核对保存的逻辑连接。'})
    if body.scenario=='meter_stale':
        issue(meter,'METER_DATA_STALE','注入零馈表时间戳过期：iEMS 不再将该样本用于本次控制决策。现场失联策略仍待厂家确认。')
        steps.append({'label':'零馈表反馈有效性','status':'FAIL','detail':'合成数据质量 STALE；未生成光伏 / 储能测试指令。'})
        return {**base,'status':'FAIL'}
    steps.append({'label':'零馈表反馈有效性','status':'PASS','detail':'合成计量质量 GOOD；购电为正、馈网为负。非现场 CT 极性确认。'})
    deficit=body.scenario=='deficit';limited=body.scenario in ('charge_limit','pv_reject')
    load=1600.0 if deficit else 800.0
    available=min(900.0 if deficit else 1250.0,125.0*len(p['pv']))
    charge=0.0 if deficit or limited else min(max(0,available-load+25),30.0*len(p['bess']))
    discharge=min(max(0,load-available-25),70.0*len(p['bess'])) if deficit else 0.0
    target_pv=min(available,max(0,load+charge-discharge-25))
    base['fixture']={'load':load,'pv_available':available,'import_target':25,'tolerance':1,'charge_cap':0 if limited else 30*len(p['bess']),'discharge_cap':70*len(p['bess']),'note':'独立稳态演练参数（kW），不是 M1 批准值或厂家性能判据；不验证动态响应、保护、SOC 实际边界或 CT 极性。'}
    steps.append({'label':'iEMS 分配策略','status':'PASS','detail':f'演练目标购电 25 kW：光伏 {target_pv:g} kW；储能充电 {charge:g} kW / 放电 {discharge:g} kW。'})
    fault=body.fault_node
    targets=p['pv'] if body.scenario=='pv_reject' else p['bess'] if body.scenario=='bess_reject' else []
    if targets:
        fault=fault or targets[0]['node_id']
        if fault not in [d['node_id'] for d in targets]:raise HTTPException(422,'故障设备不属于此场景的目标设备类型')
    elif fault:raise HTTPException(422,'此场景不接受设备故障目标')
    for kind,ds,total in [('PV',p['pv'],target_pv),('BESS',p['bess'],charge if charge else -discharge)]:
        for d in ds:
            command=total/len(ds);actual=command
            failed=d['node_id']==fault
            if failed:
                actual=available/len(ds) if kind=='PV' else 0.0
                issue(d['node_id'],'PV_LIMIT_REJECTED' if kind=='PV' else 'BESS_CHARGE_REJECTED','注入指令拒绝：光伏保持原输出，导致馈网。需核对远程控制权限、功率单位与指令确认点。' if kind=='PV' else '注入充电拒绝：储能未吸收分配功率，导致馈网。需核对控制权限、BMS 充电许可与 SOC 边界。')
            base['devices'].append({'node_id':d['node_id'],'name':d['name'],'kind':kind,'command':round(command,3),'actual':round(actual,3),'status':'FAIL' if failed else 'PASS','route':d['route'],'control_edges':d['controls']})
    devices=base['devices'];pv=sum(d['actual'] for d in devices if d['kind']=='PV');bess=sum(d['actual'] for d in devices if d['kind']=='BESS')
    grid=round(load+bess-pv,3)
    base['flow']={'load':load,'pv':round(pv,3),'charge':round(max(0,bess),3),'discharge':round(max(0,-bess),3),'grid':grid,'initial_grid':load-available,'target':25}
    steps.append({'label':'逐台指令与反馈','status':'FAIL' if issues else 'PASS','detail':f'记录 {len(devices)} 台设备的指令及合成反馈；储能正数为充电，负数为放电。'})
    ok=not issues and abs(grid-25)<=1
    if not ok and not issues:issue(ems,'IMPORT_TARGET_UNREACHED','演练可用功率不足或分配不匹配，未达到目标；请核对设备范围和设置。')
    steps.append({'label':'并网点闭环核对','status':'PASS' if ok else 'FAIL','detail':f'负载 + 充电 − 光伏 − 放电 = {grid:g} kW；演练目标 25 ± 1 kW，馈网（负值）判为异常。'})
    steps.append({'label':'结束演练','status':'PASS','detail':'清除本次合成指令；未向现场下发，不代表真实控制器已恢复。'})
    return {**base,'status':'PASS' if ok else 'FAIL'}

def register_system_tests(app,db):
    def context(id):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        if p['kind']!='plan':raise HTTPException(404,'调试依据不存在')
        return p
    @app.get('/api/plans/{id}/system-tests')
    def listing(id:str):
        p=context(id)
        return {'participants':participants(p['system_context_baseline']),'records':db.records('system_test',id),'scenarios':SCENARIOS,'stale':digest(db.get(p['project'])['model'])!=p['engineering_hash']}
    @app.post('/api/plans/{id}/system-tests')
    def execute(id:str,body:Command):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 联动测试接口未接入，未执行现场控制')
        p=context(id)
        if digest(db.get(p['project'])['model'])!=p['engineering_hash']:raise HTTPException(409,'模型已变化，请更新调试依据')
        configs=db.records('iems_configuration',p['project']);cfg=configs[0] if configs else None
        if not cfg or cfg['action']!='readback' or cfg['status']!='MATCHED' or cfg['model_hash']!=p['engineering_hash']:raise HTTPException(409,'请先在 M1 完成当前配置的模拟下发与读回一致性核对')
        result=simulate(p['system_context_baseline'],body)
        return db.add('system_test',id,{**result,'model_hash':p['engineering_hash'],'configuration_id':cfg['id']})
