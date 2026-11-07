import {useState} from 'react'
import {readinessIssues,type Issue} from './readinessIssues'
import {groupReadinessIssues,type IssueOwner} from './readinessGroups'
import type {Model} from './types'
type Validation={valid:boolean;errors:string[];warnings:string[]}
export function ReadinessReview({model,result,onLocate}:{model:Model;result:Validation|null;onLocate:(issue:Issue)=>void}){
 const [filter,setFilter]=useState('全部'),[ownerFilter,setOwnerFilter]=useState('全部')
 if(!result)return <div className="readinessBanner">尚未检查。运行检查后查看 L1–L5 的缺项、冲突和需现场验证事项。</div>
 const issues=readinessIssues(model,result),categories=['缺失信息','设置冲突','待厂家确认'] as const
 const visible=issues.filter(i=>filter==='全部'||i.layer===filter),groups=groupReadinessIssues(model,visible),allGroups=groupReadinessIssues(model,issues)
 const owners:IssueOwner[]=['EPC 现场补充','厂家确认']
 return <><div className="readinessBanner"><strong>{!result.valid||issues.some(i=>i.category==='设置冲突')?'存在数据冲突，需先修正':issues.length?'资料或设置尚待补全':'当前已覆盖的静态检查未发现阻塞项'}</strong><p>系统运行结论：待现场验证。静态资料检查不能确认接线实况、保护动作、通信质量或带载运行结果。</p><small>检查范围：当前 L1–L5 草案 · 规则 L6-READINESS-1 · 数据修改后须重新检查。厂家确认和 EPC 工程职责保持独立。</small></div>
 <p className="muted">原始检查项统计（合并展示不减少检查范围）</p><div className="issueSummary">{categories.map(c=><span key={c}>{c}<b>{issues.filter(i=>i.category===c).length}</b></span>)}<label>检查层级<select aria-label="检查层级" value={filter} onChange={e=>setFilter(e.target.value)}>{['全部','L1','L2','L3','L4','L5','L6'].map(x=><option key={x}>{x}</option>)}</select></label></div>
 <div className="reviewOverview"><strong>{allGroups.length} 条合并问题</strong><span>来自 {issues.length} 个原始检查项 · 同型号同版本的相同缺项合并；冲突不合并</span></div>
 <div className="ownerSummary">{owners.map(owner=><div key={owner}><small>{owner}</small><strong>{allGroups.filter(g=>g.owner===owner).length}<em>条合并问题</em></strong><p>{owner==='EPC 现场补充'?'现场身份、安装记录、计划与实际设置、工程资料及冲突核对':'型号适用性、参数依据、通信点表与接口兼容确认'}</p></div>)}</div>
 <p className="muted">责任分类用于安排下一步工作，不转移 EPC 设计与验收责任。EPC 可补充厂家资料引用，填写引用不等于厂家已确认。</p>
 <label>处理方<select aria-label="处理方" value={ownerFilter} onChange={e=>setOwnerFilter(e.target.value)}>{['全部',...owners].map(x=><option key={x}>{x}</option>)}</select></label>
 {owners.filter(owner=>ownerFilter==='全部'||ownerFilter===owner).map(owner=><section className="ownerIssues" key={owner} aria-label={owner+'问题'}><h3>{owner}<span>{groups.filter(g=>g.owner===owner).length} 条</span></h3>{groups.filter(g=>g.owner===owner).map(g=>{
 const first=g.items[0]
 return <article className="mergedIssue" key={g.id} data-testid={'issue-'+first.id}><div className="mergedIssueHeading"><div><small>{first.layer} · {first.category}</small><h4>{g.title}</h4><p>{g.modelLabel}</p></div><b>{g.deviceCount>0?g.deviceCount+' 台设备':'项目级'}{g.items.length>g.deviceCount?' · '+g.items.length+' 项':''}</b></div><p>{first.message}</p><div className="issueActions"><button onClick={()=>onLocate(first)} aria-label={'定位 '+first.id}>{g.items.length>1?'定位首台处理':first.action} →</button>{g.items.length>1&&<details><summary>展开 {g.items.length} 个定位入口</summary><div className="issueDeviceLinks">{g.items.slice(1).map(i=><button key={i.id} data-testid={'issue-'+i.id} aria-label={'定位 '+i.id} onClick={()=>onLocate(i)}>{model.nodes.find(n=>n.node_id===i.nodeId)?.name||i.object}<small>{i.rowId||i.nodeId}</small> →</button>)}</div></details>}</div></article>
 })}{!groups.some(g=>g.owner===owner)&&<p>当前筛选无此类问题，不代表系统已获准投运。</p>}</section>)}
 <details className="settingsGroup"><summary>后端规则详情 · {result.errors.length} 错误 / {result.warnings.length} 提示</summary><p>{result.valid?'已执行的数据结构及引用规则通过。':'数据规则存在冲突。'}</p>{[...result.errors,...result.warnings].map((s,i)=><p key={i}>{s}</p>)}</details>
 <div className="readinessBanner"><strong>待现场验证</strong><p>安装接线、保护动作、通信实测及带载运行须由有资质人员依据适用流程完成并记录证据。本检查不替代 EPC 电气设计、法定检验或合同验收。</p></div></>
}
