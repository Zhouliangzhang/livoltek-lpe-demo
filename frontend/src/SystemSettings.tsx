import type {Model} from './types'
import {GeneratedSettings} from './GeneratedSettings'
type SettingValue={value:number;unit:string;source:string;status?:string;source_ref?:string}
type Setting={parameter_id:string;owner_id:string;name:string;planned:SettingValue|null;actual:SettingValue|null;approved:SettingValue|null;criticality:string;reference_doc?:string|null;review_status:string}
export function SystemSettings({model,change}:{model:Model;change:(m:Model)=>void}){
 const parameters=model.parameters as Setting[]
 function update(id:string,phase:'planned'|'actual',raw:string){
  if(raw!==''&&!Number.isFinite(Number(raw)))return
  const m=structuredClone(model),p=(m.parameters as Setting[]).find(p=>p.parameter_id===id)!
  const prior=p[phase],unit=prior?.unit||p.planned?.unit||p.approved?.unit||''
  p[phase]=raw===''?null:{...prior,value:Number(raw),unit,source:phase==='planned'?'DESIGN':'MEASURED',status:'DRAFT'}
  p.review_status='DRAFT';change(m)
 }
 return <><div className="settingsContext"><strong>系统设置</strong><span>运行方式：{(model.project.operation_modes as string[]).join(' / ')}（来自 L1）</span><span>以厂家资料和 EPC 已确定的工程条件为依据录入；不向现场设备下发指令。</span></div><GeneratedSettings model={model} change={change}/><h3 className="legacySettingsHeading">已有系统参数与工程依据</h3><div className="tableScroll"><table className="layerTable"><thead><tr><th>设置项 / 作用对象</th><th>计划设置值</th><th>现场实际值</th><th>已确认参考值</th><th>依据 / 风险</th></tr></thead><tbody>{parameters.map(p=>{
 const configurable=p.name!=='cable_spec'&&(!!p.planned||!!p.actual||!!p.approved)
 return <tr key={p.parameter_id} id={'setting-'+p.parameter_id} tabIndex={-1}><td>{p.name==='nominal_ac_voltage'?'系统额定电压':p.name==='cable_spec'?'电缆规格（工程依据）':p.name}<small>{p.owner_id}</small></td>{(['planned','actual'] as const).map(phase=><td key={phase}>{configurable?<label>{phase==='planned'?'计划设置':'现场记录'}<input type="number" step="any" aria-label={p.name+' '+phase} value={p[phase]?.value??''} placeholder="待记录" onChange={e=>update(p.parameter_id,phase,e.target.value)}/><small>{p[phase]?.unit||p.planned?.unit||p.approved?.unit} · {p[phase]?.source||'待记录'}</small></label>:<span className="muted">{p[phase]?`${p[phase]!.value} ${p[phase]!.unit}`:'由工程资料提供'}</span>}</td>)}<td>{p.approved?`${p.approved.value} ${p.approved.unit}`:'尚无确认参考值'}<small>保留原始批准记录，不在此改写</small></td><td><input aria-label={p.name+' reference'} placeholder="工程文档编号 / 版本 / 页码" value={p.reference_doc||''} onChange={e=>{const m=structuredClone(model);(m.parameters as Setting[]).find(x=>x.parameter_id===p.parameter_id)!.reference_doc=e.target.value;change(m)}}/><small>{p.criticality==='SAFETY_CRITICAL'?'安全关键 · 需专项核实':'常规'}</small></td></tr>
 })}</tbody></table></div><div className="settingsFoot">修改后点击顶部“保存版本”。新增参数清单见上方通信、EMS 与储能设置分组；缺少厂家依据的参数不会自动确认。</div></>
}
