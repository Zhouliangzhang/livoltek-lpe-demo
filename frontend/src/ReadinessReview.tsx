import type {Model} from './types'
import {projectFramework} from './projectTopology'
import {settingsSummary} from './settingsCatalog'
type Validation={valid:boolean;errors:string[];warnings:string[]}
export function readinessFindings(model:Model){
 const generated=settingsSummary(model)
 const gaps=projectFramework(model).missing
 const assetGaps=model.device_assets.filter(a=>!a.serial_number||!a.installed_location||!a.firmware_version)
 const unverified=model.device_models.filter(m=>m.source_quality!=='VERIFIED')
 const attached=new Set(model.edges.flatMap(e=>[e.from_port_id,e.to_port_id]).map(id=>model.ports.find(p=>p.port_id===id)?.node_id))
 const disconnected=model.nodes.filter(n=>n.device_asset_id&&!attached.has(n.node_id))
 const parameters=model.parameters as {planned:{value:number;unit:string}|null;actual:{value:number;unit:string}|null;reference_doc?:string|null}[]
 const settingsGaps=parameters.filter(p=>!p.planned||!p.actual||!p.reference_doc)
 const differences=parameters.filter(p=>p.planned&&p.actual&&(p.planned.value!==p.actual.value||p.planned.unit!==p.actual.unit))
 return [
  {layer:'L1–L2',name:'项目框架与电气结构',pending:gaps.length>0,detail:gaps.length?`待补充：${gaps.map(g=>g.name).join('、')}`:'模板类型已覆盖；对象数量、归属及工程适用性仍需核实。'},
  {layer:'L3',name:'设备身份与现场资料',pending:assetGaps.length>0||unverified.length>0,detail:`${assetGaps.length} 台设备缺少 SN、位置或固件；${unverified.length} 份型号资料未核验。`},
  {layer:'L4',name:'端口与接口关系',pending:disconnected.length>0||!model.edges.length,detail:`${disconnected.length} 台设备尚无已录入的连接；具体接口兼容性需结合厂家协议核实。`},
  {layer:'L5',name:'系统设置与现场一致性',pending:settingsGaps.length>0||differences.length>0||generated.manufacturerPending>0||generated.stale>0,detail:`${generated.total} 项自动生成参数中，${generated.missing} 项缺少有效设置，${generated.manufacturerPending} 项厂家依据待确认，${generated.stale} 项版本变化。已有参数另有 ${settingsGaps.length} 项缺项、${differences.length} 项计划与实际不一致。`},
 ]
}
export function ReadinessReview({model,result}:{model:Model;result:Validation|null}){
 if(!result)return <div className="readinessBanner">尚未检查。运行检查后查看 L1–L5 的缺项、冲突和需现场验证事项。</div>
 const findings=readinessFindings(model),pending=findings.some(f=>f.pending)||result.warnings.length>0
 return <><div className="readinessBanner"><strong>{!result.valid?'存在数据冲突，需先修正':pending?'资料或设置尚待补全':'当前已覆盖的静态检查未发现阻塞项'}</strong><p>系统运行结论：待现场验证。静态资料检查不能确认接线实况、保护动作、通信质量或带载运行结果。</p></div><div className="tableScroll"><table className="layerTable"><thead><tr><th>检查范围</th><th>状态</th><th>发现 / 下一步</th></tr></thead><tbody><tr><td>数据结构与引用</td><td>{result.valid?'已通过':'需修正'}</td><td>{result.valid?'仅表示已执行的数据规则通过。':result.errors.join('；')}</td></tr>{findings.map(f=><tr key={f.layer}><td>{f.layer} · {f.name}</td><td>{f.pending?'待补充 / 核对':'资料项已覆盖'}</td><td>{f.detail}</td></tr>)}<tr><td>安装调试与运行效果</td><td>待现场验证</td><td>需由有资质人员按适用作业流程完成现场检查、测试及证据记录。</td></tr></tbody></table></div></>
}
