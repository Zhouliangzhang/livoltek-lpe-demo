import {CommissioningBasis} from './CommissioningBasis'
import {M1Start,type WorkEnvironment} from './M1Start'
import {MeterWorkflow} from './MeterWorkflow'
import {ProjectHandover,type HandoverTarget} from './Handover'
import {ConfigurationDelivery} from './ConfigurationDelivery'
import {InstallationPackages,evidenceLabels,interfaceIssue,type MissingAction} from './InstallationPackages'
import type {Issue} from './readinessIssues'
import {requirementsBefore} from './stageRequirements'
import {materializeTemplateSettings} from './settingsCatalog'
import {M1} from './M1'
import {useEffect,useState,useRef} from 'react'
import {api, type Model,type Kind,type Flow,type Plan,type Template,type Review,type Task} from './types'
import {Topology,colors} from './Topology'

const kinds:Kind[]=['ELECTRICAL','COMMUNICATION','CONTROL']
const names:Record<Kind,string>={ELECTRICAL:'电气连接',COMMUNICATION:'通信连接',CONTROL:'控制关系'}
const domainOptions=['AC','DC','ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO','CONTROL_LOGICAL']
const newId=(prefix:string)=>prefix+'_'+crypto.randomUUID().slice(0,8)
export default function App(){
 const [basisId,setBasisId]=useState(''),[m1Step,setM1Step]=useState(1)
 const [environment,setEnvironment]=useState<WorkEnvironment>(()=>{const e=localStorage.getItem('iems-environment');return e==='OFFLINE'||e==='REAL'?e:'SIMULATION'})
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
 const [handoverId,setHandoverId]=useState(''),[handoverReturn,setHandoverReturn]=useState(false),[workflowTarget,setWorkflowTarget]=useState<HandoverTarget|null>(null)
 const [loadedProject,setLoadedProject]=useState(''),[checklistError,setChecklistError]=useState('')
 const autoAttempt=useRef('')
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
 function navigate(key:string){if((key==='M2'||key==='M3')&&environment==='OFFLINE'){setTab('M1');setMessage('离线编制不启动测试或交接；请选择模拟或现场环境。');return}if(key==='M2'&&environment==='REAL'){setTab('M1');setMessage('现场 iEMS 未连接，尚不能启动现场调试。');return}if(key==='M2')setWorkflowTarget(null);if(key==='M3')setReturnPackage('');if(key==='M2'&&model&&requirementsBefore(model,'M2').length){setTab('M1');setNavigationRequest(n=>n+1);setMessage('请先补充建模必填信息，草案可以随时保存。');return}setTab(key)}
 const id=model?.project.project_id||''
 const node=model?.nodes.find(n=>n.node_id===selected),edge=model?.edges.find(e=>e.edge_id===selected)
 const asset=model?.device_assets.find(a=>a.asset_id===node?.device_asset_id)
 const device=model?.device_models.find(d=>d.model_id===asset?.model_id)
 const plan=plans[0],workflowPlan=plans.find(p=>p.id===workflowTarget?.plan_id)||plans[0],task=plan?.tasks.find(t=>t.task_id===evidenceTask)
 async function run(action:()=>Promise<void>){setBusy(true);try{await action()}catch(e){setMessage('操作未完成：'+(e as Error).message)}finally{setBusy(false)}}
 function change(m:Model){setModel(m);setDirty(true);setIssues(null)}
 function update(fn:(m:Model)=>void){if(!model)return;const m=structuredClone(model);fn(m);change(m)}
 async function refresh(projectId:string){
  const [p,t,r,h]=await Promise.all([api<Plan[]>(`/projects/${projectId}/plans`),api<Template[]>('/templates'),api<Review[]>(`/projects/${projectId}/reviews`),api<{revision:number;created:string}[]>(`/projects/${projectId}/history`)])
  setPlans(p);setTemplates(t);setReviews(r);setHistory(h)
 }
 async function load(projectId:string){setBasisId('');setWorkflowTarget(null);setHandoverId('');setHandoverReturn(false);const p=await api<{model:Model;revision:number}>(`/projects/${projectId}`);setModel(p.model);setRevision(p.revision);setDirty(false);setIssues(null);localStorage.setItem('lpe-project',projectId);await refresh(projectId);setLoadedProject(projectId);setChecklistError('');setMessage('已载入保存版本 R'+p.revision)}
 useEffect(()=>{run(async()=>{const p=await api<{id:string;name:string}[]>('/projects');setProjects(p);await load(p.find(x=>x.id===localStorage.getItem('lpe-project'))?.id||p[0].id)})},[])
 useEffect(()=>{if(!id||environment!=='SIMULATION'){setFlows({});return}let cancelled=false;const poll=async()=>{try{const t=await api<{flows:Record<string,Flow>}>(`/projects/${id}/telemetry?scenario=${scenario}`);if(!cancelled)setFlows(t.flows)}catch{if(!cancelled)setFlows({})}};poll();const timer=setInterval(poll,3000);return()=>{cancelled=true;clearInterval(timer)}},[id,scenario,environment])
 useEffect(()=>{if(!plan){setRecords([]);return}api<Record<string,unknown>[]>(`/plans/${plan.id}/evidence`).then(setRecords).catch(()=>setRecords([]))},[plan?.id])
 async function generateChecklist(){
  setBusy(true);setChecklistError('')
  try{
   // Re-read before creating: retries after a lost response reuse the existing snapshot.
   const existing=await api<Plan[]>(`/projects/${id}/plans`)
   if(!existing[0]||existing[0].stale)await api(`/projects/${id}/plans`,{})
   await refresh(id)
  }catch(e){setChecklistError((e as Error).message)}finally{setBusy(false)}
 }
 useEffect(()=>{
  const attempt=id+':'+revision
  if(tab!=='M2'||busy||dirty||plan||loadedProject!==id||autoAttempt.current===attempt)return
  autoAttempt.current=attempt
  void generateChecklist()
 },[tab,busy,dirty,plan,id,revision,loadedProject])
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
 if(!model)return <div className="loading">iEMS 工程工作台<p>{message}</p></div>
 return <div className={"app "+(tab==='M1'?'m1App':'m2App')}>
  <nav className="nav" aria-label="主导航"><div className="brand">LIVOLTEK<span>iEMS 工程工作台</span></div><div className="navLinks">{[['M1','系统建模与设置'],['M2','调试与 SAT'],['M3','项目交接'],['M4','现场服务']].map(([key,title],i)=><button key={key} className={tab===key?'active':''} aria-current={tab===key?'page':undefined} onClick={()=>navigate(key)}><b>{key}</b>{title}</button>)}</div><div className="navFoot"><span className="dot"/>iEMS 工程接入<span className="avatar">EP</span></div></nav>
  <main aria-busy={busy}><section className="iemsEnvironment" aria-label="iEMS 连接环境"><div><strong>{environment==='OFFLINE'?'离线编制 · 不连接设备':environment==='SIMULATION'?'模拟 iEMS · 独立演练环境':'真实 iEMS · 未连接'}</strong><span>{environment==='OFFLINE'?'仅保存工程草案，不下发配置、不执行测试。':environment==='SIMULATION'?'配置、测试与日志均为模拟，不代表现场状态。':'未接入设备配置、测试和日志接口；不执行真实操作。'}</span></div><select aria-label="选择 iEMS 环境" value={environment} onChange={e=>{setBasisId('');setEnvironment(e.target.value as WorkEnvironment);localStorage.setItem('iems-environment',e.target.value);setExternalIssue(null);if(e.target.value==='OFFLINE')setTab('M1')}}><option value="OFFLINE">离线编制</option><option value="SIMULATION">模拟 iEMS</option><option value="REAL">真实 iEMS（未连接）</option></select></section><fieldset disabled={busy} className="appFieldset"><header className="hero"><div className="heroCopy"><small><span className="eyebrowLine"/> CONNECTED ENERGY. CLEAR ENGINEERING.</small><h1>{tab==='M1'?<>看见系统全貌，<br/><span>连接每一步。</span></>:tab==='M2'?<>从系统模型，<br/><span>逐项完成点检。</span></>:tab==='Review'?<>让工程判断，<br/><span>有迹可循。</span></>:<>把专业经验，<br/><span>变成可靠指引。</span></>}</h1><p>{tab==='M1'?'将储能、光伏与相关设备汇聚在一张拓扑中，让工程团队围绕同一个项目，清晰建模、协同确认。':tab==='M2'?'按电气、通信、控制逐项核对设备与回路，记录现场反馈，让每个问题都有对应位置。':tab==='Review'?'围绕设备、连接与安装任务交流意见，保留每次修改依据和评审结论。':'维护厂家指导与接口检查模板，让经过评审的内容以明确版本进入项目。'}</p><div className="heroActions"><button className="primary" onClick={()=>document.getElementById('project-workspace')?.scrollIntoView({behavior:'smooth',block:'start'})}>{tab==='M1'?'进入拓扑工作区':tab==='M2'?'开始系统点检':'进入项目工作区'} <span>↗</span></button><span className="heroMode"><span className="dot"/>模拟环境 · 无真实设备连接</span></div></div><div className="heroVisual" aria-label="系统协作示意"><div className="visualTop"><span>SYSTEM / CONNECTED</span><span>LV—01</span></div><svg viewBox="0 0 480 270" role="img" aria-label="光伏、储能与电网通过能源管理系统协同的概念示意"><g fill="none" stroke="#65867b" strokeWidth="1.5"><path d="M110 90H240V140M370 90H240M240 140V225H110M240 225H370"/><circle cx="240" cy="140" r="54" strokeDasharray="3 7"/><circle cx="240" cy="140" r="38" stroke="#d4f66b"/></g><g fill="#153c32" stroke="#718f82"><rect x="60" y="40" width="100" height="66" rx="12"/><rect x="320" y="40" width="100" height="66" rx="12"/><rect x="60" y="196" width="100" height="58" rx="12"/><rect x="320" y="196" width="100" height="58" rx="12"/></g><g fontFamily="sans-serif" textAnchor="middle" fill="#f3f6eb" fontSize="12"><text x="110" y="68">☀</text><text x="110" y="90">光伏 PV</text><text x="370" y="68">▥</text><text x="370" y="90">储能 ESS</text><text x="240" y="145" fill="#d4f66b" fontSize="17">EMS</text><text x="110" y="231">电网 GRID</text><text x="370" y="231">负载 LOAD</text></g><g fill="#d4f66b"><circle cx="186" cy="90" r="4"/><circle cx="294" cy="90" r="4"/><circle cx="240" cy="192" r="4"/></g></svg><div className="visualBottom"><span>完整系统 · 共同视图</span><span>概念示意 / 非实时数据</span></div></div></header>
   {tab==='M2'?<section className="m2ProjectContext" aria-label="点检项目与依据"><select aria-label="选择项目" value={id} onChange={e=>{if(!dirty||confirm('放弃未保存修改并切换项目？'))run(()=>load(e.target.value))}}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><span>调试依据：{loadedProject===id&&plan?'M1 R'+plan.revision:'待生成'}</span><strong className={dirty||plan?.stale?'changed':''}>{busy?'正在准备…':dirty?'模型有未保存修改':plan?.stale?'模型已变化':plan?'与当前模型一致':'尚无调试依据'}</strong></section>:<>
   <section className="workspaceIntro" id="project-workspace"><div><small>YOUR PROJECT WORKSPACE</small><h2>{tab==='M1'?'系统工程拓扑':tab==='M2'?'厂家指导式点检':tab==='M3'?'项目交接':tab==='M4'?'现场服务':tab==='Review'?'技术协同记录':'受控 SOP 模板库'}</h2></div><span>配置 <i>→</i> 调试 <i>→</i> 交接 <i>→</i> 服务</span></section>
   <section className="projectBar"><div><strong>{model.project.name}</strong><span>{model.project.structure_code} · 400 V 示例 · R{revision} {dirty?' · 未保存修改':''}</span></div><div className="actions"><select aria-label="选择项目" value={id} onChange={e=>{if(!dirty||confirm('放弃未保存修改并切换项目？'))run(()=>load(e.target.value))}}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><button disabled={busy} onClick={()=>run(async()=>{const m=structuredClone(model);m.project.project_id=newId('LV01');for(const p of m.parameters as {scope:string;owner_id:string}[]){if(p.scope==='PROJECT')p.owner_id=m.project.project_id}m.project.name='LV-01 新建样板';const saved=await api<{model:Model;revision:number}>('/projects',{model:m,expected_revision:0});setProjects(await api('/projects'));await load(saved.model.project.project_id)})}>复制为新项目</button><button className="primary" disabled={busy||!dirty} onClick={()=>run(save)}>保存版本</button></div></section>
   <div className="notice" role="status">{message}</div>
   </>}
   {handoverReturn&&tab!=='M3'&&<div className="notice"><button onClick={()=>{setExternalIssue(null);setTab('M3')}}>返回 M3 交接包</button><span>封存包保持原样；处理后需更新依据、测试报告与交接版本。</span></div>}
   {returnPackage&&tab!=='M2'&&<div className="notice"><button onClick={()=>{setExternalIssue(null);navigate('M2');setTimeout(()=>{const el=document.getElementById('package-'+returnPackage);const details=el?.closest('details');if(details)details.open=true;el?.scrollIntoView({block:'center'})},100)}}>返回 M2 调试</button><span>修改模型后请保存并更新调试依据；相关结果需要重新验证。</span></div>}
   {tab==='M1'&&<M1Start key={id+environment+m1Step+(externalIssue?.id||'')} initialStep={m1Step} focusLabel={externalIssue?.m1Step?externalIssue.label:undefined} focusNode={externalIssue?.m1Step?externalIssue.nodeId:undefined} enterM2={packageId=>{void run(async()=>{const current=await api<Plan[]>(`/projects/${id}/plans`);if(!current[0]||current[0].stale)await api(`/projects/${id}/plans`,{});await refresh(id);setBasisId(packageId);setWorkflowTarget(null);setTab('M2')})}} model={model} change={change} save={async m=>{await saveConnection(m);setMessage('已保存工程草案；未下发设备。')}} revision={revision} dirty={dirty} environment={environment} locating={!!externalIssue&&!externalIssue.m1Step} legacy={<><button onClick={()=>setTab('Templates')}>型号与 SOP 模板库</button>{environment!=='OFFLINE'&&<ConfigurationDelivery key={id} projectId={id} revision={revision} dirty={dirty} environment={environment}/>}<M1 model={model} change={change} selected={selected} select={setSelected} flows={flows} review={()=>setTab('M4')} reviews={reviews} revision={revision} scenario={scenario} setScenario={setScenario} saveConnection={saveConnection} enterInstallation={()=>navigate('M2')} navigationRequest={navigationRequest} externalIssue={externalIssue}/></>}/>}
   {tab==='M2'&&environment!=='OFFLINE'&&<>
    {basisId&&<CommissioningBasis projectId={id} packageId={basisId} environment={environment} revision={revision} dirty={dirty} locate={s=>{setM1Step(s);setExternalIssue(null);setTab('M1')}}/>}
    {dirty?<div className="m2UpdateNotice" role="status"><span>模型有未保存修改。请先回到 M1 保存，再更新调试依据；原记录保留。</span><button onClick={()=>setTab('M1')}>返回 M1 保存</button></div>:plan?.stale&&<div className="m2UpdateNotice" role="status"><span>当前模型为 R{revision}，调试仍依据 R{plan.revision}。更新后形成新的调试依据；原记录保留，不自动沿用验证结论。</span><button disabled={busy} onClick={()=>void generateChecklist()}>更新调试依据</button></div>}
    {checklistError&&<div className="m2UpdateNotice" role="alert"><span>清单准备失败：{checklistError}</span><button disabled={busy||dirty} onClick={()=>void generateChecklist()}>重试</button></div>}
    {loadedProject===id&&plan?<MeterWorkflow basisId={basisId} key={(workflowPlan?.id||plan.id)+environment+basisId+(workflowTarget?.nonce||'')} planId={workflowPlan?.id||plan.id} disabled={dirty||!!workflowPlan?.stale} requested={workflowTarget} openM3={packageId=>{setHandoverId(packageId);setReturnPackage('');setHandoverReturn(false);setTab('M3')}} environment={environment} locate={issue=>{const step=issue.m1Step||(issue.layer==='L3'?4:issue.layer==='L4'?6:issue.layer==='L2'?3:10);setM1Step(step);setExternalIssue({...issue,m1Step:step,id:issue.id+'-'+Date.now()});setReturnPackage('meter-workflow');setTab('M1')}} onSupport={text=>{setSelected(id);setComment(text);setTab('M4')}}/>:<section className="empty card">{dirty?'请先保存 M1 模型。':checklistError?'请重试准备调试依据。':'正在读取已保存的 M1 调试依据…'}</section>}</>}
   {tab==='M3'&&environment!=='OFFLINE'&&<ProjectHandover key={id+environment} projectId={id} mode={environment} dirty={dirty} selectedId={handoverId} selectPackage={setHandoverId} locate={issue=>{setExternalIssue(issue);setReturnPackage('');setHandoverReturn(true);setTab('M1')}} support={text=>{setSelected(id);setComment(text);setReturnPackage('');setHandoverReturn(true);setTab('M4')}} openStep={target=>{setWorkflowTarget(target);setReturnPackage('');setHandoverReturn(true);setTab('M2')}}/>}
   {tab==='M4'&&<section className="configurationDelivery"><small>M4 / FIELD SERVICE</small><h2>现场服务与厂家协同</h2><p>保留现场问题和厂家支持意见。当前协同记录仅保存在演示工作台，尚未接通厂家服务系统，不会自动发送给厂家。</p></section>}
   {(tab==='Review'||tab==='M4')&&<div className="twoCol"><section className="card"><h2>记录技术支持意见</h2><label>评审对象<select value={selected} onChange={e=>setSelected(e.target.value)}>{[id,...model.nodes.map(x=>x.node_id),...model.edges.map(x=>x.edge_id),...templates.map(x=>x.template_id),...(plan?.tasks.map(t=>t.task_id)||[])].map(x=><option key={x}>{x}</option>)}</select></label><label>评审人<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>结论<select value={decision} onChange={e=>setDecision(e.target.value)}>{['COMMENT','UNDER_REVIEW','APPROVED','REJECTED'].map(x=><option key={x}>{x}</option>)}</select></label><label>意见<textarea aria-label="评审意见" value={comment} onChange={e=>setComment(e.target.value)}/></label><button className="primary" disabled={busy||dirty||!comment.trim()} onClick={()=>run(async()=>{await api(`/projects/${id}/reviews`,{target_id:selected,reviewer,comment,decision,revision});setComment('');await refresh(id);setMessage('评审意见已保存；模拟批准不改变正式作业权限。')})}>保存评审</button><p className="subtle">此处仅记录厂家与 EPC 的技术支持意见。模拟确认不代表系统获准投运，也不代替法定检验或合同验收。</p><h3>拓扑版本历史</h3>{history.map(h=><div className="history" key={h.revision}><span>R{h.revision} · {new Date(h.created).toLocaleString()}</span><button onClick={()=>run(async()=>{const old=await api<{model:Model}>(`/projects/${id}?revision=${h.revision}`);change(old.model);setTab('M1');setMessage('历史版本已载入为候选草案；保存会创建新版本。')})}>载入为草案</button></div>)}</section><section className="card"><h2>技术协同时间线</h2>{reviews.length?reviews.map(r=><article className="review" key={r.id}><span className="badge">{r.decision}</span><strong>{r.target_id}</strong><p>{r.comment}</p><small>{r.reviewer} · R{r.revision} · {new Date(r.created).toLocaleString()}</small></article>):<p>暂无评审意见。</p>}</section></div>}
   {tab==='Templates'&&<div className="twoCol"><section className="card"><h2>模板版本</h2><p>原始规则包为 DRAFT。批准仅用于演示版本管理，所有模板始终标识 DEMO ONLY。</p>{templates.map(t=><article className="review" key={t.template_id}><span className="badge">{t.status} · v{t.version}</span><h3>{t.title}</h3><p>{t.scope_type}</p><button onClick={()=>{setEditTemplate({...t});setRuleText(JSON.stringify(t.rule,null,2))}}>编辑 / 评审</button></article>)}</section><section className="card">{editTemplate?<><h2>创建模板新版本</h2><label>标题<input value={editTemplate.title} onChange={e=>setEditTemplate({...editTemplate,title:e.target.value})}/></label><label>指导内容<textarea rows={6} value={editTemplate.instructions} onChange={e=>setEditTemplate({...editTemplate,instructions:e.target.value})}/></label><label>来源文档<input aria-label="模板来源文档" value={editTemplate.source_document_ref||''} onChange={e=>setEditTemplate({...editTemplate,source_document_ref:e.target.value||null})}/></label><label>模拟评审状态<select value={editTemplate.status} onChange={e=>setEditTemplate({...editTemplate,status:e.target.value})}>{['DRAFT','UNDER_REVIEW','APPROVED','REJECTED'].map(x=><option key={x}>{x}</option>)}</select></label><label>评审人<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>适用规则与依赖（JSON）<textarea className="json" aria-label="模板规则" value={ruleText} onChange={e=>setRuleText(e.target.value)}/></label><label>变更原因<input value={reason} onChange={e=>setReason(e.target.value)}/></label><button className="primary" disabled={busy} onClick={()=>run(async()=>{await api('/templates/'+editTemplate.template_id,{...editTemplate,rule:JSON.parse(ruleText),expected_version:editTemplate.version,reviewer,reason});setEditTemplate(null);await refresh(id);setMessage('新模板版本已保存，已有计划保留原模板。')})}>保存新版本</button></>:<p>选择模板查看或修改。</p>}</section></div>}
   <footer>iEMS 工程工作台面向 EPC 与厂家技术支持人员，提供系统设置、调试与 SAT、项目交接和现场服务。不取代 EPC 专业电气设计、施工管理、法定检验或合同验收工具。</footer>
  </fieldset></main>
 </div>
}



