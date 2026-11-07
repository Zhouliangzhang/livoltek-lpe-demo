import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}

test('legacy installation feedback remains visible read-only without becoming new inspection evidence',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-TRACK';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=await (await request.post(`/api/projects/${model.project.project_id}/plans`,{data:{}})).json()
 const upload=await request.post(`/api/plans/${plan.id}/installation/photos?task_id=INSTALL-EARTH&target_id=BESS_01&filename=test.png`,{data:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64')})
 expect(upload.ok()).toBeTruthy()
 const photo=await upload.json()
 expect((await request.post(`/api/plans/${plan.id}/installation`,{data:{task_id:'INSTALL-EARTH',target_id:'BESS_01',status:'COMPLETED',recorder:'历史测试',note:'历史安装记录，非新点检结论',photo_ids:[photo.id]}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 await page.getByText('旧版技术参考与现场记录 · 只读',{exact:true}).click()
 const legacy=page.locator('.m2Legacy').filter({has:page.getByText('旧版技术参考与现场记录 · 只读',{exact:true})})
 await expect(legacy).toContainText('历史安装记录，非新点检结论')
 await expect(legacy.locator('img')).toHaveJSProperty('naturalWidth',1)
 await expect(legacy.locator('input,button,textarea,select')).toHaveCount(0)
 const checklist=await (await request.get(`/api/plans/${plan.id}/checklist`)).json()
 expect(checklist.records).toHaveLength(0)
 await page.reload();await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 await page.getByText('旧版技术参考与现场记录 · 只读',{exact:true}).click()
 await expect(legacy).toContainText('历史安装记录，非新点检结论')
})
