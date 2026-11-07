import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import {groupChecks,type CheckItem} from '../src/checklistGroups'
import type {Model} from '../src/types'

test('grouping preserves item IDs and separates model versions, methods and port domains',()=>{
 const base={stage:'ELECTRICAL',title:'接地',method:'核对',expected:'符合依据',manufacturer_pending:'待确认',source_status:'DRAFT',template_version:'V1',layer:'L3'}
 const items=['PV_01','PV_02'].map(id=>({...base,id:id+':earth',target_id:id,name:id,detail:id,node_ids:[id]})) as CheckItem[]
 expect(groupChecks(items,fixture as unknown as Model)).toHaveLength(1)
 const changed=structuredClone(fixture) as unknown as Model,asset=changed.device_assets.find(a=>a.asset_id===changed.nodes.find(n=>n.node_id==='PV_02')?.device_asset_id)!,model=changed.device_models.find(d=>d.model_id===asset.model_id)!
 changed.device_models.push({...model,model_id:model.model_id+'-new',master_data_version:'NEW'});asset.model_id+='-new'
 expect(groupChecks(items,changed)).toHaveLength(2)
 expect(groupChecks([items[0],{...items[1],method:'不同检查方法'}],fixture as unknown as Model)).toHaveLength(2)
 expect(groupChecks(items,fixture as unknown as Model).flatMap(g=>g.items.map(i=>i.id))).toEqual(items.map(i=>i.id))
})

test('same model shares guidance; per-device exceptions persist and resolve independently',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-GROUPS';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 const plan=(await request.post(`/api/projects/${model.project.project_id}/plans`,{data:{}})).json();const id=(await plan).id
 const data=await (await request.get(`/api/plans/${id}/checklist`)).json()
 const groups=groupChecks(data.items,model as unknown as Model)
 console.log('Grouped checklist',groups.length,'from',data.items.length,JSON.stringify(Object.fromEntries(['ELECTRICAL','COMMUNICATION','CONTROL'].map(s=>[s,groups.filter(g=>g.items[0].stage===s).length]))))
 expect(groups.length).toBeLessThan(data.items.length/2)
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'02 引导式安装',exact:true}).click()
 const root=page.getByRole('region',{name:'系统逐项点检'})
 await root.getByRole('button',{name:/03.*控制点检/}).click()
 const group=root.locator('.checkItem').filter({hasText:'光伏限功率策略与反馈'})
 await group.locator('.checkRow').click()
 await expect(group.locator('.checkMembers>button')).toHaveCount(10)
 await expect(group.getByRole('heading',{name:'如何检查 · 本组共用',exact:true})).toHaveCount(1)
 await group.locator('.checkMembers>button').first().click()
 await group.getByRole('combobox',{name:'点检结果',exact:true}).selectOption('FAIL')
 await group.getByLabel('记录人',{exact:true}).fill('自动测试 EPC')
 await group.getByLabel('现场说明 / 测量记录 / 不适用原因',{exact:true}).fill('演示异常：PV_01 反馈映射待核对，非真实现场结论。')
 await group.getByRole('button',{name:'保存点检记录',exact:true}).click()
 await expect(root.getByRole('region',{name:'异常优先处理'})).toContainText('PV_01')
 await expect(group.locator('.checkMembers>button').nth(1)).toContainText('未点检')
 await page.reload();await page.getByRole('button',{name:'02 引导式安装',exact:true}).click()
 await root.getByRole('region',{name:'异常优先处理'}).getByRole('button').click()
 await expect(group.getByRole('combobox',{name:'点检结果',exact:true})).toHaveValue('FAIL')
 await group.getByRole('combobox',{name:'点检结果',exact:true}).selectOption('PENDING')
 await group.getByRole('button',{name:'保存点检记录',exact:true}).click()
 await expect(root.getByRole('region',{name:'异常优先处理'})).toContainText('暂无已记录异常')
 await expect(group.locator('.checkMembers>button').nth(1)).toContainText('未点检')
})
