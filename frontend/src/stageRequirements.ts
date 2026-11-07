import type {Model} from './types'
import {readinessIssues,type Issue} from './readinessIssues'
export const stageOrder=['L1','L2','L3','L4','L5']
export function stageRequirements(model:Model,stage:string):Issue[]{
 const issues=readinessIssues(model),required:Issue[]=[]
 const add=(id:string,object:string,message:string,label?:string,nodeId?:string)=>required.push({id,layer:stage,category:'缺失信息',object,message,action:'补充必填项',label,nodeId})
 if(stage==='L1')return issues.filter(i=>i.layer==='L1')
 if(stage==='L2'){
  const structures=model.nodes.filter(n=>!n.device_asset_id)
  if(!structures.length)add('structure-required','电气结构','请至少录入项目适用的电气结构')
  for(const n of structures)if(!n.name.trim())add(n.node_id+'-name',n.node_id,'结构名称必填','结构名称 '+n.node_id)
 }
 if(stage==='L3'){
  required.push(...issues.filter(i=>i.layer==='L3'&&i.id.endsWith('-identity')))
  for(const n of model.nodes.filter(n=>n.device_asset_id)){
   const a=model.device_assets.find(a=>a.asset_id===n.device_asset_id),d=model.device_models.find(d=>d.model_id===a?.model_id)
   if(!n.name.trim())add(n.node_id+'-name',n.node_id,'设备名称必填','设备名称',n.node_id)
   if(d&&(!d.manufacturer.trim()||!d.model_name.trim()||!d.master_data_version.trim()))add(n.node_id+'-model',n.name,'厂家、型号及主数据版本必填',undefined,n.node_id)
  }
  // Device slots follow project energy composition; identity can be planned before site arrival.
  required.push(...issues.filter(i=>i.layer==='L3'&&i.id.startsWith('framework-')))
 }
 if(stage==='L4')required.push(...issues.filter(i=>i.layer==='L4'&&i.id.endsWith('-connection')))
 if(stage==='L5'){
  const keys=['control_strategy','export_limit','battery_operating_mode']
  required.push(...issues.filter(i=>i.layer==='L5'&&i.id.endsWith('-planned')&&keys.some(k=>i.rowId?.endsWith('.'+k))))
  required.push(...issues.filter(i=>i.id==='PAR-nominal_ac_voltageplanned'||i.category==='设置冲突'))
 }
 return required
}
export function requirementsBefore(model:Model,target:string){
 const end=target==='M2'?stageOrder.length:stageOrder.indexOf(target)
 return stageOrder.slice(0,end).flatMap(s=>stageRequirements(model,s))
}
