import {InstallationProvider} from './InstallationTracking'
import {InstallationPackages,evidenceLabels,interfaceIssue,type MissingAction} from './InstallationPackages'
import type {Issue} from './readinessIssues'
import {requirementsBefore} from './stageRequirements'
import {materializeTemplateSettings} from './settingsCatalog'
import {M1} from './M1'
import {useEffect,useState} from 'react'
import {api, type Model,type Kind,type Flow,type Plan,type Template,type Review,type Task} from './types'
import {Topology,colors} from './Topology'

const kinds:Kind[]=['ELECTRICAL','COMMUNICATION','CONTROL']
const names:Record<Kind,string>={ELECTRICAL:'电气连接',COMMUNICATION:'通信连接',CONTROL:'控制关系'}
const domainOptions=['AC','DC','ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO','CONTROL_LOGICAL']
const newId=(prefix:string)=>prefix+'_'+crypto.randomUUID().slice(0,8)
export default function App(){
 const [model,setModel]=useState<Model|null>(null),[revision,setRevision]=useState(0),[dirty,setDirty]=useState(false)
 const [projects,setProjects]=useState<{id:string;name:string}[]>([]),[tab,setTab]=useState('M1'),[selected,setSelected]=useState('BESS_01')
 const [layer,setLayer]=useState<Kind>('ELECTRICAL'),[scenario,setScenario]=useState('normal'),[flows,setFlows]=useState<Record<string,Flow>>({})
 const [message,setMessage]=useState('正在加载 LV-01…'),[busy,setBusy]=useState(false),[issues,setIssues]=useState<{valid:boolean;errors:string[];warnings:string[]}|null>(null)
 const [plans,setPlans]=useState<Plan[]>([]),[templates,setTemplates]=useState<Template[]>([]),[reviews,setReviews]=useState<Review[]>([])
 const [history,setHistory]=useState<{revision:number;created:string}[]>([]),[json,setJson]=useState(''),[showJson,setShowJson]=useState(false)
 const [reviewer,setReviewer]=useState('EPC Engineer'),[comment,setComment]=useState(''),[decision,setDecision]=useState('COMMENT')
 const [nodeType,setNodeType]=useState('PV_INVERTER'),[from,setFrom]=useState(''),[to,setTo]=useState(''),[portDomain,setPortDomain]=useState('AC')
 const [ruleText,setRuleText]=useState(''); const [editTemplate,setEditTemplate]=useState<Template|null>(null),[reason,setReason]=useState('工程评审演示')
 const [evidenceTask,setEvidenceTask]=useState(''),[evidence,setEvidence]=useState<Record<string,string>>({}),[note,setNote]=useState(''),[result,setResult]=useState('BLOCKED'),[records,setRecords]=useState<Record<string,unknown>[]>([])
 const [externalIssue,setExternalIssue]=useState<Issue|null>(null),[returnPackage,setReturnPackage]=useState('')
 const [navigationRequest,setNavigationRequest]=useState(0)
 function recordTask(t:Task,field?:string){setEvidenceTask(t.task_id);setEvidence({});setNote('');setResult('BLOCKED');setTimeout(()=>{const el=document.getElementById('task-evidence');el?.scrollIntoView({block:'center'});if(field)document.getElementById('evidence-'+field)?.focus()},100)}
 function packageAction(t:Task,a:MissingAction){
  setReturnPackage(t.task_id)
  if(a.action==='evidence'){recordTask(t,a.field||t.evidence_requirements[0]);return}
  if(a.action==='template'){const template=templates.find(x=>x.template_id===t.template_id);if(template){setEditTemplate({...template});setRuleText(JSON.stringify(template.rule,null,2));setTab('Templates');setTimeout(()=>document.querySelector<HTMLInputElement>('[aria-label="模板来源文档"]')?.focus(),100);return}}
  if(a.action==='interface'){const issue=interfaceIssue(model!,t);if(issue){setExternalIssue(issue);setTab('M1');return}}
  if(a.action==='parameter'){const p=(model!.parameters as {parameter_id:string;name:string}[]).find(p=>p.name===a.field);if(p){setExternalIssue({id:'m2-'+t.task_id,layer:'L5',category:'缺失信息',object:t.title,message:a.text,action:'补充依据',rowId:p.parameter_id,label:p.name+' reference'});setTab('M1');return}}
  setSelected(t.task_id);setComment(a.text+'\n原始要求：'+t.missing_inputs.join('；'));setTab('Review')
 }
 function navigate(key:string){if(key==='M2'&&model&&requirementsBefore(model,'M2').length){setTab('M1');setNavigationRequest(n=>n+1);setMessage('请先补充建模必填信息，草案可以随时保存。');return}setTab(key)}
 const id=model?.project.project_id||''
 const node=model?.nodes.find(n=>n.node_id===selected),edge=model?.edges.find(e=>e.edge_id===selected)
 const asset=model?.device_assets.find(a=>a.asset_id===node?.device_asset_id)
 const device=model?.device_models.find(d=>d.model_id===asset?.model_id)
 const plan=plans[0],task=plan?.tasks.find(t=>t.task_id===evidenceTask)
 async function run(action:()=>Promise<void>){setBusy(true);try{await action()}catch(e){setMessage('操作未完成：'+(e as Error).message)}finally{setBusy(false)}}
 function change(m:Model){setModel(m);setDirty(true);setIssues(null)}
 function update(fn:(m:Model)=>void){if(!model)return;const m=structuredClone(model);fn(m);change(m)}
 async function refresh(projectId:string){
  const [p,t,r,h]=await Promise.all([api<Plan[]>(`/projects/${projectId}/plans`),api<Template[]>('/templates'),api<Review[]>(`/projects/${projectId}/reviews`),api<{revision:number;created:string}[]>(`/projects/${projectId}/history`)])
  setPlans(p);setTemplates(t);setReviews(r);setHistory(h)
 }
 async function load(projectId:string){const p=await api<{model:Model;revision:number}>(`/projects/${projectId}`);setModel(p.model);setRevision(p.revision);setDirty(false);setIssues(null);localStorage.setItem('lpe-project',projectId);await refresh(projectId);setMessage('已载入保存版本 R'+p.revision)}
 useEffect(()=>{run(async()=>{const p=await api<{id:string;name:string}[]>('/projects');setProjects(p);await load(p.find(x=>x.id===localStorage.getItem('lpe-project'))?.id||p[0].id)})},[])
 useEffect(()=>{if(!id)return;let cancelled=false;const poll=async()=>{try{const t=await api<{flows:Record<string,Flow>}>(`/projects/${id}/telemetry?scenario=${scenario}`);if(!cancelled)setFlows(t.flows)}catch{if(!cancelled)setFlows({})}};poll();const timer=setInterval(poll,3000);return()=>{cancelled=true;clearInterval(timer)}},[id,scenario])
 useEffect(()=>{if(!plan){setRecords([]);return}api<Record<string,unknown>[]>(`/plans/${plan.id}/evidence`).then(setRecords).catch(()=>setRecords([]))},[plan?.id])
 async function save(){if(!model)return;const p=await api<{model:Model;revision:number}>('/projects',{model:materializeTemplateSettings(model),expected_revision:revision});setModel(p.model);setRevision(p.revision);setDirty(false);await refresh(id);setMessage('已保存不可变版本 R'+p.revision)}
 async function saveConnection(candidate:Model){
  setBusy(true)
  try{const p=await api<{model:Model;revision:number}>('/projects',{model:candidate,expected_revision:revision});setModel(p.model);setRevision(p.revision);setDirty(false);setIssues(null);setMessage('已保存连接与工程版本 R'+p.revision);try{await refresh(p.model.project.project_id)}catch{setMessage('连接已保存为 R'+p.revision+'；历史列表暂未刷新。')}}finally{setBusy(false)}
 }
 function addNode(){update(m=>{
  const nid=newId(nodeType),aid=newId('ASSET'),mid=newId('MODEL')
  const boundary=['LOAD','PCC','LV_BUS','BREAKER','TRANSFORMER'].includes(nodeType)
  m.nodes.push({node_id:nid,logical_id:nid,name:nodeType+' 新设备',node_type:nodeType,parent_node_id:null,zone_id:'ZONE_01',device_asset_id:boundary?null:aid,icon_key:nodeType.toLowerCase(),attributes:{},relationship_reason:'ENERGY_PATH'})
  if(!boundary){m.device_models.push({model_id:mid,manufacturer:'THIRD_PARTY_DEMO',model_name:'待确认型号',master_data_version:'DEMO-1',source_quality:'UNVERIFIED'});m.device_assets.push({asset_id:aid,model_id:mid,serial_number:null,sn_status:'PENDING',lifecycle_status:'PLANNED',modeling_level:'L2_INTERFACE',equipment_origin:'THIRD_PARTY',responsibility_owner:'EPC / supplier to confirm',authorization:{read_allowed:false,write_allowed:false,test_execution_allowed:false}})}
  for(const [suffix,domain,role] of [['AC','AC','BIDIRECTIONAL'],['COM','ETHERNET','BIDIRECTIONAL'],['CTRL','CONTROL_LOGICAL',nodeType==='EMS'?'OUT':'IN']])m.ports.push({port_id:nid+'.'+suffix,node_id:nid,name:suffix,domain,role,attributes:{}})
  m.view_layout.positions[nid]={x:100+Math.random()*400,y:450};setSelected(nid)
 })}
 function remove(){update(m=>{
  if(edge){m.edges=m.edges.filter(e=>e.edge_id!==selected);setMessage('连接已移除；请校验关联参数与测点。');return}
  if(!node)return
  const ports=new Set(m.ports.filter(p=>p.node_id===selected).map(p=>p.port_id))
  const removedEdges=new Set(m.edges.filter(e=>ports.has(e.from_port_id)||ports.has(e.to_port_id)).map(e=>e.edge_id))
  m.edges=m.edges.filter(e=>!removedEdges.has(e.edge_id));m.ports=m.ports.filter(p=>!ports.has(p.port_id));m.nodes=m.nodes.filter(n=>n.node_id!==selected)
  m.device_assets=m.device_assets.filter(a=>a.asset_id!==node.device_asset_id);delete m.view_layout.positions[selected]
  const removed=new Set([selected,...ports,...removedEdges,node.device_asset_id])
  m.parameters=(m.parameters as {owner_id:string}[]).filter(p=>!removed.has(p.owner_id))
  m.telemetry_bindings=(m.telemetry_bindings as {target_id:string}[]).filter(p=>!removed.has(p.target_id))
  // Keep interface/test/diagnostic references so validation explicitly flags unresolved dependencies.
  setMessage('设备已移除；关联测试与诊断引用保留供校验，修复依赖后才能保存。')
 })}
 function exportModel(){const url=URL.createObjectURL(new Blob([JSON.stringify(model,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=id+'-R'+revision+'.json';a.click();URL.revokeObjectURL(url)}
 if(!model)return <div className="loading">LIVOLTEK Project Engineer<p>{message}</p></div>
 return <div className={"app "+(tab==='M1'?'m1App':'')}>
  <nav className="nav" aria-label="主导航"><div className="brand">LIVOLTEK<span>Project Engineer</span></div><div className="navLinks">{[['M1','系统建模'],['M2','引导式安装'],['Review','技术协同'],['Templates','SOP 模板库']].map(([key,title],i)=><button key={key} className={tab===key?'active':''} aria-current={tab===key?'page':undefined} onClick={()=>navigate(key)}><b>0{i+1}</b>{title}</button>)}</div><div className="navFoot"><span className="dot"/>工程演示空间<span className="avatar">EP</span></div></nav>
  <main aria-busy={busy}><fieldset disabled={busy} className="appFieldset"><header className="hero"><div className="heroCopy"><small><span className="eyebrowLine"/> CONNECTED ENERGY. CLEAR ENGINEERING.</small><h1>{tab==='M1'?<>看见系统全貌，<br/><span>连接每一步。</span></>:tab==='M2'?<>从系统模型，<br/><span>走向有序安装。</span></>:tab==='Review'?<>让工程判断，<br/><span>有迹可循。</span></>:<>把专业经验，<br/><span>变成可靠指引。</span></>}</h1><p>{tab==='M1'?'将储能、光伏与相关设备汇聚在一张拓扑中，让工程团队围绕同一个项目，清晰建模、协同确认。':tab==='M2'?'依据项目拓扑与版本化模板，组织安装检查工作包，让每一项任务都有来源、责任与记录。':tab==='Review'?'围绕设备、连接与安装任务交流意见，保留每次修改依据和评审结论。':'维护厂家指导与接口检查模板，让经过评审的内容以明确版本进入项目。'}</p><div className="heroActions"><button className="primary" onClick={()=>document.getElementById('project-workspace')?.scrollIntoView({behavior:'smooth',block:'start'})}>{tab==='M1'?'进入拓扑工作区':tab==='M2'?'查看安装工作包':'进入项目工作区'} <span>↗</span></button><span className="heroMode"><span className="dot"/>模拟环境 · 无真实设备连接</span></div></div><div className="heroVisual" aria-label="系统协作示意"><div className="visualTop"><span>SYSTEM / CONNECTED</span><span>LV—01</span></div><svg viewBox="0 0 480 270" role="img" aria-label="光伏、储能与电网通过能源管理系统协同的概念示意"><g fill="none" stroke="#65867b" strokeWidth="1.5"><path d="M110 90H240V140M370 90H240M240 140V225H110M240 225H370"/><circle cx="240" cy="140" r="54" strokeDasharray="3 7"/><circle cx="240" cy="140" r="38" stroke="#d4f66b"/></g><g fill="#153c32" stroke="#718f82"><rect x="60" y="40" width="100" height="66" rx="12"/><rect x="320" y="40" width="100" height="66" rx="12"/><rect x="60" y="196" width="100" height="58" rx="12"/><rect x="320" y="196" width="100" height="58" rx="12"/></g><g fontFamily="sans-serif" textAnchor="middle" fill="#f3f6eb" fontSize="12"><text x="110" y="68">☀</text><text x="110" y="90">光伏 PV</text><text x="370" y="68">▥</text><text x="370" y="90">储能 ESS</text><text x="240" y="145" fill="#d4f66b" fontSize="17">EMS</text><text x="110" y="231">电网 GRID</text><text x="370" y="231">负载 LOAD</text></g><g fill="#d4f66b"><circle cx="186" cy="90" r="4"/><circle cx="294" cy="90" r="4"/><circle cx="240" cy="192" r="4"/></g></svg><div className="visualBottom"><span>完整系统 · 共同视图</span><span>概念示意 / 非实时数据</span></div></div></header>
   <section className="workspaceIntro" id="project-workspace"><div><small>YOUR PROJECT WORKSPACE</small><h2>{tab==='M1'?'系统工程拓扑':tab==='M2'?'厂家指导式安装':tab==='Review'?'技术协同记录':'受控 SOP 模板库'}</h2></div><span>建模 <i>→</i> 安装 <i>→</i> 评审</span></section>
   <section className="projectBar"><div><strong>{model.project.name}</strong><span>{model.project.structure_code} · 400 V 示例 · R{revision} {dirty?' · 未保存修改':''}</span></div><div className="actions"><select aria-label="选择项目" value={id} onChange={e=>{if(!dirty||confirm('放弃未保存修改并切换项目？'))run(()=>load(e.target.value))}}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><button disabled={busy} onClick={()=>run(async()=>{const m=structuredClone(model);m.project.project_id=newId('LV01');for(const p of m.parameters as {scope:string;owner_id:string}[]){if(p.scope==='PROJECT')p.owner_id=m.project.project_id}m.project.name='LV-01 新建样板';const saved=await api<{model:Model;revision:number}>('/projects',{model:m,expected_revision:0});setProjects(await api('/projects'));await load(saved.model.project.project_id)})}>复制为新项目</button><button className="primary" disabled={busy||!dirty} onClick={()=>run(save)}>保存版本</button></div></section>
   <div className="notice" role="status">{message}</div>
   {returnPackage&&tab!=='M2'&&<div className="notice"><button onClick={()=>{setExternalIssue(null);navigate('M2');setTimeout(()=>document.getElementById('package-'+returnPackage)?.scrollIntoView({block:'center'}),100)}}>返回安装工作包</button><span>修改项目后需保存并重新生成计划；填写资料不自动改变批准状态。</span></div>}
   {tab==='M1'&&<M1 model={model} change={change} selected={selected} select={setSelected} flows={flows} review={()=>setTab('Review')} reviews={reviews} revision={revision} scenario={scenario} setScenario={setScenario} saveConnection={saveConnection} enterInstallation={()=>navigate('M2')} navigationRequest={navigationRequest} externalIssue={externalIssue}/>}
   {tab==='M2'&&<><section className="card heading"><div><h2>安装检查工作包</h2><p>基于已保存拓扑和受控模板生成，保留生成时的版本及原始记录。</p></div><button className="primary" disabled={busy||dirty} onClick={()=>run(async()=>{await api(`/projects/${id}/plans`,{});await refresh(id);setMessage('已生成新的模拟安装计划。')})}>生成安装计划</button></section>{dirty&&<div className="warning card">拓扑有未保存修改，请先保存后生成计划。</div>}
    {plan?<><div className="planMeta">来源 R{plan.revision} · {new Date(plan.created).toLocaleString()} · {plan.stale?'拓扑已变化，必须重新生成':'当前工程模型'} · 模拟计划<button onClick={()=>run(async()=>{await api(`/plans/${plan.id}/publish`,{})})}>检查正式发布门禁</button></div><InstallationProvider key={plan.id} planId={plan.id} disabled={dirty||!!plan.stale}><InstallationPackages model={model} tasks={plan.tasks} onRecord={t=>recordTask(t)} onAction={packageAction}/></InstallationProvider>
     {task&&<section className="card" id="task-evidence"><h3>模拟结果 · {task.title}</h3><label>记录人<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label>{task.evidence_requirements.map(k=><label key={k}>{evidenceLabels[k]||'资料记录（'+k+'）'}<input id={'evidence-'+k} placeholder="证据编号、文档引用或观察记录" value={evidence[k]||''} onChange={e=>setEvidence({...evidence,[k]:e.target.value})}/></label>)}<label>结果<select value={result} onChange={e=>setResult(e.target.value)}>{['BLOCKED','FAIL','PASS'].map(x=><option key={x}>{x}</option>)}</select></label><label>备注<textarea value={note} onChange={e=>setNote(e.target.value)}/></label><button disabled={busy||dirty} onClick={()=>run(async()=>{await api(`/plans/${plan.id}/evidence`,{task_id:task.task_id,result,reviewer,evidence,note});setRecords(await api(`/plans/${plan.id}/evidence`));setMessage('模拟执行记录已保存，历史记录不会覆盖。')})}>保存模拟记录</button></section>}
     <section className="card"><h3>执行记录 ({records.length})</h3>{records.map(r=><p key={String(r.id)}>{String(r.task_id)} · {String(r.result)} · {String(r.note)} · {String(r.reviewer)}</p>)}</section><details className="card"><summary>历史计划 ({plans.length})</summary>{plans.map(p=><p key={p.id}>R{p.revision} · {p.created} · {p.tasks.length} 项 · {p.stale?'已过期':'同工程模型'}</p>)}</details></>:<section className="empty card">保存 M1 模型后，生成第一个安装检查工作包。</section>}</>}
   {tab==='Review'&&<div className="twoCol"><section className="card"><h2>记录技术支持意见</h2><label>评审对象<select value={selected} onChange={e=>setSelected(e.target.value)}>{[id,...model.nodes.map(x=>x.node_id),...model.edges.map(x=>x.edge_id),...templates.map(x=>x.template_id),...(plan?.tasks.map(t=>t.task_id)||[])].map(x=><option key={x}>{x}</option>)}</select></label><label>评审人<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>结论<select value={decision} onChange={e=>setDecision(e.target.value)}>{['COMMENT','UNDER_REVIEW','APPROVED','REJECTED'].map(x=><option key={x}>{x}</option>)}</select></label><label>意见<textarea aria-label="评审意见" value={comment} onChange={e=>setComment(e.target.value)}/></label><button className="primary" disabled={busy||dirty||!comment.trim()} onClick={()=>run(async()=>{await api(`/projects/${id}/reviews`,{target_id:selected,reviewer,comment,decision,revision});setComment('');await refresh(id);setMessage('评审意见已保存；模拟批准不改变正式作业权限。')})}>保存评审</button><p className="subtle">此处仅记录厂家与 EPC 的技术支持意见。模拟确认不代表系统获准投运，也不代替法定检验或合同验收。</p><h3>拓扑版本历史</h3>{history.map(h=><div className="history" key={h.revision}><span>R{h.revision} · {new Date(h.created).toLocaleString()}</span><button onClick={()=>run(async()=>{const old=await api<{model:Model}>(`/projects/${id}?revision=${h.revision}`);change(old.model);setTab('M1');setMessage('历史版本已载入为候选草案；保存会创建新版本。')})}>载入为草案</button></div>)}</section><section className="card"><h2>技术协同时间线</h2>{reviews.length?reviews.map(r=><article className="review" key={r.id}><span className="badge">{r.decision}</span><strong>{r.target_id}</strong><p>{r.comment}</p><small>{r.reviewer} · R{r.revision} · {new Date(r.created).toLocaleString()}</small></article>):<p>暂无评审意见。</p>}</section></div>}
   {tab==='Templates'&&<div className="twoCol"><section className="card"><h2>模板版本</h2><p>原始规则包为 DRAFT。批准仅用于演示版本管理，所有模板始终标识 DEMO ONLY。</p>{templates.map(t=><article className="review" key={t.template_id}><span className="badge">{t.status} · v{t.version}</span><h3>{t.title}</h3><p>{t.scope_type}</p><button onClick={()=>{setEditTemplate({...t});setRuleText(JSON.stringify(t.rule,null,2))}}>编辑 / 评审</button></article>)}</section><section className="card">{editTemplate?<><h2>创建模板新版本</h2><label>标题<input value={editTemplate.title} onChange={e=>setEditTemplate({...editTemplate,title:e.target.value})}/></label><label>指导内容<textarea rows={6} value={editTemplate.instructions} onChange={e=>setEditTemplate({...editTemplate,instructions:e.target.value})}/></label><label>来源文档<input aria-label="模板来源文档" value={editTemplate.source_document_ref||''} onChange={e=>setEditTemplate({...editTemplate,source_document_ref:e.target.value||null})}/></label><label>模拟评审状态<select value={editTemplate.status} onChange={e=>setEditTemplate({...editTemplate,status:e.target.value})}>{['DRAFT','UNDER_REVIEW','APPROVED','REJECTED'].map(x=><option key={x}>{x}</option>)}</select></label><label>评审人<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>适用规则与依赖（JSON）<textarea className="json" aria-label="模板规则" value={ruleText} onChange={e=>setRuleText(e.target.value)}/></label><label>变更原因<input value={reason} onChange={e=>setReason(e.target.value)}/></label><button className="primary" disabled={busy} onClick={()=>run(async()=>{await api('/templates/'+editTemplate.template_id,{...editTemplate,rule:JSON.parse(ruleText),expected_version:editTemplate.version,reviewer,reason});setEditTemplate(null);await refresh(id);setMessage('新模板版本已保存，已有计划保留原模板。')})}>保存新版本</button></>:<p>选择模板查看或修改。</p>}</section></div>}
   <footer>LIVOLTEK Project Engineer 是主设备厂家提供给 EPC 工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。不取代 EPC 专业电气设计、施工管理、法定检验或合同验收工具。</footer>
  </fieldset></main>
 </div>
}



