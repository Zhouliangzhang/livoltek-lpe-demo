import type {Model,Edge,Node,Port,DeviceModel} from './types'
import {effectiveElectricalEdges} from './singleLineData'
export type FrozenTopology={id:string;environment:string;source_revision:number;domain_id:string;scope_type:string;created?:string;content_hash:string;snapshot?:{project:Record<string,unknown>;structure:Record<string,Node>;ports:Record<string,Port>;connections:Record<string,Edge>;models:Record<string,DeviceModel>;versions?:{schema_version?:string}}}
export function currentTopology(model:Model,environment:string):Model{
 const drafts=((model.project.network_drafts||[]) as (Edge&{id:string;base_edge_id:string;environment:string})[]).filter(d=>d.environment===environment)
 const network=model.edges.filter(e=>e.edge_type!=='ELECTRICAL').map(e=>{const d=drafts.find(d=>d.base_edge_id===e.edge_id);return d?{...e,from_port_id:d.from_port_id,to_port_id:d.to_port_id}:e})
 return {...model,edges:[...effectiveElectricalEdges(model,environment),...network,...drafts.filter(d=>!d.base_edge_id).map(d=>({edge_id:d.id,edge_type:d.edge_type,from_port_id:d.from_port_id,to_port_id:d.to_port_id,review_status:'DRAFT'}))]}
}
export function frozenTopology(record:FrozenTopology):Model{
 const s=record.snapshot;if(!s)throw new Error('冻结快照尚未载入')
 // Never supplement frozen content with current draft nodes, ports or connections.
 return {schema_version:s.versions?.schema_version||'1.0.0',project:{...s.project,project_id:String(s.project.project_id),name:String(s.project.name),structure_code:'冻结范围',system_boundary:s.project.boundary},baseline:{baseline_id:record.id,version:String(record.source_revision),status:'FROZEN_DRAFT'},nodes:Object.values(s.structure),ports:Object.values(s.ports),edges:Object.values(s.connections),device_assets:[],device_models:Object.values(s.models),view_layout:{editor:'READ_ONLY',positions:{},layer_visibility:{ELECTRICAL:true,COMMUNICATION:true,CONTROL:true}}}
}
