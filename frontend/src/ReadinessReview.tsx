import {useState} from 'react'
import {readinessIssues,type Issue} from './readinessIssues'
import type {Model} from './types'
type Validation={valid:boolean;errors:string[];warnings:string[]}
export function ReadinessReview({model,result,onLocate}:{model:Model;result:Validation|null;onLocate:(issue:Issue)=>void}){
 const [filter,setFilter]=useState('全部')
 if(!result)return <div className="readinessBanner">尚未检查。运行检查后查看 L1–L5 的缺项、冲突和需现场验证事项。</div>
 const issues=readinessIssues(model,result),categories=['缺失信息','设置冲突','待厂家确认'] as const
 const visible=issues.filter(i=>filter==='全部'||i.layer===filter)
 return <><div className="readinessBanner"><strong>{!result.valid||issues.some(i=>i.category==='设置冲突')?'存在数据冲突，需先修正':issues.length?'资料或设置尚待补全':'当前已覆盖的静态检查未发现阻塞项'}</strong><p>系统运行结论：待现场验证。静态资料检查不能确认接线实况、保护动作、通信质量或带载运行结果。</p><small>检查范围：当前 L1–L5 草案 · 规则 L6-READINESS-1 · 数据修改后须重新检查。厂家确认和 EPC 工程职责保持独立。</small></div>
 <div className="issueSummary">{categories.map(c=><span key={c}>{c}<b>{issues.filter(i=>i.category===c).length}</b></span>)}<label>检查层级<select aria-label="检查层级" value={filter} onChange={e=>setFilter(e.target.value)}>{['全部','L1','L2','L3','L4','L5','L6'].map(x=><option key={x}>{x}</option>)}</select></label></div>
 {categories.map(c=><details className="settingsGroup" key={c} open><summary>{c}<span>{visible.filter(i=>i.category===c).length} 项</span></summary><div className="tableScroll"><table className="layerTable"><thead><tr><th>位置 / 对象</th><th>发现的问题</th><th>下一步</th></tr></thead><tbody>{visible.filter(i=>i.category===c).map(i=><tr key={i.id} data-testid={'issue-'+i.id}><td>{i.layer} · {i.object}</td><td>{i.message}</td><td><button onClick={()=>onLocate(i)} aria-label={'定位 '+i.id}>{i.action} →</button></td></tr>)}</tbody></table>{!visible.some(i=>i.category===c)&&<p>当前筛选未发现此类问题，不代表系统已获准投运。</p>}</div></details>)}
 <details className="settingsGroup"><summary>后端规则详情 · {result.errors.length} 错误 / {result.warnings.length} 提示</summary><p>{result.valid?'已执行的数据结构及引用规则通过。':'数据规则存在冲突。'}</p>{[...result.errors,...result.warnings].map((s,i)=><p key={i}>{s}</p>)}</details>
 <div className="readinessBanner"><strong>待现场验证</strong><p>安装接线、保护动作、通信实测及带载运行须由有资质人员依据适用流程完成并记录证据。本检查不替代 EPC 电气设计、法定检验或合同验收。</p></div></>
}
