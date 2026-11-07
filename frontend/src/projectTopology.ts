import type {Model,Node,Review} from './types'

export type ProjectSlot={key:string;type:string;name:string;layer:'L2'|'L3';rank:number}
export const templateVersion='L1-FRAMEWORK-DEMO-1'
// Presentation requirements derived from M1 V1.2 §§3, 7.7. They are not engineering assets or wiring.
export function projectSlots(model:Model):ProjectSlot[]{
 const p=model.project,features=new Set(p.energy_features as string[]),slots:ProjectSlot[]=[]
 const add=(key:string,type:string,name:string,layer:'L2'|'L3',rank:number)=>slots.push({key,type,name,layer,rank})
 if(features.has('GRID')||(p.operation_modes as string[]).includes('GRID_CONNECTED'))add('pcc','PCC','并网边界 PCC','L2',0)
 const multi=p.structure_code==='LV-02',mv=p.voltage_level==='MV'
 if(mv){add('mvbus','MV_BUS','中压母线','L2',1);add('feeder','FEEDER','中压馈线','L2',2)}
 const zones=multi?2:1
 for(let i=0;i<zones;i++){add('zone'+i,'TRANSFORMER_ZONE',multi?`台区 ${i+1} · 数量下限`:'单台区控制边界','L2',mv?3:1);add('transformer'+i,'TRANSFORMER',multi?`台区 ${i+1} 变压器`:'变压器边界','L2',mv?3:1);add('lvbus'+i,'LV_BUS',multi?`台区 ${i+1} 低压母线`:'低压母线','L2',mv?4:2)}
 if(p.structure_code==='MV-02')add('mvbus2','MV_BUS','分段 / 多母线边界待定义','L2',1)
 const rank=mv?5:3
 if(features.has('PV'))add('pv','PV_INVERTER','光伏设备位置','L3',rank)
 if(features.has('ESS'))add('ess','BESS','储能设备位置','L3',rank)
 if(features.has('DIESEL'))add('diesel','GENERATOR','柴油机设备位置','L3',rank)
 if(features.has('EV_CHARGING'))add('ev','EV_CHARGER','充电设备位置','L3',rank)
 add('load','LOAD','负载边界','L2',rank)
 add('ems','EMS',multi?'项目级协调器':'能源管理设备位置','L3',rank+1)
 return slots
}

export function projectFramework(model:Model){
 const slots=projectSlots(model),used=new Set<string>()
 const matched=slots.map(slot=>{
  const node=model.nodes.find(n=>n.node_type===slot.type&&!used.has(n.node_id))
  if(node)used.add(node.node_id)
  return {slot,node}
 })
 // Matching by type reports coverage only. It never assigns engineering ownership or connectivity.
 const rankFor=(n:Node)=>matched.find(x=>x.node?.node_id===n.node_id)?.slot.rank??(n.node_type==='BREAKER'?2:n.device_asset_id?3:1)
 const rows=new Map<number,number>(),positions:Record<string,{x:number;y:number}>={}
 for(const n of [...model.nodes].sort((a,b)=>rankFor(a)-rankFor(b)||a.node_id.localeCompare(b.node_id))){const rank=rankFor(n),row=rows.get(rank)||0;positions[n.node_id]={x:rank*245,y:row*120};rows.set(rank,row+1)}
 const missing=matched.filter(x=>!x.node).map(({slot})=>{const row=rows.get(slot.rank)||0;rows.set(slot.rank,row+1);return {...slot,id:'l1-placeholder-'+slot.key,position:{x:slot.rank*245,y:row*120}}})
 return {slots,matched,missing,positions}
}

export function completionEvidence(model:Model,reviews:Review[],revision:number){
 const framework=projectFramework(model)
 const structures=framework.matched.filter(x=>x.slot.layer==='L2')
 const identified=model.device_assets.filter(a=>a.serial_number&&model.device_models.some(d=>d.model_id===a.model_id&&d.master_data_version))
 const validEdges=model.edges.filter(e=>model.ports.some(p=>p.port_id===e.from_port_id)&&model.ports.some(p=>p.port_id===e.to_port_id))
 const parameters=model.parameters as {planned:unknown;actual:unknown;approved:unknown}[]
 const currentReviews=reviews.filter(r=>r.revision===revision)
 return [
  ['L2','电气结构',`${structures.filter(x=>x.node).length}/${structures.length} 类模板结构已录入`],
  ['L3','设备身份',`${identified.length}/${model.device_assets.length} 台具备 SN 与型号版本`],
  ['L4','端口连接',`${validEdges.length} 条端口关系已录入 · 待工程核对`],
  ['L5','配置参数',`${parameters.filter(p=>p.planned&&p.actual&&p.approved).length}/${parameters.length} 项三值齐备`],
  ['L6','工程评审',`${currentReviews.length} 条当前版本评审 · ${model.baseline.status}`],
 ]
}
