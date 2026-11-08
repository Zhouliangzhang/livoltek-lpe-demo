import type {Model} from './types'
import {generateSettings} from './settingsCatalog'
export function MeterBasis({model,nodeId,step,locate}:{model:Model;nodeId:string;step:number;locate:(layer:string,message:string,rowId?:string,label?:string)=>void}){
 const node=model.nodes.find(n=>n.node_id===nodeId),asset=model.device_assets.find(a=>a.asset_id===node?.device_asset_id),device=model.device_models.find(d=>d.model_id===asset?.model_id),attrs=node?.attributes||{}
 const settings=generateSettings(model).filter(p=>p.nodeId===nodeId&&p.definition.group==='计量')
 const show=(v:unknown)=>v==null||v===''?'未录入 · 待 EPC 补充':String(v)
 return <section className="meterBasis" aria-label="M1 零馈表依据">
  <header><div><small>M1 BASELINE · 自动带入</small><h3>{step===3?'计量覆盖、方向与倍率依据':'目标电表身份与工程映射'}</h3></div><span>工程记录 · 非现场实时读回</span></header>
  {step!==3&&<div className="meterIdentity"><div><small>厂家 / 型号</small><b>{device?.manufacturer} / {device?.model_name}</b></div><div><small>设备 SN</small><b>{show(asset?.serial_number)}</b></div><div><small>固件版本</small><b>{show(asset?.firmware_version)}</b></div><div><small>安装位置</small><b>{show(asset?.installed_location)}</b></div></div>}
  <p>草案测量回路：{show(attrs.measured_edge)} · 规划位置：{show(attrs.planned_location)} · 草案购电符号：{attrs.import_sign==='positive'?'正号为购电（待确认）':show(attrs.import_sign)}。草案不证明现场 CT/PT 或计量覆盖正确。</p>
  {step!==3&&<button onClick={()=>locate('L3','核对零馈表型号、SN、固件及安装位置；换机后重新建立会话')}>定位 M1 设备身份</button>}
  {step===3&&<><div className="mwTable"><table><thead><tr><th>计量设置</th><th>M1 计划值</th><th>M1 已录现场值</th><th>厂家依据 / 处理</th></tr></thead><tbody>{settings.map(p=><tr key={p.id}><td>{p.definition.label}</td><td>{show(p.record?.planned)} {p.definition.unit}</td><td>{show(p.record?.actual)} {p.definition.unit}</td><td><span>{p.stale?'版本已变化，待重新确认':p.record?.reference_doc||'待确认：铭牌、点表或批准计量规程'}</span><button onClick={()=>locate('L5',p.definition.label+'：补充现场值和批准依据',p.id,p.id+' actual')}>定位补充</button></td></tr>)}</tbody></table></div><p>缺少独立现场参照时不能形成方向/倍率结论。模拟参照与下列工程记录分开保存。</p></>}
 </section>
}
