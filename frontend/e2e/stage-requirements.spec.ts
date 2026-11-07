import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import type {Model} from '../src/types'
import {stageRequirements,requirementsBefore} from '../src/stageRequirements'

test('mandatory modelling data is separate from unavailable site and vendor evidence',()=>{
 const m=structuredClone(fixture) as unknown as Model
 expect(requirementsBefore(m,'M2')).toHaveLength(0)
 m.project.country_code=''
 expect(requirementsBefore(m,'L3').some(i=>i.label==='L1 country_code')).toBe(true)
 const n=m.nodes.find(n=>n.node_id==='BESS_01')!;n.name=''
 expect(stageRequirements(m,'L3').some(i=>i.nodeId==='BESS_01')).toBe(true)
 expect(stageRequirements(m,'L3').some(i=>i.id.endsWith('firmware_version'))).toBe(false)
})
test('forward prompts locate missing fields; no L6 or shortcut bypass',async({page,request})=>{
 const m=structuredClone(fixture);m.project.project_id+='-STEPS';m.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=m.project.project_id})
 expect((await request.post('/api/projects',{data:{model:m,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 await expect(page.getByRole('button',{name:/L6 运行条件检查/})).toHaveCount(0)
 await page.getByText('L1 项目定义 · 查看 / 修改',{exact:true}).click()
 await page.getByLabel('L1 country_code',{exact:true}).fill('')
 await page.getByRole('button',{name:/L3 型号与资产/}).click()
 await expect(page.getByRole('region',{name:'L2 作业区',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'补充 project-country_code',exact:true}).click()
 await expect(page.getByLabel('L1 country_code',{exact:true})).toBeFocused()
 await page.getByLabel('L1 country_code',{exact:true}).fill('ZA')
 await page.getByRole('button',{name:'继续下一环节',exact:true}).click()
 await expect(page.getByRole('region',{name:'L3 作业区',exact:true})).toBeVisible()
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await page.getByLabel('简化 control_strategy',{exact:true}).fill('')
 await page.getByRole('button',{name:'02 引导式安装',exact:true}).click()
 await expect(page.getByRole('region',{name:'下一环节必填提示',exact:true})).toContainText('缺少计划设置')
 await page.getByRole('button',{name:'补充 EMS_MASTER.control_strategy-planned',exact:true}).click()
 await expect(page.getByLabel('EMS_MASTER.control_strategy planned',{exact:true})).toBeFocused()
 await page.getByLabel('EMS_MASTER.control_strategy planned',{exact:true}).fill('自发自用；测试计划')
 await page.getByRole('button',{name:'继续下一环节',exact:true}).click()
 await expect(page.getByRole('heading',{name:'安装检查工作包',exact:true})).toBeVisible()
})


test('L4 disconnected device prompt opens its device-first connection editor',async({page,request})=>{
 const m=structuredClone(fixture);m.project.project_id+='-DISCONNECTED';m.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=m.project.project_id})
 const original=m.nodes.find(n=>n.node_id==='BESS_10')!,asset=m.device_assets.find(a=>a.asset_id===original.device_asset_id)!
 m.nodes.push({...structuredClone(original),node_id:'BESS_11',logical_id:'BESS_11',name:'Test disconnected BESS',device_asset_id:'ASSET-BESS_11'})
 m.device_assets.push({...structuredClone(asset),asset_id:'ASSET-BESS_11'})
 const port=m.ports.find(p=>p.node_id==='BESS_10'&&p.domain==='ETHERNET')!
 m.ports.push({...structuredClone(port),port_id:'BESS_11.LAN',node_id:'BESS_11'})
 expect((await request.post('/api/projects',{data:{model:m,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await page.getByRole('button',{name:'补充 BESS_11-connection',exact:true}).click()
 await expect(page.getByRole('region',{name:'L4 作业区',exact:true})).toBeVisible()
 await expect(page.getByLabel('起点设备',{exact:true})).toHaveValue('BESS_11')
 await expect(page.getByLabel('起点端口',{exact:true})).toHaveValue('BESS_11.LAN')
})
