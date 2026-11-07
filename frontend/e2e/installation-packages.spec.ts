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
test('old guidance is read-only and does not compete with the three-step workflow',async({page,request})=>{
 const m=structuredClone(fixture);m.project.project_id+='-INSTALL';m.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=m.project.project_id})
 await request.post('/api/projects',{data:{model:m,expected_revision:0}})
 await request.post(`/api/projects/${m.project.project_id}/plans`,{data:{}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 await page.getByRole('button',{name:'M3 调试与验证',exact:true}).click()
 await page.getByText('旧版技术参考与现场记录 · 只读',{exact:true}).click()
 const legacy=page.locator('.m2Legacy').filter({has:page.getByText('旧版技术参考与现场记录 · 只读',{exact:true})})
 await expect(legacy.locator('article')).not.toHaveCount(0)
 await expect(legacy.locator('button,input,textarea,select')).toHaveCount(0)
 await expect(page.locator('.m3Steps button')).toHaveCount(5)
})
