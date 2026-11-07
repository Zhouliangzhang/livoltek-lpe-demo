import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('old meter detail evidence is retained read-only; M3 field mode starts empty',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-DETAIL-HISTORY';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=await (await request.post(`/api/projects/${model.project.project_id}/plans`,{data:{}})).json()
 const data=await (await request.get(`/api/plans/${plan.id}/checklist`)).json()
 const item=data.items.find((i:any)=>i.node_ids.includes('METER_PCC')&&i.node_ids.includes('EMS_MASTER')&&i.id.endsWith(':0'))
 await request.post(`/api/plans/${plan.id}/checklist`,{data:{item_id:item.id,status:'PENDING',detail_key:'ports',actual_values:{from_terminal:'HISTORICAL-TERMINAL'},recorder:'历史 EPC',note:'保留记录',photo_ids:[]}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 await page.getByText('历史 M2 点检记录 · 只读',{exact:true}).click()
 const root=page.getByRole('region',{name:'系统逐项点检'})
 await root.locator('.m2Steps button').nth(1).click();await root.locator('.m2Topic').filter({hasText:'C01'}).click();await root.locator('.m2Object').click()
 // The first missing parent item may be settings; explicitly inspect the wiring history.
 await root.locator('.m2ItemTabs button').first().click()
 await expect(root.getByLabel('起点现场设备 / 端子号',{exact:true})).toHaveValue('HISTORICAL-TERMINAL')
 await expect(root.getByLabel('起点现场设备 / 端子号',{exact:true})).toBeDisabled()
 const flow=page.getByRole('region',{name:'M2 自动测试'});await page.getByLabel('选择 iEMS 环境',{exact:true}).selectOption('REAL')
 await expect(flow.locator('.m3Result')).toHaveCount(0)
})
