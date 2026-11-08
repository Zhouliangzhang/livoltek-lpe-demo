"""Planning-only strategy constraints. No controller command or approval side effects."""
import math

TEXT = ['import_target','export_limit','cycle_seconds','response_seconds','pv_limit','pv_ramp','pv_ack_seconds','pv_restore','charge_limit','discharge_limit','soc_min','soc_max','reserve_kwh','enable_conditions','meter_loss','pv_reject','bess_unavailable','recovery_conditions','stable_seconds','epc_ref','zero_ref','pv_ref','bess_ref','fallback_ref']
ENUMS = {'pv_mode':['KW','PERCENT'],'pv_allocation':['CAPACITY_WEIGHTED','EQUAL_SHARE'],'bess_mode':['SELF_CONSUMPTION','CHARGE_ONLY','DISCHARGE_ONLY'],'priority':['ZERO_FIRST','SELF_CONSUMPTION_FIRST']}
FLAGS = ['zero_enabled','pv_enabled','bess_enabled']
ROW = {'type':'object','additionalProperties':False,'required':TEXT+list(ENUMS)+FLAGS+['domain_id','signature','status'],'properties':{**{k:{'type':'string','maxLength':1000} for k in TEXT+['domain_id']},**{k:{'enum':['']+v} for k,v in ENUMS.items()},**{k:{'type':'boolean'} for k in FLAGS},'signature':{'type':'string','maxLength':500000},'status':{'const':'PENDING'}}}
STRATEGY_SCHEMA = {'type':'object','additionalProperties':False,'properties':{env:{'type':'array','maxItems':100,'items':ROW} for env in ('OFFLINE','SIMULATION','REAL')}}

def scope_devices(model, env, controller):
    drafts=[d for d in model['project'].get('network_drafts',[]) if d['environment']==env]
    replaced={d['base_edge_id'] for d in drafts if d['base_edge_id']}
    edges=[e for e in model['edges'] if e['edge_id'] not in replaced]+drafts
    ports={p['port_id']:p['node_id'] for p in model['ports']}
    controlled={ports.get(e['to_port_id']) for e in edges if e['edge_type']=='CONTROL' and ports.get(e['from_port_id'])==controller}
    nodes=[n for n in model['nodes'] if n['node_id'] in controlled and n['node_type'] in ('PV_INVERTER','BESS','PCS')]
    conflicts={ports.get(e['to_port_id']) for e in edges if e['edge_type']=='CONTROL' and ports.get(e['to_port_id']) in controlled and ports.get(e['from_port_id'])!=controller}
    return nodes,conflicts

def total_rating(model, nodes, key='rated_power', unit='kW'):
    if not nodes:return None
    # A modeled BESS plus its PCS must not be silently counted twice.
    if any(n['node_type']=='BESS' for n in nodes) and any(n['node_type']=='PCS' for n in nodes):return None
    assets={a['asset_id']:a for a in model['device_assets']};models={d['model_id']:d for d in model['device_models']};total=0
    for n in nodes:
        d=models.get(assets.get(n.get('device_asset_id'),{}).get('model_id'),{})
        v=d.get('rated_parameters',{}).get(key,{})
        if not isinstance(v.get('value'),(float,int)) or not math.isfinite(v['value']) or v['value']<=0 or v.get('unit')!=unit:return None
        total+=v['value']
    return float(format(total, ".12g"))

def strategy_checks(model):
    errors,warnings=[],[]
    domains={d['id']:d for d in model['project'].get('system_boundary',{}).get('domains',[])}
    for env,rows in model['project'].get('operating_strategies',{}).items():
        if len({r['domain_id'] for r in rows})!=len(rows):errors.append('同环境控制域策略重复')
        for r in rows:
            prefix=env+' / '+r['domain_id']+': '
            if r['domain_id'] not in domains:
                # Preserve historical plans when upstream boundaries change, without applying them.
                warnings.append(prefix+'控制域已移除，原策略失效且不应用');continue
            d=domains[r['domain_id']];devices,owners=scope_devices(model,env,d['controller_id'])
            pv=[n for n in devices if n['node_type']=='PV_INVERTER'];bess=[n for n in devices if n['node_type'] in ('BESS','PCS')]
            if owners:errors.append(prefix+'设备存在多个指令来源: '+', '.join(sorted(owners)))
            numbers={}
            for key in ['import_target','export_limit','cycle_seconds','response_seconds','pv_limit','pv_ramp','pv_ack_seconds','charge_limit','discharge_limit','soc_min','soc_max','reserve_kwh','stable_seconds']:
                if not r[key]:continue
                try:
                    v=float(r[key]);positive=key in ('cycle_seconds','response_seconds','pv_ramp','pv_ack_seconds','stable_seconds')
                    if not math.isfinite(v) or v<0 or positive and v==0:raise ValueError()
                    numbers[key]=v
                except (ValueError,OverflowError):errors.append(prefix+key+' 数值无效')
            required=[]
            if any(r[k] for k in FLAGS):required+=['enable_conditions','priority','epc_ref','meter_loss','pv_reject','bess_unavailable','recovery_conditions','stable_seconds','fallback_ref']
            if r['zero_enabled']:
                required+=['import_target','export_limit','cycle_seconds','response_seconds','zero_ref']
                if 'GRID_CONNECTED' not in model['project'].get('operation_modes',[]):errors.append(prefix+'零馈需要并网运行方式')
                if numbers.get('export_limit',0)!=0:errors.append(prefix+'零馈允许送电上限必须为 0')
                if r['priority'] and r['priority']!='ZERO_FIRST':errors.append(prefix+'零馈送电约束必须优先')
                meters=[v for v in model['project'].get('metering_settings',{}).get(env,[]) if v['pcc_id']==d['pcc_id']]
                if len(meters)!=1:warnings.append(prefix+'步骤08缺少当前环境唯一 PCC 计量映射')
                else:warnings.append(prefix+'计量草案依据和适用性仍需核验，不能放行控制')
                if pv and not r['pv_enabled']:warnings.append(prefix+'需定义光伏限功率配合')
            if r['bess_enabled'] and r['bess_mode']=='SELF_CONSUMPTION' and not r['zero_enabled']:
                warnings.append(prefix+'自发自用策略需要核验当前环境 PCC 计量依据')
            if r['pv_enabled']:
                required+=['pv_mode','pv_limit','pv_allocation','pv_ramp','pv_ack_seconds','pv_restore','pv_ref']
                if not pv:errors.append(prefix+'缺少光伏控制关系')
                rated=total_rating(model,pv)
                if rated is None:warnings.append(prefix+'光伏额定基准未知')
                limit=numbers.get('pv_limit')
                if limit is not None and (r['pv_mode']=='PERCENT' and limit>100 or r['pv_mode']=='KW' and rated is not None and limit>rated):errors.append(prefix+'光伏限值超过额定基准')
            if r['bess_enabled']:
                required+=['bess_mode','charge_limit','discharge_limit','soc_min','soc_max','reserve_kwh','bess_ref']
                if not bess:errors.append(prefix+'缺少储能控制关系')
                rated=total_rating(model,bess);energy=total_rating(model,bess,'capacity','kWh')
                if rated is None:warnings.append(prefix+'储能铭牌范围未知或 BESS/PCS 重叠，需明确计量边界')
                for k in ('charge_limit','discharge_limit'):
                    if rated is not None and numbers.get(k,0)>rated:errors.append(prefix+k+' 超过储能铭牌合计')
                if energy is not None and numbers.get('reserve_kwh',0)>energy:errors.append(prefix+'预约容量超过铭牌能量')
                for k in ('soc_min','soc_max'):
                    if numbers.get(k,0)>100:errors.append(prefix+'SOC 超过 100%')
                if 'soc_min' in numbers and 'soc_max' in numbers and numbers['soc_min']>=numbers['soc_max']:errors.append(prefix+'SOC 下限必须小于上限')
                if r['bess_mode']=='CHARGE_ONLY' and numbers.get('discharge_limit',0)!=0:errors.append(prefix+'仅充电模式不能设置非零放电限值')
                if r['bess_mode']=='DISCHARGE_ONLY' and numbers.get('charge_limit',0)!=0:errors.append(prefix+'仅放电模式不能设置非零充电限值')
            if 'cycle_seconds' in numbers and 'response_seconds' in numbers and numbers['response_seconds']<numbers['cycle_seconds']:errors.append(prefix+'响应判据不能短于控制周期')
            missing=[k for k in required if not str(r[k]).strip()]
            if missing:warnings.append(prefix+'策略缺项待确认: '+', '.join(missing))
            warnings.append(prefix+'厂家依据待核验；实时能力未知；草案未下发且不代表控制有效')
    return errors,warnings
