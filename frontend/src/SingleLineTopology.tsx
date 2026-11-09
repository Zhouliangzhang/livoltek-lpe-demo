import {useEffect,useMemo,useRef} from 'react'
import {Graph} from '@antv/x6'
import type {Model,Node} from './types'
import {electricalView,branchDiagrams,type ElectricalGroup} from './singleLineData'
import './singleLineTopology.css'
const symbol:Record<string,string>={TRANSFORMER:'◎',PCC:'◉',LV_BUS:'━',MV_BUS:'━',BREAKER:'⊟',PV_INVERTER:'☀',BESS:'▥',LOAD:'▦',FEEDER:'┬'}
export function SingleLineTopology({model,context='已录入工程草案'}:{model:Model;context?:string}){
 const view=useMemo(()=>electricalView(model),[model])
 return <section className="singleLine" aria-label="系统电气单线拓扑"><header className="singleLineTitle"><div><small>POWER SYSTEM / READ ONLY</small><h3>系统电气单线拓扑</h3><p>{context} · 主配电 / 光伏 / 储能 / 负载</p></div><span>{view.groups.reduce((s,g)=>s+g.edges.length,0)} 条有效端口关系</span></header><p className="singleLineLegend">实线仅表示已录入的电气端口连接；虚线边框为跨区对象引用。归属不生成连线，箭头不推定潮流方向。仅支持按钮缩放，滚轮上下浏览。</p>
 {view.issues.length>0&&<details className="singleLineIssues"><summary>待补 / 待核实 · {view.issues.length} 项（在步骤03–05补充）</summary><ul>{view.issues.map((s,i)=><li key={i}>{s}</li>)}</ul></details>}
 {view.groups.map((g,i)=><section className={'singleLineGroup singleLine-'+g.id} key={g.id} aria-label={g.title+'电气单线图'}><header><div><small>0{i+1}</small><h4>{g.title}</h4><span>{g.nodes.length-g.references.size} 个对象 · {g.edges.length} 条连接</span></div></header>{g.nodes.length?branchDiagrams(model,g).map((part,j)=><div key={j}>{part.title!==g.title&&<p className="singleLineLegend">{part.title} · 按已录入连接展开；上级母线为同一对象引用</p>}<SingleLineCanvas model={model} group={part} connected={view.connected}/></div>):<p className="singleLineEmpty">本组尚无对象，待按系统范围补充；不自动推定设备或连接。</p>}</section>)}
 <p className="singleLineLegend">未连通对象以橙色标注“待补”。备用端口不自动判为缺项。已录入不代表图纸批准、接线核验或可上电。</p></section>
}
function SingleLineCanvas({model,group,connected}:{model:Model;group:ElectricalGroup;connected:Set<string>}){
 const ref=useRef<HTMLDivElement>(null),graph=useRef<Graph|null>(null)
 useEffect(()=>{
  const g=new Graph({container:ref.current!,width:ref.current!.clientWidth,height:group.height,interacting:false,panning:false,mousewheel:{enabled:false},connecting:{allowBlank:false,allowNode:false,allowPort:false},background:{color:'#fbfcfa'}});graph.current=g
  const ports=new Map(model.ports.map(p=>[p.port_id,p]))
  for(const n of group.nodes){const pos=group.positions[n.node_id],missing=!connected.has(n.node_id),bus=['LV_BUS','MV_BUS'].includes(n.node_type),refNode=group.references.has(n.node_id)
   const ps=model.ports.filter(p=>p.node_id===n.node_id&&['AC','DC'].includes(p.domain))
   g.addNode({id:n.node_id,...pos,width:190,height:76,attrs:{body:{fill:missing?'#fff6e8':bus?'#edf5f0':'#fff',stroke:missing?'#c98a39':'#7e9c8c',strokeWidth:bus?3:1.4,strokeDasharray:refNode?'6 4':undefined,rx:bus?2:8,ry:bus?2:8},label:{text:`${symbol[n.node_type]||'◇'} ${n.node_id}${refNode?' · 跨区引用':''}\n${n.name}\n${missing?'待补端口 / 电气连接':n.node_type==='PCC'?'并网边界 · 按已录入位置表示':''}`,fontSize:13,fill:'#244d40',textWrap:{width:178,height:68,ellipsis:true}}},ports:{groups:{top:{position:group.id==='main'?'left':'top',attrs:{circle:{r:3,magnet:false,stroke:'#36896a',fill:'#fff'}}},bottom:{position:group.id==='main'?'right':'bottom',attrs:{circle:{r:3,magnet:false,stroke:'#36896a',fill:'#fff'}}}},items:ps.map(p=>{const upstream=group.edges.some(e=>{const other=e.from_port_id===p.port_id?ports.get(e.to_port_id):e.to_port_id===p.port_id?ports.get(e.from_port_id):undefined;return other&&(group.id==='main'?(group.positions[other.node_id]?.x??pos.x)<pos.x:(group.positions[other.node_id]?.y??pos.y)<pos.y)});return {id:p.port_id,group:upstream?'top':'bottom',attrs:{circle:{title:p.port_id+' · '+p.name}}}})}})
  }
  for(const e of group.edges){const a=ports.get(e.from_port_id)!,b=ports.get(e.to_port_id)!;g.addEdge({id:e.edge_id,source:{cell:a.node_id,port:a.port_id},target:{cell:b.node_id,port:b.port_id},router:{name:'manhattan',args:{padding:18}},connector:{name:'rounded',args:{radius:6}},zIndex:0,attrs:{line:{stroke:'#378368',strokeWidth:1.8,sourceMarker:null,targetMarker:null}},labels:[{position:.35,attrs:{label:{text:a.name+' ↔ '+b.name,fontSize:10,fill:'#416b5c'},body:{fill:'#fbfcfa'}}}]})}
  const fit=()=>{g.resize(ref.current!.clientWidth,group.height);g.zoomToFit({padding:38,maxScale:1})};const ro=new ResizeObserver(fit);ro.observe(ref.current!);fit();return()=>{ro.disconnect();g.dispose();graph.current=null}
 },[model,group,connected])
 return <><div className="singleLineZoom" aria-label={group.title+'缩放'}><button aria-label={'缩小'+group.title+'单线图'} onClick={()=>graph.current?.zoom(-.15,{minScale:.1,maxScale:3})}>−</button><button onClick={()=>graph.current?.zoomToFit({padding:38,maxScale:1})}>适应全图</button><button aria-label={'放大'+group.title+'单线图'} onClick={()=>graph.current?.zoom(.15,{minScale:.1,maxScale:3})}>＋</button></div><div ref={ref} data-testid={'single-line-'+group.id} style={{height:group.height}}/><details className="singleLinePorts"><summary>端口关系明细 · {group.edges.length} 条</summary><ul>{group.edges.map(e=><li key={e.edge_id}><b>{e.edge_id}</b> {e.from_port_id} ↔ {e.to_port_id} <small>依据待核验</small></li>)}</ul></details></>
}
export function StructureTree({model,expanded=false}:{model:Model;expanded?:boolean}){
 const nodes=model.nodes.filter(n=>!n.device_asset_id),ids=new Set(nodes.map(n=>n.node_id)),seen=new Set<string>()
 function branch(n:Node):React.ReactNode{if(seen.has(n.node_id))return <li key={n.node_id+'cycle'}>归属循环：{n.node_id} · 待修正</li>;seen.add(n.node_id);const children=nodes.filter(x=>x.parent_node_id===n.node_id);return <li key={n.node_id}><span><b>{n.node_id}</b> {n.name}{n.parent_node_id&&!ids.has(n.parent_node_id)&&<em> 上级缺失 · 待补</em>}</span>{children.length>0&&<ul>{children.map(branch)}</ul>}</li>}
 const roots=nodes.filter(n=>!n.parent_node_id||!ids.has(n.parent_node_id)),tree=roots.map(branch),left=nodes.filter(n=>!seen.has(n.node_id))
 return <details className="structureTree" open={expanded||undefined}><summary>结构归属树 · {nodes.length} 个对象</summary><p>仅表示区域和结构归属，不表示电气接线。</p><ul>{tree}{left.filter(n=>!seen.has(n.node_id)).map(branch)}</ul></details>
}
