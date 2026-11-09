import {useEffect,useState} from 'react'
import {StructureTree} from './SingleLineTopology'
import type {Model,Node} from './types'
import './electricalStructure.css'
const types:Record<string,string>={PCC:'并网点 PCC',TRANSFORMER_ZONE:'变压器区',TRANSFORMER:'变压器',MV_BUS:'中压母线',LV_BUS:'低压母线',COMBINER:'汇流柜',FEEDER:'馈线',BREAKER:'断路器'}
type Details={circuit_id?:string;voltage_level?:string;phase_system?:string;purpose?:string;epc_drawing_ref?:string;manufacturer_ref?:string;structure_role?:string}
const metadata=(n:Node)=>(n.attributes?.engineering||{}) as Details
const kind=(n:Node)=>metadata(n).structure_role==='COMBINER'?'COMBINER':n.node_type
const included=(n:Node)=>!!types[n.node_type]&&!n.device_asset_id
export function ElectricalStructure({model,change,save,dirty,back,next,environment='OFFLINE'}:{environment?:string;model:Model;change:(m:Model)=>void;save:(m:Model)=>Promise<void>;dirty:boolean;back:()=>void;next:()=>void}){
 const rows=model.nodes.filter(included), boundary=model.project.system_boundary as {scope?:string;reference?:string;domains?:{id:string;pcc_id:string}[]}|undefined
 const [editing,setEditing]=useState<string|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[filter,setFilter]=useState('ALL'),[limit,setLimit]=useState(10)
 const blank=()=>({id:'',name:'',type:'FEEDER',parent:'',circuit:'',voltage:String(model.project.voltage_level),phase:'',purpose:'',epc:'',manufacturer:''})
 const [form,setForm]=useState(blank)
 useEffect(()=>{if(editing)document.querySelector('.structureEditor')?.scrollIntoView({block:'start'})},[editing])
 const field=(k:keyof typeof form,v:string)=>setForm(f=>({...f,[k]:v}))
 function open(n?:Node){setError('');setMessage('');setEditing(n?.node_id||'NEW');const d=n?metadata(n):{};setForm(n?{id:n.node_id,name:n.name,type:kind(n),parent:n.parent_node_id||'',circuit:d.circuit_id||'',voltage:d.voltage_level||'',phase:d.phase_system||'',purpose:d.purpose||'',epc:d.epc_drawing_ref||'',manufacturer:d.manufacturer_ref||''}:blank())}
 function descendant(id:string){let current=model.nodes.find(n=>n.node_id===id);const seen=new Set<string>();while(current){if(current.node_id===editing)return true;if(seen.has(current.node_id))return true;seen.add(current.node_id);current=model.nodes.find(n=>n.node_id===current?.parent_node_id)}return false}
 const parents=rows.filter(n=>!descendant(n.node_id))
 async function commit(){
  const id=form.id.trim(),circuit=form.circuit.trim();let reason=''
  if(!id||!form.name.trim())reason='请填写结构编号和名称。'
  else if(editing==='NEW'&&model.nodes.some(n=>n.node_id===id))reason='结构编号已存在，请使用唯一编号。'
  else if(!form.parent&&!['TRANSFORMER_ZONE','PCC'].includes(form.type))reason='请选择所属结构，明确本回路归属。'
  else if(['FEEDER','BREAKER'].includes(form.type)&&!circuit)reason='馈线和断路器需要回路编号。'
  else if(form.parent&&!parents.some(n=>n.node_id===form.parent))reason='所属结构无效或形成循环。'
  else if(!form.voltage)reason='请选择设计电压等级；额定值仍需依据核定。'
  if(reason){setError(reason);return}
  const m=structuredClone(model),old=m.nodes.find(n=>n.node_id===editing)
  let zone:string|null=form.type==='TRANSFORMER_ZONE'?id:null,ancestor=m.nodes.find(n=>n.node_id===form.parent);const seen=new Set<string>();while(ancestor&&!seen.has(ancestor.node_id)){seen.add(ancestor.node_id);if(ancestor.node_type==='TRANSFORMER_ZONE'){zone=ancestor.node_id;break}ancestor=m.nodes.find(n=>n.node_id===ancestor?.parent_node_id)}
  const n:Node={...(old||{}),node_id:id,logical_id:old?.logical_id||id,name:form.name.trim(),node_type:form.type==='COMBINER'?(form.voltage==='MV'?'MV_BUS':'LV_BUS'):form.type,parent_node_id:form.parent||null,zone_id:zone,device_asset_id:null,icon_key:form.type.toLowerCase(),relationship_reason:'ENERGY_PATH',attributes:{...old?.attributes,engineering:{circuit_id:circuit,voltage_level:form.voltage,phase_system:form.phase,purpose:form.purpose,epc_drawing_ref:form.epc.trim(),manufacturer_ref:form.manufacturer.trim(),structure_role:form.type==='COMBINER'?'COMBINER':'STRUCTURE',basis_status:'PENDING'}}}
  if(old)m.nodes=m.nodes.map(x=>x.node_id===old.node_id?n:x);else m.nodes.push(n)
  // Reparenting a branch must update descendant zone ownership as well.
  for(const child of m.nodes){if(child.node_id===id)continue;let a:Node|undefined=child;const visited=new Set<string>();let z:string|null=null,related=false;while(a&&!visited.has(a.node_id)){visited.add(a.node_id);if(a.node_id===id)related=true;if(z===null&&a.node_type==='TRANSFORMER_ZONE')z=a.node_id;a=m.nodes.find(x=>x.node_id===a?.parent_node_id)}if(related)child.zone_id=z}
  m.view_layout.positions[id]??={x:0,y:0}
  setBusy(true);setError('');try{await save(m);setEditing(null);setFilter(form.type);setLimit(10);setMessage('结构已保存，归属拓扑已更新；图纸与厂家引用仍待核验。')}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <article className="startCard electricalStep" aria-label="步骤03 电气结构"><div className="startCardHeading"><span>03</span><div><h2>建立电气结构</h2><p>先明确结构与回路归属，再在后续步骤定义设备端口和接线。</p></div></div>
 <section className="structureBoundary" aria-label="继承系统边界"><div><small>来自步骤02</small><strong>{boundary?.scope||'尚未填写系统范围'}</strong><p>{String(model.project.voltage_level)} · {model.project.structure_code} · {boundary?.domains?.map(d=>d.id+' / '+(d.pcc_id||'PCC 待建立')).join('；')||'控制域待定义'}</p></div><button onClick={back}>修改系统边界</button><p>项目依据：{boundary?.reference||'待 EPC 提供图纸及并网条件'}。项目引用不自动确认每个回路的设计。</p></section>
 <div className="structureToolbar"><div><h3>结构清单 <small>{rows.length} 个非 SN 对象</small></h3><p>汇流柜作为母线结构记录；不要求结构对象填写设备 SN。</p></div><select aria-label="结构清单筛选" value={filter} onChange={e=>{setFilter(e.target.value);setLimit(10)}}><option value="ALL">所有结构类型</option>{Object.entries(types).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select><button className="primary" onClick={()=>open()}>添加电气结构</button></div>
 <div className="structureTable"><table><thead><tr><th>结构 / 类型</th><th>所属结构与变压器区</th><th>回路</th><th>设计依据</th><th>操作</th></tr></thead><tbody>{rows.filter(n=>filter==='ALL'||kind(n)===filter).slice(0,limit).map(n=>{const d=metadata(n);return <tr key={n.node_id}><td><b>{n.name}</b><small>{n.node_id} · {types[kind(n)]}</small></td><td>{model.nodes.find(x=>x.node_id===n.parent_node_id)?.name||(n.parent_node_id?'归属无效':'项目根节点')}<small>区域：{model.nodes.find(x=>x.node_id===n.zone_id)?.name||'待 EPC 明确'}</small></td><td>{d.circuit_id||'待补回路编号'}<small>{d.voltage_level||'电压等级待确认'} · {d.phase_system||'相制待确认'}</small></td><td><span className="startTag">{d.epc_drawing_ref?'EPC 引用待核验':'待 EPC 补充图纸'}</span><small>{d.manufacturer_ref?'厂家引用待核验':'厂家规格依据待确认'}</small></td><td><button aria-label={'编辑结构 '+n.node_id} onClick={()=>open(n)}>编辑 / 补充</button></td></tr>})}</tbody></table></div>{rows.filter(n=>filter==='ALL'||kind(n)===filter).length>limit&&<button onClick={()=>setLimit(v=>v+10)}>再显示10个结构对象</button>}
 {editing&&<section className="structureEditor" aria-label="结构编辑"><header><h3>{editing==='NEW'?'添加结构对象':'补充结构与回路归属'}</h3><button onClick={()=>setEditing(null)}>取消编辑</button></header><div className="startForm"><label>结构编号<input aria-label="结构编号" value={form.id} disabled={editing!=='NEW'} maxLength={128} onChange={e=>field('id',e.target.value)}/></label><label>结构名称<input aria-label="结构名称" value={form.name} maxLength={128} onChange={e=>field('name',e.target.value)}/></label><label>结构类型<select aria-label="结构类型" value={form.type} disabled={editing!=='NEW'} onChange={e=>field('type',e.target.value)}>{Object.entries(types).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>所属结构<select aria-label="所属结构" value={form.parent} onChange={e=>field('parent',e.target.value)}><option value="">项目根节点（仅 PCC / 变压器区）</option>{parents.map(n=><option key={n.node_id} value={n.node_id}>{n.name} · {n.node_id}</option>)}</select></label><label>回路编号<input aria-label="回路编号" value={form.circuit} maxLength={128} onChange={e=>field('circuit',e.target.value)}/></label><label>设计电压等级<select aria-label="结构电压等级" value={form.voltage} onChange={e=>field('voltage',e.target.value)}><option value="">待确认</option><option>LV</option><option>MV</option></select></label><label>相制<select aria-label="结构相制" value={form.phase} onChange={e=>field('phase',e.target.value)}><option value="">待 EPC 确认</option><option>三相三线</option><option>三相四线</option><option>单相</option><option>不适用 / 待详细定义</option></select></label><label>用途<input aria-label="结构用途" value={form.purpose} onChange={e=>field('purpose',e.target.value)} placeholder="主配电 / 光伏汇流 / 储能汇流"/></label><label>EPC 图纸引用<input aria-label="EPC 图纸引用" value={form.epc} onChange={e=>field('epc',e.target.value)} placeholder="图号、版本、回路页码；缺失保留待补"/></label><label>厂家依据引用<input aria-label="厂家依据引用" value={form.manufacturer} onChange={e=>field('manufacturer',e.target.value)} placeholder="型号规格或端口文件；缺失保留待确认"/></label></div><p className="startHelp">不自动填写容量、额定电流、保护整定或电缆截面。录入引用仍为待核验，不产生批准结论。{dirty?'保存本对象将同时保存当前未保存的工程草案。':''}</p><button className="primary" disabled={busy} onClick={()=>void commit()}>{busy?'正在保存…':'保存结构并更新拓扑'}</button></section>}
 {error&&<p className="startError" role="alert">{error}</p>}{message&&<p className="startSuccess" role="status">{message}</p>}
 <div className="startPending"><b>依据待确认</b><span>EPC 补充现场图纸、回路归属和设计电压；厂家确认适用结构接口和设备规格。归属线不代表电气接线，结构已录入不代表工程批准。</span></div>
 <StructureTree model={model} expanded/>
 <div className="startActions"><button onClick={back}>返回步骤02</button><button onClick={next}>继续录入设备（现有作业区）</button></div>
 </article>
}
