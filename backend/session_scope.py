"""Step 01 scope and frozen prerequisite evidence; no inferred field approval."""
from .domain import digest

def preflight(model,route):
 ids=[route['ems']['node_id'],route['meter']['node_id']];devices=[];gaps=[]
 def gap(key,title,owner,reason,layer,node=None):
  gaps.append(dict(key=key,title=title,owner=owner,reason=reason,layer=layer,node_id=node,action='定位 M1 补充' if layer else '补充本步资料',blocks='现场验证',status='待现场补充' if owner.startswith('EPC') else '待厂家确认'))
 for nid in ids:
  n=next(n for n in model['nodes'] if n['node_id']==nid)
  a=next((a for a in model['device_assets'] if a['asset_id']==n['device_asset_id']),{})
  d=next((d for d in model['device_models'] if d['model_id']==a.get('model_id')), {})
  devices.append(dict(node_id=nid,name=n['name'],model_id=d.get('model_id'),model_name=d.get('model_name'),manufacturer=d.get('manufacturer'),master_data_version=d.get('master_data_version'),serial_number=a.get('serial_number'),firmware_version=a.get('firmware_version')))
  missing=[label for k,label in [('serial_number','SN'),('firmware_version','固件')] if not a.get(k)]
  if missing:gap('identity-'+nid,nid+' 缺少 '+' / '.join(missing),'EPC 现场工程师','不能核对现场设备身份及型号固件适配','L3',nid)
 gap('binding','iEMS 与站点身份尚未核验','iEMS 厂家','真实适配器未接入，无法读取控制器SN并与当前站点绑定',None,ids[0])
 gap('package','现场驱动和测试包适用依据未批准','iEMS 与表计厂家','缺少适用型号、固件、驱动版本和批准测试包；不能放行现场测试','L3',ids[1])
 gap('terminals','两端实物端子与线缆依据待确认','iEMS 与表计厂家','逻辑连接不能证明实物接线满足要求','L4',ids[1])
 gap('criteria','计量验证判据待确认','iEMS 与表计厂家','方向、倍率、刷新、误差与观察窗无受控批准依据，阻断计量通过判定','L5',ids[1])
 return dict(devices=devices,ports=[route['ems'],route['meter']],connections=[e for e in model['edges'] if e['edge_id']==route['edge_id']],project_id=model['project']['project_id'],control_domain=route['ems']['node_id'],gaps=gaps)

def freeze(p,model,route,body):
 pre=preflight(model,route);sim=body.mode=='SIMULATION';gaps=list(pre['gaps'])
 for key,title in [('installation_ref','必要安装检查记录'),('energization_ref','通信及调试上电条件记录'),('authorization_ref','作业授权记录'),('procedure_ref','批准规程编号与版本')]:
  value=getattr(body,key)
  gaps.append(dict(key=key,title=title+('已引用，待核验' if value.strip() else '未提供'),owner='EPC 现场工程师' if key!='procedure_ref' else '项目授权方 / 厂家',reason='资料引用不等于已核验；本演示未接入现场审批及文件校验',layer=None,node_id=None,action='补充本步资料',blocks='现场放行',status='待核验' if value.strip() else '待补充'))
 if body.scope=='READ_ONLY':
  for g in gaps:
   if g['key'] in ['terminals','criteria']:g['blocks']='后续计量验证，不阻断具备依据的只读诊断'
 snapshot={**{k:v for k,v in pre.items() if k!='gaps'},'model_hash':p['engineering_hash'],'configuration_revision':p['revision'],'parameters':[x for x in model.get('parameters',[]) if x.get('owner_id') in [d['node_id'] for d in pre['devices']]],'device_configuration':[n for n in model['nodes'] if n['node_id'] in [d['node_id'] for d in pre['devices']]],'controller_binding':dict(expected_sn=pre['devices'][0]['serial_number'],observed_sn='SIM-IEMS-001' if sim else None,site_id=pre['project_id'],status='SIMULATED' if sim else 'UNVERIFIED'),'driver':dict(id='SIM-METER-DRIVER' if sim else None,version='1' if sim else None,status='SIMULATION_ONLY' if sim else 'PENDING'),'test_package':dict(id='SIM-METER-SEQ' if sim else None,version='SIM-METER-SEQ-1' if sim else None,status='SIMULATION_ONLY' if sim else 'PENDING'),'scope':body.scope,'witness_requirement':body.witness_requirement,'witness_name':body.witness_name,'references':{key:getattr(body,key) for key in ['installation_ref','energization_ref','authorization_ref','procedure_ref']}}
 snapshot['snapshot_hash']=digest(snapshot)
 return dict(snapshot=snapshot,gate=dict(next_step_allowed=sim,field_release=False,read_only_allowed=sim,reason='仅允许独立演练，现场缺项保留' if sim else '现场身份及适用测试包未核验，尚不能进入02；已具备依据的只读诊断未来可单独开放',gaps=gaps))
