import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}

test('meter feedback gap, failover and recovery stay simulation-only; page scrolls',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-METER-DYNAMIC';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 for(const action of ['send','readback'])await request.post(`/api/projects/${model.project.project_id}/iems-configuration`,{data:{mode:'SIMULATION',revision:1,action}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 // The canvas must not consume ordinary wheel input or edit the topology.
 const canvas=page.getByTestId('topology-canvas').first()
 await canvas.scrollIntoViewIfNeeded();await canvas.hover()
 const before=await page.evaluate(()=>scrollY)
 await page.mouse.wheel(0,400)
 await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(before+100)
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 const panel=page.getByRole('region',{name:'动态联动模拟'})
 for(const fault of ['meter_comm_loss','meter_invalid']){
  await panel.getByLabel('动态异常注入',{exact:true}).selectOption(fault)
  await panel.getByRole('button',{name:'运行动态模拟',exact:true}).click()
  await expect(panel.getByRole('region',{name:'控制降级与恢复结果'})).toContainText('已完成模拟恢复')
  const feedback=panel.getByRole('region',{name:'并网点反馈与控制状态'})
  await expect(feedback).toContainText(fault==='meter_comm_loss'?'通信中断 · 无新鲜反馈':'数据异常 · 越界值已拒用')
  await expect(feedback).toContainText('有效计量：不可用')
  await panel.getByLabel('动态时间点',{exact:true}).fill('58')
  await expect(feedback).toContainText('观察期间保持降级')
  await panel.getByLabel('动态时间点',{exact:true}).fill('120')
  await expect(feedback).toContainText('模拟闭环调节')
 }
 await panel.getByLabel('故障恢复模式',{exact:true}).selectOption('persistent')
 await panel.getByRole('button',{name:'运行动态模拟',exact:true}).click()
 await expect(panel.locator('.dynRecovery')).toContainText('反馈仍不可用')
 await panel.locator('.dynChart').hover();const y=await page.evaluate(()=>scrollY)
 await page.mouse.wheel(0,400);await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(y+100)
 await page.mouse.wheel(0,-400);await expect.poll(()=>page.evaluate(()=>scrollY)).toBeLessThan(y+100)
 await page.getByLabel('选择 iEMS 环境',{exact:true}).selectOption('REAL')
 await expect(panel.locator('.dynChart,.dynFeedback')).toHaveCount(0)
 await expect(panel.getByRole('button',{name:'启动现场动态测试',exact:true})).toBeDisabled()
})
