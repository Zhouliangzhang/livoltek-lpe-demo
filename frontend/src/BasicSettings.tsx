import {useState} from 'react'
import type {Model} from './types'
import {generateSettings,updateSetting,type SettingScalar} from './settingsCatalog'

export function applyFleetPlan(model:Model,nodeIds:string[],values:Record<string,SettingScalar>){
 let next=model
 for(const id of nodeIds)for(const [key,value] of Object.entries(values)){
  const row=generateSettings(next).find(r=>r.nodeId===id&&r.definition.key===key)
  if(!row||row.stale)throw new Error('设备型号或参数版本需要先确认，请在高级设置中处理。')
  next=updateSetting(next,row,'planned',value)
 }
 return next
}

export function BasicSettings({model,change}:{model:Model;change:(m:Model)=>void}){
 const rows=generateSettings(model),controllers=model.nodes.filter(n=>n.node_type==='EMS')
 const [controller,setController]=useState(''),[fleet,setFleet]=useState(''),[draft,setDraft]=useState<Record<string,SettingScalar>>({}),[message,setMessage]=useState('')
 const active=controllers.find(n=>n.node_id===controller)||controllers[0]
 const storage=rows.filter(r=>model.nodes.find(n=>n.node_id===r.nodeId)?.node_type==='BESS')
 const groups=[...new Map(storage.map(r=>[r.modelId+'|'+r.modelVersion,{key:r.modelId+'|'+r.modelVersion,name:r.modelName+' · '+r.modelVersion}])).values()]
 const selected=groups.find(g=>g.key===fleet)||groups[0]
 const ids=[...new Set(storage.filter(r=>r.modelId+'|'+r.modelVersion===selected?.key).map(r=>r.nodeId))]
 const field=(key:string,label:string,type='text')=>{
  const row=rows.find(r=>r.nodeId===active?.node_id&&r.definition.key===key)
  if(!row)return <p>{label}：当前项目不适用或尚无控制器资料。</p>
  return <label>{label}<input aria-label={'简化 '+key} type={type} disabled={row.stale} value={row.record?.planned??''} placeholder={row.stale?'型号变化，需先确认':'待设置 / 待厂家确认'} onChange={e=>{change(updateSetting(model,row,'planned',e.target.value===''?null:type==='number'?Number(e.target.value):e.target.value));setMessage('计划已修改，尚未保存；现场值与厂家确认状态未改变。')}}/><small>{row.stale?'旧设置需在高级设置中重新确认':'待厂家确认 · 仅记录计划'}</small></label>
 }
 const fleetFields=[['battery_operating_mode','充放电方式','text'],['charge_schedule','充电时段 / 电源','text'],['soc_min','最低 SOC (%)','number'],['soc_max','最高 SOC (%)','number'],['charge_power_limit','单台充电上限 (kW)','number'],['discharge_power_limit','单台放电上限 (kW)','number']]
 const common=(key:string)=>{const values=ids.map(id=>rows.find(r=>r.nodeId===id&&r.definition.key===key)?.record?.planned);return values.every(v=>v===values[0])?values[0]:undefined}
 function apply(){
  try{
   if(!Object.keys(draft).length)return
   change(applyFleetPlan(model,ids,draft));setDraft({});setMessage(`已更新 ${ids.length} 台储能的指定计划字段，未改动现场值。请保存版本并重新运行 L6。`)
  }catch(e){setMessage((e as Error).message)}
 }
 return <div className="basicSettings"><div className="basicIntro"><div><h3>先确定三项运行策略</h3><p>这里只编辑计划。厂家依据与现场实际值在高级设置中核对，L6 仍检查全部参数。</p></div>{controllers.length>1&&<label>控制器<select aria-label="简化设置控制器" value={active?.node_id||''} onChange={e=>setController(e.target.value)}>{controllers.map(n=><option key={n.node_id} value={n.node_id}>{n.name}</option>)}</select></label>}</div>
 <section className="basicCard"><header><b>01</b><div><h3>零馈控制</h3><p>通过 PCC 电表反馈，由 {active?.name||'待录入 iEMS'} 协调。</p></div><span>待厂家确认</span></header><div className="basicGrid">{field('export_limit','允许送电上限 (kW，0 = 零馈)','number')}{field('grid_power_target','PCC 进口目标 / 裕量 (kW)','number')}</div></section>
 <section className="basicCard"><header><b>02</b><div><h3>光伏如何利用余电</h3><p>确定供负载、充储能和限发的顺序。</p></div><span>待厂家确认</span></header><div className="basicGrid">{field('control_strategy','系统运行策略')}{field('pv_curtailment','余电与光伏限发策略')}</div></section>
 <section className="basicCard"><header><b>03</b><div><h3>储能何时充放电</h3><p>同型号统一计划，现场差异仍可在高级设置中逐台记录。</p></div><span>待厂家确认</span></header>{selected?<><label>同型号设备组<select aria-label="储能统一设置设备组" value={selected.key} onChange={e=>{setFleet(e.target.value);setDraft({});setMessage('')}}>{groups.map(g=><option key={g.key} value={g.key}>{g.name}</option>)}</select></label><p className="fleetScope">本次范围：{ids.length} 台 · {ids.join('、')}</p><div className="basicGrid">{fleetFields.map(([key,label,type])=><label key={key}>{label}<input aria-label={'统一 '+key} type={type} min={type==='number'?0:undefined} max={key.startsWith('soc_')?100:undefined} value={draft[key]??''} placeholder={common(key)==null?'各台未填或存在差异；不自动覆盖':`当前一致计划：${common(key)}`} onChange={e=>setDraft({...draft,[key]:e.target.value===''?null:type==='number'?Number(e.target.value):e.target.value})}/></label>)}</div><p className="muted">只更新本次编辑的字段；留白未编辑的字段保留原值。功率为单台上限，SOC 不预填猜测值。</p><button onClick={apply} disabled={!Object.keys(draft).length}>应用到 {ids.length} 台计划值</button></>:<p>尚无储能型号与资产，请先在 L3 建档。</p>}</section>
 {message&&<p className="basicMessage" role="status">{message}</p>}</div>
}
