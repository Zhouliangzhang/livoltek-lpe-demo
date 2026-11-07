import {useEffect,useRef} from 'react'
import {Graph} from '@antv/x6'
import type {Model,Kind,Flow} from './types'

export const colors:Record<Kind,string>={ELECTRICAL:'#16a085',COMMUNICATION:'#4488de',CONTROL:'#bc81e9'}
const symbols:Record<string,string>={PCC:'⌁',BESS:'▥',EMS:'▤',METER:'◉',PV_INVERTER:'☀',LOAD:'▦',BREAKER:'⊟',LV_BUS:'━',GENERATOR:'G',ATS:'⇄',TRANSFORMER:'◎'}
// Display geometry is derived from recorded connections, never written back to the model.
export function automaticPositions(model:Model){
 const adjacency=new Map(model.nodes.map(n=>[n.node_id,new Set<string>()]))
 const owner=new Map(model.ports.map(p=>[p.port_id,p.node_id]))
 for(const e of model.edges.filter(e=>e.edge_type==='ELECTRICAL')){const a=owner.get(e.from_port_id),b=owner.get(e.to_port_id);if(a&&b&&a!==b){adjacency.get(a)?.add(b);adjacency.get(b)?.add(a)}}
 const ranks=new Map<string,number>(),queue:string[]=[]
 for(const n of model.nodes.filter(n=>n.node_type==='PCC').sort((a,b)=>a.node_id.localeCompare(b.node_id))){ranks.set(n.node_id,0);queue.push(n.node_id)}
 for(let i=0;i<queue.length;i++){const id=queue[i];for(const next of [...(adjacency.get(id)||[])].sort()){if(!ranks.has(next)){ranks.set(next,ranks.get(id)!+1);queue.push(next)}}}
 const groups=new Map<number,string[]>()
 for(const n of [...model.nodes].sort((a,b)=>a.node_id.localeCompare(b.node_id))){const rank=ranks.get(n.node_id)??-1;groups.set(rank,[...(groups.get(rank)||[]),n.node_id])}
 const positions:Record<string,{x:number;y:number}>={}
 const height=Math.max(1,...[...groups.entries()].filter(([r])=>r>=0).map(([,ids])=>ids.length))*125
 for(const [rank,ids] of groups){ids.forEach((id,i)=>{positions[id]=rank<0?{x:(i%5)*245,y:height+70+Math.floor(i/5)*125}:{x:rank*245,y:i*125}})}
 return positions
}
export function Topology({model,flows}:{model:Model;flows:Record<string,Flow>}) {
 const container=useRef<HTMLDivElement>(null)
 const graphRef=useRef<Graph|null>(null)
 useEffect(()=>{
  const graph=new Graph({container:container.current!,width:container.current!.clientWidth,height:410,background:{color:'#f6f9f9'},grid:{visible:true,size:20},interacting:false,panning:false,mousewheel:{enabled:true,minScale:0.15,maxScale:3},connecting:{allowBlank:false,allowNode:false,allowPort:false,validateMagnet:()=>false}})
  graphRef.current=graph
  const observer=new ResizeObserver(()=>{if(container.current){graph.resize(container.current.clientWidth,410);graph.zoomToFit({padding:32,maxScale:1})}})
  observer.observe(container.current!)
  return ()=>{observer.disconnect();graph.dispose();graphRef.current=null}
 },[])
 useEffect(()=>{
  const graph=graphRef.current;if(!graph)return
  const positions=automaticPositions(model)
  graph.clearCells()
  for(const n of model.nodes){
   const asset=model.device_assets.find(a=>a.asset_id===n.device_asset_id)
   const pos=positions[n.node_id]
   graph.addNode({id:n.node_id,x:pos.x,y:pos.y,width:180,height:76,shape:'rect',
    attrs:{body:{fill:asset?.equipment_origin==='THIRD_PARTY'?'#fff9f0':'#fff',stroke:asset?.equipment_origin==='THIRD_PARTY'?'#dba455':'#9dafbc',rx:12,ry:12,strokeWidth:1.5},label:{text:`${symbols[(n.icon_key||'').toUpperCase()]||symbols[n.node_type]||'◇'}  ${n.name}\n${asset?.modeling_level?.split('_')[0]||'BOUNDARY'} · ${n.node_type}`,fontSize:12,fill:'#203e50',textWrap:{width:162,height:65,ellipsis:true}}},
    ports:{groups:{power:{position:'bottom',attrs:{circle:{r:5,magnet:false,stroke:colors.ELECTRICAL,fill:'#fff'}}},comm:{position:'right',attrs:{circle:{r:5,magnet:false,stroke:colors.COMMUNICATION,fill:'#fff'}}},control:{position:'top',attrs:{circle:{r:5,magnet:false,stroke:colors.CONTROL,fill:'#fff'}}}},
     items:model.ports.filter(p=>p.node_id===n.node_id).map(p=>({id:p.port_id,group:['AC','DC'].includes(p.domain)?'power':p.domain==='CONTROL_LOGICAL'?'control':'comm',attrs:{circle:{title:p.name+' · '+p.domain}}}))}})
  }
  for(const e of model.edges){
   if(!model.view_layout.layer_visibility[e.edge_type])continue
   const a=model.ports.find(p=>p.port_id===e.from_port_id),b=model.ports.find(p=>p.port_id===e.to_port_id)
   if(!a||!b||!graph.getCellById(a.node_id)||!graph.getCellById(b.node_id))continue
   graph.addEdge({id:e.edge_id,source:{cell:a.node_id,port:a.port_id},target:{cell:b.node_id,port:b.port_id},router:{name:'manhattan',args:{padding:25}},connector:{name:'rounded'},zIndex:0,attrs:{line:{stroke:colors[e.edge_type],strokeWidth:2,strokeDasharray:e.edge_type==='CONTROL'?'5 5':undefined}},labels:[{attrs:{label:{text:e.edge_id,fill:'#668095',fontSize:10}}}]})
  }
  graph.zoomToFit({padding:32,maxScale:1})
 },[model])
 useEffect(()=>{
  for(const edge of graphRef.current?.getEdges()||[]){
   const semantic=model.edges.find(e=>e.edge_id===edge.id);if(semantic?.edge_type!=='ELECTRICAL')continue
   const f=flows[edge.id]
   edge.attr('line/class',f?.animate?(f.reverse?'flow reverse':'flow'):'')
   edge.attr('line/strokeDasharray',f?.animate?'8 5':'')
   edge.attr('line/targetMarker',f?.animate&&!f.reverse?{name:'classic',size:8}:null)
   edge.attr('line/sourceMarker',f?.animate&&f.reverse?{name:'classic',size:8}:null)
   edge.setLabels([{attrs:{label:{text:f?.available?`${edge.id} · ${f.value} kW 模拟`:`${edge.id} · 无有效测点`,fill:'#397669',fontSize:10}}}])
  }
 },[flows,model])
 return <div className="readonlyTopology"><div className="zoomControls" aria-label="拓扑缩放"><button aria-label="缩小拓扑" onClick={()=>graphRef.current?.zoom(-0.15,{minScale:0.15,maxScale:3})}>−</button><button aria-label="适应全部拓扑" onClick={()=>graphRef.current?.zoomToFit({padding:32,maxScale:1})}>适应</button><button aria-label="放大拓扑" onClick={()=>graphRef.current?.zoom(0.15,{minScale:0.15,maxScale:3})}>＋</button></div><div className="canvas" ref={container} data-testid="topology-canvas"/></div>
}
