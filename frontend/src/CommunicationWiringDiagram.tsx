import type {Model,Edge,Port} from './types'
type Route={edge:Edge;from:Port;to:Port;group:string}
export function cableLabel(domain:string){return domain==='RS485'?'RS485 通信线':domain==='ETHERNET'?'以太网线':domain==='CAN'?'CAN 通信线':'信号线'}
export function CommunicationWiringDiagram({model,routes,selected,onSelect}:{model:Model;routes:Route[];selected?:string;onSelect:(id:string)=>void}){
 const ids=[...new Set(routes.flatMap(r=>[r.from.node_id,r.to.node_id]))]
 const level:Record<string,number>={};ids.forEach(id=>level[id]=0)
 // Bound iterations; retain every original route even for unusual cyclic engineering drafts.
 for(let i=0;i<ids.length;i++){let changed=false;for(const r of routes){if(r.from.node_id===r.to.node_id)continue;const next=Math.min(2,level[r.from.node_id]+1);if(level[r.to.node_id]<next){level[r.to.node_id]=next;changed=true}}if(!changed)break}
 const columns=[...new Set(Object.values(level))].sort(),maxLevel=Math.max(...columns,0)
 const inPorts=(id:string)=>[...new Map(routes.filter(r=>r.to.node_id===id).map(r=>[r.to.port_id,r.to])).values()]
 const outPorts=(id:string)=>[...new Map(routes.filter(r=>r.from.node_id===id).map(r=>[r.from.port_id,r.from])).values()]
 const boxHeight=(id:string)=>Math.max(140,Math.max(inPorts(id).length,outPorts(id).length)*160-20)
 const total=(l:number)=>ids.filter(id=>level[id]===l).reduce((v,id)=>v+boxHeight(id)+20,0)
 const height=Math.max(220,...columns.map(total))+40,width=maxLevel*550+300
 const positions:Record<string,{x:number;y:number;h:number}>={}
 for(const l of columns){let y=(height-total(l))/2;for(const id of ids.filter(id=>level[id]===l)){positions[id]={x:20+l*550,y,h:boxHeight(id)};y+=boxHeight(id)+20}}
 function anchor(p:Port,side:'in'|'out'){const pos=positions[p.node_id],ports=side==='in'?inPorts(p.node_id):outPorts(p.node_id),i=ports.findIndex(x=>x.port_id===p.port_id);return{x:pos.x+(side==='out'?260:0),y:ports.length>1?pos.y+102+i*160:pos.y+64+(pos.h-64)/2}}
 return <div className="wiringScroll"><svg className="wiringSvg" viewBox={`0 0 ${width} ${height}`} style={{minWidth:maxLevel>1?1100:850}} aria-label={routes[0]?.group+' 端口接线图'}>
 {routes.map(r=>{const a=anchor(r.from,'out'),b=anchor(r.to,'in'),mid=(a.x+b.x)/2,path=`M${a.x},${a.y} H${mid} V${b.y} H${b.x}`,active=selected===r.edge.edge_id;return <g key={r.edge.edge_id} role="button" tabIndex={0} aria-label={'查看连接 '+r.edge.edge_id+' '+r.from.port_id+' 到 '+r.to.port_id} aria-pressed={active} className={'wiringLink '+(active?'selected':'')} data-edge-id={r.edge.edge_id} onClick={()=>onSelect(r.edge.edge_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(r.edge.edge_id)}}}><title>{r.from.port_id+' → '+r.to.port_id+' · '+cableLabel(r.from.domain)+' · 规格待厂家确认'}</title><path d={path} className="wiringHit"/><path d={path} className={'wiringStroke '+r.from.domain}/><rect x={mid-107} y={b.y-26} width={214} height={49} rx={8}/><text x={mid} y={b.y-7} textAnchor="middle">{cableLabel(r.from.domain)}</text><text className="wiringPending" x={mid} y={b.y+11} textAnchor="middle">规格待厂家确认 · {r.edge.edge_id}</text></g>})}
 {ids.map(id=>{const pos=positions[id],n=model.nodes.find(n=>n.node_id===id)!,bus=!n.device_asset_id&&['COMM_BUS','COMMUNICATION_BUS','JUNCTION'].includes(n.node_type);return <g key={id} className={'wiringDevice '+(bus?'logical':'')}><rect x={pos.x} y={pos.y} width={260} height={pos.h} rx={12}/><text x={pos.x+16} y={pos.y+25} className="wiringNodeName">{n.name.length>24?n.name.slice(0,24)+'…':n.name}</text><text x={pos.x+16} y={pos.y+45} className="wiringNodeId">{id}{bus?' · 逻辑总线，非实体接线盒':''}</text>{(['in','out'] as const).map(side=>(side==='in'?inPorts(id):outPorts(id)).map(p=>{const a=anchor(p,side);return <g key={side+p.port_id}><circle cx={a.x} cy={a.y} r={5}/><text x={a.x+(side==='in'?12:-12)} y={a.y+4} textAnchor={side==='in'?'start':'end'} className="wiringPort">{p.name}</text></g>}))}</g>})}
 </svg></div>
}
