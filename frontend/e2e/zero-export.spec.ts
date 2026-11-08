import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('zero export links full plant, faults locate, recovery persists, real stays locked',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-ZERO09';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=await(await request.post(`/api/projects/${model.project.project_id}/plans`)).json(),base=`/api/plans/${plan.id}`
 const session=await(await request.post(base+'/meter-workflow',{data:{mode:'SIMULATION',edge_id:'CI-072',acknowledged:true,operator:'联动演练',reference:'独立合成测试'}})).json()
 for(const step of ['selfcheck','route','identity','quality','reference','stability','complete'])await request.post(base+'/meter-workflow/'+session.id+'/run',{data:{step}})
 for(const endpoint of ['pv-communication','bess-communication','configuration-readback','pv-control','bess-control']){const r=await request.post(base+'/'+endpoint,{data:{session_id:session.id,acknowledged:true,request_id:endpoint}});expect(r.ok()).toBeTruthy()}
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id);await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 const go=()=>page.getByRole('navigation',{name:'调试顺序'}).getByRole('button',{name:/09 零馈控制联动/}).click()
 await go();const view=page.getByRole('region',{name:'零馈控制联动测试'})
 await view.getByRole('checkbox').check();await view.getByRole('button',{name:'执行模拟联动测试'}).click()
 await expect(view.getByRole('status')).toContainText('本轮 · 模拟满足');await expect(view.getByRole('img',{name:'零馈控制联动功率曲线'})).toBeVisible()
 await view.getByLabel('联动演练场景').selectOption('pv_reject');await view.getByLabel('联动异常设备').selectOption('PV_03');await view.getByRole('button',{name:'执行模拟联动测试'}).click()
 await expect(view.getByRole('region',{name:'PV_03 联动异常'})).toContainText('光伏拒绝限功率')
 await view.getByRole('button',{name:'定位处理 PV_03'}).click();await expect(page.getByRole('region',{name:'L5 作业区'})).toBeVisible()
 await page.getByRole('button',{name:'返回 M2 调试',exact:true}).click();await go();await view.getByRole('checkbox').check()
 await view.getByLabel('联动演练场景').selectOption('meter_lost');await view.getByRole('button',{name:'执行模拟联动测试'}).click();await expect(view.getByRole('alert')).toContainText('恢复未确认')
 await expect(view.getByRole('button',{name:'执行模拟联动测试'})).toBeDisabled()
 await page.reload();await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click();await go();await expect(view.getByRole('alert')).toContainText('恢复未确认')
 await view.getByRole('checkbox').check();await view.getByRole('button',{name:'复核模拟恢复（不启动新测试）'}).click();await expect(view).toContainText('原失败记录保留')
 await view.getByRole('button',{name:'执行模拟联动测试'}).click();await expect(view.getByRole('status')).toContainText('本轮 · 模拟满足')
 await page.getByLabel('选择 iEMS 环境').selectOption('REAL');await go();await expect(view.getByRole('button',{name:'现场控制不可用'})).toBeDisabled();await expect(view.getByRole('status')).toHaveCount(0)
})
