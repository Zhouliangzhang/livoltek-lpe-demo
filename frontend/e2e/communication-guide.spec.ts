import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import {communicationRoutes} from '../src/CommunicationGuide'
import type {Model} from '../src/types'
test('all physical communication routes appear exactly once; control commands are excluded',()=>{
 const routes=communicationRoutes(fixture as unknown as Model)
 expect(routes.length).toBe(fixture.edges.filter(e=>e.edge_type==='COMMUNICATION').length)
 expect(new Set(routes.map(r=>r.edge.edge_id)).size).toBe(routes.length)
 expect(routes.find(r=>r.from.node_id==='METER_PCC'&&r.to.node_id==='EMS_MASTER')?.group).toBe('零馈计量')
 expect(routes.some(r=>r.edge.edge_type==='CONTROL')).toBe(false)
})
test('communication guide shows ports, settings and verification, then locates L5',async({page,request})=>{
 const model=structuredClone(fixture);model.project.project_id+='-GUIDE';model.parameters.forEach(p=>{if(p.scope==='PROJECT')p.owner_id=model.project.project_id})
 await request.post('/api/projects',{data:{model,expected_revision:0}})
 await page.goto('/');await page.getByLabel('选择项目').selectOption(model.project.project_id)
 await page.getByRole('button',{name:'02 引导式安装',exact:true}).click();await page.getByRole('button',{name:'生成安装计划',exact:true}).click()
 const meter=page.getByRole('article',{name:'零馈计量 接线指引',exact:true})
 await expect(page.locator('.wireSelectedDetail')).toHaveCount(0)
 await expect(page.locator('.wiringLink')).toHaveCount(model.edges.filter(e=>e.edge_type==='COMMUNICATION').length)
 await meter.getByRole('button',{name:/查看连接 .*METER_PCC.RS485 到 EMS_MASTER.METER_RS485/}).click()
 await expect(meter.getByRole('region',{name:'零馈计量 连接详情',exact:true})).toBeVisible()
 await meter.getByRole('button',{name:'收起详情',exact:true}).click()
 await expect(meter.locator('.wireSelectedDetail')).toHaveCount(0)
 await meter.getByRole('button',{name:/查看连接 .*METER_PCC.RS485 到 EMS_MASTER.METER_RS485/}).press('Enter')
 await expect(meter.locator('.wireSelectedDetail')).toBeVisible()
 await expect(meter).toContainText('METER_PCC.RS485');await expect(meter).toContainText('EMS_MASTER.METER_RS485')
 await expect(meter).toContainText('不可仅凭 A/B');await expect(meter).toContainText('三相电压/电流');await expect(meter).not.toContainText('IP 地址')
 await expect(page.locator('#package-INSTALL-POSITION')).toHaveCount(0);await expect(page.locator('#package-RULE-BESS-PREP')).toHaveCount(0)
 await meter.getByRole('button',{name:/设置 /}).first().click()
 await expect(page.getByRole('heading',{name:'系统设置',exact:true})).toBeVisible()
 await expect(page.locator(':focus')).toHaveAttribute('aria-label',/planned$/)
})
