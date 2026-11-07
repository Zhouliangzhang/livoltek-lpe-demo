import {test,expect} from '@playwright/test'
import fixture from '../../baselines/lv01-mixed-vendors.engineering-model.json' with {type:'json'}
import type {Model} from '../src/types'
import {generateSettings,updateSetting,resetSetting,settingsSummary} from '../src/settingsCatalog'
const sample=()=>structuredClone(fixture) as unknown as Model

test('L1 modes and L3 devices/interfaces generate distinct empty candidate settings',()=>{
 const m=sample(),rows=generateSettings(m)
 expect(rows.some(r=>r.id==='EMS_01.export_limit')).toBe(true)
 expect(rows.some(r=>r.id==='BESS_01.charge_schedule')).toBe(true)
 expect(rows.some(r=>r.id==='BESS_01.ip_address')).toBe(true)
 expect(rows.some(r=>r.id==='BESS_01.baud_rate')).toBe(false)
 expect(rows.every(r=>!r.record)).toBe(true)
 m.project.operation_modes=['OFF_GRID']
 const off=generateSettings(m)
 expect(off.some(r=>r.id==='EMS_01.export_limit')).toBe(false)
 expect(off.some(r=>r.id==='BESS_01.reserve_soc')).toBe(true)
 expect(off.some(r=>r.id==='EMS_01.load_priority')).toBe(true)
})
test('model version change flags saved settings and reconfirmation archives old values',()=>{
 let m=sample(),row=generateSettings(m).find(r=>r.id==='BESS_01.soc_min')!
 m=updateSetting(m,row,'planned',20)
 row=generateSettings(m).find(r=>r.id==='BESS_01.soc_min')!
 m=updateSetting(m,row,'reference_doc','USER-REFERENCE')
 expect(settingsSummary(m).manufacturerPending).toBe(settingsSummary(m).total)
 m.device_models.find(d=>d.model_id===row.modelId)!.master_data_version='CHANGED'
 row=generateSettings(m).find(r=>r.id==='BESS_01.soc_min')!
 expect(row.stale).toBe(true)
 expect(()=>updateSetting(m,row,'planned',30)).toThrow()
 m=resetSetting(m,row)
 expect(generateSettings(m).find(r=>r.id===row.id)?.record?.planned).toBeNull()
 expect(m.nodes.find(n=>n.node_id==='BESS_01')!.attributes!.l5_settings_history).toHaveLength(1)
})
test('mode changes retain inactive recorded settings without applying them',()=>{
 let m=sample(),row=generateSettings(m).find(r=>r.id==='BESS_01.charge_schedule')!
 m=updateSetting(m,row,'planned','TEST-DOCUMENT')
 m.project.operation_modes=['OFF_GRID']
 expect(settingsSummary(m).inactive).toBe(1)
 expect(generateSettings(m).some(r=>r.id===row.id)).toBe(false)
})
