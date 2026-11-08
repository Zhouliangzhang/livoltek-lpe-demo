import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('independent restoration keeps alarm until both are verified and stable',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-INDEPENDENT';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 for(const action of ['send','readback'])await request.post(`/api/projects/${model.project.project_id}/iems-configuration`,{data:{mode:'SIMULATION',revision:1,action}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 const panel=page.getByRole('region',{name:'动态联动模拟'})
 await panel.getByLabel('动态异常注入',{exact:true}).selectOption('meter_pv_reject')
 await panel.getByLabel('动态故障设备',{exact:true}).selectOption('PV_03')
 for(const order of ['meter_first','pv_first','meter_only','pv_only']){
  await panel.getByLabel('复合异常恢复顺序').selectOption(order)
  await panel.getByRole('button',{name:'运行动态模拟',exact:true}).click()
  await expect(panel.getByRole('button',{name:'运行动态模拟',exact:true})).toBeEnabled()
  await panel.getByLabel('动态时间点',{exact:true}).fill('50')
  const gates=panel.getByRole('region',{name:'独立恢复验证'})
  await expect(gates).toContainText(order.startsWith('meter')?'仍拒绝限功率':'仍失联 · 反馈不可用')
  await expect(panel.locator('.dynCompoundAlarm header')).toContainText('严重告警')
  await panel.getByLabel('动态时间点',{exact:true}).fill('160')
  await expect(panel.locator('.dynCompoundAlarm header')).toContainText(order.endsWith('only')?'严重告警':'模拟告警已解除')
  if(!order.endsWith('only')){
   await panel.getByLabel('动态时间点',{exact:true}).fill('50')
   await expect(panel.locator('.dynCompoundAlarm header')).toContainText('严重告警')
  }
 }
 await page.getByLabel('选择 iEMS 环境',{exact:true}).selectOption('REAL')
 await expect(panel.locator('.dynRecoveryGates,.dynChart')).toHaveCount(0)
 await expect(panel.getByRole('button',{name:'启动现场动态测试',exact:true})).toBeDisabled()
})
