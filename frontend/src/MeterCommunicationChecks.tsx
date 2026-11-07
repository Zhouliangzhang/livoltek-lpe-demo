import type {Model} from './types'
import type {CheckItem} from './checklistGroups'
import {CheckEditor,labels,type Entry} from './CheckEditor'
import {generateSettings} from './settingsCatalog'
export function MeterCommunicationChecks({model,item,records,planId,disabled,refresh}:{model:Model;item:CheckItem;records:Entry[];planId:string;disabled:boolean;refresh:()=>Promise<void>}){
 const edge=model.edges.find(e=>e.edge_id===item.target_id)
 const ports=[edge?.from_port_id,edge?.to_port_id].map(id=>model.ports.find(p=>p.port_id===id)).filter(p=>!!p)
 const rows=generateSettings(model).filter(r=>r.definition.group==='通信'&&ports.some(p=>p.node_id===r.nodeId&&r.definition.domains.includes(p.domain)&&(!r.portId||r.portId===p.port_id)))
 const show=(v:unknown)=>v===null||v===undefined||v===''?'未录入':String(v)
 const checks=item.id.endsWith(':0')?[
  {id:'ports',title:'01 两端设备与端口是否对应',method:'沿本回路标识核对两端设备铭牌、接口标签和现场端子号，记录实际对应。上方为工程逻辑端口，不能当作实物针脚号。',missing:'电表与 iEMS 对应交付型号的接口接线图、实物端子编号 / 针脚定义及适用固件版本。',fields:[{key:'from_terminal',label:'起点现场设备 / 端子号'},{key:'to_terminal',label:'终点现场设备 / 端子号'},{key:'circuit_label',label:'现场线号 / 回路标识'}]},
  {id:'wiring',title:'02 线缆、线序与屏蔽如何连接',method:'在批准的安全作业条件下，对照双方接线图记录线缆标识、各芯线两端端子、屏蔽和终端处理。没有图纸时只记录观察，不推定 A/B 极性或终端电阻。',missing:'双方线序及信号极性定义、允许线缆规格 / 长度、屏蔽接地方式、是否需要终端及其取值。',fields:[{key:'cable',label:'现场线缆型号 / 规格 / 长度'},{key:'cores',label:'各芯线两端对应关系'},{key:'shield',label:'屏蔽连接实际情况'},{key:'termination',label:'终端处理实际情况'}]},
 ]:[
  {id:'settings',title:'03 双方通信参数是否匹配',method:'分别读取或查阅双方已确认的现场配置，将实际参数与下方 M1 值逐项比较。站号须与 iEMS 的目标从站配置对应，不能要求主从设备地址相同；同一总线的波特率等须满足双方协议要求。',missing:'适用协议与版本、站号分配约定、双方支持的串口 / 网络参数、iEMS 电表驱动兼容性说明。参数文档引用不等于批准。',fields:rows.map(r=>({key:r.id,label:r.deviceName+' / '+r.definition.label+(r.definition.unit?' ('+r.definition.unit+')':'')}))},
  {id:'identity',title:'04 iEMS 识别的是哪台电表',method:'仅在现场已批准上电与诊断条件下，使用厂家诊断界面核对读取到的电表型号、地址、设备标识及驱动。页面不主动连接设备。',missing:'设备识别点表 / 读取方法、支持的电表驱动与固件组合、通信成功及故障码定义。',powered:true,fields:[{key:'model',label:'实际识别型号 / 固件'},{key:'identity',label:'实际 SN / 设备标识'},{key:'address',label:'iEMS 读取目标地址 / 驱动'},{key:'diagnostic',label:'诊断界面状态 / 故障码'}]},
  {id:'readings',title:'05 并网点功率数据是否有效',method:'在已批准的测试条件下记录同一时刻的电表显示与 iEMS 读取值、单位、时间和质量状态，说明当时购电 / 送电工况。不得仅凭数值非零判定正确；不开展动态零馈测试。',missing:'并网点有功功率寄存器 / 点位、倍率与单位、正负方向约定、更新周期、质量标志、允许偏差和失联判据。',powered:true,fields:[{key:'time',label:'观察时间（含时区）'},{key:'meter_power',label:'电表有功功率读数及单位'},{key:'ems_power',label:'iEMS 对应读数及单位'},{key:'direction',label:'现场工况与正负方向观察'},{key:'quality',label:'更新时间 / 数据质量 / 超时情况'},{key:'point',label:'读取点位及倍率'}]},
 ]
 return <section className="meterChecks" aria-label="零馈表与 iEMS 具体点检">
  <div className="meterRoute">{ports.map((p,index)=>{const n=model.nodes.find(n=>n.node_id===p.node_id),asset=model.device_assets.find(a=>a.asset_id===n?.device_asset_id),device=model.device_models.find(d=>d.model_id===asset?.model_id);return <div key={p.port_id}><small>{index===0?'M1 起点':'M1 终点'} · {p.domain}</small><h4>{n?.name}</h4><strong>{p.port_id}</strong><p>{device?.manufacturer} · {device?.model_name||'型号待补'}<br/>SN：{asset?.serial_number||'现场待补'} · 固件：{asset?.firmware_version||'现场待补'}</p></div>})}</div>
  <p className="meterCaption">{edge?.edge_id} · M1 基线中的逻辑连接；实物端子及线缆要求待厂家文件确认。</p>
  <details className="meterParameters" open={!item.id.endsWith(':0')}><summary>M1 通信参数 · 计划值与已录入现场值 ({rows.length})</summary><div className="meterTable"><table><thead><tr><th>设备 / 参数</th><th>计划值</th><th>M1 现场值</th><th>依据</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.deviceName}<br/><strong>{r.definition.label}</strong></td><td>{show(r.record?.planned)} {r.definition.unit}</td><td>{show(r.record?.actual)} {r.definition.unit}</td><td>{r.stale?'型号 / 模板版本已变更':r.record?.reference_doc||'未提供参数依据'}<small>批准值 / 厂家适用性待确认</small></td></tr>)}</tbody></table>{!rows.length&&<p>当前连接没有匹配的通信参数，请到 M1 补充接口与配置。</p>}</div></details>
  <p className="meterCaption">以下填写本次观察结果，独立保存，不覆盖 M1 设置，也不自动形成“通过”结论。</p>
  {checks.map(c=>{const history=records.filter(r=>r.item_id===item.id&&r.detail_key===c.id),record=history[0];return <details className="meterCheck" key={c.id} open><summary><b>{c.title}</b><span className={'m2Tag '+(record?.status==='FAIL'?'danger':'')}>{record?labels[record.status]:'未记录'}</span></summary><p>{c.method}</p><div className="meterMissing"><b>厂家需提供 · 待确认</b><p>{c.missing}</p></div><CheckEditor key={item.id+c.id} item={item} record={record} history={history} planId={planId} disabled={disabled} refresh={refresh} detailKey={c.id} fields={c.fields} requiresExecution={'powered' in c&&!!c.powered}/></details>})}
  {!!records.filter(r=>r.item_id===item.id&&!r.detail_key).length&&<details><summary>原综合反馈（保留，不作为逐项完成）</summary>{records.filter(r=>r.item_id===item.id&&!r.detail_key).map(r=><p key={r.id}>{r.recorder} · {r.note}</p>)}</details>}
 </section>
}
