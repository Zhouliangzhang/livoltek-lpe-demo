"""Environment-scoped PCC metering plans, never a commissioning result."""
import math

FIELDS = ['meter_id','pcc_id','signature','location','phases','ct_mode','ct_primary','ct_secondary','pt_mode','pt_primary','pt_secondary','meter_ct_ratio','meter_pt_ratio','read_side','power_field','input_unit','raw_sign','driver_scale','epc_ref','manufacturer_ref','time_source','refresh_seconds','stale_seconds','quality_field']
ENUMS = {'phases':['SINGLE','THREE_3','THREE_4'],'ct_mode':['DIRECT','EXTERNAL'],'pt_mode':['DIRECT','EXTERNAL'],'read_side':['PRIMARY','SECONDARY'],'input_unit':['W','kW','MW'],'raw_sign':['IMPORT_POSITIVE','EXPORT_POSITIVE']}
ROW = {'type':'object','additionalProperties':False,'required':FIELDS+['status'],'properties':{**{k:{'type':'string','maxLength':30000 if k=='signature' else 500} for k in FIELDS},**{k:{'enum':['']+v} for k,v in ENUMS.items()},'status':{'const':'PENDING'}}}
METERING_SCHEMA = {'type':'object','additionalProperties':False,'properties':{e:{'type':'array','maxItems':1000,'items':ROW} for e in ('OFFLINE','SIMULATION','REAL')}}

def metering_checks(model):
    errors, warnings = [], []
    nodes = {n['node_id']:n for n in model['nodes']}
    for env, rows in model['project'].get('metering_settings',{}).items():
        meter_ids, pcc_ids = set(), set()
        for r in rows:
            prefix = env+' / '+r['meter_id']+': '
            if nodes.get(r['meter_id'],{}).get('node_type') != 'METER':
                errors.append(prefix+'电表对象不存在或类型错误')
            if r['pcc_id'] and nodes.get(r['pcc_id'],{}).get('node_type') != 'PCC':
                errors.append(prefix+'PCC 对象不存在或类型错误')
            if r['meter_id'] in meter_ids or r['pcc_id'] and r['pcc_id'] in pcc_ids:
                errors.append(prefix+'电表或 PCC 反馈映射重复')
            meter_ids.add(r['meter_id']); pcc_ids.add(r['pcc_id'])
            numbers = {}
            for key in ['ct_primary','ct_secondary','pt_primary','pt_secondary','meter_ct_ratio','meter_pt_ratio','driver_scale','refresh_seconds','stale_seconds']:
                if not r[key]:
                    continue
                try:
                    value = float(r[key])
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError()
                    numbers[key] = value
                except (ValueError, OverflowError):
                    errors.append(prefix+key+' 必须为有限正数')
            for kind in ('ct','pt'):
                mode = r[kind+'_mode']
                if mode == 'DIRECT' and (r[kind+'_primary'] or r[kind+'_secondary']):
                    errors.append(prefix+kind.upper()+' 直接接入与外置额定值冲突')
                ratio = 1 if mode == 'DIRECT' else None
                if mode == 'EXTERNAL' and kind+'_primary' in numbers and kind+'_secondary' in numbers:
                    ratio = numbers[kind+'_primary']/numbers[kind+'_secondary']
                    if not math.isfinite(ratio):
                        errors.append(prefix+kind.upper()+' 比值溢出')
                if r['read_side']=='PRIMARY' and ratio is not None and 'meter_'+kind+'_ratio' in numbers and not math.isclose(ratio,numbers['meter_'+kind+'_ratio'],rel_tol=1e-9,abs_tol=1e-8):
                    errors.append(prefix+'仪表内部 '+kind.upper()+' 倍率与铭牌比值不一致')
            if numbers.get('stale_seconds',math.inf)<numbers.get('refresh_seconds',0):
                errors.append(prefix+'过期判定不能短于刷新周期')
            required = ['pcc_id','location','phases','ct_mode','pt_mode','meter_ct_ratio','meter_pt_ratio','read_side','power_field','input_unit','raw_sign','driver_scale','epc_ref','manufacturer_ref','time_source','refresh_seconds','stale_seconds','quality_field']
            for kind in ('ct','pt'):
                if r[kind+'_mode']=='EXTERNAL':
                    required += [kind+'_primary',kind+'_secondary']
            missing = [k for k in required if not r[k].strip()]
            if missing:
                warnings.append(prefix+'计量缺项待补充: '+', '.join(missing))
            warnings.append(prefix+'EPC / 厂家依据待核验；未下发或现场验证，不能据此放行零馈控制')
    return errors, warnings
