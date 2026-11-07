import catalog from '../../config/l5-catalog.json' with {type:'json'}
import type {Model} from './types'
import {connectedPorts,modelTemplates} from './communication'
export type SettingScalar=string|number|null
export type SettingRecord={planned:SettingScalar;actual:SettingScalar;reference_doc:string;model_id:string;master_data_version:string;template_version:string}
export type Definition={key:string;label:string;group:string;type:string;unit:string;node_types:string[];domains:string[];modes:string[];features:string[];min?:number;max?:number}
export type GeneratedSetting={id:string;portId?:string;nodeId:string;deviceName:string;modelId:string;modelName:string;manufacturer:string;modelVersion:string;definition:Definition;record?:SettingRecord;stale:boolean;reason:string}
export const settingsVersion=catalog.version
export function generateSettings(model:Model):GeneratedSetting[]{
 const rows:GeneratedSetting[]=[],modes=model.project.operation_modes as string[],features=model.project.energy_features as string[]
 for(const node of model.nodes){
  const asset=model.device_assets.find(a=>a.asset_id===node.device_asset_id),device=model.device_models.find(d=>d.model_id===asset?.model_id)
  if(!asset||!device)continue
  const linked=connectedPorts(model).filter(p=>p.node_id===node.node_id)
  const domains=new Set(linked.map(p=>p.domain))
  const records=(node.attributes?.l5_settings as Record<string,SettingRecord>|undefined)||{}
  for(const d of catalog.parameters as Definition[]){
   if(d.node_types.length&&!d.node_types.includes(node.node_type))continue
   if(d.domains.length&&!d.domains.some(x=>domains.has(x)))continue
   if(d.modes.length&&!d.modes.some(x=>modes.includes(x)))continue
   if(d.features.length&&!d.features.some(x=>features.includes(x)))continue
   const matching=linked.filter(p=>d.domains.includes(p.domain))
   const targets=d.group==='通信'&&d.domains[0]!=='ETHERNET'?matching:[undefined]
   for(const target of targets){
   const multi=target&&matching.length>1
   const portRecords=target?.attributes?.l5_settings as Record<string,SettingRecord>|undefined
   const record=portRecords?.[d.key]||(!multi?records[d.key]:undefined)
   const template=device.manufacturer.toUpperCase()==='LIVOLTEK'?modelTemplates(model,node.node_id).find(t=>d.domains.includes(t.domain)):undefined
   const value=template?.values[d.key]
   const effective=record||(template&&value!=null&&template.reference_doc?{planned:value,actual:null,reference_doc:`${template.id} / ${template.version} / ${template.status}: ${template.reference_doc}`,model_id:device.model_id,master_data_version:device.master_data_version,template_version:settingsVersion}:undefined)
   rows.push({id:(multi?target.port_id:node.node_id)+'.'+d.key,portId:target?.port_id,nodeId:node.node_id,deviceName:node.name,modelId:device.model_id,modelName:device.model_name,manufacturer:device.manufacturer,modelVersion:device.master_data_version,definition:d,record:effective,stale:!!record&&(record.model_id!==device.model_id||record.master_data_version!==device.master_data_version||record.template_version!==settingsVersion),reason:[d.domains.length?d.domains.filter(x=>domains.has(x)).join(' / '):node.node_type,d.modes.length?modes.filter(x=>d.modes.includes(x)).join(' / '):'',d.features.length?features.filter(x=>d.features.includes(x)).join(' / '):''].filter(Boolean).join(' · ')})
   }
  }
 }
 return rows
}
export function updateSetting(model:Model,row:GeneratedSetting,field:'planned'|'actual'|'reference_doc',value:SettingScalar):Model{
 const next=structuredClone(model),node=next.nodes.find(n=>n.node_id===row.nodeId)!
 node.attributes??={}
 const owner=row.portId?next.ports.find(p=>p.port_id===row.portId)!:node
 owner.attributes??={}
 const records=(owner.attributes.l5_settings??={}) as Record<string,SettingRecord>
 if(row.stale)throw new Error('型号或模板版本已变化，请先重新确认。')
 records[row.definition.key]={...(records[row.definition.key]||row.record||{planned:null,actual:null,reference_doc:''}),model_id:row.modelId,master_data_version:row.modelVersion,template_version:settingsVersion,[field]:value}
 return next
}
export function resetSetting(model:Model,row:GeneratedSetting):Model{
 const next=structuredClone(model),node=next.nodes.find(n=>n.node_id===row.nodeId)!
 node.attributes??={};const owner=row.portId?next.ports.find(p=>p.port_id===row.portId)!:node
 owner.attributes??={}
 const records=(owner.attributes.l5_settings??={}) as Record<string,SettingRecord>
 const history=(owner.attributes.l5_settings_history??=[]) as unknown[]
 if(records[row.definition.key]||row.record)history.push({key:row.definition.key,record:records[row.definition.key]||row.record,archived_at:new Date().toISOString()})
 records[row.definition.key]={planned:null,actual:null,reference_doc:'',model_id:row.modelId,master_data_version:row.modelVersion,template_version:settingsVersion}
 return next
}
export function settingsSummary(model:Model){
 const rows=generateSettings(model),active=new Set(rows.map(r=>r.id))
 const inactive=model.nodes.reduce((sum,n)=>sum+Object.keys((n.attributes?.l5_settings as object)||{}).filter(k=>!active.has(n.node_id+'.'+k)).length,0)
 return {rows,total:rows.length,missing:rows.filter(r=>r.stale||r.record?.planned==null||r.record?.planned===''||r.record?.actual==null||r.record?.actual==='').length,stale:rows.filter(r=>r.stale).length,inactive,manufacturerPending:rows.length}
}

export function materializeTemplateSettings(model:Model):Model{
 let next=model
 for(const row of generateSettings(model)){
  if(row.definition.group!=='通信'||!row.record||row.stale)continue
  const owner=row.portId?model.ports.find(p=>p.port_id===row.portId):model.nodes.find(n=>n.node_id===row.nodeId)
  if(!(owner?.attributes?.l5_settings as Record<string,SettingRecord>|undefined)?.[row.definition.key])next=updateSetting(next,row,'planned',row.record.planned)
 }
 return next
}
