import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('step13 summarizes scoped evidence and exports unsigned SIM snapshots',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-REPORT13';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=await(await request.post(`/api/projects/${model.project.project_id}/plans`)).json(),base=`/api/plans/${plan.id}`
 const session=await(await request.post(base+'/meter-workflow',{data:{mode:'SIMULATION',edge_id:'CI-072',acknowledged:true,operator:'报告演练',reference:'独立合成测试'}})).json()
 for(const step of ['selfcheck','route','identity','quality','reference','stability','complete'])await request.post(base+'/meter-workflow/'+session.id+'/run',{data:{step}})
 for(const endpoint of ['pv-communication','bess-communication','configuration-readback','pv-control','bess-control','zero-export','dynamic-response','degradation','continuous-observation'])expect((await request.post(base+'/'+endpoint,{data:{session_id:session.id,acknowledged:true,request_id:endpoint}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id);await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 const go=()=>page.getByRole('navigation',{name:'调试顺序'}).getByRole('button',{name:/13 结果汇总/}).click()
 await go();const view=page.getByRole('region',{name:'测试结果汇总与SAT报告'})
 await expect(view.getByRole('heading',{name:'模拟调试汇总 · 非现场 SAT'})).toBeVisible();await expect(view.locator('.satStep')).toHaveCount(12)
 await expect(view.locator('.satStep').nth(5)).toContainText('依据待确认')
 await view.getByRole('button',{name:'查看证据 12',exact:true}).click();await expect(view.getByRole('region',{name:'原始证据详情'})).toContainText('SIMULATOR')
 await view.getByRole('button',{name:'保存报告快照',exact:true}).click();await expect(view.getByRole('status')).toContainText('最新快照与本次汇总一致')
 const downloadPromise=page.waitForEvent('download');await view.getByRole('link',{name:'下载可打印报告',exact:true}).click();expect((await downloadPromise).suggestedFilename()).toContain('SIMULATION')
 await request.post(base+'/continuous-observation',{data:{session_id:session.id,acknowledged:true,request_id:'fault-report13',scenario:'pv_loss',fault_node:'PV_03',pattern:'persistent'}})
 await view.getByRole('button',{name:'刷新汇总',exact:true}).click();await expect(view.getByRole('status')).toContainText('已有快照已过期');await expect(view.locator('.satStep').nth(11)).toContainText('未完成')
 await view.getByRole('button',{name:'定位处理 PV_03',exact:true}).click();await expect(page.getByRole('region',{name:'L4 作业区'})).toBeVisible()
 await page.getByRole('button',{name:'返回 M2 调试',exact:true}).click();await go()
 await view.getByText(/待补充与待厂家确认 · .*合并主题/).click();await expect(view.getByText('填入引用不等于厂家批准。',{exact:false})).toBeVisible()
 await page.getByLabel('选择 iEMS 环境').selectOption('REAL');await go();await expect(view.getByRole('heading',{name:'现场 SAT 资料草稿 · 尚无现场结果'})).toBeVisible();await expect(view.getByRole('button',{name:'保存报告快照',exact:true})).toBeDisabled();await expect(view.getByRole('link',{name:'下载可打印报告',exact:true})).toHaveCount(0)
})
