export type Kind = 'ELECTRICAL'|'COMMUNICATION'|'CONTROL'
export interface Node {node_id:string; logical_id:string; name:string; node_type:string; icon_key?:string; device_asset_id:string|null; parent_node_id:string|null; zone_id:string|null; attributes?:Record<string,unknown>; relationship_reason?:string|null}
export interface Port {port_id:string;node_id:string;name:string;domain:string;role:string;attributes?:Record<string,unknown>}
export interface Edge {edge_id:string;edge_type:Kind;from_port_id:string;to_port_id:string;review_status:string;design_ref?:string|null;attributes?:Record<string,unknown>}
export interface Asset {installed_location?:string|null;firmware_version?:string|null;asset_id:string;model_id:string;serial_number:string|null;sn_status:string;lifecycle_status:string;modeling_level?:string;equipment_origin?:string;responsibility_owner?:string|null;authorization?:Record<string,unknown>}
export interface DeviceModel {model_id:string;manufacturer:string;model_name:string;master_data_version:string;[key:string]:unknown}
export interface Model {schema_version:string;project:{project_id:string;name:string;structure_code:string;[key:string]:unknown};baseline:{baseline_id:string;version:string;status:string;[key:string]:unknown};nodes:Node[];ports:Port[];edges:Edge[];device_assets:Asset[];device_models:DeviceModel[];view_layout:{editor:string;positions:Record<string,{x:number;y:number}>;layer_visibility:Record<Kind,boolean>};[key:string]:unknown}
export interface Flow {available:boolean;animate:boolean;reverse:boolean;value:number|null;quality:string;timestamp:number}
export interface Task {task_id:string;title:string;instructions:string;scope_type:string;task_owner:string;readiness:string;work_package:string;risk:string;template_id:string;template_version:number;missing_inputs:string[];depends_on:string[];evidence_requirements:string[]}
export interface Plan {id:string;revision:number;stale?:boolean;tasks:Task[];created:string}
export interface Template {rule:Record<string,unknown>;template_id:string;version:number;title:string;instructions:string;status:string;source_document_ref:string|null;scope_type:string}
export interface Review {id:string;target_id:string;reviewer:string;comment:string;decision:string;revision:number;created:string}
export async function api<T>(path:string, data?:unknown):Promise<T> {
 const r=await fetch('/api'+path,data===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
 const body=await r.json()
 if(!r.ok) throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail))
 return body as T
}

