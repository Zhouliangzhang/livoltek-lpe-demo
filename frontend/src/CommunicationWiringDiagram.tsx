import type {Model,Edge,Port} from './types'
type Route={edge:Edge;from:Port;to:Port;group:string}
export function cableLabel(domain:string){return domain==='RS485'?'RS485 通信线':domain==='ETHERNET'?'以太网线':domain==='CAN'?'CAN 通信线':'信号线'}
export function CommunicationWiringDiagram({model,routes,selected,onSelect}:{model:Model;routes:Route[];selected?:string;onSelect:(id:string)=>void}){
 const ids=[...new Set(routes.flatMap(r=>[r.from.node_id,r.to.node_id]))]
 const nodes=ids.map(id=>model.nodes.find(n=>n.node_id===id)!),pv=nodes.filter(n=>n.node_type==='PV_INVERTER'),bess=nodes.filter(n=>n.node_type==='BESS'),ems=nodes.filter(n=>n.node_type==='EMS'),meters=nodes.filter(n=>n.node_type==='METER')
 const neighbours=(id:string)=>routes.filter(r=>[r.from.node_id,r.to.node_id].includes(id)).map(r=>r.from.node_id===id?r.to.node_id:r.from.node_id)
 const buses=nodes.filter(n=>!pv.includes(n)&&!ems.includes(n)&&neighbours(n.node_id).some(id=>pv.some(p=>p.node_id===id)))
 const switches=nodes.filter(n=>!bess.includes(n)&&!ems.includes(n)&&neighbours(n.node_id).some(id=>bess.some(p=>p.node_id===id)))
 type Box={x:number;y:number;w:number;h:number;role:string}
 const boxes:Record<string,Box>={};const rows=Math.max(pv.length,bess.length,1),height=Math.max(500,rows*76+330)
 pv.forEach((n,i)=>boxes[n.node_id]={x:20,y:290+i*76,w:210,h:60,role:'pv'})
 bess.forEach((n,i)=>boxes[n.node_id]={x:1330,y:290+i*76,w:210,h:60,role:'bess'})
 ems.forEach((n,i)=>boxes[n.node_id]={x:760+i*260,y:30,w:240,h:150,role:'ems'})
 meters.forEach((n,i)=>boxes[n.node_id]={x:360,y:30+i*170,w:210,h:150,role:'meter'})
 buses.forEach((n,i)=>boxes[n.node_id]={x:500+i*240,y:260,w:210,h:rows*76+36,role:'bus'})
 switches.forEach((n,i)=>boxes[n.node_id]={x:850+i*240,y:260,w:210,h:rows*76+36,role:'switch'})
 let extra=0;for(const n of nodes)if(!boxes[n.node_id]){boxes[n.node_id]={x:20,y:30+extra*160,w:180,h:150,role:'other'};extra++}
 function anchor(p:Port,peer:Port){const b=boxes[p.node_id],other=boxes[peer.node_id];let x=b.x,y=b.y+100,side='left'
  if(b.role==='pv'){x=b.x+b.w;y=b.y+43;side='right'}
  else if(b.role==='bess'){y=b.y+43}
  else if(b.role==='bus'){if(other.role==='pv'){y=other.y+43}else{x=b.x+b.w/2;y=b.y;side='top'}}
  else if(b.role==='switch'){if(other.role==='bess'){x=b.x+b.w;y=other.y+43;side='right'}else{x=b.x+b.w/2;y=b.y;side='top'}}
  else if(b.role==='ems'){if(other.role==='bus'){x=b.x+40;y=b.y+b.h;side='bottom'}else if(other.role==='switch'){x=b.x+b.w-40;y=b.y+b.h;side='bottom'}}
  else if(other.x>b.x){x=b.x+b.w;side='right'}
  return {x,y,side}
 }
 const ports=new Map<string,{port:Port;peer:Port}>();for(const r of routes){ports.set(r.from.port_id,{port:r.from,peer:r.to});ports.set(r.to.port_id,{port:r.to,peer:r.from})}
 return <div className="wiringScroll totalWiring"><svg className="wiringSvg" viewBox={`0 0 1560 ${height}`} style={{minWidth:1200}} aria-label="系统通信接线总图">
 <text x={20} y={238} className="totalLane">光伏 · {pv.length} 台</text><text x={1330} y={238} className="totalLane">储能 · {bess.length} 台</text>
 {routes.map(r=>{const a=anchor(r.from,r.to),b=anchor(r.to,r.from),active=selected===r.edge.edge_id,vertical=['top','bottom'].includes(a.side)||['top','bottom'].includes(b.side),midY=220,mid=(a.x+b.x)/2,path=vertical?`M${a.x},${a.y} V${midY} H${b.x} V${b.y}`:`M${a.x},${a.y} H${mid} V${b.y} H${b.x}`,labelX=vertical?mid:(a.x+b.x)/2,labelY=vertical?midY:b.y,labelW=vertical?164:Math.min(210,Math.max(136,Math.abs(a.x-b.x)-18));return <g key={r.edge.edge_id} role="button" tabIndex={0} aria-label={'查看连接 '+r.edge.edge_id+' '+r.from.port_id+' 到 '+r.to.port_id} aria-pressed={active} className={'wiringLink '+(active?'selected':'')} data-edge-id={r.edge.edge_id} onClick={()=>onSelect(r.edge.edge_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(r.edge.edge_id)}}}><title>{r.from.port_id+' → '+r.to.port_id+' · '+cableLabel(r.from.domain)+' · 规格待厂家确认'}</title><path d={path} className="wiringHit"/><path d={path} className={'wiringStroke '+r.from.domain}/><rect x={labelX-labelW/2} y={labelY-24} width={labelW} height={46} rx={8}/><text x={labelX} y={labelY-6} textAnchor="middle">{cableLabel(r.from.domain)}</text><text className="wiringPending" x={labelX} y={labelY+10} textAnchor="middle">待厂家确认 · {r.edge.edge_id}</text></g>})}
 {nodes.map(n=>{const b=boxes[n.node_id],bus=b.role==='bus';return <g key={n.node_id} data-node-id={n.node_id} className={'wiringDevice '+(bus?'logical':'')}><rect x={b.x} y={b.y} width={b.w} height={b.h} rx={10}/><text x={b.x+12} y={b.y+22} className="wiringNodeName">{['pv','bess'].includes(b.role)?n.node_id.replace('_',' ')+' · '+(b.role==='pv'?'光伏':'储能'):b.role==='ems'?'iEMS · 系统控制器':b.role==='bus'?'光伏 RS485 逻辑总线':b.role==='switch'?'工业交换机':n.name.split(' · ')[0]}</text>{!['pv','bess'].includes(b.role)&&<text x={b.x+12} y={b.y+42} className="wiringNodeId">{n.node_id}</text>}{bus&&<text x={b.x+12} y={b.y+60} className="wiringNodeId">逻辑连接 · 非星形接线施工图</text>}{[...ports.values()].filter(v=>v.port.node_id===n.node_id).map(({port,peer})=>{const a=anchor(port,peer);return <g key={port.port_id}><circle cx={a.x} cy={a.y} r={4}/><text x={a.x+(a.side==='left'?10:a.side==='right'?-10:0)} y={a.y+(a.side==='top'?-10:a.side==='bottom'?-12:4)} textAnchor={a.side==='left'?'start':a.side==='right'?'end':'middle'} className="wiringPort">{port.name}</text></g>})}</g>})}
 </svg></div>
}
