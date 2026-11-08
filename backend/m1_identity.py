"""Environment-scoped device identity drafts; no automatic verification."""
from jsonschema import Draft202012Validator, FormatChecker

FIELDS = ['sn','firmware','factory_firmware','location','structure','circuit','source','raw_scan','updated_at','replacement_reason']
RECORD = {'type':'object','required':FIELDS+['basis_status'],'additionalProperties':False,'properties':{
    **{k:{'type':'string','maxLength':4000 if k=='raw_scan' else 1000} for k in FIELDS},
    'basis_status':{'const':'PENDING'},
    'source':{'enum':['SIMULATION_QR','SIMULATION_MANUAL','QR_UNVERIFIED','MANUAL_UNVERIFIED']},
    'updated_at':{'type':'string','format':'date-time'},
    'third_party':{'type':'object','additionalProperties':False,'required':['manufacturer','model','reference','template','template_version'],'properties':{k:{'type':'string','maxLength':1000} for k in ['manufacturer','model','reference','template','template_version']}}
}}

def identity_errors(model):
    errors=[];nodes={n['node_id']:n for n in model['nodes']};seen={}
    for n in nodes.values():
        records=n.get('attributes',{}).get('identity_records',{})
        if not isinstance(records,dict):
            errors.append('设备身份记录格式无效');continue
        for env,r in records.items():
            if env not in ('OFFLINE','SIMULATION','REAL'):
                errors.append('设备身份环境无效');continue
            failures=list(Draft202012Validator(RECORD,format_checker=FormatChecker()).iter_errors(r))
            if failures:
                errors.extend(f'{n["node_id"]} 身份记录: {e.message}' for e in failures);continue
            if not n.get('device_asset_id'):
                errors.append('身份记录必须关联设备资产')
            if env!='SIMULATION' and (r['source'].startswith('SIMULATION') or r['sn'].startswith('SIM-')):
                errors.append('模拟身份不能作为离线或现场身份')
            if env=='SIMULATION' and not r['source'].startswith('SIMULATION'):
                errors.append('模拟环境需要模拟来源标记')
            parent=nodes.get(r['structure']);circuit=nodes.get(r['circuit'])
            if not parent or parent.get('device_asset_id') or parent['node_type'] not in ('PCC','TRANSFORMER_ZONE','TRANSFORMER','MV_BUS','LV_BUS','FEEDER','BREAKER'):
                errors.append('设备所属结构必须引用步骤03有效结构')
            if r['circuit'] and (not circuit or circuit.get('device_asset_id') or not (circuit['node_id']==r['structure'] or circuit.get('parent_node_id')==r['structure']) or not (circuit['node_type'] in ('FEEDER','BREAKER') or circuit.get('attributes',{}).get('engineering',{}).get('circuit_id'))):
                errors.append('设备回路必须属于所选结构')
            sn=r['sn'].strip()
            if sn:
                key=(env,sn)
                if key in seen and seen[key]!=n['node_id']:errors.append(f'{env} SN 重复: {sn}')
                seen[key]=n['node_id']
    # Existing canonical real assets also participate in uniqueness checks.
    for n in nodes.values():
        a=next((a for a in model['device_assets'] if a['asset_id']==n.get('device_asset_id')),None)
        if a and a.get('serial_number'):
            key=('REAL',a['serial_number'].strip())
            if key in seen and seen[key]!=n['node_id']:errors.append('现场 SN 与已有资产重复')
    return errors
