import {useEffect,useState} from 'react'
import {api,type Task} from './types'
type RecordEntry={id:string;task_id:string;target_id:string;status:string;note:string;recorder:string;photo_ids:string[]}
export function LegacyInspectionRecords({planId,tasks}:{planId:string;tasks:Task[]}){
 const [records,setRecords]=useState<RecordEntry[]>([]),[error,setError]=useState('')
 useEffect(()=>{let live=true;api<{records:RecordEntry[]}>(`/plans/${planId}/installation`).then(d=>{if(live)setRecords(d.records)}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[planId])
 return <details className="m2Legacy"><summary>旧版技术参考与现场记录 · 只读</summary><p>历史工作包及现场反馈原样保留，新的点检统一在上方三步骤中填写。</p>{error&&<p role="alert">{error}</p>}{tasks.map(t=><article key={t.task_id}><b>{t.title} · 模板 v{t.template_version}</b><p>{t.instructions}</p>{records.filter(r=>r.task_id===t.task_id).map(r=><div key={r.id}><p>{r.target_id} · {r.status} · {r.recorder} · {r.note}</p>{r.photo_ids.map(id=><a key={id} href={'/api/installation/photos/'+id} target="_blank" rel="noreferrer"><img src={'/api/installation/photos/'+id} alt="历史现场照片"/></a>)}</div>)}</article>)}</details>
}
