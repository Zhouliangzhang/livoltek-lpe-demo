"""Reproducible planned project. No SN, field measurements or approvals are invented."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain import pilot, validate

PROJECT_ID = 'LPE-CI20-1250PV-2612ESS'
REF = 'CI20-ASSUMPTIONS-R1'
SOURCES = {
 'PV-DS': 'https://info-support.livoltek.com/2-Product-Material/1-Product%20Datasheet/1-Grid-tied%20Inverter/GT3-75~125kW.pdf',
 'BESS-DS-2025-10V1': 'https://info-support.livoltek.com/2-Product-Material/datasheets/Battery/BESS-125kW%2B261kWh.pdf',
 'IEMS-HXEM100-MANUAL': 'https://info-support.livoltek.com/2-Product-Material/ProductFiles/others/User%20Manual_HXEM100.pdf',
 'REFERENCE-ZERO-EXPORT': 'https://info-support.sungrowpower.com/product-materials/ef49ce80-425a-4a13-b805-b90bd2271866/GUID-95D9D42B-B7B3-4A78-8F0B-1B3CE881F779.html',
}

def build():
 m = pilot()
 for k,v in m.items():
  if isinstance(v,list):m[k]=[]
 m['project'].update(project_id=PROJECT_ID,name='CI-20 工厂光储 · PV 1.25MW / BESS 2.612MWh',country_code='ZA',epc_org_id='EPC-SIMULATION-PENDING',operation_modes=['GRID_CONNECTED'])
 m['baseline'].update(baseline_id='BL-CI20-R1',version='0.1.0',source_design_refs=[REF],country_profile_ref='ZA-ASSUMED-NOT-APPROVED',device_master_version='PUBLIC-SOURCES-2026-11-07',approved_by=None,approved_at=None)
 m['view_layout']['positions']={}
 def node(id,kind,name,parent='ZONE_01',asset=None,**attrs):
  n=dict(node_id=id,logical_id=id,node_type=kind,name=name,parent_node_id=parent,zone_id='ZONE_01',device_asset_id=asset,icon_key=kind.lower(),relationship_reason='ENERGY_PATH',attributes={'source_ref':REF,'source_quality':'DRAFT','entry_method':'PLANNED_SCENARIO','assumption':True,**attrs})
  m['nodes'].append(n);return n
 def port(id,name,domain='AC',voltage=400,role='BIDIRECTIONAL'):
  pid=id+'.'+name
  if any(p['port_id']==pid for p in m['ports']):return pid
  m['ports'].append(dict(port_id=pid,node_id=id,name=name,domain=domain,role=role,attributes={'voltage':voltage,'phases':3,'source':REF,'verified':False} if domain=='AC' else {'source':REF,'verified':False},approved_spec_ref=None));return pid
 def edge(a,b,kind='ELECTRICAL',profile=None):
  eid='CI-'+str(len(m['edges'])+1).zfill(3)
  m['edges'].append(dict(edge_id=eid,edge_type=kind,from_port_id=a,to_port_id=b,design_ref=REF,review_status='DRAFT',attributes={'simulation_profile':profile} if profile else {}))
  if profile:m['telemetry_bindings'].append(dict(binding_id='TEL-'+eid,target_type='EDGE',target_id=eid,measurement='ACTIVE_POWER',source_system='OTHER',point_ref='SIM.CI20.'+eid,unit='kW',positive_direction='FROM_TO',max_age_seconds=30,quality_required='GOOD'))
  return eid
 def model(id,mfr,name,ref=None,power=None,energy=None):
  rated={}
  for key,value,unit in [('rated_power',power,'kW'),('capacity',energy,'kWh')]:
   if value is not None:rated[key]=dict(value=value,unit=unit,source='MASTER_DATA',status='DRAFT',source_ref=ref or REF)
  m['device_models'].append(dict(model_id=id,manufacturer=mfr,model_name=name,master_data_version=ref or REF,source_quality='DRAFT',datasheet_ref=SOURCES.get(ref,REF),rated_parameters=rated,document_refs=[ref or REF]))
 def device(id,kind,name,mid,location,own=False,**attrs):
  aid='ASSET-'+id
  m['device_assets'].append(dict(asset_id=aid,model_id=mid,serial_number=None,sn_status='PENDING',installed_location=None,firmware_version=None,lifecycle_status='PLANNED',equipment_origin='LIVOLTEK' if own else 'THIRD_PARTY',modeling_level='L1_FULL' if own else 'L2_INTERFACE',responsibility_owner='EPC / LIVOLTEK 产品支持' if own else 'EPC / 第三方厂家',authorization=dict(read_allowed=False,write_allowed=False,test_execution_allowed=False)))
  return node(id,kind,name,asset=aid,planned_location=location,**attrs)
 model('PV-GT3','LIVOLTEK','GT3-125K-1','PV-DS',125)
 model('BESS-261','LIVOLTEK','BES-P125X261E','BESS-DS-2025-10V1',125,261.2)
 model('EMS-USER20','LIVOLTEK','iEMS · 20台接入，交付型号待核','USER-CONFIRMED-20')
 for mid,name in [('METER','三相四线 CT 接入零馈表 · 型号待选'),('SWITCH','工业以太网交换机 24口 · 型号待选'),('UPS','控制电源 UPS · 型号及容量待核'),('CT','PCC 三相 CT 组 · 4000/5A 候选')]:model(mid,'第三方厂家待选',name)
 zone=node('ZONE_01','TRANSFORMER_ZONE','单台区 · 400V 光储工厂',parent=None)
 zone['attributes'].update(scenario_id=PROJECT_ID,source_urls=SOURCES,scope='PLANNED / SIMULATION ONLY',capacity={'pv_ac_kw':1250,'bess_kw':1250,'bess_kwh':2612,'pv_dc_kwp_assumed':1500},open_questions=['用户确认一台iEMS管理20台设备；具体交付型号、固件及点表待核','柜间距/消防/地基','短路电流/选择性/电缆/接地','PCC CT方向与变比/反馈符号/失联策略','组件串并联与MPPT分配未设计'],operating_cases={'normal':'PV1250 + PCC25 = load800 + BESS charge475 (kW); ideal lossless simulation','reverse':'PV0 + PCC1100 + BESS discharge500 = load1600 (kW); ideal lossless simulation'})
 node('TX_01','TRANSFORMER','既有变压器 · 2500kVA 假设',rated_kva_assumed=2500,ratio_assumed='11/0.4kV',scope='LV terminal only; upstream MV outside detailed model')
 node('QF_MAIN','BREAKER','总进线 ACB · 4000AF 假设',frame_a_assumed=4000,trip_setting=None)
 device('CT_PCC','JUNCTION','PCC 三相 CT 组','CT','进线计量室')
 node('PCC_01','PCC','PCC 零馈控制边界')
 node('LV_BUS_01','LV_BUS','主配电柜母线 · 5000A 假设',rated_a_assumed=5000)
 root=['TX_01','QF_MAIN','CT_PCC','PCC_01','LV_BUS_01']
 for a,b in zip(root,root[1:]):edge(port(a,'OUT'),port(b,'IN'),profile={'normal':25,'reverse':1100})
 node('QF_LOAD','BREAKER','负载馈线 · 3200AF 假设',frame_a_assumed=3200,trip_setting=None)
 node('LOAD_01','LOAD','工厂负载 · 2MW 包络假设',peak_kw_assumed=2000,includes_auxiliary_load=True)
 edge(port('LV_BUS_01','LOAD'),port('QF_LOAD','IN'),profile={'normal':800,'reverse':1600})
 edge(port('QF_LOAD','OUT'),port('LOAD_01','AC'),profile={'normal':800,'reverse':1600})
 for group,kind,mid in [('PV','PV_INVERTER','PV-GT3'),('BESS','BESS','BESS-261')]:
  for g in [1,2]:
   board=f'{group}_ACB_{g}';qf='QF_'+board
   node(qf,'BREAKER',f'{group} 汇流总开关 {g} · 1250AF 假设',frame_a_assumed=1250,trip_setting=None)
   node(board,'LV_BUS',f'{group} AC汇流柜 {g} · 5回路 / 1250A 假设',rated_a_assumed=1250)
   profile={'normal':-625 if group=='PV' else 237.5,'reverse':0 if group=='PV' else -250}
   edge(port('LV_BUS_01',board),port(qf,'IN'),profile=profile);edge(port(qf,'OUT'),port(board,'IN'),profile=profile)
   for i in range((g-1)*5+1,g*5+1):
    id=f'{group}_{i:02}';branch='QF_'+id
    device(id,kind,f'{group} {i:02} · 125kW'+('/261.2kWh' if group=='BESS' else ''),mid,f'{group}区 {g} / 机位{i:02}',True)
    node(branch,'BREAKER',f'{group} {i:02} 支路 · 250AF 假设',parent=board,frame_a_assumed=250,trip_setting=None)
    profile={'normal':-125 if group=='PV' else 47.5,'reverse':0 if group=='PV' else -50}
    edge(port(board,id),port(branch,'IN'),profile=profile);edge(port(branch,'OUT'),port(id,'AC'),profile=profile)
    if group=='PV':
     array='ARRAY_'+str(i).zfill(2);node(array,'OTHER',f'PV阵列 {i:02} · 150kWp 假设',scope='Aggregated DC boundary; module model/string sizing/MPPT assignment pending; integrated inverter DC switch per source')
     edge(port(array,'DC','DC'),port(id,'DC_AGGREGATE','DC'))
 device('EMS_MASTER','EMS','iEMS 系统控制器 · 统一控制20台','EMS-USER20','控制柜',True,scope='Single iEMS for 10 PV + 10 BESS confirmed by user; delivered model/firmware/point map pending')
 device('NET_01','OTHER','工业交换机 · 24口候选','SWITCH','控制柜')
 device('METER_PCC','METER','PCC 零馈表 · CT式候选','METER','PCC计量室',measured_edge='CI-003',import_sign='positive',external_meter_compatibility='pending; HXEM100 integrated metering alternative requires review')
 device('UPS_01','OTHER','控制电源 UPS · 候选','UPS','控制柜')
 node('QF_AUX','BREAKER','控制柜辅助电源开关 · 待选')
 edge(port('LV_BUS_01','AUX'),port('QF_AUX','IN'));edge(port('QF_AUX','OUT'),port('UPS_01','INPUT'))
 for id in ['EMS_MASTER','NET_01']:edge(port('UPS_01',id),port(id,'SUPPLY'))
 node('FUSE_METER','SWITCH','计量电压取样熔断器 · 待选')
 edge(port('PCC_01','V_TAP'),port('FUSE_METER','IN'));edge(port('FUSE_METER','OUT'),port('METER_PCC','V_INPUT'))
 edge(port('CT_PCC','CT_SECONDARY','ANALOG_IO'),port('METER_PCC','CT_INPUT','ANALOG_IO'),'COMMUNICATION')
 edge(port('METER_PCC','RS485','RS485'),port('EMS_MASTER','METER_RS485','RS485'),'COMMUNICATION')
 node('PV_RS485_BUS','JUNCTION','PV RS485 总线 · 非星形接线示意',scope='Logical multidrop bus; termination, polarity, routing and shield details pending')
 edge(port('EMS_MASTER','PV_RS485','RS485'),port('PV_RS485_BUS','MASTER','RS485'),'COMMUNICATION')
 for i in range(1,11):edge(port('PV_RS485_BUS',f'DEV{i}','RS485'),port(f'PV_{i:02}','RS485','RS485'),'COMMUNICATION')
 for id in ['EMS_MASTER']+[f'BESS_{i:02}' for i in range(1,11)]:edge(port('NET_01',id,'ETHERNET'),port(id,'LAN','ETHERNET'),'COMMUNICATION')
 for group in ['PV','BESS']:
  for i in range(1,11):edge(port('EMS_MASTER',f'{group}_SETPOINT_{i}','CONTROL_LOGICAL',role='OUT'),port(f'{group}_{i:02}','SETPOINT','CONTROL_LOGICAL',role='IN'),'CONTROL')
 for n in m['nodes']:
  if not n['device_asset_id']:continue
  aid=n['device_asset_id'];m['interface_bindings'].append(dict(binding_id='IF-'+n['node_id'],asset_id=aid,signal_name='SITE_INTERFACE_PENDING',direction='READ',protocol='Vendor mapping pending',point_ref=None,unit=None,verification_status='UNVERIFIED',source_ref=REF,authorization_ref=None))
 # Candidate settings: design intent only; actual/approved values deliberately remain absent.
 catalog=json.loads((ROOT/'config/l5-catalog.json').read_text(encoding='utf-8'))
 for n in m['nodes']:
  a=next((a for a in m['device_assets'] if a['asset_id']==n['device_asset_id']),None)
  if not a:continue
  d=next(d for d in m['device_models'] if d['model_id']==a['model_id']);domains={p['domain'] for p in m['ports'] if p['node_id']==n['node_id']}
  settings={};num=int(n['node_id'].split('_')[-1]) if n['node_id'].split('_')[-1].isdigit() else {'EMS_MASTER':1}.get(n['node_id'],50)
  values={'addressing_mode':'STATIC - proposed','ip_address':f'192.0.2.{20+num if n["node_type"]=="BESS" else 10 if n['node_id']=='NET_01' else num}','subnet_mask':'255.255.255.0','network_protocol':'Modbus TCP candidate; register map pending','station_address':str(num),'control_strategy':'自发自用；PCC 零馈优先','dispatch_priority':'Zero-export > site demand ceiling > self-consumption; pending manufacturer review','power_feedback_source':'METER_PCC at LV incomer; import positive; CT polarity unverified','command_authority':'SIMULATION_ONLY - no write permission','communication_loss_action':'Request safe power curtailment; timing and fallback pending manufacturer validation','export_limit':0,'grid_power_target':25,'pv_curtailment':'先供负载 → 余电充储能 → 剩余光伏限发','charge_power_limit':125,'discharge_power_limit':125,'battery_operating_mode':'自发自用：余电充电、缺电放电；受 SOC 及功率上限约束','charge_schedule':'优先光伏余电充电；暂不启用电网定时充电'}
  for item in catalog['parameters']:
   if item['node_types'] and n['node_type'] not in item['node_types']:continue
   if item['domains'] and not domains.intersection(item['domains']):continue
   if item['modes'] and not set(m['project']['operation_modes']).intersection(item['modes']):continue
   if item['features'] and not set(m['project']['energy_features']).intersection(item['features']):continue
   key=item['key']
   if key not in values:continue
   settings[key]=dict(planned=values[key],actual=None,reference_doc=REF+'; candidate, not approved',model_id=d['model_id'],master_data_version=d['master_data_version'],template_version=catalog['version'])
  n['attributes']['l5_settings']=settings
 for name,value,unit in [('nominal_ac_voltage',400,'V'),('nominal_frequency',50,'Hz'),('site_import_limit',2000,'kW'),('transformer_capacity',2500,'kVA')]:
  m['parameters'].append(dict(parameter_id='PAR-'+name,scope='PROJECT',owner_id=PROJECT_ID,name=name,planned=dict(value=value,unit=unit,source='DESIGN',status='DRAFT',source_ref=REF),actual=None,approved=None,criticality='NORMAL',reference_doc=REF,review_status='DRAFT'))
 m['parameters'].append(dict(parameter_id='PAR-CABLE',scope='PROJECT',owner_id=PROJECT_ID,name='cable_spec',planned=None,actual=None,approved=None,criticality='SAFETY_CRITICAL',reference_doc=None,review_status='DRAFT'))
 return m

if __name__=='__main__':
 model=build();result=validate(model)
 if not result['valid']:print(json.dumps(result,indent=2));raise SystemExit(1)
 path=ROOT/'examples/ci20-pilot.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'file':str(path),'nodes':len(model['nodes']),'ports':len(model['ports']),'edges':len(model['edges']),'assets':len(model['device_assets']),'warnings':len(result['warnings'])}))
 if '--install' in sys.argv:
  import urllib.request
  request=urllib.request.Request('http://127.0.0.1:8000/api/projects',data=json.dumps({'model':model,'expected_revision':0}).encode(),headers={'Content-Type':'application/json'})
  saved=json.load(urllib.request.urlopen(request))
  print(json.dumps({'installed':PROJECT_ID,'revision':saved['revision']}))
