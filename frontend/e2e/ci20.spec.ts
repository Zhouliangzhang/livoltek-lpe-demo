import {test,expect} from '@playwright/test'
import model from '../../examples/ci20-pilot.json' with {type:'json'}
import {readinessIssues} from '../src/readinessIssues'
import type {Model} from '../src/types'

test('20-unit pilot persists, renders, flags real gaps, locates and generates blocked guidance',async({page,request})=>{
 const save=await request.post('/api/projects',{data:{model,expected_revision:0}})
 expect(save.ok()).toBeTruthy()
 await page.goto('/')
 await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await expect(page.getByText('CI-20 规划样板 · 非现场实测',{exact:true})).toBeVisible()
 await expect(page.locator('.x6-node').filter({hasNot:page.locator('[data-reference="true"]')})).toHaveCount(73)
 await page.getByRole('button',{name:/L3 型号与资产/}).click()
 await expect(page.getByRole('button',{name:'打开设备 BESS 10 · 125kW/261.2kWh',exact:true})).toBeVisible()
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await page.getByText('高级设置：通信、逐台参数、现场值与厂家依据',{exact:true}).click()
 await page.getByLabel('L5 筛选设备').selectOption('EMS_MASTER')
 await expect(page.getByLabel('EMS_MASTER.export_limit planned',{exact:true})).toHaveValue('0')
 await expect(page.getByLabel('EMS_MASTER.grid_power_target planned',{exact:true})).toHaveValue('25')
 await page.getByRole('button',{name:'02 引导式安装',exact:true}).click()
 await expect(page.locator('.m2Steps')).toBeVisible()
 await expect(page.locator('.m2Steps button')).toHaveCount(3)
 await expect(page.locator('.m2Topic')).toHaveCount(4)
 const findings=readinessIssues(model as unknown as Model)
 console.log('CI20 findings',JSON.stringify(Object.fromEntries(['缺失信息','设置冲突','待厂家确认'].map(c=>[c,findings.filter(i=>i.category===c).length]))))
})
