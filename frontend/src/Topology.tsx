import {useEffect,useRef} from 'react'
import {Graph} from '@antv/x6'
import type {Model,Kind,Flow} from './types'

export const colors:Record<Kind,string>={ELECTRICAL:'#16a085',COMMUNICATION:'#4488de',CONTROL:'#bc81e9'}
const symbols:Record<string,string>={PCC:'⌁',BESS:'▥',EMS:'▤',METER:'◉',PV_INVERTER:'☀',LOAD:'▦',BREAKER:'⊟',LV_BUS:'━',GENERATOR:'G',ATS:'⇄',TRANSFORMER:'◎'}
export function Topology({model,onChange,onSelect,layer,flows}:{model:Model;onChange:(m:Model)=>void;onSelect:(id:string)=>void;layer:Kind;flows:Record<string,Flow>}) {
 const container=useRef<HTMLDivElement>(null)
 const graphRef=useRef<Graph|null>(null)
 const current=useRef({model,onChange,onSelect,layer});current.current={model,onChange,onSelect,layer}
 const rendering=useRef(false)
 const fitted=useRef(false)
 useEffect(()=>{
  const graph=new Graph({container:container.current!,width:container.current!.clientWidth,height:560,background:{color:'#f5f8fb'},grid:{visible:true,size:20},panning:true,mousewheel:{enabled:true,minScale:0.3,maxScale:2},
   connecting:{snap:true,allowBlank:false,allowNode:false,allowLoop:false,allowMulti:false,
    createEdge(){return this.createEdge({attrs:{line:{stroke:colors[current.current.layer],strokeWidth:2}},router:{name:'manhattan'},connector:{name:'rounded'}})},
    validateConnection({sourcePort,targetPort}){
     const {model,layer}=current.current
     const a=model.ports.find(p=>p.port_id===sourcePort),b=model.ports.find(p=>p.port_id===targetPort)
     if(!a||!b||a.node_id===b.node_id||a.domain!==b.domain)return false
     if(layer==='CONTROL')return a.domain==='CONTROL_LOGICAL'&&a.role!=='IN'&&b.role!=='OUT'
     return layer==='ELECTRICAL'?['AC','DC'].includes(a.domain):['ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO'].includes(a.domain)
    }}})
  graphRef.current=graph
  const observer=new ResizeObserver(()=>{if(container.current)graph.resize(container.current.clientWidth,560)})
  observer.observe(container.current!)
  graph.on('node:click',({node})=>current.current.onSelect(node.id))
  graph.on('edge:click',({edge})=>current.current.onSelect(edge.id))
  graph.on('node:moved',({node})=>{if(rendering.current)return;const m=structuredClone(current.current.model);m.view_layout.positions[node.id]=node.position();current.current.onChange(m)})
  graph.on('edge:connected',({edge,isNew})=>{if(rendering.current||!isNew)return;const m=structuredClone(current.current.model);m.edges.push({edge_id:edge.id,edge_type:current.current.layer,from_port_id:edge.getSourcePortId()!,to_port_id:edge.getTargetPortId()!,review_status:'DRAFT',attributes:{},design_ref:null});current.current.onChange(m)})
  return ()=>{observer.disconnect();graph.dispose();graphRef.current=null;fitted.current=false}
 },[])
 useEffect(()=>{
  const graph=graphRef.current;if(!graph)return
  rendering.current=true
  graph.clearCells()
  for(const n of model.nodes){
   const asset=model.device_assets.find(a=>a.asset_id===n.device_asset_id)
   const pos=model.view_layout.positions[n.node_id]||{x:60,y:60}
   graph.addNode({id:n.node_id,x:pos.x,y:pos.y,width:180,height:76,shape:'rect',
    attrs:{body:{fill:asset?.equipment_origin==='THIRD_PARTY'?'#fff9f0':'#fff',stroke:asset?.equipment_origin==='THIRD_PARTY'?'#dba455':'#9dafbc',rx:12,ry:12,strokeWidth:1.5},label:{text:`${symbols[(n.icon_key||'').toUpperCase()]||symbols[n.node_type]||'◇'}  ${n.name}\n${asset?.modeling_level?.split('_')[0]||'BOUNDARY'} · ${n.node_type}`,fontSize:12,fill:'#203e50',textWrap:{width:162,height:65,ellipsis:true}}},
    ports:{groups:{power:{position:'bottom',attrs:{circle:{r:5,magnet:true,stroke:colors.ELECTRICAL,fill:'#fff'}}},comm:{position:'right',attrs:{circle:{r:5,magnet:true,stroke:colors.COMMUNICATION,fill:'#fff'}}},control:{position:'top',attrs:{circle:{r:5,magnet:true,stroke:colors.CONTROL,fill:'#fff'}}}},
     items:model.ports.filter(p=>p.node_id===n.node_id).map(p=>({id:p.port_id,group:['AC','DC'].includes(p.domain)?'power':p.domain==='CONTROL_LOGICAL'?'control':'comm',attrs:{circle:{title:p.name+' · '+p.domain}}}))}})
  }
  for(const e of model.edges){
   if(!model.view_layout.layer_visibility[e.edge_type])continue
   const a=model.ports.find(p=>p.port_id===e.from_port_id),b=model.ports.find(p=>p.port_id===e.to_port_id)
   if(!a||!b||!graph.getCellById(a.node_id)||!graph.getCellById(b.node_id))continue
   graph.addEdge({id:e.edge_id,source:{cell:a.node_id,port:a.port_id},target:{cell:b.node_id,port:b.port_id},router:{name:'manhattan',args:{padding:25}},connector:{name:'rounded'},zIndex:0,attrs:{line:{stroke:colors[e.edge_type],strokeWidth:2,strokeDasharray:e.edge_type==='CONTROL'?'5 5':undefined}},labels:[{attrs:{label:{text:e.edge_id,fill:'#668095',fontSize:10}}}]})
  }
  rendering.current=false
  if(!fitted.current){graph.zoomToFit({padding:35,maxScale:1});fitted.current=true}
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
 return <div className="canvas" ref={container} data-testid="topology-canvas"/>
}
