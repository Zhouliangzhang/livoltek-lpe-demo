import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import {orderedTasks,missingActions} from '../src/InstallationPackages'
import type {Task} from '../src/types'
test('installation order respects dependencies and separates both document owners',()=>{
 const task=(id:string,wp:string,deps:string[]=[])=>({task_id:id,work_package:wp,depends_on:deps,missing_inputs:['approved manufacturer / EPC source document']} as Task)
 expect(orderedTasks([task('upper','WP07',['comm']),task('comm','WP04',['prep']),task('prep','WP02'),task('boundary','WP01')]).map(t=>t.task_id)).toEqual(['boundary','prep','comm','upper'])
 expect(orderedTasks([task('a','WP01',['b']),task('b','WP04')]).map(t=>t.task_id)).toEqual(['b','a'])
 expect(missingActions(task('x','WP02')).map(a=>a.owner)).toEqual(['厂家提供','EPC 补充'])
})
test('M2 Chinese missing inputs navigate to evidence, template, interface and engineering reference',async({page,request})=>{
 const m=structuredClone(fixture);m.project.project_id+='-INSTALL';m.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=m.project.project_id})
 expect((await request.post('/api/projects',{data:{model:m,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 await page.getByRole('button',{name:'02 引导式安装',exact:true}).click();await page.getByRole('button',{name:'生成点检清单',exact:true}).click()
 await page.getByText('其它技术参考与现场记录',{exact:true}).click()
 await expect(page.locator('.installationTask')).toHaveCount(12)
 await expect(page.locator('.installationTask').first()).toContainText('现场与系统边界')
 await expect(page.locator('.installationTask').last()).toContainText('上电前资料确认')
 for(const id of ['EARTH','POWER','COMMS','PREPOWER']){
  await expect(page.locator('#package-INSTALL-'+id+' .installationSteps li')).toHaveCount(3)
  await expect(page.locator('#package-INSTALL-'+id)).toContainText('待厂家确认')
 }
 await page.getByRole('button',{name:'INSTALL-EARTH EPC 补充 0',exact:true}).click()
 await expect(page.locator('#evidence-installation_record')).toBeFocused()
 await expect(page.locator('.installationFlow')).not.toContainText('approved manufacturer')
 await page.getByRole('button',{name:'BOUNDARY-PCC_01 EPC 补充 0',exact:true}).click()
 await expect(page.locator('#evidence-design_reference')).toBeFocused()
 await page.getByRole('button',{name:'INSTALL-COMMS 厂家提供 0',exact:true}).click()
 await expect(page.getByLabel('模板来源文档',{exact:true})).toBeFocused()
 await page.getByRole('button',{name:'返回安装工作包',exact:true}).click()
 await page.getByRole('button',{name:'INTERFACE-ASSET-METER_PCC 厂家提供 0',exact:true}).click()
 await expect(page.getByLabel('IF-METER_PCC point_ref',{exact:true})).toBeFocused()
 await page.getByRole('button',{name:'返回安装工作包',exact:true}).click()
 await page.getByRole('button',{name:'RULE-ENERGIZATION-REVIEW EPC 补充 0',exact:true}).click()
 await expect(page.getByLabel('cable_spec reference',{exact:true})).toBeFocused()
})
