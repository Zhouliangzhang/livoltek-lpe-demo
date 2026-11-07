import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
import {api} from './types'
type Target={id:string;name:string;kind:string;detail:string}
type Entry={id:string;task_id:string;target_id:string;status:string;recorder:string;note:string;photo_ids:string[];created:string}
type Data={targets:Record<string,Target[]>;records:Entry[]}
const Context=createContext<{planId:string;disabled:boolean;data:Data;refresh:()=>Promise<void>}|null>(null)
const statuses:Record<string,string>={NOT_STARTED:'未开始',IN_PROGRESS:'安装中',COMPLETED:'安装已记录完成',BLOCKED:'待处理'}
export function InstallationProvider({planId,disabled,children}:{planId:string;disabled:boolean;children:ReactNode}){
 const [data,setData]=useState<Data>({targets:{},records:[]}),[error,setError]=useState('')
 async function refresh(){setData(await api<Data>(`/plans/${planId}/installation`))}
 useEffect(()=>{let active=true;api<Data>(`/plans/${planId}/installation`).then(d=>{if(active)setData(d)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[planId])
 return <Context.Provider value={{planId,disabled,data,refresh}}>{error&&<p role="alert">安装记录加载失败：{error}</p>}{children}</Context.Provider>
}
export function InstallationTracking({taskId}:{taskId:string}){
 const ctx=useContext(Context)!,{data,planId,disabled,refresh}=ctx
 const [open,setOpen]=useState(false),[onlyMissing,setOnlyMissing]=useState(true),[selected,setSelected]=useState<Target|null>(null)
 const [status,setStatus]=useState('NOT_STARTED'),[recorder,setRecorder]=useState('EPC Engineer'),[note,setNote]=useState(''),[photos,setPhotos]=useState<string[]>([]),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 const items=data.targets[taskId]||[],latest=(id:string)=>data.records.find(r=>r.task_id===taskId&&r.target_id===id)
 const missing=items.filter(t=>latest(t.id)?.status!=='COMPLETED')
 function edit(t:Target){const r=latest(t.id);setSelected(t);setStatus(r?.status||'NOT_STARTED');setRecorder(r?.recorder||'EPC Engineer');setNote(r?.note||'');setPhotos(r?.photo_ids||[]);setMessage('');setTimeout(()=>{const el=document.getElementById(`install-note-${taskId}`);el?.scrollIntoView({block:'center'});el?.focus()},80)}
 async function upload(files:FileList|null){if(!files||!selected)return;setBusy(true);setMessage('');try{
  if(files.length+photos.length>10)throw Error('每条记录最多 10 张照片')
  for(const file of Array.from(files)){
   if(file.size>5*1024*1024)throw Error('单张照片不能超过 5 MB')
   const params=new URLSearchParams({task_id:taskId,target_id:selected.id,filename:file.name})
   const response=await fetch(`/api/plans/${planId}/installation/photos?${params}`,{method:'POST',body:file,headers:{'Content-Type':file.type}})
   const result=await response.json();if(!response.ok)throw Error(result.detail)
   setPhotos(p=>[...p,result.id])
  }
  setMessage('照片已上传，请保存安装记录以关联本次状态。')
 }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function save(){if(!selected)return;setBusy(true);setMessage('');try{await api(`/plans/${planId}/installation`,{task_id:taskId,target_id:selected.id,status,recorder,note,photo_ids:photos});await refresh();setMessage('安装记录已保存；未改变厂家确认或工程批准状态。')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <section className="installationTracking" aria-label={taskId+' 逐项安装记录'}><div className="trackingHeading"><div><h4>设备 / 回路安装台账</h4><span>{items.length} 项关联 · {items.length-missing.length} 项已记录完成 · {missing.length} 项未完成</span></div><button onClick={()=>setOpen(!open)}>{open?'收起台账':'查看未完成项'} →</button></div>
 {open&&<><label className="trackingFilter"><input type="checkbox" checked={onlyMissing} onChange={e=>setOnlyMissing(e.target.checked)}/>只看未完成</label><div className="trackingTable"><table><thead><tr><th>设备 / 回路</th><th>安装状态</th><th>现场照片</th><th>处理</th></tr></thead><tbody>{(onlyMissing?missing:items).map(t=>{const r=latest(t.id);return <tr key={t.id}><td><strong>{t.name}</strong><small>{t.kind} · {t.id}<br/>{t.detail}</small></td><td>{statuses[r?.status||'NOT_STARTED']}</td><td>{r?.photo_ids.length||0} 张</td><td><button disabled={busy} onClick={()=>edit(t)} aria-label={taskId+' 处理 '+t.id}>定位补充 →</button></td></tr>})}</tbody></table>{onlyMissing&&!missing.length&&<p>当前工作包全部已记录完成；仍须满足厂家确认与工程批准要求。</p>}</div>
 {selected&&<section className="installationEditor" aria-label={taskId+' 安装记录编辑'}><h4>{selected.name} · {selected.id}</h4><p>记录对应当前计划，重新生成计划后不自动沿用完成结论。旧记录保留在历史计划中。</p><fieldset disabled={disabled||busy}><div className="trackingFields"><label>安装状态<select aria-label={taskId+' 安装状态'} value={status} onChange={e=>setStatus(e.target.value)}>{Object.entries(statuses).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>记录人<input value={recorder} onChange={e=>setRecorder(e.target.value)}/></label></div><label>现场说明 / 未完成原因<textarea id={'install-note-'+taskId} value={note} onChange={e=>setNote(e.target.value)}/></label><label>上传现场照片（PNG / JPEG，每张不超过 5 MB）<input type="file" accept="image/png,image/jpeg" multiple aria-label={taskId+' 上传现场照片'} onChange={e=>{void upload(e.target.files);e.target.value=''}}/></label><div className="installationPhotos">{photos.map(id=><a key={id} href={'/api/installation/photos/'+id} target="_blank" rel="noreferrer"><img src={'/api/installation/photos/'+id} alt={selected.name+' 现场记录照片'}/></a>)}</div><button className="primary" onClick={save}>保存此项安装记录</button></fieldset><p role="status">{message}</p>{disabled&&<p>模型已修改或计划已过期，请先保存并重新生成计划。</p>}<small>“安装已记录完成”需现场说明及照片，不等于检查通过或允许上电。</small><details><summary>本项记录历史（{data.records.filter(r=>r.task_id===taskId&&r.target_id===selected.id).length}）</summary>{data.records.filter(r=>r.task_id===taskId&&r.target_id===selected.id).map(r=><p key={r.id}>{statuses[r.status]} · {r.recorder} · {new Date(r.created).toLocaleString()} · {r.note} · {r.photo_ids.length} 张照片</p>)}</details></section>}</>}
 </section>
}
