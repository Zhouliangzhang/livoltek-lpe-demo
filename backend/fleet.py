"""Per-device simulator results, derived from the saved M1 baseline. No hardware I/O."""
from collections import deque
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel
from .domain import digest

class FleetCommand(BaseModel):
    mode: Literal['SIMULATION','REAL']
    node_id: str
    failure_step: str | None = None

def groups_for(model):
    nodes={n['node_id']:n for n in model['nodes']}
    ports={p['port_id']:p for p in model['ports']}
    assets={a['asset_id']:a for a in model['device_assets']}
    models={m['model_id']:m for m in model['device_models']}
    ems={n['node_id'] for n in model['nodes'] if n['node_type']=='EMS'}
    adjacency={}
    for e in model['edges']:
        a,b=ports[e['from_port_id']],ports[e['to_port_id']]
        if e['edge_type']=='COMMUNICATION' and a['domain']==b['domain']:
            for x,y in [(a,b),(b,a)]:
                adjacency.setdefault(x['node_id'],[]).append((y['node_id'],x,y,e['edge_id']))
    def route(start):
        queue=deque([(start,[],None)]);seen=set()
        while queue:
            node,path,domain=queue.popleft()
            if (node,domain) in seen:continue
            seen.add((node,domain))
            if node in ems:return path
            if node!=start and nodes[node]['node_type'] not in ('OTHER','JUNCTION'):continue
            for target,a,b,eid in adjacency.get(node,[]):
                if domain is None or domain==a['domain']:
                    queue.append((target,path+[{'edge_id':eid,'from':a['port_id'],'to':b['port_id'],'domain':a['domain']}],a['domain']))
        return []
    groups={}
    for n in model['nodes']:
        if n['node_type'] not in ('PV_INVERTER','BESS'):continue
        asset=assets.get(n.get('device_asset_id'),{});dm=models.get(asset.get('model_id'),{})
        key=n['node_type']+':'+dm.get('model_id',n['node_id'])
        group=groups.setdefault(key,{'id':key,'kind':n['node_type'],'name':'光伏逆变器' if n['node_type']=='PV_INVERTER' else '储能系统','model':dm.get('model_name','型号待补'),'manufacturer':dm.get('manufacturer','厂家待补'),'version':dm.get('master_data_version','待确认'),'devices':[]})
        path=route(n['node_id'])
        controller=ports[path[-1]['to']]['node_id'] if path else None
        controls=[e for e in model['edges'] if e['edge_type']=='CONTROL' and ports[e['from_port_id']]['node_id']==controller and ports[e['to_port_id']]['node_id']==n['node_id']]
        group['devices'].append({'node_id':n['node_id'],'name':n['name'],'sn':asset.get('serial_number'),'route':path,'controls':controls})
    return list(groups.values())

def register_fleet(app,db):
    def context(id):
        try:p=db.record(id)
        except KeyError:raise HTTPException(404,'调试依据不存在')
        if p['kind']!='plan':raise HTTPException(404,'调试依据不存在')
        return p,groups_for(p['system_context_baseline'])

    @app.get('/api/plans/{id}/fleet')
    def listing(id:str):
        p,groups=context(id)
        return {'groups':groups,'records':db.records('fleet_test',id),'stale':digest(db.get(p['project'])['model'])!=p['engineering_hash'],'real_connected':False}

    @app.post('/api/plans/{id}/fleet')
    def execute(id:str,body:FleetCommand):
        if body.mode=='REAL':raise HTTPException(503,'真实 iEMS 未接入：未执行通信或控制操作')
        p,groups=context(id)
        if digest(db.get(p['project'])['model'])!=p['engineering_hash']:raise HTTPException(409,'模型已变化，请更新调试依据')
        configs=db.records('iems_configuration',p['project']);config=configs[0] if configs else None
        if not config or config['action']!='readback' or config['status']!='MATCHED' or config['model_hash']!=p['engineering_hash']:
            raise HTTPException(409,'请先在 M1 完成当前配置的模拟下发与读回一致性核对')
        found=next(((g,d) for g in groups for d in g['devices'] if d['node_id']==body.node_id),None)
        if not found:raise HTTPException(422,'设备不在当前光伏 / 储能调试依据中')
        group,device=found
        specs=[('communication','通信连通','合成链路响应正常；不是现场连通性结果。'),('identity','设备识别','模拟驱动返回目标设备标识；不代表已核对现场 SN。'),('data','数据有效性','合成功率与状态质量 GOOD、时间戳新鲜；无现场测量。')]
        if group['kind']=='PV_INVERTER':
            specs += [('limit','光伏限功率','模拟限功率指令 → 合成确认与反馈一致；未向设备下发。')]
        else:
            specs += [('charge','储能充电','模拟充电指令 → 合成充电状态与方向一致；无实际充电。'),('discharge','储能放电','模拟放电指令 → 合成放电状态与方向一致；无实际放电。')]
        specs += [('restore','控制恢复','模拟撤销测试指令并恢复演练初始状态；无现场操作。')]
        if body.failure_step and body.failure_step not in [s[0] for s in specs]:raise HTTPException(422,'故障步骤不适用于该设备')
        results=[]
        for key,label,observation in specs:
            status='PASS';code='SIM_OK'
            if key=='communication' and not device['route']:
                status='BLOCKED';code='M1_ROUTE_MISSING';observation='M1 缺少设备到 iEMS 的可追溯通信路径，请补充 L4 连接。'
            elif key in ('limit','charge') and not device['controls']:
                status='BLOCKED';code='M1_CONTROL_MISSING';observation='M1 缺少同一 iEMS 到该设备的控制关系，请补充 L4。'
            elif key==body.failure_step:
                status='FAIL';code='DEVICE_TIMEOUT' if key in ('communication','identity','data') else 'CONTROL_FEEDBACK_MISMATCH'
                observation='模拟异常：设备未返回有效响应，请核对通信配置与驱动。' if code=='DEVICE_TIMEOUT' else '模拟异常：指令确认与反馈不一致；后续正常测试停止，模拟状态已复位。现场恢复结果未知。'
            results.append({'key':key,'label':label,'status':status,'code':code,'observation':observation})
            if status!='PASS':break
        return db.add('fleet_test',id,{'node_id':body.node_id,'group_id':group['id'],'mode':'SIMULATION','source':'SIMULATOR','version':'M2-FLEET-1','configuration_id':config['id'],'model_hash':p['engineering_hash'],'status':results[-1]['status'],'steps':results,'route':device['route'],'controls':device['controls'],'manufacturer_basis':'PENDING','field_result':None})
