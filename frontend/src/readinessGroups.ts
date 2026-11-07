import type {Model} from './types'
import type {Issue} from './readinessIssues'
export type IssueOwner='EPC 现场补充'|'厂家确认'
export type IssueGroup={id:string;owner:IssueOwner;title:string;modelLabel:string;items:Issue[];deviceCount:number}
export function groupReadinessIssues(model:Model,issues:Issue[]):IssueGroup[]{
 const grouped=new Map<string,IssueGroup>()
 for(const issue of issues){
  const owner:IssueOwner=issue.category==='待厂家确认'?'厂家确认':'EPC 现场补充'
  const node=model.nodes.find(n=>n.node_id===issue.nodeId),asset=model.device_assets.find(a=>a.asset_id===node?.device_asset_id),device=model.device_models.find(d=>d.model_id===asset?.model_id)
  // Only explicit identical finding types can merge, and never across model versions or conflicts.
  const key=issue.mergeKey&&device&&issue.category!=='设置冲突'?JSON.stringify([owner,device.manufacturer,device.model_id,device.master_data_version,issue.layer,issue.category,issue.mergeKey,issue.message]):issue.id
  const prior=grouped.get(key)
  if(prior)prior.items.push(issue)
  else grouped.set(key,{id:issue.id,owner,title:issue.subject||issue.object,modelLabel:device?device.model_name+' · '+device.master_data_version:issue.object,items:[issue],deviceCount:0})
 }
 return [...grouped.values()].map(g=>({...g,deviceCount:new Set(g.items.map(i=>i.nodeId).filter(Boolean)).size})).sort((a,b)=>b.deviceCount-a.deviceCount)
}
