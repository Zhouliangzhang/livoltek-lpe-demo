"""Versioned, model-bound system inspection, separate from construction tracking."""
import base64
from typing import Literal
from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field
from .domain import digest

VERSION = 'CHECKLIST-1'

def checklist(model):
    nodes = {n['node_id']: n for n in model['nodes']}
    ports = {p['port_id']: p for p in model['ports']}
    items = []
    def add(key, stage, title, target, name, detail, node_ids, method, expected, pending, layer):
        items.append(dict(id=key, stage=stage, title=title, target_id=target, name=name,
            detail=detail, node_ids=node_ids, method=method, expected=expected,
            manufacturer_pending=pending, source_status='DRAFT', template_version=VERSION, layer=layer))
    for e in model['edges']:
        a,b = ports[e['from_port_id']], ports[e['to_port_id']]
        name = nodes[a['node_id']]['name'] + ' → ' + nodes[b['node_id']]['name']
        detail = a['port_id'] + ' → ' + b['port_id']
        stage = e['edge_type']
        checks = {
            'ELECTRICAL': [('接线与回路对应', '由有权限的现场人员在安全隔离条件下，对照批准图纸核对两端设备、端口、回路标识及现场接线，记录差异。', '现场回路与批准设计一致；导体规格、保护配置和端子要求有适用依据。', '端子定义、线缆及紧固要求、适用检查判据', 'L4')],
            'COMMUNICATION': [('通信接线', '对照双方接口定义核对两端端口、线缆类型及现场线路标识。总线接法以厂家受控图纸为准。', '两端端口与现场线路一一对应，无接口域混接。', '型号针脚图、屏蔽/终端要求及线缆规格', 'L4'), ('通信设置与数据读取', '核对 L5 的现场参数；具备批准的上电和测试条件后，由现场人员通过厂家诊断界面记录设备身份、数据及通信异常。', '读取对象、数据方向、单位与预期设备一致；有效性和稳定性满足确认后的判据。', '协议点表、诊断方法、超时/重试及有效性判据', 'L5')],
            'CONTROL': [('控制对象映射', '核对 iEMS 指令目标、设备身份、逻辑端口及反馈对象。此项为映射核对，不发送控制命令。', '目标设备及反馈与本控制关系一致，不串设备。', '指令/反馈点表、控制权限和固件兼容性', 'L4'), ('控制策略与反馈', '核对 L5 零馈、光伏限功率或储能充放电策略；现场动态验证须另行具备已批准的方法、权限及执行前提。', '设定、反馈、计量方向和异常处理策略一致；具体限值与验证判据经厂家确认。', '零馈响应、限功率、SOC/功率边界、失联策略及动态验证方法', 'L5')],
        }
        if stage=='CONTROL':
            target_type=nodes[b['node_id']]['node_type']
            if target_type=='PV_INVERTER':
                checks[stage][1]=('光伏限功率策略与反馈', '核对该逆变器的限功率模式、功率基准、指令来源和反馈点；不在页面下发限功率命令。动态测试需厂家确认方法及现场批准。', 'iEMS 目标功率、设备限值与反馈单位一致，设备失联后的策略明确。', '限功率协议、基准/量纲、响应判据及失联策略', 'L5')
            elif target_type=='BESS':
                checks[stage][1]=('储能充放电策略与反馈', '核对该储能的充放电功率方向、SOC 边界、工作模式、可用状态及保护约束；动态测试需具备批准的方法和现场执行条件。', '计划设置与现场值一致，充放电方向、功率边界和反馈对应正确。', 'SOC/功率边界、模式优先级、保护联锁及反馈判据', 'L5')
        for index,(title,method,expected,pending,layer) in enumerate(checks.get(stage, [])):
            add(f'{e["edge_id"]}:{index}',stage,title,e['edge_id'],name,detail,[a['node_id'],b['node_id']],method,expected,pending,layer)
    for n in model['nodes']:
        if n.get('device_asset_id'):
            add(n['node_id']+':earth','ELECTRICAL','保护接地核对',n['node_id'],n['name'],n['device_asset_id'],[n['node_id']],
                '由现场人员对照批准设计及设备手册核对 PE 端子、接地连接和标识；测量须采用已批准的方法并记录仪器和结果。',
                '接地连接与批准设计一致，测量结果符合适用的确认判据。','PE 端子、连接要求及测量判据','L3')
    ems=next((n for n in model['nodes'] if n['node_type']=='EMS'),None)
    for meter in (n for n in model['nodes'] if n['node_type']=='METER'):
        add(meter['node_id']+':metering','ELECTRICAL','零馈计量位置与方向',meter['node_id'],meter['name'],'PCC / CT / 电表',[meter['node_id']],
            '对照批准设计核对计量点位置、CT 对应相别、方向与倍率，现场核对须遵守隔离和计量回路作业条件。',
            '计量覆盖目标并网点，现场方向、相别与配置一致。','计量接线图、CT 要求、符号约定及核验方法','L5')
        if ems:
            add(meter['node_id']+':zero-export','CONTROL','零馈闭环与异常策略',meter['node_id'],meter['name']+' → '+ems['name'],'计量反馈 → iEMS → 光伏 / 储能',[ems['node_id'],meter['node_id']],
                '核对零馈启用条件、并网点计量映射、功率方向、目标值及失联处理。只核对设置；动态验证须按厂家确认方法和现场批准条件执行。',
                '计量反馈与调节对象一致，零馈目标、调节优先级和异常降级策略有已确认依据。','零馈控制判据、响应时间、容差、光储协调及计量失联策略','L5')
    return items

class CheckRecord(BaseModel):
    item_id: str
    status: Literal['PASS','FAIL','PENDING','NA']
    recorder: str = Field(min_length=1,max_length=100)
    note: str = Field(min_length=1,max_length=4000)
    photo_ids: list[str] = Field(default_factory=list,max_length=10)

def register_checklist(app,db):
    def context(id,item_id=None,write=False):
        try: plan=db.record(id)
        except KeyError: raise HTTPException(404,'点检清单不存在')
        if plan['kind']!='plan': raise HTTPException(404,'点检清单不存在')
        if write and digest(db.get(plan['project'])['model'])!=plan['engineering_hash']:
            raise HTTPException(409,'模型已变化，请重新生成点检清单；历史记录保留')
        items=plan.get('checklist_items')
        if items is None: items=checklist(plan['system_context_baseline'])
        item=next((i for i in items if i['id']==item_id),None)
        if item_id is not None and item is None: raise HTTPException(422,'点检项不属于当前清单')
        return plan,items,item

    @app.get('/api/plans/{id}/checklist')
    def listing(id:str):
        _,items,_=context(id)
        return {'version':VERSION,'items':items,'records':db.records('checklist',id)}

    @app.post('/api/plans/{id}/checklist')
    def save(id:str,body:CheckRecord):
        _,_,item=context(id,body.item_id,True)
        if not body.note.strip() or not body.recorder.strip(): raise HTTPException(422,'请填写记录人及现场说明；不适用须说明原因')
        if body.status=='PASS' and item['source_status']!='APPROVED': raise HTTPException(422,'缺少厂家已确认依据，不能记录为通过')
        for pid in body.photo_ids:
            try: photo=db.record(pid)
            except KeyError: raise HTTPException(422,'照片不存在')
            if photo['kind']!='checklist_photo' or photo['project']!=id or photo['item_id']!=body.item_id: raise HTTPException(422,'照片必须属于本清单点检项')
        return db.add('checklist',id,{**body.model_dump(),'template_version':item['template_version'],'approval':'NOT_APPROVED'})

    @app.post('/api/plans/{id}/checklist/photos')
    async def upload(id:str,request:Request,item_id:str,filename:str):
        context(id,item_id,True)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>5*1024*1024: raise HTTPException(413,'单张照片不能超过 5 MB')
            chunks.append(chunk)
        data=b''.join(chunks)
        mime='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None
        if not mime: raise HTTPException(415,'请上传 PNG 或 JPEG 照片')
        photo=db.add('checklist_photo',id,{'item_id':item_id,'filename':filename[:150],'mime':mime,'data':base64.b64encode(data).decode()})
        return {'id':photo['id']}

    @app.get('/api/checklist/photos/{id}')
    def photo(id:str):
        try: p=db.record(id)
        except KeyError: raise HTTPException(404,'照片不存在')
        if p['kind']!='checklist_photo': raise HTTPException(404,'照片不存在')
        return Response(base64.b64decode(p['data']),media_type=p['mime'],headers={'X-Content-Type-Options':'nosniff'})
