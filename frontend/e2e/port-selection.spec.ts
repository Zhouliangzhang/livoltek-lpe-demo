import {test,expect} from '@playwright/test'
import {sourcePorts,targetPorts,choosePort} from '../src/ConnectionEditor'
import type {Model,Port} from '../src/types'

const port=(id:string,node:string,domain:string,role='BIDIRECTIONAL'):Port=>({port_id:id,node_id:node,name:id,domain,role})
const m=()=>({ports:[port('A.AC','A','AC'),port('A.RS','A','RS485'),port('B.AC','B','AC'),port('B.ETH','B','ETHERNET'),port('C.IN','C','CONTROL_LOGICAL','IN'),port('D.OUT','D','CONTROL_LOGICAL','OUT')],edges:[]} as unknown as Model)
test('device-first filtering and single-port selection',()=>{
 const model=m();const starts=sourcePorts(model,'A','ELECTRICAL')
 expect(choosePort(starts,'')).toBe('A.AC')
 expect(choosePort(starts,'OLD')).toBe('A.AC')
 expect(choosePort([...starts,port('A.AC2','A','AC')],'')).toBe('')
 expect(choosePort([],'OLD')).toBe('')
 expect(targetPorts(model,'B','ELECTRICAL',starts[0]).map(p=>p.port_id)).toEqual(['B.AC'])
 expect(targetPorts(model,'A','ELECTRICAL',starts[0])).toEqual([])
 expect(targetPorts(model,'B','COMMUNICATION',model.ports[1])).toEqual([])
})
test('direction, known voltage and duplicate constraints exclude invalid targets',()=>{
 const model=m()
 expect(sourcePorts(model,'C','CONTROL')).toEqual([])
 expect(targetPorts(model,'C','CONTROL',model.ports[5]).map(p=>p.port_id)).toEqual(['C.IN'])
 model.ports[0].attributes={voltage:400};model.ports[2].attributes={voltage:230}
 expect(targetPorts(model,'B','ELECTRICAL',model.ports[0])).toEqual([])
 model.ports[2].attributes={voltage:400}
 model.edges.push({edge_id:'E',edge_type:'ELECTRICAL',from_port_id:'B.AC',to_port_id:'A.AC',review_status:'DRAFT'})
 expect(targetPorts(model,'B','ELECTRICAL',model.ports[0])).toEqual([])
})
