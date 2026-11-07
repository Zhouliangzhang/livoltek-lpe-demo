import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('M1 L5 goes to M2 automatic testing without silently claiming configuration effective',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-M1-M2';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await page.getByRole('button',{name:'完成建模，进入调试与 SAT',exact:true}).click()
 await expect(page.getByRole('region',{name:'M2 自动测试'})).toBeVisible()
 await page.getByRole('button',{name:'启动模拟 iEMS 自动测试',exact:true}).click()
 await expect(page.getByRole('alert')).toContainText('模拟下发与读回一致性核对')
})
