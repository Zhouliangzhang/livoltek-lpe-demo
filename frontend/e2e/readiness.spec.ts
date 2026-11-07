import {test,expect} from '@playwright/test'
import baseline from '../../baselines/lv01-mixed-vendors.engineering-model.json' with {type:'json'}
import type {Model} from '../src/types'
import {readinessIssues} from '../src/readinessIssues'
import {generateSettings,updateSetting} from '../src/settingsCatalog'

test('readiness separates gaps, mismatches, manufacturer evidence and authoritative conflicts',()=>{
 let m=structuredClone(baseline) as Model
 m.project.operation_modes=[]
 expect(readinessIssues(m).some(i=>i.layer==='L1'&&i.category==='缺失信息')).toBeTruthy()
 let row=generateSettings(m).find(r=>r.definition.key==='soc_min')!
 m=updateSetting(m,row,'planned',20);row=generateSettings(m).find(r=>r.id===row.id)!
 m=updateSetting(m,row,'actual',30)
 const issues=readinessIssues(m,{valid:false,errors:[`L5 ${row.id}.actual: invalid number value`],warnings:[]})
 expect(issues.find(i=>i.id===row.id+'-difference')?.label).toBe(row.id+' actual')
 expect(issues.find(i=>i.id==='rule-0')?.layer).toBe('L5')
 expect(issues.find(i=>i.id===row.id+'-evidence')?.category).toBe('待厂家确认')
 expect(new Set(issues.map(i=>i.id)).size).toBe(issues.length)
 expect(readinessIssues(m,{valid:false,errors:['project/country_code: invalid code'],warnings:[]}).find(i=>i.id==='rule-0')?.label).toBe('L1 country_code')
})

test('L6 links to a precise setting and device field; edits invalidate checks',async({page})=>{
 await page.goto('/')
 await page.getByRole('button',{name:'复制为新项目'}).click()
 await expect(page.locator('.projectBar strong')).toHaveText('LV-01 新建样板')
 const check=async()=>{await page.getByRole('button',{name:/L6 运行条件检查/}).click();await page.getByRole('button',{name:'运行数据规则检查',exact:true}).click();await expect(page.locator('.issueSummary')).toBeVisible()}
 await check()
 await page.getByRole('button',{name:'定位 BESS_01.soc_min-planned',exact:true}).click()
 await expect(page.getByLabel('BESS_01.soc_min planned',{exact:true})).toBeFocused()
 await page.getByLabel('BESS_01.soc_min planned',{exact:true}).fill('25')
 await page.getByRole('button',{name:'返回 L6 重新检查'}).click()
 await expect(page.getByText('尚未检查。运行检查后查看 L1–L5 的缺项、冲突和需现场验证事项。')).toBeVisible()
 await check()
 await expect(page.getByTestId('issue-BESS_01.soc_min-planned')).toHaveCount(0)
 await expect(page.getByTestId('issue-BESS_01.soc_min-evidence')).toBeVisible()
 await page.getByRole('button',{name:'定位 BESS_01-installed_location',exact:true}).click()
 await expect(page.getByLabel('安装位置',{exact:true})).toBeFocused()
 await page.getByLabel('安装位置',{exact:true}).fill('L6-test-site')
 await page.getByRole('button',{name:'返回 L6 重新检查'}).click()
 await check()
 await expect(page.getByTestId('issue-BESS_01-installed_location')).toHaveCount(0)
 await expect(page.getByText('待现场验证',{exact:true})).toBeVisible()
 await page.getByText('L1 项目定义 · 查看 / 修改',{exact:true}).click()
 await page.getByLabel('L1 country_code',{exact:true}).fill('INVALID')
 await check()
 await page.getByRole('button',{name:'定位 rule-0',exact:true}).click()
 await expect(page.getByLabel('L1 country_code',{exact:true})).toBeFocused()
 await page.getByLabel('L1 country_code',{exact:true}).fill('ZA')
 await page.getByRole('button',{name:'返回 L6 重新检查'}).click()
 await check()
 await page.getByRole('button',{name:'保存版本',exact:true}).click()
 await expect(page.getByRole('status')).toContainText('已保存不可变版本')
})

test('connection finding opens device-first correction and preserves connection identity',async({page})=>{
 await page.goto('/')
 await page.getByRole('button',{name:'复制为新项目'}).click()
 await expect(page.locator('.projectBar strong')).toHaveText('LV-01 新建样板')
 const edge=baseline.edges[0]
 // Inject a rule result to exercise navigation without persisting an invalid engineering graph.
 await page.route('**/api/validate',route=>route.fulfill({json:{valid:false,errors:[`voltage mismatch: ${edge.edge_id}`],warnings:[]}}))
 await page.getByRole('button',{name:/L6 运行条件检查/}).click()
 await page.getByRole('button',{name:'运行数据规则检查',exact:true}).click()
 await page.getByRole('button',{name:'定位 rule-0',exact:true}).click()
 await expect(page.getByRole('heading',{name:'修正连接 · '+edge.edge_id})).toBeVisible()
 await expect(page.getByLabel('起点设备',{exact:true})).toHaveValue(baseline.ports.find(p=>p.port_id===edge.from_port_id)!.node_id)
 await expect(page.getByLabel('起点端口',{exact:true})).toHaveValue(edge.from_port_id)
 await expect(page.getByLabel('终点端口',{exact:true})).toHaveValue(edge.to_port_id)
 await page.getByLabel('连接设计依据',{exact:true}).fill('L6-CORRECTION-TEST')
 await page.getByRole('button',{name:'保存连接并更新拓扑',exact:true}).click()
 await expect(page.locator('.connectionSuccess')).toBeVisible()
 const id=await page.getByLabel('选择项目').inputValue()
 const saved=await (await page.request.get('/api/projects/'+id)).json()
 expect(saved.model.edges).toHaveLength(baseline.edges.length)
 expect(saved.model.edges.find((e:{edge_id:string})=>e.edge_id===edge.edge_id).design_ref).toBe('L6-CORRECTION-TEST')
})
