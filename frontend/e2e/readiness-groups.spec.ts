import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import type {Model} from '../src/types'
import {readinessIssues} from '../src/readinessIssues'
import {groupReadinessIssues} from '../src/readinessGroups'

test('grouping preserves every finding, separates model versions, phases and ownership',()=>{
 const m=structuredClone(fixture) as unknown as Model,issues=readinessIssues(m),groups=groupReadinessIssues(m,issues)
 expect(groups.flatMap(g=>g.items).map(i=>i.id).sort()).toEqual(issues.map(i=>i.id).sort())
 const firmware=groups.find(g=>g.items[0].id==='BESS_01-firmware_version')!
 expect(firmware.deviceCount).toBe(10);expect(firmware.owner).toBe('EPC 现场补充')
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-evidence')?.owner).toBe('厂家确认')
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-planned')?.items).toHaveLength(10)
 expect(groups.find(g=>g.items[0].id==='BESS_01.soc_min-actual')?.items).toHaveLength(10)
 const d=m.device_models.find(d=>d.model_id==='BESS-261')!;m.device_models.push({...d,model_id:'BESS-NEW',master_data_version:'NEW'})
 m.device_assets.find(a=>a.asset_id==='ASSET-BESS_10')!.model_id='BESS-NEW'
 expect(groupReadinessIssues(m,readinessIssues(m)).find(g=>g.items[0].id==='BESS_01-firmware_version')?.deviceCount).toBe(9)
})
test('merged finding opens selected device and manufacturer interface reference',async({page,request})=>{
 const m=structuredClone(fixture);m.project.project_id+='-GROUPS';m.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=m.project.project_id})
 expect((await request.post('/api/projects',{data:{model:m,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 const check=async()=>{await page.getByRole('button',{name:/L6 运行条件检查/}).click();await page.getByRole('button',{name:'运行数据规则检查',exact:true}).click()}
 await check()
 const group=page.getByTestId('issue-BESS_01-installed_location')
 await expect(group).toContainText('10 台设备')
 await group.getByText('展开 10 个定位入口',{exact:true}).click()
 await page.getByRole('button',{name:'定位 BESS_07-installed_location',exact:true}).click()
 await expect(page.getByLabel('安装位置',{exact:true})).toBeFocused()
 await page.getByLabel('安装位置',{exact:true}).fill('测试位置 07')
 await page.getByRole('button',{name:'返回 L6 重新检查'}).click();await check()
 await expect(page.getByTestId('issue-BESS_01-installed_location')).toContainText('9 台设备')
 await page.getByLabel('处理方',{exact:true}).selectOption('厂家确认')
 await expect(page.getByRole('region',{name:'EPC 现场补充问题',exact:true})).toHaveCount(0)
 const interfaces=page.locator('.mergedIssue').filter({has:page.getByRole('heading',{name:'通信接口与点表依据',exact:true})}).filter({hasText:'GT3-125K-1'})
 await interfaces.getByRole('button',{name:/定位 warning-/}).first().click()
 await expect(page.getByLabel('IF-PV_01 point_ref',{exact:true})).toBeFocused()
 await page.getByLabel('IF-PV_01 point_ref',{exact:true}).fill('TEST-POINT-MAP-PENDING')
 await page.getByRole('button',{name:'保存版本',exact:true}).click()
 await expect(page.getByText(/已保存不可变版本/)).toBeVisible()
 const saved=await (await request.get('/api/projects/'+m.project.project_id)).json()
 expect(saved.model.interface_bindings.find((b:any)=>b.binding_id==='IF-PV_01').verification_status).toBe('UNVERIFIED')
})
