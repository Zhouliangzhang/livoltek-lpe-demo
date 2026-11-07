import {test,expect} from '@playwright/test'
import {projectFramework,completionEvidence} from '../src/projectTopology'
import type {Model} from '../src/types'

const empty=():Model=>({schema_version:'1.0.0',project:{project_id:'EMPTY',name:'Project only',structure_code:'LV-01',voltage_level:'LV',country_code:'ZA',epc_org_id:'EPC',energy_features:['PV','ESS','GRID'],operation_modes:['GRID_CONNECTED']},baseline:{baseline_id:'EMPTY-R1',version:'1',status:'DRAFT'},nodes:[],ports:[],edges:[],device_assets:[],device_models:[],parameters:[],view_layout:{editor:'x6',positions:{},layer_visibility:{ELECTRICAL:true,COMMUNICATION:true,CONTROL:true}}})
test('L1 alone produces a non-mutating initial framework without physical wiring',()=>{
 const m=empty(),before=JSON.stringify(m),f=projectFramework(m)
 expect(f.missing.map(s=>s.type)).toEqual(expect.arrayContaining(['PCC','TRANSFORMER_ZONE','TRANSFORMER','LV_BUS','PV_INVERTER','BESS','EMS']))
 expect(JSON.stringify(m)).toBe(before)
 expect(m.edges).toEqual([])
})
test('L2 replaces only its placeholder and L1 energy changes retain recorded equipment',()=>{
 const m=empty();m.nodes.push({node_id:'BUS',logical_id:'BUS',name:'LV Bus',node_type:'LV_BUS',parent_node_id:null,zone_id:null,device_asset_id:null})
 expect(projectFramework(m).missing.some(s=>s.type==='LV_BUS')).toBe(false)
 expect(projectFramework(m).missing.some(s=>s.type==='BESS')).toBe(true)
 m.project.energy_features=['DIESEL'];m.project.operation_modes=['OFF_GRID']
 const f=projectFramework(m)
 expect(f.slots.some(s=>s.type==='PV_INVERTER'||s.type==='PCC')).toBe(false)
 expect(f.slots.some(s=>s.type==='GENERATOR')).toBe(true)
 expect(f.positions.BUS).toBeDefined()
})
test('LV-02 preserves unfilled zone requirements without inventing interties',()=>{
 const m=empty();m.project.structure_code='LV-02'
 expect(projectFramework(m).missing.filter(s=>s.type==='TRANSFORMER_ZONE')).toHaveLength(2)
 expect(m.edges).toEqual([])
 expect(completionEvidence(m,[],1).some(row=>row[0]==='L6')).toBe(false)
})
