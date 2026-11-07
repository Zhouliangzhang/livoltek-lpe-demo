import type {Model,Port} from './types'
export const communicationDomains=['ETHERNET','RS485','CAN']
export const sharedKeys:Record<string,string[]>={RS485:['baud_rate','parity','stop_bits'],CAN:['can_bitrate','can_protocol'],ETHERNET:[]}
export function connectedPorts(model:Model){
 const ids=new Set(model.edges.filter(e=>e.edge_type==='COMMUNICATION').flatMap(e=>[e.from_port_id,e.to_port_id]))
 return model.ports.filter(p=>ids.has(p.port_id)&&communicationDomains.includes(p.domain))
}
export function communicationBuses(model:Model){
 const ports=connectedPorts(model),parent=new Map(ports.map(p=>[p.port_id,p.port_id]))
 const root=(id:string):string=>parent.get(id)===id?id:root(parent.get(id)!)
 const join=(a:string,b:string)=>{if(parent.has(a)&&parent.has(b))parent.set(root(a),root(b))}
 for(const e of model.edges.filter(e=>e.edge_type==='COMMUNICATION')){
  const a=ports.find(p=>p.port_id===e.from_port_id),b=ports.find(p=>p.port_id===e.to_port_id)
  if(a&&b&&a.domain===b.domain)join(a.port_id,b.port_id)
 }
 for(const n of model.nodes){
  // Only an explicit passive bus or network switch bridges its ports; never a controller.
  if(!['COMM_BUS','COMMUNICATION_BUS','NETWORK_SWITCH'].includes(n.node_type)&&n.attributes?.communication_bridge!==true&&n.node_type!=='JUNCTION')continue
  for(const domain of communicationDomains){const pp=ports.filter(p=>p.node_id===n.node_id&&p.domain===domain);for(const p of pp.slice(1))join(pp[0].port_id,p.port_id)}
 }
 const groups=new Map<string,Port[]>()
 for(const p of ports){const id=root(p.port_id);groups.set(id,[...(groups.get(id)||[]),p])}
 return [...groups.values()].map(pp=>({id:pp.map(p=>p.port_id).sort().join('|'),domain:pp[0].domain,ports:pp,name:pp.some(p=>p.node_id==='METER_PCC')?'零馈计量':pp.some(p=>p.node_id.startsWith('PV_'))?'光伏通信':pp.some(p=>p.node_id.startsWith('BESS_'))?'储能通信':'设备通信'}))
}
export type CommunicationTemplate={id:string;version:string;domain:string;values:Record<string,string|number|null>;reference_doc:string;status:string}
export function modelTemplates(model:Model,nodeId:string):CommunicationTemplate[]{
 const n=model.nodes.find(n=>n.node_id===nodeId),a=model.device_assets.find(a=>a.asset_id===n?.device_asset_id),d=model.device_models.find(d=>d.model_id===a?.model_id)
 const templates=d?.communication_templates as (CommunicationTemplate&{master_data_version:string})[]|undefined
 return (templates||[]).filter(t=>t.master_data_version===d?.master_data_version&&communicationDomains.includes(t.domain))
}
