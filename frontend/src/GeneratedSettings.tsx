import {useState} from 'react'
import type {Model} from './types'
import {generateSettings,settingsSummary,settingsVersion,updateSetting,resetSetting,type GeneratedSetting} from './settingsCatalog'

export function GeneratedSettings({model,change}:{model:Model;change:(m:Model)=>void}){
 const [device,setDevice]=useState(''),[error,setError]=useState('')
 const summary=settingsSummary(model),rows=generateSettings(model).filter(r=>!device||r.nodeId===device)
 const groups=['通信','EMS 控制策略','储能运行']
 const devices=[...new Map(summary.rows.map(r=>[r.nodeId,r])).values()]
 function field(row:GeneratedSetting,phase:'planned'|'actual'){
  const d=row.definition,numeric=['number','integer'].includes(d.type)
  return <input aria-label={row.id+' '+phase} type={numeric?'number':'text'} step={d.type==='integer'?1:'any'} min={d.min} max={d.max} disabled={row.stale} value={row.record?.[phase]??''} placeholder="待确认，不设默认值" onChange={e=>{const raw=e.target.value;const value=numeric&&raw!==''?Number(raw):raw||null;if(typeof value==='number'&&!Number.isFinite(value))return;try{change(updateSetting(model,row,phase,value));setError('')}catch(e){setError(String(e))}}}/>
 }
 return <div className="generatedSettings"><div className="settingsSummary"><div><strong>按项目与型号生成的设置清单</strong><p>{summary.total} 项候选参数 · {summary.manufacturerPending} 项厂家依据待确认 · {summary.stale} 项版本变化</p></div><label>筛选设备<select aria-label="L5 筛选设备" value={device} onChange={e=>setDevice(e.target.value)}><option value="">全部设备</option>{devices.map(d=><option key={d.nodeId} value={d.nodeId}>{d.deviceName} · {d.modelName}</option>)}</select></label></div><p className="catalogNotice">清单版本 {settingsVersion}。依据 L1 运行方式、L3 型号及已有接口生成；当前为通用候选项，适用性、单位、范围和推荐值均需对应型号厂家资料确认。填写文档编号不等于依据已核验。</p>
 {groups.map(group=>{const items=rows.filter(r=>r.definition.group===group);return <details className="settingsGroup" open key={group}><summary>{group}<span>{items.length} 项</span></summary>{items.length?<div className="tableScroll"><table className="layerTable"><thead><tr><th>参数 / 设备型号</th><th>计划设置</th><th>现场实际</th><th>厂家依据 / 状态</th></tr></thead><tbody>{items.map(row=><tr key={row.id} id={'setting-'+row.id} tabIndex={-1}><td><b>{row.definition.label}{row.definition.unit?' ('+row.definition.unit+')':''}</b><small>{row.deviceName} · {row.manufacturer}</small><small>{row.modelName} · {row.modelVersion}</small><small>适用来源：{row.reason}</small></td><td>{field(row,'planned')}</td><td>{field(row,'actual')}</td><td><span className="pendingEvidence">{row.stale?'型号 / 模板版本变化，待重新确认':'待厂家确认'}</span><input aria-label={row.id+' reference'} value={row.record?.reference_doc||''} disabled={row.stale} placeholder="厂家文档编号 / 版本 / 页码" onChange={e=>change(updateSetting(model,row,'reference_doc',e.target.value))}/><small>{row.record?.reference_doc?'已填引用 · 未核验适用性':'缺少对应型号的厂家依据'}</small>{row.stale&&<button onClick={()=>change(resetSetting(model,row))}>保留旧记录，重新录入</button>}</td></tr>)}</tbody></table></div>:<p className="muted">当前运行方式、设备类型与已录入接口未生成此类参数。</p>}</details>})}
 {summary.inactive>0&&<div className="catalogNotice">有 {summary.inactive} 项已保存设置不再适用于当前运行方式或接口，已保留原记录，不自动应用到当前清单。<details><summary>查看历史适用项</summary><pre>{JSON.stringify(model.nodes.filter(n=>n.attributes?.l5_settings).map(n=>({device:n.name,settings:n.attributes?.l5_settings})),null,2)}</pre></details></div>}
 {error&&<p role="alert">{error}</p>}<div className="settingsFoot">此处记录配置，不下发设备。保存项目版本后保留参数值、型号版本、清单版本和文档引用。安全保护整定值仅引用已批准工程文件，不由工具计算。</div></div>
}
