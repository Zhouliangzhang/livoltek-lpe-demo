"""Step03 detailed synthetic metering evidence, never field driver output."""
from copy import deepcopy
EXTRA={'identity':['duplicate_address','bad_frames','parameter_mismatch','model_mismatch'],'quality':['time_reverse','phase_sum','jump','duplicate','quality_unknown'],'reference':['no_reference','ct_ratio','pt_ratio']}
DIAG={
 'timeout':('未收到有效应答','核对供电条件、两端端口、总线及地址；检查日志后重试','EPC / iEMS 厂家','L4'),
 'wrong_identity':('应答身份与预期目标不符','核对SN及设备映射；换机须回M1确认后建立新会话','EPC 现场工程师','L3'),
 'model_mismatch':('型号或固件与演练驱动适配表不一致','请厂家提供型号/固件/驱动适配依据，不自动替换型号','表计 / iEMS 厂家','L3'),
 'duplicate_address':('同一总线地址出现两个应答身份','定位总线，核对各设备地址；未经批准不自动改址','EPC 现场工程师','L4'),
 'bad_frames':('检测到错误帧，通信质量不满足演练判据','核查波特率、校验与停止位；随后检查屏蔽和终端依据，不据此直接认定接线错误','EPC / iEMS 厂家','L4'),
 'parameter_mismatch':('表计与iEMS的模拟通信设置不一致','对照M1及实物设置核对协议、地址、速率和帧格式','EPC / iEMS 厂家','L5'),
 'stale':('计量源数据陈旧，轮询成功不能证明数据新鲜','检查源时间、刷新周期及点表映射，确认厂家允许的数据年龄','iEMS 厂家','L5'),
 'frozen':('源序号未更新，计量数据疑似冻结','核对采集序号和源时间，不以恒定功率本身判定冻结','iEMS 厂家','L5'),
 'bad':('设备质量字段为BAD','核对表计告警、质量定义和驱动解析依据','表计 / iEMS 厂家','L3'),
 'scale':('单位、倍率或范围校核不一致','核对单位、点表比例及CT/PT；禁止用同源读数自证','表计 / EPC','L5'),
 'reverse':('在已知购电演练状态下，功率符号与独立参照相反','核对M1计量覆盖范围、符号约定、相序和CT方向；不得为验证主动制造馈网','EPC / 表计厂家','L5'),
 'gap':('连续计量窗口出现缺测','检查通信质量和采样周期，恢复后重新累计完整窗口','iEMS 厂家','L4'),
 'time_reverse':('源时间倒退，无法建立连续时序','核对表计时钟、网关时间和采集时间策略','iEMS 厂家','L5'),
 'phase_sum':('总有功与三相有功之和不一致','核对点表、采样同步性、相量单位与总量定义','表计 / iEMS 厂家','L3'),
 'jump':('相邻样本功率跳变超出演练边界','核查原始帧、采样同步和实际负载事件；现场边界由厂家确认','iEMS 厂家','L5'),
 'duplicate':('重复数据序号，无法证明源数据刷新','检查轮询缓存及设备更新序号规则','iEMS 厂家','L5'),
 'quality_unknown':('没有设备质量字段，也没有批准的驱动质量推导依据','请厂家提供质量推导方法及限制；通信应答不等于有效计量','iEMS 厂家','L3'),
 'no_reference':('独立参考证据不足','补充参考仪表身份/校验依据、同期购电测量及PCC覆盖确认；不能自动通过','EPC 现场工程师','L5'),
 'ct_ratio':('CT倍率与独立演练参照不一致','核对CT铭牌、一次/二次值及驱动换算；补充现场依据','EPC / 表计厂家','L5'),
 'pt_ratio':('PT倍率与独立演练参照不一致','核对PT或直接电压接入方式、铭牌及驱动换算','EPC / 表计厂家','L5')}


def basis(model,route):
 node=next(n for n in model['nodes'] if n['node_id']==route['meter']['node_id'])
 asset=next((a for a in model['device_assets'] if a['asset_id']==node['device_asset_id']),{})
 device=next((d for d in model['device_models'] if d['model_id']==asset.get('model_id')), {})
 return dict(meter=dict(node_id=node['node_id'],name=node['name'],model=device.get('model_name'),manufacturer=device.get('manufacturer'),serial_number=asset.get('serial_number'),firmware=asset.get('firmware_version'),installed_location=asset.get('installed_location'),attributes=deepcopy(node.get('attributes',{}))),ports=deepcopy([route['meter'],route['ems']]),source='FROZEN_M1_NOT_FIELD_READBACK')


def enrich(result,step,scenario,model,route):
 result['m1_evidence']=basis(model,route)
 def check(label,actual,expected,passed):result['checks'].append(dict(label=label,actual=str(actual),expected=expected,passed=passed))
 if step=='identity':
  check('型号 / 固件适配','SIM-METER-X / SIM-FW-1' if scenario=='model_mismatch' else 'SIM-METER / SIM-FW-1','独立模拟驱动适配；M1现场身份待核',scenario!='model_mismatch')
  check('地址唯一性','2个应答身份' if scenario=='duplicate_address' else '1个应答身份','演练同一地址唯一应答',scenario!='duplicate_address')
  check('通信帧质量','CRC错误3帧 / 10帧' if scenario=='bad_frames' else '0错误 / 10帧','演练：10帧无错误；现场门槛待确认',scenario!='bad_frames')
  check('双方通信参数','表计19200 / iEMS9600' if scenario=='parameter_mismatch' else ('RS485 / Modbus RTU / 地址1 / 9600 / 8N1' if route['domain']=='RS485' else 'ETHERNET / Modbus TCP / 演练端点 / 502'),'合成配置与合成读回匹配；不替代M1批准值',scenario!='parameter_mismatch')
 if step in ['quality','stability']:
  for i,s in enumerate(result['samples']):
   s['phases']=[dict(phase=p,voltage_v=230,current_a=round((s['meter_kw'] or 0)*1000/3/230,2),active_kw=round((s['meter_kw'] or 0)/3,4)) for p in ['L1','L2','L3']] if s['meter_kw'] is not None else []
   s['quality_source']='UNAVAILABLE' if scenario=='quality_unknown' else 'SIMULATED_DEVICE_FLAG'
   if scenario=='time_reverse' and i==4:s['source_time']=1
   if scenario=='duplicate' and i==4:s['sequence']=s['sequence']-1
   if scenario=='phase_sum' and i==4:s['phases'][0]['active_kw']+=10
   if scenario=='jump' and i==4:s['meter_kw']=90;s['iems_kw']=90;s['phases']=[dict(phase=p,voltage_v=230,current_a=130.43,active_kw=30) for p in ['L1','L2','L3']]
   if scenario=='quality_unknown':s['quality']='UNKNOWN'
  samples=result['samples']
  for sample in samples:sample['age']=sample['time']-sample['source_time']
  for c in result['checks']:
   if c['label']=='数据质量':c.update(actual=','.join(sorted({x['quality'] for x in samples})),passed=all(x['quality']=='GOOD' for x in samples))
   if c['label']=='数据新鲜度':c.update(actual=f"最大年龄 {max(x['age'] for x in samples)} s",passed=all(0<=x['age']<=2 for x in samples))
   if c['label']=='更新连续性':c.update(actual=f"{len({x['sequence'] for x in samples})} 个不同序号",passed=len({x['sequence'] for x in samples})==7)
  check('源时间单调性',[s['source_time'] for s in samples],'演练源时间不倒退',all(b['source_time']>=a['source_time'] for a,b in zip(samples,samples[1:])))
  check('源序号无重复',[s['sequence'] for s in samples],'每个采样点有新源序号',len({s['sequence'] for s in samples})==len(samples))
  deviation=max((abs(sum(p['active_kw'] for p in s['phases'])-s['meter_kw']) for s in samples if s['meter_kw'] is not None),default=0)
  check('总功率与分相关系',f'最大偏差 {deviation:.4f} kW','演练总有功与三相之和偏差≤0.1 kW',deviation<=0.1)
  jump=max((abs(b['meter_kw']-a['meter_kw']) for a,b in zip(samples,samples[1:]) if a['meter_kw'] is not None and b['meter_kw'] is not None),default=0)
  check('相邻样本跳变',f'{jump:.2f} kW','演练相邻变化≤5 kW；非现场阈值',jump<=5)
  check('质量来源可解释','质量未知且无推导依据' if scenario=='quality_unknown' else '模拟设备显式质量字段','设备质量字段或有依据的驱动推导，不能仅凭通信成功',scenario!='quality_unknown')
 if step=='reference':
  result['reference_evidence']=dict(source='INDEPENDENT_SIMULATOR',instrument='SIM-REFERENCE-001' if scenario!='no_reference' else None,reference_kw=25 if scenario!='no_reference' else None,meter_kw=-25 if scenario=='reverse' else 250 if scenario=='scale' else 25,ct_ratio=10 if scenario=='ct_ratio' else 1,pt_ratio=10 if scenario=='pt_ratio' else 1,expected_ct_ratio=1,expected_pt_ratio=1,state='KNOWN_IMPORT',timestamp='SIM-T0',field_evidence=False)
  check('独立参照完整性','缺少参考仪表及同期读数' if scenario=='no_reference' else 'SIM-REFERENCE-001 · SIM-T0 · 独立购电+25 kW','必须有独立参考来源和同期读数',scenario!='no_reference')
  check('CT比例核对','10:1' if scenario=='ct_ratio' else '1:1','演练CT 1:1；现场铭牌和实际比例仍待确认',scenario!='ct_ratio')
  check('PT比例核对','10:1' if scenario=='pt_ratio' else '1:1','演练PT 1:1；实际接入方式仍待确认',scenario!='pt_ratio')
  if scenario=='no_reference':
   for c in result['checks']:
    if c['label']!='独立参照完整性':c.update(passed=False,actual='证据不足，未作判定')
 passed=all(c['passed'] for c in result['checks'])
 result['status']='PASS' if passed else 'FAIL'
 if not passed:
  reason,action,owner,layer=DIAG[scenario]
  result['diagnosis']=dict(reason=reason,action=action,owner=owner,layer=layer,node_id=route['meter']['node_id'],edge_id=route['edge_id'])
  if scenario in sum(EXTRA.values(),[]):result['code']='EVIDENCE_INSUFFICIENT' if scenario=='no_reference' else 'METER_'+scenario.upper()
 result['criteria_version']='SIM-METER-DETAIL-2'
 return result
