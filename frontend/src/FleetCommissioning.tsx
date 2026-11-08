import {useEffect,useRef,useState} from 'react'
import {api,type Edge} from './types'
import type {Environment} from './ConfigurationDelivery'
import type {Issue} from './readinessIssues'
import './fleet.css'

type Device={node_id:string;name:string;sn:string|null;route:{edge_id:string;from:string;to:string;domain:string}[];controls:Edge[]}
type Group={id:string;kind:string;name:string;model:string;manufacturer:string;version:string;devices:Device[]}
type Step={key:string;label:string;status:string;code:string;observation:string}
type Result={id:string;node_id:string;mode:string;status:string;created:string;steps:Step[]}
type Data={groups:Group[];records:Result[];stale:boolean}
const labels:Record<string,string>={communication:'通信连通',identity:'设备识别',data:'数据有效性',limit:'光伏限功率',charge:'储能充电',discharge:'储能放电',restore:'控制恢复'}
export function FleetCommissioning({planId,environment,disabled,locate,onSupport}:{planId:string;environment:Environment;disabled:boolean;locate:(i:Issue)=>void;onSupport:(s:string)=>void}){
 const [data,setData]=useState<Data|null>(null),[error,setError]=useState(''),[running,setRunning]=useState(''),[busy,setBusy]=useState(false),[done,setDone]=useState(0),[total,setTotal]=useState(0),[open,setOpen]=useState<string[]>([]),[selected,setSelected]=useState(''),[fault,setFault]=useState(''),[failureStep,setFailureStep]=useState('identity')
 const cancelled=useRef(false),active=useRef(false)
 useEffect(()=>{cancelled.current=false;api<Data>(`/plans/${planId}/fleet`).then(d=>{if(!cancelled.current)setData(d)}).catch(e=>{if(!cancelled.current)setError(e.message)});return()=>{cancelled.current=true}},[planId])
 const devices=data?.groups.flatMap(g=>g.devices)||[],real=environment==='REAL'
 const latest=(id:string)=>real?undefined:data?.records.find(r=>r.node_id===id&&r.mode==='SIMULATION')
 const failures=devices.filter(d=>['FAIL','BLOCKED'].includes(latest(d.node_id)?.status||''))
 const passed=devices.filter(d=>latest(d.node_id)?.status==='PASS').length
 const faultGroup=data?.groups.find(g=>g.devices.some(d=>d.node_id===fault))
 const keys=(g?:Group)=>['communication','identity','data',...(g?.kind==='BESS'?['charge','discharge']:['limit']),'restore']
 const blocked=disabled||!!data?.stale||real
 function focus(g:Group,d:Device){setOpen(o=>o.includes(g.id)?o:[...o,g.id]);setSelected(d.node_id)}
 function fix(d:Device,layer:'L4'|'L5'){locate({id:'fleet-'+d.node_id,layer,category:'缺失信息',object:d.name,message:'补充通信连接、控制关系与厂家参数依据',action:'补充资料',nodeId:d.node_id,rowId:layer==='L4'?d.route[0]?.edge_id:undefined})}
 async function run(targets:Device[]){
  if(active.current||blocked)return
  active.current=true;cancelled.current=false;setBusy(true);setDone(0);setTotal(targets.length);setError('')
  try{for(const d of targets){
   if(cancelled.current)break
   setRunning(d.node_id)
   const result=await api<Result>(`/plans/${planId}/fleet`,{mode:environment,node_id:d.node_id,failure_step:fault===d.node_id?failureStep:null})
   if(cancelled.current)break
   setData(old=>old?{...old,records:[result,...old.records]}:old);setDone(n=>n+1)
  }}catch(e){if(!cancelled.current)setError((e as Error).message)}finally{active.current=false;if(!cancelled.current){setBusy(false);setRunning('')}}
 }
 return <section className="fleet" aria-label="光储设备自动测试"><header className="fleetTitle"><div><small>M2 / DEVICE TESTS</small><h2>光伏、储能与 iEMS</h2><p>同型号合并展示 · 逐台检测通信与控制 · 异常独立处理</p></div><span className={'fleetSource '+(real?'real':'')}>{real?'现场结果 · 尚未接入':'模拟结果 · 合成数据'}</span></header>
 <div className="fleetSummary"><div><strong>{devices.length}</strong><span>台设备</span></div><div><strong>{passed}</strong><span>{real?'现场通过':'模拟通过'}</span></div><div className={failures.length?'warn':''}><strong>{failures.length}</strong><span>异常 / 阻塞</span></div><div><strong>{devices.length-passed-failures.length}</strong><span>{real?'等待现场测试':'未检测'}</span></div><p>{real?'真实 iEMS 未接入，无现场结果；模拟记录不会作为现场 SAT 结果。':'模拟器逐台执行，单台异常停止该台后续步骤，继续检测其余设备。控制演练不会下发到现场。'}</p></div>
 {!data&&<p>正在加载设备分组…</p>}
 <div className="fleetToolbar"><button className="primary" disabled={busy||blocked||!devices.length} onClick={()=>void run(devices)}>{busy?`逐台检测中 ${done} / ${total}`:real?'启动现场设备测试':'自动检测全部光储设备'}</button>{running&&<span role="status">正在检测 {running}</span>}{!real&&<><label>模拟故障设备<select aria-label="模拟故障设备" disabled={busy} value={fault} onChange={e=>{setFault(e.target.value);setFailureStep('identity')}}><option value="">不注入故障</option>{devices.map(d=><option key={d.node_id} value={d.node_id}>{d.node_id} · {d.name}</option>)}</select></label>{fault&&<label>故障项目<select aria-label="光储故障项目" disabled={busy} value={failureStep} onChange={e=>setFailureStep(e.target.value)}>{keys(faultGroup).map(k=><option key={k} value={k}>{labels[k]}</option>)}</select></label>}</>}{!busy&&total>0&&<span role="status">本轮已检测 {done} / {total} 台</span>}</div>
 {error&&<p role="alert" className="fleetError">{error}</p>}{disabled||data?.stale?<p className="fleetError">M1 模型尚未保存或依据已变化，请先保存并更新调试依据。</p>:null}
 {failures.length>0&&<aside className="fleetExceptions" aria-label="光储异常"><h3>需要处理 · {failures.length} 台</h3>{failures.map(d=>{const g=data!.groups.find(g=>g.devices.includes(d))!,r=latest(d.node_id)!,s=r.steps.at(-1)!;return <div key={d.node_id}><b>{d.node_id}</b><span>{s.label} · {s.code}<small>{s.observation}</small></span><button onClick={()=>focus(g,d)}>查看逐台记录</button><button onClick={()=>fix(d,s.code.startsWith('M1_')?'L4':'L5')}>定位 M1</button><button onClick={()=>onSupport(`模拟演练 / ${d.node_id} / ${s.label}\n${s.code}: ${s.observation}\n记录 ${r.id}（不是现场故障）`)}>准备厂家协同</button></div>})}</aside>}
 <div className="fleetGroups">{data?.groups.map(g=>{const count=g.devices.filter(d=>latest(d.node_id)?.status==='PASS').length,errors=g.devices.filter(d=>['FAIL','BLOCKED'].includes(latest(d.node_id)?.status||'')).length;return <article className="fleetGroup" key={g.id} aria-label={g.name+'测试组'}><header><div><small>{g.kind==='BESS'?'ENERGY STORAGE':'SOLAR INVERTERS'}</small><h3>{g.name} <span>{g.devices.length} 台</span></h3><b>{g.model}</b><p>{g.manufacturer} · 主数据 {g.version}</p></div><div className="fleetGroupActions"><strong>{real?'无现场结果':`${count} / ${g.devices.length} 模拟通过`}</strong>{errors>0&&<span className="fleetBad">{errors} 台异常 / 阻塞</span>}<button disabled={busy||blocked} onClick={()=>void run(g.devices)}>检测本组</button></div></header><div className="fleetTopics">{keys(g).map(k=><span key={k}>{labels[k]}</span>)}</div><p className="fleetBasis">厂家依据待确认：驱动 / 点表、通信超时与数据质量判据、{g.kind==='BESS'?'充放电方向、SOC 与功率边界、联锁':'限功率单位、范围与斜率'}、控制反馈容差和恢复方法。合成结果不确认这些要求。</p><button className="fleetExpand" aria-expanded={open.includes(g.id)} onClick={()=>setOpen(o=>o.includes(g.id)?o.filter(x=>x!==g.id):[...o,g.id])}>{open.includes(g.id)?'收起':'展开'}逐台记录 · {g.devices.length} 台 <span>{open.includes(g.id)?'−':'＋'}</span></button>
 {open.includes(g.id)&&<div className="fleetRows">{g.devices.map(d=>{const r=latest(d.node_id),isFail=r&&r.status!=='PASS';return <div key={d.node_id} className={'fleetDevice '+(isFail?'hasError':'')}><div className="fleetDeviceLine"><button aria-expanded={selected===d.node_id} onClick={()=>setSelected(selected===d.node_id?'':d.node_id)}><b>{d.node_id}</b><span>{d.name}</span></button><span className={isFail?'fleetBad':''}>{running===d.node_id?'检测中…':real?'无现场结果':r?(r.status==='PASS'?'✓ 模拟通过':r.status==='BLOCKED'?'待补 M1':'✕ 模拟异常'):'未检测'}</span><button disabled={busy||blocked} onClick={()=>void run([d])}>重测此台</button></div>{selected===d.node_id&&<div className="fleetDetail"><p>现场 SN：{d.sn||'待 EPC 录入'} · {r?new Date(r.created).toLocaleString():'尚无测试记录'}</p><div className="fleetRoute">{d.route.length?d.route.map(e=><span key={e.edge_id}>{e.from} → {e.to} · {e.domain}</span>):'M1 缺少通信路径'}{d.controls.map(e=><span key={e.edge_id}>逻辑控制：{e.from_port_id} → {e.to_port_id}</span>)}</div><p>上述端口来自 M1；逻辑控制关系不代表独立物理线缆，实物针脚与协议映射待厂家确认。</p>{keys(g).map(k=>{const s=r?.steps.find(s=>s.key===k);return <div className="fleetStep" key={k}><b>{labels[k]}</b><span>{s?s.status==='PASS'?'✓ 模拟通过':s.status==='BLOCKED'?'待补资料':'✕ 异常':r&&r.status!=='PASS'?'未执行 · 前置异常':'未执行'}<small>{s?.observation}</small></span></div>})}<button onClick={()=>fix(d,'L5')}>查看 / 补充 M1 参数</button></div>}</div>})}</div>}</article>})}</div>
 <p className="fleetFootnote">每次结果独立保存并关联 M1 配置读回记录。实际通信、控制效果及 SAT 结论须由真实 iEMS 和适用厂家判据验证。</p></section>
}
