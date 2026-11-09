import type {Model,Node,Edge} from './types'
export type ElectricalGroup={id:string;title:string;nodes:Node[];edges:Edge[];references:Set<string>;positions:Record<string,{x:number;y:number}>;height:number}
export function effectiveElectricalEdges(model:Model,environment:string):Edge[]{
 const drafts=(model.project.electrical_drafts||[]) as {id:string;base_edge_id:string;environment:string;from_port_id:string;to_port_id:string}[]
 const local=drafts.filter(d=>d.environment===environment)
 return [...model.edges.filter(e=>e.edge_type==='ELECTRICAL').map(e=>{const d=local.find(d=>d.base_edge_id===e.edge_id);return d?{...e,from_port_id:d.from_port_id,to_port_id:d.to_port_id}:e}),...local.filter(d=>!d.base_edge_id).map(d=>({edge_id:d.id,edge_type:'ELECTRICAL' as const,from_port_id:d.from_port_id,to_port_id:d.to_port_id,review_status:'DRAFT'}))]
}
export function electricalView(model:Model){
 const ports=new Map(model.ports.map(p=>[p.port_id,p])),byId=new Map(model.nodes.map(n=>[n.node_id,n])),issues:string[]=[]
 const edges=model.edges.filter(e=>e.edge_type==='ELECTRICAL').filter(e=>{
  const a=ports.get(e.from_port_id),b=ports.get(e.to_port_id)
  if(!a||!b||!byId.has(a.node_id)||!byId.has(b.node_id)){issues.push(`${e.edge_id}：两端对象或端口缺失，待补；未绘制此线`);return false}
  if(!['AC','DC'].includes(a.domain)||a.domain!==b.domain){issues.push(`${e.edge_id}：电气端口域冲突，待核实；未绘制此线`);return false}return true
 })
 const connected=new Set(edges.flatMap(e=>[ports.get(e.from_port_id)!.node_id,ports.get(e.to_port_id)!.node_id]))
 const nodes=model.nodes.filter(n=>n.node_type!=='TRANSFORMER_ZONE'&&(connected.has(n.node_id)||model.ports.some(p=>p.node_id===n.node_id&&['AC','DC'].includes(p.domain))||['PCC','TRANSFORMER','LV_BUS','MV_BUS','BREAKER','FEEDER','LOAD','GRID','PV_INVERTER','BESS'].includes(n.node_type)))
 const ownership=new Map<string,string>()
 for(const n of nodes){
  const label=n.node_id+' '+n.name+' '+String((n.attributes?.engineering as Record<string,unknown>)?.purpose||'')
  ownership.set(n.node_id,['PV_INVERTER','PV_ARRAY'].includes(n.node_type)||/PV|光伏/i.test(label)?'pv':n.node_type==='BESS'||/BESS|储能/i.test(label)?'bess':n.node_type==='LOAD'||/LOAD|负载/i.test(label)?'load':'main')
  if(!model.ports.some(p=>p.node_id===n.node_id&&['AC','DC'].includes(p.domain)))issues.push(`${n.node_id}：待补电气端口定义`)
  else if(!connected.has(n.node_id))issues.push(`${n.node_id}：待补电气连接`)
  else if(['BREAKER','FEEDER'].includes(n.node_type)){const missing=model.ports.filter(p=>p.node_id===n.node_id&&['AC','DC'].includes(p.domain)&&!edges.some(e=>e.from_port_id===p.port_id||e.to_port_id===p.port_id));if(missing.length)issues.push(`${n.node_id}：待补回路端口连接 ${missing.map(p=>p.name).join('、')}`)}
 }
 const adjacency=new Map(nodes.map(n=>[n.node_id,[] as string[]]))
 for(const e of edges){const a=ports.get(e.from_port_id)!.node_id,b=ports.get(e.to_port_id)!.node_id;adjacency.get(a)?.push(b);adjacency.get(b)?.push(a)}
 const edgeGroup=(e:Edge)=>{const a=ownership.get(ports.get(e.from_port_id)!.node_id),b=ownership.get(ports.get(e.to_port_id)!.node_id);return a!=='main'?a:b||'main'}
 const groups:ElectricalGroup[]=[['main','主配电'],['pv','光伏'],['bess','储能'],['load','负载']].map(([id,title])=>{
  const es=edges.filter(e=>edgeGroup(e)===id),owned=nodes.filter(n=>ownership.get(n.node_id)===id),ids=new Set(owned.map(n=>n.node_id))
  es.forEach(e=>{ids.add(ports.get(e.from_port_id)!.node_id);ids.add(ports.get(e.to_port_id)!.node_id)})
  const ns=nodes.filter(n=>ids.has(n.node_id)),references=new Set(ns.filter(n=>ownership.get(n.node_id)!==id).map(n=>n.node_id))
  const links=new Map(ns.map(n=>[n.node_id,[] as string[]]));es.forEach(e=>{const a=ports.get(e.from_port_id)!.node_id,b=ports.get(e.to_port_id)!.node_id;links.get(a)?.push(b);links.get(b)?.push(a)})
  const rank=(n:Node)=>references.has(n.node_id)?0:['GRID','TRANSFORMER'].includes(n.node_type)?1:n.node_type==='PCC'?2:3
  const ordered=[...ns].sort((a,b)=>rank(a)-rank(b)||a.node_id.localeCompare(b.node_id,undefined,{numeric:true}))
  const depth=new Map<string,number>(),children=new Map<string,string[]>(),roots:string[]=[]
  for(const n of ordered){if(depth.has(n.node_id))continue;roots.push(n.node_id);depth.set(n.node_id,0);const queue=[n.node_id];for(let i=0;i<queue.length;i++){const p=queue[i];for(const next of links.get(p)||[]){if(depth.has(next))continue;depth.set(next,depth.get(p)!+1);children.set(p,[...(children.get(p)||[]),next]);queue.push(next)}}}
  let slot=0;const positions:ElectricalGroup['positions']={}
  const place=(id:string):number=>{const kids=children.get(id)||[],x=kids.length?kids.map(place).reduce((a,b)=>a+b,0)/kids.length:slot++*230;positions[id]={x,y:depth.get(id)!*155};return x}
  roots.forEach(place)
  if(id==='main')for(const pos of Object.values(positions)){const x=pos.x;pos.x=pos.y*1.45;pos.y=x*.65}
  return {id,title,nodes:ns,edges:es,references,positions,height:id==='main'?360:Math.max(300,140+Math.max(0,...depth.values())*155)}
 })
 return {groups,issues,connected}
}
/** Split separate recorded branches beneath shared upstream references for legible rendering. */
export function branchDiagrams(model:Model,group:ElectricalGroup):ElectricalGroup[]{
 if(!['pv','bess'].includes(group.id))return [group]
 const ports=new Map(model.ports.map(p=>[p.port_id,p])),seen=new Set<string>(),parts:Set<string>[]=[]
 for(const n of group.nodes){if(group.references.has(n.node_id)||seen.has(n.node_id))continue;const ids=new Set([n.node_id]),queue=[n.node_id];seen.add(n.node_id)
  for(let i=0;i<queue.length;i++)for(const e of group.edges){const a=ports.get(e.from_port_id)!.node_id,b=ports.get(e.to_port_id)!.node_id;const other=a===queue[i]?b:b===queue[i]?a:'';if(other&&!group.references.has(other)&&!seen.has(other)){seen.add(other);ids.add(other);queue.push(other)}}parts.push(ids)
 }
 if(parts.length<2)return [group]
 return parts.map((ids,i)=>{const edges=group.edges.filter(e=>ids.has(ports.get(e.from_port_id)!.node_id)||ids.has(ports.get(e.to_port_id)!.node_id));edges.forEach(e=>{ids.add(ports.get(e.from_port_id)!.node_id);ids.add(ports.get(e.to_port_id)!.node_id)})
  const sub={...model,nodes:model.nodes.filter(n=>ids.has(n.node_id)),edges};const g=electricalView(sub).groups.find(g=>g.id===group.id)!;return {...g,title:group.title+'支路组 '+(i+1)}
 })
}
