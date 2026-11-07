import {useState} from 'react'
import type {Model} from './types'
import {communicationBuses,sharedKeys,modelTemplates} from './communication'
import {generateSettings,updateSetting,resetSetting,type GeneratedSetting,type SettingScalar} from './settingsCatalog'

export function applyBusSettings(model:Model,busId:string,values:Record<string,SettingScalar>){
 const bus=communicationBuses(model).find(b=>b.id===busId)
 if(!bus)throw new Error('L4 连接已变化，请重新选择总线。')
 let next=model
 for(const [key,value] of Object.entries(values)){
  if(!sharedKeys[bus.domain].includes(key))throw new Error('设备地址不可批量统一。')
  const rows=generateSettings(next).filter(r=>r.definition.key===key&&bus.ports.some(p=>p.port_id===r.portId))
  if(rows.some(r=>r.stale))throw new Error('请先核对型号版本变化的记录。')
  for(const row of rows)next=updateSetting(next,row,'planned',value)
 }
 return next
}
export function CommunicationSettings({model,change}:{model:Model;change:(m:Model)=>void}){
 const buses=communicationBuses(model),rows=generateSettings(model).filter(r=>r.definition.group==='通信')
 const [drafts,setDrafts]=useState<Record<string,Record<string,SettingScalar>>>({}),[message,setMessage]=useState('')
 function field(row:GeneratedSetting,phase:'planned'|'actual'){
  const numeric=['number','integer'].includes(row.definition.type)
  return <input aria-label={row.id+' '+phase} disabled={row.stale} type={numeric?'number':'text'} step={row.definition.type==='integer'?1:'any'} value={row.record?.[phase]??''} placeholder="待厂家确认" onChange={e=>change(updateSetting(model,row,phase,e.target.value===''?null:numeric?Number(e.target.value):e.target.value))}/>
 }
 return <section className="communicationSettings" aria-label="按连接配置通信"><header className="commHeading"><div><h3>通信连接与设置</h3><p>来自 L4 的 {buses.length} 个通信网络 · 只显示已连接接口需要的参数</p></div><span className="pendingEvidence">厂家依据待确认</span></header>
 {!buses.length&&<p>尚未录入通信连接，请先在 L4 连接设备端口。未连接接口不要求填写通信参数。</p>}
 {buses.map(bus=>{
  const members=rows.filter(r=>bus.ports.some(p=>r.portId?p.port_id===r.portId:p.node_id===r.nodeId&&p.domain==='ETHERNET'))
  const nodes=[...new Set(members.map(r=>r.nodeId))],draft=drafts[bus.id]||{}
  return <article className="commBus" key={bus.id} data-domain={bus.domain}><header><div><small>{bus.domain} · L4 自动分组</small><h3>{bus.name}</h3><p>{nodes.length} 台设备 · {bus.domain==='ETHERNET'?'使用网络地址，不显示串口参数':'公共通信格式统一填写，设备地址分别核对'}</p></div><span className="commCount">{bus.ports.length} 个接口</span></header>
  <p className="commRoute">{bus.ports.filter(p=>model.nodes.find(n=>n.node_id===p.node_id)?.node_type==='EMS').map(p=>p.port_id).join(' / ')||bus.ports[0].port_id} → {bus.name}</p>
  {!!sharedKeys[bus.domain].length&&<div className="commShared"><div className="basicGrid">{sharedKeys[bus.domain].map(key=>{
   const entries=members.filter(r=>r.definition.key===key),d=entries[0]?.definition
   if(!d)return null
   const common=entries.map(r=>r.record?.planned),equal=common.every(v=>v===common[0]),numeric=['number','integer'].includes(d.type)
   return <label key={key}>{d.label}<input aria-label={bus.name+'统一 '+key} type={numeric?'number':'text'} step="any" value={draft[key]??''} placeholder={equal&&common[0]!=null?'当前计划：'+common[0]:equal?'厂家值未提供 · 待确认':'各设备设置不同 · 需核对'} onChange={e=>setDrafts({...drafts,[bus.id]:{...draft,[key]:e.target.value===''?null:numeric?Number(e.target.value):e.target.value}})}/></label>
  })}</div><button disabled={!Object.keys(draft).length} onClick={()=>{try{change(applyBusSettings(model,bus.id,draft));setDrafts({...drafts,[bus.id]:{}});setMessage(bus.name+'的公共计划已统一；现场值未改动，请保存版本。')}catch(e){setMessage((e as Error).message)}}}>统一本总线计划</button><small>只更新本次编辑的字段；不会统一站号，也不会覆盖其他总线。</small></div>}
  <div className="commDevices">{nodes.map(id=>{
   const rr=members.filter(r=>r.nodeId===id),sample=rr[0],livoltek=sample.manufacturer.toUpperCase()==='LIVOLTEK',templates=modelTemplates(model,id).filter(t=>t.domain===bus.domain)
   return <details className="commDevice" key={id} data-comm-node={id}><summary><strong>{sample.deviceName}</strong><span>{sample.modelName}</span><small>{livoltek?'型号自动匹配':'第三方模板优先'} · 待厂家确认</small></summary><div className="commTemplate"><b>{livoltek?'LIVOLTEK 型号模板':'第三方设备模板'}</b><p>{sample.modelName} · {sample.modelVersion}</p>{livoltek?<p>{templates.length?'已自动带出型号模板中有依据的候选值；仅作计划，现场需核对。':'尚无该版本的厂家通信默认值，已带出所需字段，数值待厂家确认。'}</p>:<label>选择模板<select aria-label={id+' 通信模板'} defaultValue="" onChange={e=>{const t=templates.find(t=>t.id===e.target.value);if(!t){setMessage('已使用 '+bus.domain+' 空白字段模板；没有厂家默认值，请按设备资料填写。');return}let next=model;for(const r of rr){const v=t.values[r.definition.key];if(v!=null&&t.reference_doc&&!r.stale&&r.record?.planned==null){next=updateSetting(next,r,'planned',v);const fresh=generateSettings(next).find(x=>x.id===r.id)!;next=updateSetting(next,fresh,'reference_doc',t.id+' / '+t.version+' / '+t.status+': '+t.reference_doc)}}change(next);setMessage('仅补入模板中有依据的空白计划字段，现场值未改动。')}}><option value="">选择型号模板 / 无模板时手录</option>{templates.map(t=><option key={t.id} value={t.id}>{t.id} · {t.version} · {t.status}</option>)}<option value="blank">{bus.domain} 通用字段模板（无厂家默认值）</option></select></label>}</div>
   <div className="tableScroll"><table className="layerTable"><thead><tr><th>参数 / 接口</th><th>计划值</th><th>现场值</th><th>依据</th></tr></thead><tbody>{rr.map(r=><tr id={'setting-'+r.id} key={r.id} tabIndex={-1}><td>{r.definition.label}<small>{r.portId||'以太网接口'}</small>{sharedKeys[bus.domain].includes(r.definition.key)&&<small>可在总线公共设置统一修改</small>}</td><td>{field(r,'planned')}</td><td>{field(r,'actual')}</td><td><span className="pendingEvidence">{r.stale?'型号版本变化，待重新确认':'待厂家确认'}</span><input aria-label={r.id+' reference'} disabled={r.stale} value={r.record?.reference_doc||''} placeholder="文档 / 版本 / 页码" onChange={e=>change(updateSetting(model,r,'reference_doc',e.target.value))}/>{r.stale&&<button onClick={()=>change(resetSetting(model,r))}>保留旧记录，重新录入</button>}</td></tr>)}</tbody></table></div></details>
  })}</div></article>
 })}{message&&<p role="status">{message}</p>}</section>
}
