import {test,expect} from '@playwright/test'
import {busIssues,blankBus,step06Model,templateConflicts} from '../src/communicationSetupModel'
import {communicationBuses} from '../src/communication'
import type {Model} from '../src/types'
const model=()=>({project:{network_drafts:[]},nodes:[{node_id:'EMS',node_type:'EMS',device_asset_id:'A'},{node_id:'PV',node_type:'PV',device_asset_id:'B'}],device_assets:[{asset_id:'A',model_id:'M'},{asset_id:'B',model_id:'M'}],device_models:[{model_id:'M',manufacturer:'LIVOLTEK',master_data_version:'V1',communication_templates:[{id:'T',version:'1',domain:'RS485',master_data_version:'V1',reference_doc:'TEST ONLY',status:'DRAFT',values:{baud_rate:9600}}]}],ports:[{port_id:'EMS.RS',node_id:'EMS',domain:'RS485'},{port_id:'PV.RS',node_id:'PV',domain:'RS485'}],edges:[{edge_id:'E',edge_type:'COMMUNICATION',from_port_id:'EMS.RS',to_port_id:'PV.RS'}]} as unknown as Model)
test('model defaults retain pending evidence and bus conflicts normalize addresses',()=>{
 const m=model(),b=communicationBuses(m)[0],c=blankBus(m,b);expect(c.shared.baud_rate).toBe('9600');expect(c.status).toBe('PENDING');expect(c.devices['PV.RS'].address).toBeUndefined();c.devices={'EMS.RS':{address:'01'},'PV.RS':{address:'1'}};expect(busIssues(c)[0].message).toContain('重复');c.devices['PV.RS'].address='2';expect(busIssues(c)).toEqual([]);
})
test('wrong model version does not autofill; conflicting templates are visible',()=>{
 const m=model(),b=communicationBuses(m)[0];m.device_models[0].master_data_version='V2';expect(blankBus(m,b).shared).toEqual({});m.device_models[0].master_data_version='V1';const ts=m.device_models[0].communication_templates as any[];ts.push({...ts[0],id:'OTHER',values:{baud_rate:19200}});expect(blankBus(m,b).shared.baud_rate).toBeUndefined();expect(templateConflicts(m,b)[0]).toContain('9600 / 19200');
})
test('step06 overrides are isolated by environment',()=>{
 const m=model();m.project.network_drafts=[{id:'D',base_edge_id:'E',environment:'SIMULATION',edge_type:'COMMUNICATION',from_port_id:'PV.RS',to_port_id:'EMS.RS'}];expect(step06Model(m,'REAL').edges[0].from_port_id).toBe('EMS.RS');expect(step06Model(m,'SIMULATION').edges[0].from_port_id).toBe('PV.RS');
})
