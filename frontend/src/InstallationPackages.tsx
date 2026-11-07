import {CommunicationGuide} from './CommunicationGuide'
import {InstallationTracking} from './InstallationTracking'
import type {Model,Task} from './types'
import type {Issue} from './readinessIssues'
export const installationStages=[['WP01','现场与系统边界'],['WP03G','保护接地'],['WP03P','电气接线'],['WP04','接口核对'],['WP05','通信接线'],['WP06','上电前检查'],['WP07','上电前资料确认']]
export function orderedTasks(tasks:Task[]){
 const remaining=[...tasks],ordered:Task[]=[]
 while(remaining.length){const ready=remaining.filter(t=>!t.depends_on.some(id=>remaining.some(x=>x.task_id===id)))
  if(!ready.length)return [...ordered,...remaining] // Preserve all tasks; backend rejects dependency cycles.
  ready.sort((a,b)=>{const rank=(t:Task)=>{const n=installationStages.findIndex(s=>s[0]===t.work_package);return n<0?99:n};return rank(a)-rank(b)||a.task_id.localeCompare(b.task_id)})
  const next=ready[0];ordered.push(next);remaining.splice(remaining.indexOf(next),1)
 }
 return ordered
}
export const evidenceLabels:Record<string,string>={installation_record:'现场安装记录（逐台 / 逐回路）',photo:'现场照片引用',installation_clearance_review:'安装空间核对记录',communication_map:'通信映射资料',test_record:'通信测试记录',approved_design_reference:'已批准设计引用',signed_checklist:'签署的检查记录',vendor_document:'厂家文件编号 / 版本',interface_map:'接口点表与核对记录',design_reference:'EPC 批准设计引用',boundary_observation:'现场边界核对记录',manual_revision:'厂家手册版本',nameplate_photo:'铭牌照片引用',installation_space_check:'安装空间核对记录'}
export type MissingAction={owner:'EPC 补充'|'厂家提供';text:string;action:'evidence'|'template'|'interface'|'parameter'|'review';field?:string}
export function missingActions(t:Task):MissingAction[]{
 return t.missing_inputs.flatMap((m):MissingAction[]=>{
  if(m.startsWith('vendor installation: '))return [{owner:'厂家提供',text:'待厂家确认：'+m.slice(21)+'。',action:'template'}]
  if(m.startsWith('epc installation: '))return [{owner:'EPC 补充',text:'待现场补充：'+m.slice(18)+'。',action:'evidence',field:'installation_record'}]
  if(m==='approved EPC boundary documentation')return [{owner:'EPC 补充',text:'已批准的系统边界设计，以及现场连接点、额定参数核对记录。',action:'evidence',field:'design_reference'}]
  if(m==='verified interface mapping and vendor documentation')return [{owner:'厂家提供',text:'对应设备的通信协议、接口点表和适用版本。',action:'interface'},{owner:'EPC 补充',text:'现场接口映射、接线及信号核对记录。',action:'evidence',field:'interface_map'}]
  if(m==='approved manufacturer / EPC source document')return [{owner:'厂家提供',text:'适用于本型号的安装手册或技术指导文件，注明版本及适用范围。',action:'template'},{owner:'EPC 补充',text:'与本工作包相关的批准设计及现场核对资料。',action:'evidence'}]
  if(m==='template approval')return [{owner:'厂家提供',text:'本指导模板的受控版本与评审确认。',action:'template'}]
  if(m.startsWith('approved parameter / source: '))return [{owner:'EPC 补充',text:(m.endsWith('cable_spec')?'电缆规格':'工程参数')+'的已批准数值及工程文件依据；填写引用不等于批准。',action:'parameter',field:m.split(': ')[1]}]
  if(m.startsWith('missing dependency: '))return [{owner:'EPC 补充',text:'前置工作包尚未生成，需要核对模板适用条件并重新生成计划。',action:'review'}]
  return [{owner:'EPC 补充',text:'此项资料要求需进一步核对，请查看技术协同中的原始要求。',action:'review'}]
 })
}
export function interfaceIssue(model:Model,t:Task):Issue|undefined{
 const assetId=t.task_id.startsWith('INTERFACE-')?t.task_id.slice(10):model.nodes.find(n=>n.node_type==='METER')?.device_asset_id
 const binding=(model.interface_bindings as {binding_id:string;asset_id:string}[]).find(b=>b.asset_id===assetId)
 if(!binding)return undefined
 return {id:'m2-'+t.task_id,layer:'L5',category:'待厂家确认',object:t.title,message:'请补充接口点表与来源依据，记录仍需厂家核验。',action:'补充资料',nodeId:model.nodes.find(n=>n.device_asset_id===assetId)?.node_id,rowId:'interface-'+binding.binding_id,label:binding.binding_id+' point_ref'}
}
export function InstallationPackages({model,tasks,onRecord,onAction,locate}:{model:Model;tasks:Task[];locate:(issue:Issue)=>void;onRecord:(task:Task)=>void;onAction:(task:Task,a:MissingAction)=>void}){
 tasks=tasks.filter(t=>!['RULE-BESS-PREP','INSTALL-POSITION'].includes(t.task_id))
 const ordered=orderedTasks(tasks)
 return <><CommunicationGuide model={model} locate={locate}/><details className="otherGuidance" open><summary>其它技术参考与现场记录</summary><section className="installationFlow" aria-label="按安装顺序的工作包"><div className="installIntro"><h2>相关技术参考</h2><p>通信接线技术指引见上方；以下保留边界、接地与上电前技术参考，不代替 EPC 施工管理。</p><small>现场作业由 EPC 按批准设计组织。以下安装步骤为草案；厂家具体要求待确认，记录齐备不等于获准上电。</small></div><div className="installSteps">{installationStages.map(([id,name],i)=><div key={id}><b>0{i+1}</b><span>{name}<small>{tasks.filter(t=>t.work_package===id).length} 个工作包</small></span></div>)}</div>
 {ordered.map((t,i)=>{const stage=installationStages.find(s=>s[0]===t.work_package),assetId=t.task_id.startsWith('INTERFACE-')?t.task_id.slice(10):undefined,node=model.nodes.find(n=>n.device_asset_id===assetId),title=node?'第三方接口资料核对 · '+node.name:t.title
 return <article className="task card installationTask" key={t.task_id} id={'package-'+t.task_id} data-task-id={t.task_id} data-readiness={t.readiness}><header><span className="installNumber">{String(i+1).padStart(2,'0')}</span><div><small>{stage?.[1]||'其他工作包'} · 模板 v{t.template_version}</small><h3>{title}</h3></div><span className="badge amber">{t.missing_inputs.length?'待补资料':t.readiness==='BLOCKED'?'需专项确认':'仅供模拟核对'}</span></header><p>{t.instructions}</p>{!!t.installation_steps?.length&&<div className="installationSteps"><h4>现场作业内容 · 待确认流程</h4><ol>{t.installation_steps.map((step,j)=><li key={j}>{step}</li>)}</ol></div>}<div className="installDependency">前置工作：{t.depends_on.length?t.depends_on.map(id=>tasks.find(x=>x.task_id===id)?.title||'前置工作包尚未生成').join('；'):'可先开展资料准备'}<span>风险：{({LOW:'低',MEDIUM:'中',HIGH:'高',SAFETY_CRITICAL:'安全关键'} as Record<string,string>)[t.risk]||'待确认'}</span></div>
 <InstallationTracking taskId={t.task_id}/><div className="missingColumns">{(['EPC 补充','厂家提供'] as const).map(owner=><section key={owner}><h4>{owner}</h4>{missingActions(t).filter(a=>a.owner===owner).map((a,j)=><div className="missingItem" key={j}><p>{a.text}</p><button onClick={()=>onAction(t,a)} aria-label={t.task_id+' '+owner+' '+j}>{a.action==='template'?'查看模板与依据':a.action==='interface'?'定位接口资料':a.action==='parameter'?'定位工程依据':a.action==='review'?'进入技术协同':'补充记录'} →</button></div>)}{!missingActions(t).some(a=>a.owner===owner)&&<p className="muted">当前模板未列出此方缺项，不代表现场工作已完成。</p>}</section>)}</div><footer><small>资料引用与模拟记录不自动构成批准。</small><button onClick={()=>onRecord(t)}>记录模拟结果</button></footer></article>})}</section></details></>
}
