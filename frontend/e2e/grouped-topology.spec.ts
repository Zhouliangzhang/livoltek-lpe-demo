import {test,expect} from '@playwright/test'
import pilot from '../../examples/ci20-pilot.json' with {type:'json'}
import {groupedTopology} from '../src/groupedTopology'
import {controlTopology} from '../src/controlTopology'
import type {Model} from '../src/types'

test('four groups preserve every object and every original port connection without mutation',()=>{
 const model=structuredClone(pilot) as unknown as Model,before=JSON.stringify(model),groups=groupedTopology(model)
 expect(groups.map(g=>g.title)).toEqual(['主配电','光伏汇流','储能汇流','通信控制'])
 const owned=groups.flatMap(g=>g.model.nodes.filter(n=>!g.references.has(n.node_id)).map(n=>n.node_id))
 expect(owned.length).toBe(73);expect(new Set(owned).size).toBe(73)
 const edges=groups.flatMap(g=>g.model.edges)
 expect(edges.length).toBe(114);expect(new Set(edges.map(e=>e.edge_id)).size).toBe(114)
 expect(JSON.stringify(model)).toBe(before)
 for(const group of groups){
  const positions=Object.values(group.positions)
  for(let i=0;i<positions.length;i++)for(let j=i+1;j<positions.length;j++)expect(Math.abs(positions[i].x-positions[j].x)>=120||Math.abs(positions[i].y-positions[j].y)>=64).toBeTruthy()
  for(const e of group.model.edges)for(const endpoint of [e.from_port_id,e.to_port_id])expect(group.model.nodes.some(n=>n.node_id===model.ports.find(p=>p.port_id===endpoint)?.node_id)).toBeTruthy()
 }
 const shuffled={...model,nodes:[...model.nodes].reverse()}
 expect(groupedTopology(shuffled).map(g=>g.positions)).toEqual(groups.map(g=>g.positions))
})

test('group views only zoom; telemetry does not reset zoom or enable edits',async({page,request})=>{
 const id=pilot.project.project_id
 const existing=await request.get('/api/projects/'+id)
 if(!existing.ok())expect((await request.post('/api/projects',{data:{model:pilot,expected_revision:0}})).ok()).toBeTruthy()
 await page.goto('/')
 await page.getByLabel('选择项目').selectOption(id)
 await expect(page.getByLabel('选择项目')).toBeEnabled()
 await expect(page.locator('.topologyGroup')).toHaveCount(4)
 const pv=page.getByRole('region',{name:'光伏汇流拓扑'})
 const node=pv.locator('.x6-node').filter({hasNot:page.locator('[data-reference="true"]')}).first()
 await expect(pv.locator('.x6-node')).toHaveCount(35)
 await node.scrollIntoViewIfNeeded()
 const start=await node.getAttribute('transform'),box=await node.boundingBox()
 expect(box).not.toBeNull()
 await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2)
 await page.mouse.down();await page.mouse.move(box!.x+80,box!.y+50,{steps:5});await page.mouse.up()
 await expect(node).toHaveAttribute('transform',start!)
 const viewport=pv.locator('.x6-graph-svg-viewport')
 const original=await viewport.getAttribute('transform')
 await page.getByRole('button',{name:'放大光伏汇流',exact:true}).click()
 await expect(viewport).not.toHaveAttribute('transform',original!)
 const zoom=await viewport.getAttribute('transform')
 await page.waitForResponse(r=>r.url().includes('/telemetry?'))
 await expect(viewport).toHaveAttribute('transform',zoom!)
 await expect(page.getByRole('button',{name:'保存版本',exact:true})).toBeDisabled()
 await page.getByRole('button',{name:'适应光伏汇流',exact:true}).click()
 await expect(viewport).toHaveAttribute('transform',original!)
 const control=page.getByRole('region',{name:'iEMS 统一控制关系图',exact:true})
 await expect(control.locator('.x6-node')).toHaveCount(21)
 const controlView=control.locator('.x6-graph-svg-viewport')
 const before=await controlView.getAttribute('transform')
 await page.getByRole('button',{name:'放大iEMS 统一控制',exact:true}).click()
 await expect(controlView).not.toHaveAttribute('transform',before!)
 await expect(page.getByRole('button',{name:'保存版本',exact:true})).toBeDisabled()
})

test('control views separate feedback commands and transport with one real controller',()=>{
 const model=structuredClone(pilot) as unknown as Model
 const parent=groupedTopology(model).find(g=>g.id==='control')!,before=JSON.stringify(parent.model)
 const views=controlTopology(parent)
 expect(views.map(v=>v.model.edges.length)).toEqual([4,20,11,11,4])
 const edges=views.flatMap(v=>v.model.edges.map(e=>e.edge_id))
 expect(new Set(edges).size).toBe(parent.model.edges.length)
 expect(edges.length).toBe(parent.model.edges.length)
 const owned=views.flatMap(v=>v.model.nodes.filter(n=>!v.references.has(n.node_id)))
 expect(new Set(owned.map(n=>n.node_id)).size).toBe(7)
 expect(owned.filter(n=>n.node_type==='EMS')).toHaveLength(1)
 const control=views.find(v=>v.id==='control-hierarchy')!
 expect(control.model.edges.every(e=>e.from_port_id.startsWith('EMS_MASTER.')&&e.edge_type==='CONTROL')).toBeTruthy()
 for(const view of views){
  const positions=Object.values(view.positions)
  for(let i=0;i<positions.length;i++)for(let j=i+1;j<positions.length;j++)expect(Math.abs(positions[i].x-positions[j].x)>=120||Math.abs(positions[i].y-positions[j].y)>=64).toBeTruthy()
 }
 expect(JSON.stringify(parent.model)).toBe(before)
})
