import {test,expect} from '@playwright/test'
import fixture from '../../examples/ci20-pilot.json' with {type:'json'}
import type {Model} from '../src/types'
import {communicationBuses} from '../src/communication'
import {generateSettings,updateSetting} from '../src/settingsCatalog'
import {readinessIssues} from '../src/readinessIssues'
import {applyBusSettings} from '../src/CommunicationSettings'
const sample=()=>structuredClone(fixture) as unknown as Model

test('L4 limits fields and keeps two iEMS serial channels isolated',()=>{
 let m=sample(),buses=communicationBuses(m)
 expect(buses).toHaveLength(3)
 expect(buses.filter(b=>b.domain==='RS485')).toHaveLength(2)
 expect(generateSettings(m).some(r=>r.nodeId==='BESS_01'&&r.definition.key==='baud_rate')).toBe(false)
 const meter=buses.find(b=>b.name==='零馈计量')!
 m=applyBusSettings(m,meter.id,{baud_rate:9600,parity:'无',stop_bits:1})
 expect(generateSettings(m).find(r=>r.id==='EMS_MASTER.METER_RS485.baud_rate')?.record?.planned).toBe(9600)
 expect(generateSettings(m).find(r=>r.id==='EMS_MASTER.PV_RS485.baud_rate')?.record).toBeUndefined()
 expect(()=>applyBusSettings(m,meter.id,{station_address:'1'})).toThrow()
 m.edges=m.edges.filter(e=>!e.from_port_id.startsWith('METER_PCC.')&&!e.to_port_id.startsWith('METER_PCC.'))
 expect(generateSettings(m).some(r=>r.nodeId==='METER_PCC')).toBe(false)
})
test('exact model template auto-fills only missing plans and preserves actual evidence',()=>{
 let m=sample();const d=m.device_models.find(d=>d.model_id==='PV-GT3')!
 d.communication_templates=[{id:'TEST-ONLY',version:'1',master_data_version:d.master_data_version,domain:'RS485',values:{baud_rate:9600},reference_doc:'Synthetic test evidence, not vendor defaults',status:'DRAFT'}]
 let row=generateSettings(m).find(r=>r.id==='PV_01.baud_rate')!
 expect(row.record?.planned).toBe(9600);expect(row.record?.actual).toBeNull()
 m=updateSetting(m,row,'actual',19200)
 row=generateSettings(m).find(r=>r.id===row.id)!
 m=updateSetting(m,row,'planned',19200)
 expect(generateSettings(m).find(r=>r.id===row.id)?.record?.actual).toBe(19200)
 expect(generateSettings(m).find(r=>r.id===row.id)?.record?.planned).toBe(19200)
 d.master_data_version='NEW'
 expect(generateSettings({...m,device_models:[...m.device_models.filter(x=>x.model_id!==d.model_id),d]}).find(r=>r.id==='PV_02.baud_rate')?.record).toBeUndefined()
})
test('communication cards persist isolated bus plans and L6 opens nested device fields',async({page,request})=>{
 const m=sample();m.project.project_id+='-COMM';for(const p of m.parameters as {scope:string;owner_id:string}[])if(p.scope==='PROJECT')p.owner_id=m.project.project_id
 expect((await request.post('/api/projects',{data:{model:m,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/');await page.getByLabel('选择项目').selectOption(m.project.project_id)
 await page.getByRole('button',{name:/L5 系统设置/}).click()
 await page.getByText('高级设置：通信、逐台参数、现场值与厂家依据',{exact:true}).click()
 await expect(page.locator('.commBus')).toHaveCount(3)
 await expect(page.getByLabel('储能通信统一 baud_rate',{exact:true})).toHaveCount(0)
 await page.getByLabel('零馈计量统一 baud_rate',{exact:true}).fill('9600')
 await page.locator('.commBus').filter({has:page.getByRole('heading',{name:'零馈计量',exact:true})}).getByRole('button',{name:'统一本总线计划'}).click()
 await page.getByRole('button',{name:'保存版本',exact:true}).click()
 await expect(page.getByText(/已保存不可变版本/)).toBeVisible()
 const saved=await (await request.get('/api/projects/'+m.project.project_id)).json()
 expect(generateSettings(saved.model).find(r=>r.id==='EMS_MASTER.METER_RS485.baud_rate')?.record?.planned).toBe(9600)
 await page.getByRole('button',{name:/L6 运行条件检查/}).click();await page.getByRole('button',{name:'运行数据规则检查',exact:true}).click()
 await page.getByRole('button',{name:'定位 EMS_MASTER.PV_RS485.baud_rate-planned',exact:true}).click()
 await expect(page.getByLabel('EMS_MASTER.PV_RS485.baud_rate planned',{exact:true})).toBeFocused()
})

test('L6 detects duplicate addresses within a bus and differing serial formats',()=>{
 let m=sample()
 for(const [id,key,value] of [['PV_02','station_address','1'],['PV_01','baud_rate',9600],['PV_02','baud_rate',19200]] as const){
  const row=generateSettings(m).find(r=>r.nodeId===id&&r.definition.key===key)!
  m=updateSetting(m,row,'planned',value)
 }
 const conflicts=readinessIssues(m).filter(i=>i.category==='设置冲突')
 expect(conflicts.some(i=>i.message.includes('地址重复')&&i.object==='光伏通信')).toBe(true)
 expect(conflicts.some(i=>i.message.includes('格式不一致')&&i.object==='光伏通信')).toBe(true)
 expect(conflicts.some(i=>i.object==='零馈计量')).toBe(false)
})
