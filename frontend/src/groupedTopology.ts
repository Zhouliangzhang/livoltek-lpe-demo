import type {Model,Node} from './types'
export type Point={x:number;y:number}
export type GroupDiagram={id:string;title:string;subtitle:string;model:Model;positions:Record<string,Point>;references:Set<string>;height:number}
const order=(a:Node,b:Node)=>a.node_id.localeCompare(b.node_id,undefined,{numeric:true})

/** View-only partition from recorded electrical paths, never writes engineering relationships. */
export function groupedTopology(model:Model):GroupDiagram[]{
 const byId=new Map(model.nodes.map(n=>[n.node_id,n])),ports=new Map(model.ports.map(p=>[p.port_id,p]))
 const adjacency=new Map(model.nodes.map(n=>[n.node_id,new Set<string>()]))
 for(const e of model.edges.filter(e=>e.edge_type==='ELECTRICAL')){
  const a=ports.get(e.from_port_id)?.node_id,b=ports.get(e.to_port_id)?.node_id
  if(a&&b){adjacency.get(a)?.add(b);adjacency.get(b)?.add(a)}
 }
 const main=new Set(model.nodes.filter(n=>['PCC','TRANSFORMER','TRANSFORMER_ZONE','LOAD','MV_BUS'].includes(n.node_type)).map(n=>n.node_id))
 const path=(start:string,end:string)=>{
  const queue=[start],parent=new Map<string,string|null>([[start,null]])
  for(let i=0;i<queue.length;i++){const n=queue[i];if(n===end)break;for(const next of adjacency.get(n)||[])if(!parent.has(next)){parent.set(next,n);queue.push(next)}}
  if(!parent.has(end))return
  let current:string|null=end;while(current){main.add(current);current=parent.get(current)??null}
 }
 const pcc=model.nodes.filter(n=>n.node_type==='PCC')
 for(const root of pcc)for(const n of model.nodes.filter(n=>['TRANSFORMER','LOAD'].includes(n.node_type)))path(root.node_id,n.node_id)
 const ownership=new Map<string,string>();for(const id of main)ownership.set(id,'main')
 const controlTypes=new Set(['EMS','METER'])
 for(const [group,type] of [['pv','PV_INVERTER'],['bess','BESS']]){
  const queue=model.nodes.filter(n=>n.node_type===type).sort(order).map(n=>n.node_id)
  for(let i=0;i<queue.length;i++){
   const id=queue[i];if(ownership.has(id)||controlTypes.has(byId.get(id)!.node_type))continue
   ownership.set(id,group)
   for(const other of adjacency.get(id)||[])if(!ownership.has(other)&&!queue.includes(other))queue.push(other)
  }
 }
 for(const n of model.nodes)if(!ownership.has(n.node_id))ownership.set(n.node_id,'control')
 const definitions=[['main','主配电','变压器低压端 → 总进线 / PCC → 主母线 → 工厂负载'],['pv','光伏汇流','按已录入汇流柜与支路自动排列 · 每台设备独立呈现'],['bess','储能汇流','按已录入汇流柜与支路自动排列 · 双向充放电路径'],['control','通信控制','计量反馈、通信网络及逻辑控制 · 引用主设备不重复建档']]
 const edgeGroup=(e:Model['edges'][number])=>{
  if(e.edge_type!=='ELECTRICAL')return 'control'
  const a=ownership.get(ports.get(e.from_port_id)?.node_id||''),b=ownership.get(ports.get(e.to_port_id)?.node_id||'')
  return a==='control'||b==='control'?'control':a==='pv'||b==='pv'?'pv':a==='bess'||b==='bess'?'bess':'main'
 }
 return definitions.map(([id,title,subtitle])=>{
  const edges=model.edges.filter(e=>edgeGroup(e)===id),owned=model.nodes.filter(n=>ownership.get(n.node_id)===id)
  const included=new Set(owned.map(n=>n.node_id));for(const e of edges)for(const p of [e.from_port_id,e.to_port_id]){const n=ports.get(p)?.node_id;if(n)included.add(n)}
  const nodes=model.nodes.filter(n=>included.has(n.node_id)).sort(order),references=new Set(nodes.filter(n=>ownership.get(n.node_id)!==id).map(n=>n.node_id))
  const positions:Record<string,Point>={};let height=440
  if(id==='pv'||id==='bess'){
   const roots=[...references].filter(n=>ownership.get(n)==='main').sort(),depth=new Map<string,number>(),queue=[...roots]
   roots.forEach(n=>depth.set(n,0))
   for(let i=0;i<queue.length;i++)for(const next of adjacency.get(queue[i])||[])if(included.has(next)&&!depth.has(next)){depth.set(next,depth.get(queue[i])!+1);queue.push(next)}
   // Allocate leaf slots first; upstream equipment centers over its recorded descendants.
   const children=(n:string)=>[...(adjacency.get(n)||[])].filter(x=>included.has(x)&&depth.get(x)===(depth.get(n)??0)+1).sort()
   let leaf=0;const xs=new Map<string,number>()
   const place=(n:string):number=>{if(xs.has(n))return xs.get(n)!;const kids=children(n);const x=kids.length?kids.map(place).reduce((a,b)=>a+b,0)/kids.length:leaf++*138;xs.set(n,x);return x}
   roots.forEach(place)
   for(const n of nodes){if(!depth.has(n.node_id)){depth.set(n.node_id,0);xs.set(n.node_id,leaf++*138)}positions[n.node_id]={x:xs.get(n.node_id)??place(n.node_id),y:40+depth.get(n.node_id)!*110}}
   height=Math.max(420,150+Math.max(0,...depth.values())*110)
  }else if(id==='main'){
   const roots=model.nodes.filter(n=>n.node_type==='TRANSFORMER'&&included.has(n.node_id));const seen=new Set<string>();let col=0
   const walk=(n:string)=>{if(seen.has(n))return;seen.add(n);positions[n]={x:col++*170,y:150};for(const next of [...(adjacency.get(n)||[])].sort())if(included.has(next))walk(next)}
   roots.forEach(n=>walk(n.node_id));for(const n of nodes)if(!seen.has(n.node_id))positions[n.node_id]={x:0,y:20}
   height=330
  }else{
   const primary=owned.filter(n=>n.node_type==='EMS').sort(order)
   const rest=owned.filter(n=>n.node_type!=='EMS').sort(order)
   primary.forEach((n,i)=>positions[n.node_id]={x:220+i*360,y:180})
   rest.forEach((n,i)=>positions[n.node_id]={x:(i%7)*180,y:Math.floor(i/7)*100})
   const refs=nodes.filter(n=>references.has(n.node_id)),pv=refs.filter(n=>n.node_type==='PV_INVERTER'),bess=refs.filter(n=>n.node_type==='BESS'),other=refs.filter(n=>!['PV_INVERTER','BESS'].includes(n.node_type))
   pv.forEach((n,i)=>positions[n.node_id]={x:(i%10)*138,y:340+Math.floor(i/10)*100})
   const bessY=340+Math.max(1,Math.ceil(pv.length/10))*130
   bess.forEach((n,i)=>positions[n.node_id]={x:(i%10)*138,y:bessY+Math.floor(i/10)*100})
   other.forEach((n,i)=>positions[n.node_id]={x:i*180,y:bessY+Math.max(1,Math.ceil(bess.length/10))*130})
   height=230+bessY+Math.max(1,Math.ceil(bess.length/10))*130
  }
  return {id,title,subtitle,positions,references,height,model:{...model,nodes,edges,ports:model.ports.filter(p=>included.has(p.node_id))}}
 })
}

export function compactNodeLabel(n:Node){
 if(['PV_INVERTER','BESS'].includes(n.node_type))return n.name.replace(/ · .*/,'')+'\n'+(n.name.split(' · ')[1]||n.node_type)
 const [name,rating]=n.name.split(' · ')
 return name+'\n'+(rating||n.node_id)
}
