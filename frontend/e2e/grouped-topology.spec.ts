import {test,expect} from '@playwright/test'
import pilot from '../../examples/ci20-pilot.json' with {type:'json'}
import {groupedTopology} from '../src/groupedTopology'
import type {Model} from '../src/types'

test('four groups preserve every object and every original port connection without mutation',()=>{
 const model=structuredClone(pilot) as unknown as Model,before=JSON.stringify(model),groups=groupedTopology(model)
 expect(groups.map(g=>g.title)).toEqual(['主配电','光伏汇流','储能汇流','通信控制'])
 const owned=groups.flatMap(g=>g.model.nodes.filter(n=>!g.references.has(n.node_id)).map(n=>n.node_id))
 expect(owned.length).toBe(75);expect(new Set(owned).size).toBe(75)
 const edges=groups.flatMap(g=>g.model.edges)
 expect(edges.length).toBe(120);expect(new Set(edges.map(e=>e.edge_id)).size).toBe(120)
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
})
