import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import type {Model} from '../src/types'
import {applyFleetPlan} from '../src/BasicSettings'
import {generateSettings} from '../src/settingsCatalog'

test('fleet changes only selected planned fields, retains actual and vendor pending',()=>{
 const model=structuredClone(fixture) as unknown as Model,ids=model.nodes.filter(n=>n.node_type==='BESS').map(n=>n.node_id)
 const before=JSON.stringify(model)
 const next=applyFleetPlan(model,ids,{charge_power_limit:100})
 expect(JSON.stringify(model)).toBe(before)
 for(const id of ids){
  const row=generateSettings(next).find(r=>r.nodeId===id&&r.definition.key==='charge_power_limit')!
  expect(row.record?.planned).toBe(100);expect(row.record?.actual).toBeNull()
  expect(generateSettings(next).find(r=>r.nodeId===id&&r.definition.key==='discharge_power_limit')?.record?.planned).toBe(125)
 }
 model.device_models.find(d=>d.model_id==='BESS-261')!.master_data_version='new-version'
 expect(()=>applyFleetPlan(model,ids,{charge_power_limit:100})).toThrow(/版本/)
})

test('L5 defaults to three cards; bulk plan saves without hiding manufacturer gaps',async({page,request})=>{
 const model=structuredClone(fixture),id=model.project.project_id+'-BASIC'
 model.project.project_id=id
 model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=id})
 expect((await request.post('/api/projects',{data:{model,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(id)
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await expect(page.locator('.basicCard')).toHaveCount(3)
 await expect(page.locator('.advancedSettings')).not.toHaveAttribute('open')
 await expect(page.getByLabel('EMS_MASTER.ip_address planned',{exact:true})).not.toBeVisible()
 await expect(page.getByLabel('简化 export_limit',{exact:true})).toHaveValue('0')
 await page.getByLabel('统一 charge_power_limit',{exact:true}).fill('100')
 await page.getByRole('button',{name:'应用到 10 台计划值',exact:true}).click()
 await expect(page.getByText(/已更新 10 台储能的指定计划字段/)).toBeVisible()
 await page.getByRole('button',{name:'保存版本',exact:true}).click()
 await expect(page.getByText(/已保存不可变版本/)).toBeVisible()
 const saved=await (await request.get('/api/projects/'+id)).json()
 expect(generateSettings(saved.model).filter(r=>r.definition.key==='charge_power_limit').every(r=>r.record?.planned===100&&r.record.actual===null)).toBeTruthy()
 await expect(page.getByRole('button',{name:/L6 运行条件检查/})).toHaveCount(0)
})
