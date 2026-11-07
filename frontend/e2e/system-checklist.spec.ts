import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('historical M2 checklist evidence remains read-only after M3 migration',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-HISTORY';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=await (await request.post(`/api/projects/${model.project.project_id}/plans`,{data:{}})).json()
 const data=await (await request.get(`/api/plans/${plan.id}/checklist`)).json()
 const item=data.items.find((i:any)=>i.title==='光伏限功率策略与反馈')
 await request.post(`/api/plans/${plan.id}/checklist`,{data:{item_id:item.id,status:'FAIL',recorder:'历史 EPC',note:'历史异常仍保留',photo_ids:[]}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'M3 调试与验证',exact:true}).click()
 await page.getByText('历史 M2 点检记录 · 只读',{exact:true}).click()
 const root=page.getByRole('region',{name:'系统逐项点检'})
 await root.getByRole('button',{name:/^异常处理/}).click()
 await expect(root).toContainText('历史异常仍保留')
 await root.getByRole('button',{name:'查看对象与补充反馈 →',exact:true}).click()
 await expect(root.getByRole('button',{name:'保存点检记录',exact:true})).toBeDisabled()
})
