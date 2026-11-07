import type {Model} from './types'
export type CheckItem={id:string;stage:string;title:string;target_id:string;name:string;detail:string;node_ids:string[];method:string;expected:string;manufacturer_pending:string;source_status:string;template_version:string;layer:string}
export type CheckGroup={id:string;title:string;family:string;items:CheckItem[]}
// Group presentation only. Original item IDs remain the record and photo ownership keys.
export function groupChecks(items:CheckItem[],model:Model):CheckGroup[]{
 const groups=new Map<string,CheckGroup>()
 const structureNames:Record<string,string>={BREAKER:'断路器',LV_BUS:'低压母线',JUNCTION:'汇流节点',PCC:'并网点',LOAD:'负载',TRANSFORMER:'变压器',SWITCH:'开关',OTHER:'接口对象'}
 for(const item of items){
  const models=item.node_ids.map(id=>{const node=model.nodes.find(n=>n.node_id===id),asset=model.device_assets.find(a=>a.asset_id===node?.device_asset_id),device=model.device_models.find(d=>d.model_id===asset?.model_id);return {node,asset,device}})
  const signature=models.map(({node,asset,device})=>device?[node?.node_type,device.model_id,device.manufacturer,device.master_data_version]:asset?['unknown',asset.asset_id]:['structure',node?.node_type])
  const edge=model.edges.find(e=>e.edge_id===item.target_id),domains=edge?[edge.from_port_id,edge.to_port_id].map(id=>{const p=model.ports.find(p=>p.port_id===id);return [p?.domain,p?.role]}):[]
  const key=JSON.stringify([item.stage,item.title,item.method,item.expected,item.manufacturer_pending,item.source_status,item.template_version,signature,domains])
  const family=[...new Set(models.flatMap(({device})=>device?[device.manufacturer+' '+device.model_name]:[]))].join(' ↔ ')||models.map(({node})=>structureNames[node?.node_type||'']||'电气结构').join(' → ')
  if(!groups.has(key))groups.set(key,{id:item.id,title:item.title,family,items:[]})
  groups.get(key)!.items.push(item)
 }
 return [...groups.values()].map(g=>g.items.length===1?{...g,family:g.items[0].name}:g)
}
