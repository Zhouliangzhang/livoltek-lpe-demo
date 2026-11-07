import {test,expect} from '@playwright/test'
import baseline from '../../baselines/lv01-mixed-vendors.engineering-model.json' with {type:'json'}
import type {Model} from '../src/types'
import {readinessIssues} from '../src/readinessIssues'
import {generateSettings,updateSetting} from '../src/settingsCatalog'

test('readiness separates gaps, mismatches, manufacturer evidence and authoritative conflicts',()=>{
 let m=structuredClone(baseline) as Model
 m.project.operation_modes=[]
 expect(readinessIssues(m).some(i=>i.layer==='L1'&&i.category==='缺失信息')).toBeTruthy()
 let row=generateSettings(m).find(r=>r.definition.key==='soc_min')!
 m=updateSetting(m,row,'planned',20);row=generateSettings(m).find(r=>r.id===row.id)!
 m=updateSetting(m,row,'actual',30)
 const issues=readinessIssues(m,{valid:false,errors:[`L5 ${row.id}.actual: invalid number value`],warnings:[]})
 expect(issues.find(i=>i.id===row.id+'-difference')?.label).toBe(row.id+' actual')
 expect(issues.find(i=>i.id==='rule-0')?.layer).toBe('L5')
 expect(issues.find(i=>i.id===row.id+'-evidence')?.category).toBe('待厂家确认')
 expect(new Set(issues.map(i=>i.id)).size).toBe(issues.length)
 expect(readinessIssues(m,{valid:false,errors:['project/country_code: invalid code'],warnings:[]}).find(i=>i.id==='rule-0')?.label).toBe('L1 country_code')
})
