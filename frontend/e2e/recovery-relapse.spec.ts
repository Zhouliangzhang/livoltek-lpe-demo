import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
test('relapse resets recovery timers and retains alarm until stable',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-RELAPSE';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 for(const action of ['send','readback'])await request.post(`/api/projects/${model.project.project_id}/iems-configuration`,{data:{mode:'SIMULATION',revision:1,action}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
 const panel=page.getByRole('region',{name:'动态联动模拟'})
 await panel.getByLabel('动态异常注入',{exact:true}).selectOption('meter_pv_reject')
 await panel.getByLabel('动态故障设备',{exact:true}).selectOption('PV_03')
 await panel.getByLabel('复合异常恢复顺序').selectOption('pv_first')
 for(const relapse of ['meter','pv'])for(const window of ['qualification','stabilization']){
  await panel.getByLabel('恢复期间复发',{exact:true}).selectOption(relapse)
  await panel.getByLabel('复发观察阶段',{exact:true}).selectOption(window)
  await panel.getByRole('button',{name:'运行动态模拟',exact:true}).click()
  await expect(panel.getByRole('button',{name:'运行动态模拟',exact:true})).toBeEnabled()
  await panel.getByRole('button',{name:relapse==='meter'?/零馈表再次失联/:/光伏再次拒令/}).click()
  await expect(panel.locator('.dynTimers')).toContainText('两个计时已清零')
  await expect(panel.locator('.dynCompoundAlarm header')).toContainText('严重告警')
  await panel.getByLabel('动态时间点',{exact:true}).fill('160')
  await expect(panel.locator('.dynCompoundAlarm header')).toContainText('模拟告警已解除')
 }
 await page.getByLabel('选择 iEMS 环境',{exact:true}).selectOption('REAL')
 await expect(panel.locator('.dynRecoveryGates,.dynChart')).toHaveCount(0)
 await expect(panel.getByRole('button',{name:'启动现场动态测试',exact:true})).toBeDisabled()
})
