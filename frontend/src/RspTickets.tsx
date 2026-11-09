import {useEffect,useState} from 'react'
import {api} from './types'
export function RspTickets({project,mode,blocked,open}:{project:string;mode:string;blocked:boolean;open:(id:string)=>Promise<void>}){
 const [data,setData]=useState<{packages:{id:string;revision:number}[];tickets:{id:string;package_id:string;device_id:string;symptom:string;site_id:string;case_id:string|null}[]}>({packages:[],tickets:[]}),[pid,setPid]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const root=`/projects/${project}/rsp-tickets`
 async function refresh(){setData(await api(root+'?mode='+mode))}
 useEffect(()=>{void refresh().catch(e=>setError(e.message))},[root,mode])
 async function act(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <article className="serviceCard"><small>RSP → M4 / SIMULATION</small><h2>模拟 RSP 工单箱</h2><p>由厂家建档回执关联站点与交接基线，接单后自动带入设备、端口和故障现象。真实平台尚未接入，不发送工单或现场指令。</p>{error&&<p role="alert">{error}</p>}{mode==='SIMULATION'?<><label>已建档交接基线<select aria-label="RSP工单交接基线" value={pid||data.packages[0]?.id||''} onChange={e=>setPid(e.target.value)}>{data.packages.map(p=><option key={p.id} value={p.id}>R{p.revision} · {p.id.slice(0,8)}</option>)}</select></label><button disabled={busy||blocked||!data.packages.length} onClick={()=>void act(async()=>{await api(root,{mode,package_id:pid||data.packages[0].id});await refresh()})}>生成零馈表失联模拟工单</button>{!data.packages.length&&<p>先在 M3 完成厂家服务建档模拟回执。</p>}{data.tickets.map(t=><div className="serviceCheck" key={t.id}><div><h3>{t.device_id} · 零馈表失联</h3><p>{t.symptom}</p><small>模拟工单 {t.id.slice(0,8)} · 站点 {t.site_id} · 交接 {t.package_id.slice(0,8)}</small></div><button disabled={busy||blocked} onClick={()=>void act(async()=>{const c=await api<{id:string}>(root+'/'+t.id+'/accept',{mode});await refresh();await open(c.id)})}>{t.case_id?'打开关联服务单':'接单并进入引导诊断'}</button></div>)}</>:<p>当前环境不接收模拟工单；真实 RSP 接入待完成。</p>}</article>
}
