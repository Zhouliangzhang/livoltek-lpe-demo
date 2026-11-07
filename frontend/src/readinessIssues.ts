import type {Model} from './types'
import {communicationBuses,sharedKeys} from './communication'
import {generateSettings} from './settingsCatalog'
import {projectFramework} from './projectTopology'
export type Issue={id:string;category:'缺失信息'|'设置冲突'|'待厂家确认';layer:string;object:string;message:string;action:string;nodeId?:string;label?:string;rowId?:string;mergeKey?:string;subject?:string}
export type Validation={valid:boolean;errors:string[];warnings:string[]}
export function readinessIssues(model:Model,result?:Validation|null):Issue[]{
 const issues:Issue[]=[]
 const add=(i:Issue)=>issues.push(i)
 for(const key of ['country_code','epc_org_id','operation_modes','energy_features','voltage_level','structure_code']){
  const v=model.project[key]
  if(v==null||v===''||(Array.isArray(v)&&!v.length))add({id:'project-'+key,category:'缺失信息',layer:'L1',object:'项目定义',message:`缺少 ${key}`,action:'补充项目定义',label:'L1 '+key})
 }
 for(const gap of projectFramework(model).missing)add({id:'framework-'+gap.id,category:'缺失信息',layer:gap.layer,object:gap.name,message:'L1 框架对应对象尚未录入；类型检查不代表设计完整。',action:'补录对应对象'})
 for(const n of model.nodes.filter(n=>n.device_asset_id)){
  const a=model.device_assets.find(a=>a.asset_id===n.device_asset_id),d=model.device_models.find(d=>d.model_id===a?.model_id)
  if(!a||!d){add({id:n.node_id+'-identity',category:'缺失信息',layer:'L3',object:n.name,message:'资产或型号引用缺失',action:'核对设备资料',nodeId:n.node_id});continue}
  for(const [key,label] of [['serial_number','设备序列号'],['installed_location','安装位置'],['firmware_version','现场固件版本']] as const)if(!a[key])add({id:n.node_id+'-'+key,mergeKey:'asset-'+key,subject:label,category:'缺失信息',layer:'L3',object:n.name,message:`缺少${label}`,action:key==='serial_number'&&a.equipment_origin==='LIVOLTEK'?'核对扫码身份；厂家字段只读':'补充现场资料',nodeId:n.node_id,label})
  if(d.source_quality!=='VERIFIED')add({id:n.node_id+'-manufacturer',mergeKey:'model-evidence',subject:'型号厂家资料',category:'待厂家确认',layer:'L3',object:n.name,message:`${d.model_name} · ${d.master_data_version} 的厂家资料尚未核验`,action:'查看型号来源并协同确认',nodeId:n.node_id})
  const connected=model.edges.some(e=>[e.from_port_id,e.to_port_id].some(id=>model.ports.some(p=>p.port_id===id&&p.node_id===n.node_id)))
  if(!connected)add({id:n.node_id+'-connection',category:'缺失信息',layer:'L4',object:n.name,message:'尚无已录入连接；需核对适用电气、通信及控制路径。',action:'补充设备端口连接',nodeId:n.node_id,label:'起点设备'})
 }
 for(const r of generateSettings(model)){
  const base={mergeKey:'setting-'+r.definition.key,subject:r.definition.label,layer:'L5',object:r.deviceName+' / '+r.definition.label,nodeId:r.nodeId,rowId:r.id}
  for(const phase of ['planned','actual'] as const)if(r.record?.[phase]==null||r.record[phase]==='')add({...base,id:r.id+'-'+phase,category:'缺失信息',message:`缺少${phase==='planned'?'计划设置':'现场实际值'}`,action:'补充设置',label:r.id+' '+phase})
  if(r.stale)add({...base,id:r.id+'-stale',category:'设置冲突',message:'型号或清单版本已变化，旧设置不能直接沿用。',action:'保留旧记录并重新确认'})
  if(r.record?.planned!=null&&r.record.actual!=null&&r.record.planned!==''&&r.record.actual!==''&&r.record.planned!==r.record.actual)add({...base,id:r.id+'-difference',category:'设置冲突',message:`计划值 ${r.record.planned} 与现场值 ${r.record.actual} 不一致；需核对偏差原因。`,action:'核对现场设置',label:r.id+' actual'})
  add({...base,id:r.id+'-evidence',category:'待厂家确认',message:'缺少已核验的对应型号厂家依据；填写文档引用不等于确认适用性。',action:'补充厂家文档并协同确认',label:r.id+' reference'})
 }
 const commRows=generateSettings(model).filter(r=>r.definition.group==='通信')
 for(const bus of communicationBuses(model)){
  const members=commRows.filter(r=>bus.ports.some(p=>r.portId?p.port_id===r.portId:p.node_id===r.nodeId&&p.domain==='ETHERNET'))
  for(const phase of ['planned','actual'] as const){
   for(const key of [...sharedKeys[bus.domain],bus.domain==='RS485'?'station_address':bus.domain==='CAN'?'can_node_id':'ip_address']){
    const rr=members.filter(r=>r.definition.key===key&&!r.stale&&r.record?.[phase]!=null&&r.record?.[phase]!=='')
    const shared=sharedKeys[bus.domain].includes(key),values=rr.map(r=>String(r.record![phase]).trim().toLowerCase())
    if(shared?new Set(values).size>1:new Set(values).size<values.length){
     const row=rr[0]
     add({id:bus.id+'-'+key+'-'+phase,category:'设置冲突',layer:'L5',object:bus.name,message:shared?'同一总线的通信格式不一致，请核对各设备。':'同一通信网络的设备地址重复，请核对。',action:'核对通信设置',nodeId:row.nodeId,rowId:row.id,label:row.id+' '+phase})
    }
   }
  }
 }
 const parameters=model.parameters as {parameter_id:string;name:string;planned:{value:number;unit:string}|null;actual:{value:number;unit:string}|null;reference_doc?:string}[]
 for(const p of parameters){
  const base={layer:'L5',object:p.name,rowId:p.parameter_id}
  for(const phase of ['planned','actual'] as const)if(!p[phase])add({...base,id:p.parameter_id+phase,category:'缺失信息',message:`缺少${phase==='planned'?'计划值':'现场值'} / 工程依据`,action:'补充参数或工程文档',label:p.name+' '+phase})
  if(p.planned&&p.actual&&(p.planned.value!==p.actual.value||p.planned.unit!==p.actual.unit))add({...base,id:p.parameter_id+'difference',category:'设置冲突',message:'计划值与现场值或单位不一致',action:'核对参数',label:p.name+' actual'})
  if(!p.reference_doc)add({...base,id:p.parameter_id+'reference',category:'缺失信息',message:'缺少工程文档依据',action:'补充依据',label:p.name+' reference'})
 }
 // Backend remains authoritative for schema, references, numeric bounds and interface compatibility.
 for(const [i,message] of (result?.warnings||[]).entries()){
  if(message.startsWith('L5 '))continue // Per-parameter manufacturer evidence is already listed above.
  const binding=(model.interface_bindings as {binding_id:string;asset_id:string;signal_name:string;direction:string;protocol:string}[]).find(b=>message==='Unverified interface: '+b.binding_id)
  if(binding){
   const node=model.nodes.find(n=>n.device_asset_id===binding.asset_id)
   add({id:'warning-'+i,category:'待厂家确认',layer:'L5',object:node?.name||binding.binding_id,message:'接口点表、协议适用性及读写权限尚待厂家确认；填写引用不会自动通过核验。',action:'补充接口依据',nodeId:node?.node_id,rowId:'interface-'+binding.binding_id,label:binding.binding_id+' point_ref',mergeKey:'interface-'+binding.signal_name+'-'+binding.direction+'-'+binding.protocol,subject:'通信接口与点表依据'})
   continue
  }
  const p=parameters.find(p=>message.includes(p.name))
  add({id:'warning-'+i,category:p?'缺失信息':'待厂家确认',layer:p?'L5':'L4',object:p?.name||'接口资料',message,action:p?'核对工程依据':'核对接口并协同确认',rowId:p?.parameter_id,label:p?p.name+' reference':'起点设备'})
 }
 for(const [i,message] of (result?.errors||[]).entries()){
  const projectPath=message.match(/^project\/([^/:]+)/)
  if(projectPath){add({id:'rule-'+i,category:'设置冲突',layer:'L1',object:'项目定义',message,action:'修正项目定义',label:'L1 '+projectPath[1]});continue}
  const parameterPath=message.match(/^parameters\/(\d+)/)
  const parameter=parameterPath?parameters[Number(parameterPath[1])]:undefined
  if(parameter){add({id:'rule-'+i,category:'设置冲突',layer:'L5',object:parameter.name,message,action:'修正参数',rowId:parameter.parameter_id,label:parameter.name+' '+(message.includes('/actual')?'actual':'planned')});continue}
  const row=generateSettings(model).find(r=>message.includes(r.id))||generateSettings(model).find(r=>message.includes(r.nodeId)&&message.includes('SOC')&&r.definition.key==='soc_min'),edge=model.edges.find(e=>message.includes(e.edge_id))
  add({id:'rule-'+i,category:'设置冲突',layer:row?'L5':edge?'L4':'L6',object:row?row.deviceName+' / '+row.definition.label:edge?.edge_id||'数据规则',message,action:row?'修正设置':edge?'核对连接':'查看规则详情并技术协同',nodeId:row?.nodeId,rowId:row?.id||edge?.edge_id,label:row?row.id+' '+(message.includes('.actual')?'actual':'planned'):edge?'起点设备':undefined})
 }
 return issues
}
