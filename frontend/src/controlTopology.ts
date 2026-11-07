import type {GroupDiagram,Point} from './groupedTopology'

/** Display slices of existing edges, never inferred control or physical wiring. */
export function controlTopology(group:GroupDiagram):GroupDiagram[]{
 const model=group.model,ports=new Map(model.ports.map(p=>[p.port_id,p])),nodes=new Map(model.nodes.map(n=>[n.node_id,n]))
 const ends=(e:typeof model.edges[number])=>[ports.get(e.from_port_id)!.node_id,ports.get(e.to_port_id)!.node_id]
 const meters=new Set(model.nodes.filter(n=>n.node_type==='METER').map(n=>n.node_id))
 const taps=new Set(model.edges.filter(e=>e.edge_type==='ELECTRICAL'&&ends(e).some(n=>meters.has(n))).flatMap(ends).filter(n=>nodes.get(n)?.node_type==='SWITCH'))
 const pvBus=new Set(model.edges.filter(e=>e.edge_type==='COMMUNICATION'&&ends(e).some(n=>nodes.get(n)?.node_type==='PV_INVERTER')).flatMap(ends).filter(n=>nodes.get(n)?.node_type==='JUNCTION'))
 const bessHubs=new Set(model.edges.filter(e=>e.edge_type==='COMMUNICATION'&&ends(e).some(n=>nodes.get(n)?.node_type==='BESS')).flatMap(ends).filter(n=>nodes.get(n)?.node_type!=='BESS'))
 const route=(e:typeof model.edges[number])=>{
  const ids=ends(e)
  if(e.edge_type==='CONTROL')return 'hierarchy'
  if(ids.some(n=>meters.has(n)||taps.has(n)))return 'meter'
  if(e.edge_type==='COMMUNICATION'&&ids.some(n=>nodes.get(n)?.node_type==='PV_INVERTER'||pvBus.has(n)))return 'pv-network'
  if(e.edge_type==='COMMUNICATION'&&ids.some(n=>nodes.get(n)?.node_type==='BESS'||bessHubs.has(n)))return 'bess-network'
  return 'support'
 }
 const definitions=[
  ['meter','零馈计量','PCC 电压取样与 CT → 零馈表 → iEMS 主控；计量方向与协议仍待现场确认'],
  ['hierarchy','iEMS 统一控制','单台 iEMS → 10 台光伏 + 10 台储能；紫色虚线仅表示逻辑控制关系'],
  ['pv-network','光伏通信','iEMS → RS485 逻辑总线 → 10 台光伏逆变器；不是星形物理接线图'],
  ['bess-network','储能通信','iEMS → 工业交换机 → 10 台储能柜；只显示网络连接，不暗示读写授权'],
  ['support','辅助供电与控制器网络','辅助电源和控制器上联单独保留，避免与计量、指令线路交叉'],
 ]
 const preferred=(id:string)=>{
  if(meters.has(id)||taps.has(id))return 'meter'
  if(nodes.get(id)?.node_type==='EMS')return 'hierarchy'
  if(pvBus.has(id))return 'pv-network'
  if(model.edges.some(e=>route(e)==='bess-network'&&ends(e).includes(id)))return 'bess-network'
  return 'support'
 }
 return definitions.map(([key,title,subtitle])=>{
  const edges=model.edges.filter(e=>route(e)===key)
  const owned=model.nodes.filter(n=>!group.references.has(n.node_id)&&preferred(n.node_id)===key)
  const included=new Set([...owned.map(n=>n.node_id),...edges.flatMap(ends)])
  const visible=model.nodes.filter(n=>included.has(n.node_id)).sort((a,b)=>a.node_id.localeCompare(b.node_id,undefined,{numeric:true}))
  const references=new Set(visible.filter(n=>group.references.has(n.node_id)||preferred(n.node_id)!==key).map(n=>n.node_id))
  const positions:Record<string,Point>={},routes:Record<string,Point[]>={};let height=340
  if(key==='hierarchy'){
   const controllers=visible.filter(n=>n.node_type==='EMS')
   controllers.forEach((n,i)=>positions[n.node_id]={x:600+i*160,y:20})
   for(const [family,type] of ['PV_INVERTER','BESS'].entries()){
    visible.filter(n=>n.node_type===type).forEach((n,i)=>positions[n.node_id]={x:family*730+(i%5)*138,y:210+Math.floor(i/5)*130})
   }
   for(const e of edges){
    const [a,b]=ends(e),source=positions[a],target=positions[b]
    if(!source||!target)continue
    const family=nodes.get(b)?.node_type==='BESS'?1:0
    routes[e.edge_id]=target.y>210?[{x:source.x+60,y:110},{x:family*730+690,y:110},{x:family*730+690,y:target.y-30},{x:target.x+60,y:target.y-30}]:[{x:source.x+60,y:150},{x:target.x+60,y:150}]
   }
   height=520
  }else if(key==='pv-network'||key==='bess-network'){
   const devices=visible.filter(n=>n.node_type===(key==='pv-network'?'PV_INVERTER':'BESS'))
   const core=visible.filter(n=>!devices.includes(n))
   core.forEach((n,i)=>positions[n.node_id]={x:350+i*280,y:20})
   devices.forEach((n,i)=>positions[n.node_id]={x:(i%10)*138,y:200+Math.floor(i/10)*120})
   height=370+Math.max(0,Math.ceil(devices.length/10)-1)*120
  }else if(key==='meter'){
   const meter=visible.find(n=>n.node_type==='METER'),ems=visible.find(n=>n.node_type==='EMS')
   if(meter)positions[meter.node_id]={x:640,y:110}
   if(ems)positions[ems.node_id]={x:960,y:110}
   let other=0
   for(const n of visible){if(positions[n.node_id])continue
    positions[n.node_id]=n.node_type==='PCC'?{x:40,y:20}:taps.has(n.node_id)?{x:330,y:20}:{x:330,y:200+other++*100}
   }
   height=380
  }else{
   const ems=visible.filter(n=>n.node_type==='EMS'),other=visible.filter(n=>n.node_type!=='EMS')
   other.forEach((n,i)=>positions[n.node_id]={x:i*240,y:20})
   ems.forEach((n,i)=>positions[n.node_id]={x:220+i*350,y:200})
   height=360
  }
  // Preserve unfamiliar or incomplete objects instead of dropping them from the view.
  let unplaced=0;for(const n of visible)if(!positions[n.node_id])positions[n.node_id]={x:unplaced++*150,y:height-80}
  const usedPorts=new Set(edges.flatMap(e=>[e.from_port_id,e.to_port_id]))
  return {id:'control-'+key,title,subtitle,height,positions,routes,references,model:{...model,nodes:visible,edges,ports:model.ports.filter(p=>usedPorts.has(p.port_id))}}
 })
}
