import {useState} from 'react'
import type {Model,Edge,Port} from './types'
import {generateSettings} from './settingsCatalog'
import type {Issue} from './readinessIssues'
export const guideGroups=['零馈计量','iEMS 通信骨干','光伏通信','储能通信']
export function communicationRoutes(model:Model){
 return model.edges.filter(e=>e.edge_type==='COMMUNICATION').map(edge=>{
  const from=model.ports.find(p=>p.port_id===edge.from_port_id)!,to=model.ports.find(p=>p.port_id===edge.to_port_id)!
  const ids=[from.node_id,to.node_id],nodes=model.nodes.filter(n=>ids.includes(n.node_id))
  const group=nodes.some(n=>n.node_type==='METER'||n.node_id==='CT_PCC')?'零馈计量':nodes.some(n=>n.node_type==='PV_INVERTER'||n.node_id.startsWith('PV_RS485'))?'光伏通信':nodes.some(n=>n.node_type==='BESS')?'储能通信':'iEMS 通信骨干'
  return {edge,from,to,group}
 }).sort((a,b)=>(a.from.domain==='RS485'?-1:0)-(b.from.domain==='RS485'?-1:0)||a.edge.edge_id.localeCompare(b.edge.edge_id))
}
const checks:Record<string,{method:string;expected:string;failure:string}[]>={
 '零馈计量':[{method:'在获准供电与通信条件下，读取 iEMS 中的电表在线状态、三相电压/电流及 PCC 有功功率。',expected:'能够持续读取与电表本地显示相对应的数据；量纲、时间戳及功率方向一致。允许误差和刷新周期待厂家确认。',failure:'先核对端口与协议，再核对站号、串口格式及寄存器映射；方向异常交由 EPC 核对 CT 方向/相序，不能仅修改符号掩盖接线问题。'}],
 'iEMS 通信骨干':[{method:'在获准供电后检查 iEMS 与交换机链路状态，再从厂家诊断页面读取设备发现或连接状态。',expected:'物理链路建立，目标设备可被协议识别；仅有链路灯或 ping 响应不能证明业务通信正常。',failure:'依次核对所接端口、网段、地址重复、交换机配置和应用协议；管理口是否兼作业务口待厂家确认。'}],
 '光伏通信':[{method:'在 iEMS 厂家诊断界面逐台读取光伏设备身份、在线状态和有功功率，与对应逆变器本地显示核对。',expected:'设备身份与实际设备一致，同一总线站号无重复；所有计划接入设备可稳定读取。',failure:'全总线离线先核对 iEMS 通道及公共通信格式；单机离线定位该支路、地址与设备协议。限功率下发不属于本只读验证。'}],
 '储能通信':[{method:'在厂家授权诊断界面逐台读取储能身份、SOC、功率与告警，核对资产对应关系。',expected:'读取的是对应储能设备，单位及功率方向匹配；协议、数据刷新周期和兼容固件待厂家确认。',failure:'先确认设备网络地址及链路，再确认业务协议、端口和权限。在线不代表已具备充放电控制条件。'}]
}
export function CommunicationGuide({model,locate}:{model:Model;locate:(issue:Issue)=>void}){
 const routes=communicationRoutes(model),settings=generateSettings(model).filter(r=>r.definition.group==='通信'),[selected,setSelected]=useState<Record<string,string>>({})
 const node=(p:Port)=>model.nodes.find(n=>n.node_id===p.node_id)!
 function endpoint(p:Port){const n=node(p),a=model.device_assets.find(a=>a.asset_id===n.device_asset_id),d=model.device_models.find(d=>d.model_id===a?.model_id);return <div className="wireEndpoint"><small>{n.node_type==='COMM_BUS'?'逻辑总线节点 · 非实体端子':'设备 / 接口'}</small><h4>{n.name}</h4><strong>{p.port_id}</strong><p>{p.name} · {p.domain}</p><small>{d?`${d.manufacturer} / ${d.model_name} · ${d.master_data_version}`:'非 SN 结构；实体接线点需 EPC 与厂家共同确认'}</small></div>}
 function go(edge:Edge,layer:'L4'|'L5',label?:string,rowId?:string){locate({id:'comm-guide-'+edge.edge_id,layer,category:'待厂家确认',object:edge.edge_id,message:layer==='L4'?'核对两端设备及端口连接':'补充通信设置与厂家依据',action:'查看',nodeId:model.ports.find(p=>p.port_id===edge.to_port_id)?.node_id,rowId:rowId||edge.edge_id,label})}
 return <section className="communicationGuide" aria-label="通信接线技术指引"><div className="stageHeading"><div><small>M2 / COMMUNICATION WIRING</small><h2>把每条通信连接接清楚</h2><p>来自当前 L4 的 {routes.length} 条通信连接 · 两端端口、接线要求、L5 设置和只读验证</p></div><span className="badge amber">型号专用接线依据待确认</span></div><p>以下端口号是工程模型标识，不等同于实物针脚。逻辑控制关系不作为通信电缆；本页面不下发控制指令。</p>
 {guideGroups.map(group=>{const list=routes.filter(r=>r.group===group),r=list.find(r=>r.edge.edge_id===selected[group])||list[0];if(!r)return <section key={group} className="card"><h3>{group}</h3><p>未录入此类通信连接，请在 L4 补充。</p></section>;
 const linked=settings.filter(s=>s.definition.domains.some(d=>[r.from.domain,r.to.domain].includes(d))&&(s.portId?[r.from.port_id,r.to.port_id].includes(s.portId):[r.from.node_id,r.to.node_id].includes(s.nodeId)))
 const serial=r.from.domain==='RS485',ethernet=r.from.domain==='ETHERNET'
 return <article key={group} className="card wireGroup" aria-label={group+' 接线指引'}><header className="trackingHeading"><div><h3>{group}</h3><p>{list.length} 条连接 · 逐条查看，不推定现场已接通</p></div><button onClick={()=>go(r.edge,'L4')}>查看 L4 连接 →</button></header><label>选择具体连接<select aria-label={group+' 选择连接'} value={r.edge.edge_id} onChange={e=>setSelected({...selected,[group]:e.target.value})}>{list.map(x=><option key={x.edge.edge_id} value={x.edge.edge_id}>{x.edge.edge_id} · {node(x.from).name} → {node(x.to).name}</option>)}</select></label><div className="wireRoute">{endpoint(r.from)}<span className="wireArrow">↔<small>{r.edge.edge_id}</small></span>{endpoint(r.to)}</div>
 <div className="wireColumns"><section><h4>接线要求</h4><ol><li>先按设备铭牌及型号手册识别上述接口，再核对线缆两端标识。涉及接线操作时按 EPC 批准的隔离条件执行。</li><li>{serial?'按双方手册确认差分信号对应关系；不可仅凭 A/B 或 +/− 名称推定极性。两端具体针脚及参考地连接：待厂家确认。':ethernet?'核对两端是否为业务以太网接口，按厂家批准线缆接入指定网络端口。接口物理形式、针脚、线缆类别及允许长度：待厂家确认。':'按双方厂家接口定义匹配信号与端子；具体针脚、线缆、极性与连接方式待厂家确认，不按 RS485 或以太网规则套用。'}</li><li>{serial?'总线接线拓扑、分支限制、屏蔽接法、终端电阻位置/数值：待厂家确认。L4 逻辑汇流节点不表示实体接线盒或串接次序。':'屏蔽及接地方式、设备间隔离要求：待厂家确认；图中的逻辑连接不替代实体接线图。'}</li></ol><span className="pendingEvidence">无已核准的型号针脚图，禁止据此猜测接线</span></section><section><h4>验证方法与预期结果</h4>{(serial||ethernet?checks[group]:[{method:'按厂家批准的该信号接口测试方法核验映射关系；方法未确认前不执行测试。',expected:'信号通道、量程、方向和单位与所接设备一致，判据待厂家确认。',failure:'转厂家确认接口定义，并由 EPC 核对现场连接。'}]).map(c=><div key={c.method}><p><b>方法：</b>{c.method}</p><p><b>预期：</b>{c.expected}</p><p><b>异常时：</b>{c.failure}</p></div>)}<small>待厂家确认：诊断菜单、寄存器/数据点、兼容固件与测试判据。页面没有连接真实设备，不会显示虚构测试通过。</small></section></div>
 <details className="wireSettings" open><summary>L5 通信设置 · {linked.length} 项关联参数</summary>{linked.length?<div className="tableScroll"><table className="layerTable"><thead><tr><th>设备 / 参数</th><th>计划值</th><th>现场值</th><th>依据</th><th>处理</th></tr></thead><tbody>{linked.map(s=><tr key={s.id}><td>{s.deviceName}<small>{s.definition.label}</small></td><td>{s.record?.planned??'待确认'}</td><td>{s.record?.actual??'待现场补充'}</td><td>{s.stale?'型号版本已变化 · 待重新确认':s.record?.reference_doc||'待厂家确认'}<small>厂家适用性待确认 · 引用不等于批准</small></td><td><button aria-label={'设置 '+s.id} onClick={()=>go(r.edge,'L5',s.id+' planned',s.id)}>定位设置 →</button></td></tr>)}</tbody></table></div>:<p>本接口暂无适用设置，请先由厂家确认接口类型和参数要求。</p>}</details></article>})}</section>
}
