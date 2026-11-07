import {useEffect,useState} from 'react'
import {type Model,type Kind,type Port} from './types'

export function sourcePorts(model:Model,device:string,kind:Kind){
 const domains=kind==='ELECTRICAL'?['AC','DC']:kind==='COMMUNICATION'?['ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO']:['CONTROL_LOGICAL']
 return model.ports.filter(p=>p.node_id===device&&domains.includes(p.domain)&&p.role!=='IN')
}
export function targetPorts(model:Model,device:string,kind:Kind,source:Port|undefined){
 if(!source||device===source.node_id)return []
 return model.ports.filter(p=>p.node_id===device&&p.domain===source.domain&&p.role!=='OUT'&&
  (kind!=='ELECTRICAL'||['voltage','phases'].every(k=>source.attributes?.[k]==null||p.attributes?.[k]==null||source.attributes[k]===p.attributes[k]))&&
  !model.edges.some(e=>e.edge_type===kind&&((e.from_port_id===source.port_id&&e.to_port_id===p.port_id)||(kind!=='CONTROL'&&e.to_port_id===source.port_id&&e.from_port_id===p.port_id))))
}
export function choosePort(ports:Port[],selected:string){return ports.some(p=>p.port_id===selected)?selected:ports.length===1?ports[0].port_id:''}

export function ConnectionEditor({model,kind,save,initialDevice,editId}:{model:Model;kind:Kind;save:(model:Model)=>Promise<void>;initialDevice?:string;editId?:string}){
 const [fromDevice,setFromDevice]=useState(''),[toDevice,setToDevice]=useState(''),[fromChoice,setFromChoice]=useState(''),[toChoice,setToChoice]=useState('')
 useEffect(()=>{if(initialDevice){setFromDevice(initialDevice);setFromChoice('');setToDevice('');setToChoice('')}},[initialDevice])
 const [saving,setSaving]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[reference,setReference]=useState('')
 const editing=model.edges.find(e=>e.edge_id===editId)
 useEffect(()=>{if(editing){const a=model.ports.find(p=>p.port_id===editing.from_port_id),b=model.ports.find(p=>p.port_id===editing.to_port_id);setFromDevice(a?.node_id||'');setToDevice(b?.node_id||'');setFromChoice(a?.port_id||'');setToChoice(b?.port_id||'');setReference(editing.design_ref||'')}},[editId])
 const compatibilityModel=editing?{...model,edges:model.edges.filter(e=>e.edge_id!==editId)}:model
 const starts=sourcePorts(model,fromDevice,kind),from=choosePort(starts,fromChoice),source=starts.find(p=>p.port_id===from)
 const ends=targetPorts(compatibilityModel,toDevice,kind,source),to=choosePort(ends,toChoice)
 const fromName=model.nodes.find(n=>n.node_id===fromDevice)?.name,toName=model.nodes.find(n=>n.node_id===toDevice)?.name
 async function submit(){
  if(!source||!to||saving)return
  setSaving(true);setError('');setMessage('')
  try{
   const m=structuredClone(model)
   const connection={edge_id:editing?.edge_id||'EDGE_'+crypto.randomUUID().slice(0,8),edge_type:kind,from_port_id:from,to_port_id:to,review_status:'DRAFT',design_ref:reference.trim()||null};if(editing)m.edges=m.edges.map(e=>e.edge_id===editId?{...e,...connection}:e);else m.edges.push(connection)
   await save(m)
   setMessage(`已保存连接：${fromName} / ${source.name} → ${toName} / ${ends.find(p=>p.port_id===to)?.name}。系统拓扑已自动更新。`)
   setFromDevice('');setToDevice('');setFromChoice('');setToChoice('');setReference('')
  }catch(e){setError('连接未保存：'+(e as Error).message)}finally{setSaving(false)}
 }
 return <section className="connectionForm" aria-label="设备端口连接表单"><div className="connectionIntro"><h3>{editing?'修正连接 · '+editing.edge_id:'新增连接'}</h3><span>选择设备，再选择端口 · 单一可用端口自动选中</span></div><fieldset disabled={saving}>
  <div className="connectionEndpoints"><div className="endpoint"><h4><b>01</b> 起点</h4><label>起点设备<select aria-label="起点设备" value={fromDevice} onChange={e=>{setFromDevice(e.target.value);setFromChoice('');setToDevice('');setToChoice('');setError('');setMessage('')}}><option value="">先选择起点设备 / 电气结构</option>{model.nodes.map(n=><option key={n.node_id} value={n.node_id} disabled={!sourcePorts(model,n.node_id,kind).length}>{n.name} · {n.node_type}</option>)}</select></label><label>起点端口<select aria-label="起点端口" disabled={!fromDevice||!starts.length} value={from} onChange={e=>{setFromChoice(e.target.value);setToChoice('');setError('');setMessage('')}}><option value="">{fromDevice?'请选择起点端口':'请先选择起点设备'}</option>{starts.map(p=><option key={p.port_id} value={p.port_id}>{p.name} · {p.domain} · {p.port_id}</option>)}</select></label><small>{starts.length===1?'已自动选中唯一可用端口':fromDevice?`${starts.length} 个可用端口，请选择`:'端口来自已录入的设备或结构'}</small></div>
  <span className="connectionArrow">→</span><div className="endpoint"><h4><b>02</b> 终点</h4><label>终点设备<select aria-label="终点设备" disabled={!source} value={toDevice} onChange={e=>{setToDevice(e.target.value);setToChoice('');setError('');setMessage('')}}><option value="">选择终点设备 / 电气结构</option>{model.nodes.filter(n=>n.node_id!==fromDevice).map(n=><option key={n.node_id} value={n.node_id}>{n.name} · {n.node_type}</option>)}</select></label><label>终点端口<select aria-label="终点端口" disabled={!toDevice||!ends.length} value={to} onChange={e=>{setToChoice(e.target.value);setError('');setMessage('')}}><option value="">{!toDevice?'请先选择终点设备':!ends.length?'无兼容的可用端口':'请选择终点端口'}</option>{ends.map(p=><option key={p.port_id} value={p.port_id}>{p.name} · {p.domain} · {p.port_id}</option>)}</select></label><small>{ends.length===1?'已自动选中唯一可用端口':toDevice&&!ends.length?'没有符合域、方向及已有连接约束的端口':ends.length?`${ends.length} 个可用端口，请选择`:'根据起点端口筛选兼容接口'}</small></div></div>
  <div className="connectionSave"><label>连接设计依据（可补充）<input aria-label="连接设计依据" value={reference} onChange={e=>setReference(e.target.value)} placeholder="图纸 / 文档编号"/></label><div><p>{from&&to?`${fromName} / ${source?.name} → ${toName} / ${ends.find(p=>p.port_id===to)?.name}`:'两端设备与端口确认后可保存'}</p><small>同时保存当前项目待保存修改；仍为工程草案。</small><button className="primary" disabled={!from||!to||saving} onClick={submit}>{saving?'正在保存…':'保存连接并更新拓扑'}</button></div></div>
  </fieldset>{error&&<p className="error" role="alert">{error}</p>}{message&&<p className="connectionSuccess" role="status">{message}</p>}</section>
}
