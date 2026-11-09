import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
const pilot=JSON.parse(readFileSync(new URL('../../examples/ci20-pilot.json',import.meta.url),'utf8'))
import type {Model} from '../src/types'
import {electricalView,effectiveElectricalEdges,branchDiagrams} from '../src/singleLineData'
import {currentTopology,frozenTopology,type FrozenTopology} from '../src/topologySnapshot'
test('overview updates current environment but never supplements frozen snapshots with draft data',()=>{
 const m=structuredClone(pilot) as unknown as Model
 const wire=m.edges.find(e=>e.edge_type==='COMMUNICATION')!
 m.project.network_drafts=[{id:'N1',base_edge_id:wire.edge_id,environment:'SIMULATION',from_port_id:wire.from_port_id,to_port_id:'new-port'}]
 expect(currentTopology(m,'SIMULATION').edges.find(e=>e.edge_id===wire.edge_id)?.to_port_id).toBe('new-port')
 expect(currentTopology(m,'REAL').edges.find(e=>e.edge_id===wire.edge_id)?.to_port_id).toBe(wire.to_port_id)
 const record:FrozenTopology={id:'frozen',environment:'SIMULATION',source_revision:1,domain_id:'D1',scope_type:'PARTIAL',content_hash:'hash',snapshot:{project:{project_id:'P1',name:'Frozen name'},structure:{one:structuredClone(m.nodes[0])},ports:{},connections:{},models:{}}}
 const archived=JSON.stringify(record)
 m.nodes[0].name='New draft';m.nodes.push({...m.nodes[0],node_id:'later'})
 const result=frozenTopology(record)
 expect(result.nodes).toHaveLength(1);expect(result.nodes[0].name).not.toBe('New draft');expect(result.edges).toHaveLength(0)
 expect(JSON.stringify(record)).toBe(archived)
})
test('only recorded valid electrical port relations are drawn once, with four groups',()=>{
 const m=structuredClone(pilot) as unknown as Model
 const before=JSON.stringify(m),v=electricalView(m)
 expect(v.groups.map(g=>g.id)).toEqual(['main','pv','bess','load'])
 const drawn=v.groups.flatMap(g=>g.edges.map(e=>e.edge_id))
 expect(new Set(drawn).size).toBe(drawn.length)
 expect(drawn.sort()).toEqual(m.edges.filter(e=>e.edge_type==='ELECTRICAL').map(e=>e.edge_id).sort())
 expect(JSON.stringify(m)).toBe(before)
 expect(v.groups.find(g=>g.id==='main')!.nodes.some(n=>n.node_id.startsWith('ARRAY_'))).toBeFalsy()
 for(const group of v.groups){const diagrams=branchDiagrams(m,group);expect(diagrams.flatMap(g=>g.edges.map(e=>e.edge_id)).sort()).toEqual(group.edges.map(e=>e.edge_id).sort())}
 const edge=m.edges.find(e=>e.edge_type==='ELECTRICAL')!
 edge.to_port_id='MISSING'
 const broken=electricalView(m)
 expect(broken.issues.some(i=>i.includes(edge.edge_id))).toBeTruthy()
 expect(broken.groups.flatMap(g=>g.edges).some(e=>e.edge_id===edge.edge_id)).toBeFalsy()
})
test('ownership never creates a wire; missing ports and disconnected devices remain visible',()=>{
 const m=structuredClone(pilot) as unknown as Model;m.edges=[]
 const v=electricalView(m)
 expect(v.groups.flatMap(g=>g.edges)).toHaveLength(0)
 expect(v.issues.some(i=>i.includes('待补'))).toBeTruthy()
 expect(v.groups.flatMap(g=>g.nodes).some(n=>n.node_type==='PV_INVERTER')).toBeTruthy()
})
test('environment drafts are isolated and replace rather than duplicate reference edges',()=>{
 const m=structuredClone(pilot) as unknown as Model,e=m.edges.find(e=>e.edge_type==='ELECTRICAL')!
 m.project.electrical_drafts=[{id:'SIM',base_edge_id:e.edge_id,environment:'SIMULATION',from_port_id:e.from_port_id,to_port_id:'SIM_PORT'}]
 expect(effectiveElectricalEdges(m,'SIMULATION').find(x=>x.edge_id===e.edge_id)?.to_port_id).toBe('SIM_PORT')
 expect(effectiveElectricalEdges(m,'REAL').find(x=>x.edge_id===e.edge_id)?.to_port_id).toBe(e.to_port_id)
})
