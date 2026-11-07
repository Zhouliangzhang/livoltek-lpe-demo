import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import {groupChecks,type CheckItem} from '../src/checklistGroups'
import type {Model} from '../src/types'

test('grouping preserves item IDs and separates model versions, methods and port domains',()=>{
 const base={stage:'ELECTRICAL',title:'接地',method:'核对',expected:'符合依据',manufacturer_pending:'待确认',source_status:'DRAFT',template_version:'V1',layer:'L3'}
 const items=['PV_01','PV_02'].map(id=>({...base,id:id+':earth',target_id:id,name:id,detail:id,node_ids:[id]})) as CheckItem[]
 expect(groupChecks(items,fixture as unknown as Model)).toHaveLength(1)
 const changed=structuredClone(fixture) as unknown as Model,asset=changed.device_assets.find(a=>a.asset_id===changed.nodes.find(n=>n.node_id==='PV_02')?.device_asset_id)!,model=changed.device_models.find(d=>d.model_id===asset.model_id)!
 changed.device_models.push({...model,model_id:model.model_id+'-new',master_data_version:'NEW'});asset.model_id+='-new'
 expect(groupChecks(items,changed)).toHaveLength(2)
 expect(groupChecks([items[0],{...items[1],method:'不同检查方法'}],fixture as unknown as Model)).toHaveLength(2)
 expect(groupChecks(items,fixture as unknown as Model).flatMap(g=>g.items.map(i=>i.id))).toEqual(items.map(i=>i.id))
})
