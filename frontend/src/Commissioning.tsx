import type {Environment} from './ConfigurationDelivery'
import {CommunicationGuide} from './CommunicationGuide'
import {useEffect,useState} from 'react'
import {api,type Model,type Edge} from './types'
import {generateSettings} from './settingsCatalog'
import type {Issue} from './readinessIssues'
import './m2.css'
import './m3.css'
type Entry={id:string;edge_id:string;mode:string;step:string;status:string;observation:string;reference:string;recorder:string;created:string;predecessor_id:string|null}
type Data={model:Model;edges:Edge[];records:Entry[];stale:boolean}
const steps=[
 ['conditions','调试条件','确认现场执行条件','EPC 已完成必要安装检查；核对现场上电、诊断权限与本次测试边界。填写对应确认记录，不由本工具签发许可。','EPC 现场确认记录、测试范围及执行权限'],
 ['wiring','接口与接线','核对两端端口与线序','对照双方适用接线图，核对设备铭牌、实物端子、线号、线缆、屏蔽与终端处理。逻辑端口不能当作实物针脚号。','厂家端子图、信号极性定义、线缆与屏蔽要求、终端配置'],
 ['settings','通信参数','核对双方参数与目标地址','核对电表站号与 iEMS 目标从站配置；逐项比较波特率、校验及停止位等适用参数。不要要求主从设备使用相同自身地址。','适用协议版本、地址分配约定、支持参数及电表驱动兼容性'],
 ['identity','设备识别','确认读到正确电表','在批准的上电及诊断条件下，通过厂家诊断界面记录电表型号、SN、实际目标地址和通信状态。','设备识别点表、驱动与固件兼容性、通信成功 / 故障码定义'],
 ['data','数据有效性','比较计量数据与质量','记录同一时刻电表与 iEMS 的功率、单位、方向、更新时间及质量状态。仅有非零读数不等于有效，不进行动态零馈测试。','功率点表、倍率和单位、正负方向、更新周期、允许偏差及失联判据'],
]
export function Commissioning({planId,disabled,locate,environment,onSupport}:{onSupport:(text:string)=>void;environment:Environment;planId:string;disabled:boolean;locate:(issue:Issue)=>void}){
 const [data,setData]=useState<Data|null>(null),[mode,setMode]=useState(environment==='SIMULATION'?'SIMULATION':'REAL'),[edgeId,setEdgeId]=useState(''),[index,setIndex]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState(false),[scenario,setScenario]=useState('normal'),[failureStep,setFailureStep]=useState('identity'),[status,setStatus]=useState('PENDING'),[recorder,setRecorder]=useState(''),[observation,setObservation]=useState(''),[reference,setReference]=useState('')
 async function refresh(){const d=await api<Data>(`/plans/${planId}/commissioning`);setData(d);setEdgeId(e=>d.edges.some(x=>x.edge_id===e)?e:d.edges[0]?.edge_id||'')}
 useEffect(()=>{void refresh().catch(e=>setError(e.message))},[planId])
 function choose(i:number){setIndex(i);setError('');setStatus('PENDING');setObservation('');setReference('')}
 if(!data)return <section className="m3Flow">{error?<p role="alert">{error}<button onClick={()=>void refresh().catch(e=>setError(e.message))}>重试</button></p>:<p>正在加载调试依据…</p>}</section>
 const edge=data.edges.find(e=>e.edge_id===edgeId),ports=edge?[edge.from_port_id,edge.to_port_id].map(id=>data.model.ports.find(p=>p.port_id===id)!):[]
 const params=generateSettings(data.model).filter(r=>r.definition.group==='通信'&&ports.some(p=>p.node_id===r.nodeId&&r.definition.domains.includes(p.domain)&&(!r.portId||r.portId===p.port_id)))
 let valid=true,parent:string|null=null
 const states=steps.map(([key])=>{const r=data.records.find(r=>r.edge_id===edgeId&&r.mode===mode&&r.step===key),unlocked=valid,current=!!(r&&valid&&r.predecessor_id===parent);valid=current&&r?.status==='PASS';parent=r?.id||null;return{r,current,unlocked}})
 const state=states[index],step=steps[index],allPassed=states.every(s=>s.current&&s.r?.status==='PASS'),readOnly=disabled||data.stale||environment==='REAL'
 async function automatic(){setBusy(true);setError('');try{const result=await api<{results:Entry[]}>(`/plans/${planId}/commissioning/auto`,{edge_id:edgeId,mode:environment,failure_step:scenario==='failure'?failureStep:null});await refresh();const failed=result.results.find(r=>r.status==='FAIL');setIndex(failed?steps.findIndex(s=>s[0]===failed.step):4)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const describe=(s:typeof state)=>s.r&&!s.current?'需重新验证':!s.r?'未验证':s.r.status==='PASS'?(mode==='SIMULATION'?'✓ 模拟通过':'条件已记录'):s.r.status==='FAIL'?'✕ 异常':'待确认'
 return <section className="m3Flow" aria-label="M2 自动测试"><header className="m3Title"><div><small>M2 / COMMISSIONING & SAT</small><h2>零馈表与 iEMS · 自动测试</h2><p>由 iEMS 测试程序按依赖顺序执行，工作台展示结果与异常。</p></div></header>
 <div className={'m3ModeNotice '+(mode==='REAL'?'field':'')}><b>{mode==='SIMULATION'?'模拟演练 · 未连接现场设备':'真实 iEMS · 未接入自动测试接口'}</b><span>{mode==='SIMULATION'?'使用独立合成数据，可演练正常与故障流程。不会写入 M1 参数，也不计入现场通过。':'当前没有真实设备结果。必须接入 iEMS 测试程序和适用厂家判据后才能执行，不能由人工打钩替代。'}</span></div>
 {!edge?<p>本模型没有零馈表与 iEMS 的直接通信连接。请先在 M1 补充设备与端口连接。</p>:<>
 {data.edges.length>1&&<label>选择通信回路<select value={edgeId} onChange={e=>{setEdgeId(e.target.value);choose(0)}}>{data.edges.map(e=><option key={e.edge_id}>{e.edge_id}</option>)}</select></label>}
 <div className="m3Route">{ports.map(p=><div key={p.port_id}><strong>{data.model.nodes.find(n=>n.node_id===p.node_id)?.name}</strong><small>{p.port_id} · {p.domain}</small></div>)}<span>{edgeId} · M1 逻辑连接 / 实物端子待确认</span></div>
 <nav className="m3Steps" aria-label="分步验证">{steps.map((s,i)=><button key={s[0]} aria-current={index===i?'step':undefined} onClick={()=>choose(i)}><b>0{i+1}</b><strong>{s[1]}</strong><small>{!states[i].unlocked?'等待前置验证':describe(states[i])}</small></button>)}</nav>
 {allPassed&&<div className="m3Complete" role="status">{mode==='SIMULATION'?'模拟 iEMS 自动测试完成。全部结果为合成数据，不是现场 SAT 通过。':'等待真实 iEMS 返回测试结果。'}</div>}
 <article className="m3Work"><header><div><small>STEP 0{index+1}</small><h3>{step[2]}</h3></div><span className="m2Tag">{describe(state)}</span></header>
 <p className="m3Method">{step[3]}</p><div className="m3Missing"><b>{index===0?'现场前提':'厂家依据待确认'}</b><span>{step[4]}</span></div>
 {index===1&&<div className="m3Wiring"><b>{ports[0].port_id}</b><span>→ 通信线缆、实物端子与线序待厂家图纸确认 →</span><b>{ports[1].port_id}</b><p>现场记录需包含：两端实物端子、各芯线对应、线缆规格、屏蔽与终端情况；不推定 A/B 极性。</p></div>}
 {index===2&&<div className="meterTable"><table><thead><tr><th>M1 设备 / 参数</th><th>计划值</th><th>已录入现场值</th><th>依据</th></tr></thead><tbody>{params.map(p=><tr key={p.id}><td>{p.deviceName} · {p.definition.label}</td><td>{String(p.record?.planned??'未录入')}</td><td>{String(p.record?.actual??'未录入')}</td><td>{p.stale?'版本变化，待重核':p.record?.reference_doc||'厂家依据待补'}</td></tr>)}</tbody></table></div>}
 {index===1&&<details className="otherGuidance"><summary>本步骤参考 · 系统通信接线总图</summary><CommunicationGuide model={data.model} locate={locate}/></details>}
 <button className="m3Locate" onClick={()=>locate({id:'m3-'+edgeId,layer:index===1?'L4':index===0?'L3':'L5',category:'缺失信息',object:step[1],message:step[4],action:'补充资料',nodeId:ports[0].node_id,rowId:index===1?edgeId:params[0]?.id,label:index===2&&params[0]?params[0].id+' actual':undefined})}>查看 / 补充 M1 {index===1?'接线':'资料与参数'} →</button>
 {!state.unlocked&&<p className="m3Blocked">等待前置步骤。自动程序将在前置通过后执行本项；异常会停止后续测试。</p>}{readOnly&&<p className="m3Blocked">{environment==='REAL'?'真实 iEMS 未连接：自动测试不可用，当前仅可查看步骤和依据。':'模型已变化，当前仅供查看。请先更新调试依据。'}</p>}
 <fieldset disabled={busy||readOnly} className="m3Inputs">{environment==='SIMULATION'&&<><label>自动测试场景<select aria-label="自动测试场景" value={scenario} onChange={e=>setScenario(e.target.value)}><option value="normal">全部正常（模拟）</option><option value="failure">指定步骤故障（模拟）</option></select></label>{scenario==='failure'&&<label>模拟故障步骤<select aria-label="模拟故障步骤" value={failureStep} onChange={e=>setFailureStep(e.target.value)}>{steps.map(s=><option key={s[0]} value={s[0]}>{s[1]}</option>)}</select></label>}</>}<button className="primary" onClick={()=>void automatic()}>{busy?'iEMS 正在执行…':environment==='SIMULATION'?'启动模拟 iEMS 自动测试':'启动真实 iEMS 自动测试'}</button></fieldset>
 {error&&<p role="alert">{error}</p>}{state.r&&<div className={'m3Result '+(state.r.status==='FAIL'?'failure':'')}><b>{mode==='SIMULATION'?'模拟结果':'现场记录'} · {describe(state)}</b><p>{state.r.observation}</p><small>{state.r.recorder} · {new Date(state.r.created).toLocaleString()} · {state.r.reference}</small>{state.r.status==='FAIL'&&<button onClick={()=>onSupport(`${environment==='SIMULATION'?'模拟演练':'真实 iEMS'} / ${edgeId} / ${step[1]}\n${state.r?.observation}\n测试记录：${state.r?.id}`)}>准备厂家协同 →</button>}</div>}
 <footer><button disabled={index===0} onClick={()=>choose(index-1)}>上一步</button><span>重做前置步骤后，后续结果需重新验证。</span><button className="primary" disabled={index===4||busy} onClick={()=>choose(index+1)}>查看下一测试项 →</button></footer>
 </article><details className="m3History"><summary>{mode==='SIMULATION'?'模拟':'现场'}历史记录 · {data.records.filter(r=>r.edge_id===edgeId&&r.mode===mode).length}</summary>{data.records.filter(r=>r.edge_id===edgeId&&r.mode===mode).map(r=><p key={r.id}>{steps.find(s=>s[0]===r.step)?.[1]} · {r.status} · {r.observation} · {r.created}</p>)}</details></>}
 </section>
}
