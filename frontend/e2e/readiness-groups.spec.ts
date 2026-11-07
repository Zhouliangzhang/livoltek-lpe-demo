import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import type {Model} from '../src/types'
import {readinessIssues} from '../src/readinessIssues'
import {groupReadinessIssues} from '../src/readinessGroups'

test('grouping preserves every finding, separates model versions, phases and ownership',()=>{
 const m=structuredClone(fixture) as unknown as Model,issues=readinessIssues(m),groups=groupReadinessIssues(m,issues)
 expect(groups.flatMap(g=>g.items).map(i=>i.id).sort()).toEqual(issues.map(i=>i.id).sort())
 const firmware=groups.find(g=>g.items[0].id==='BESS_01-firmware_version')!
 expect(firmware.deviceCount).toBe(10);expect(firmware.owner).toBe('EPC 现场补充')
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-evidence')?.owner).toBe('厂家确认')
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-planned')?.items).toHaveLength(10)
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-actual')?.items).toHaveLength(10)
 const d=m.device_models.find(d=>d.model_id==='BESS-261')!;m.device_models.push({...d,model_id:'BESS-NEW',master_data_version:'NEW'})
 m.device_assets.find(a=>a.asset_id==='ASSET-BESS_10')!.model_id='BESS-NEW'
 expect(groupReadinessIssues(m,readinessIssues(m)).find(g=>g.items[0].id==='BESS_01-firmware_version')?.deviceCount).toBe(9)
})
