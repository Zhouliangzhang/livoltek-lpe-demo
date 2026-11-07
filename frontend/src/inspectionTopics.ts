import type {Model} from './types'
import type {CheckItem} from './checklistGroups'

export const inspectionSteps = [
 ['E','电气点检','确认接口、回路与保护接地'],
 ['C','通信点检','从零馈计量到每台设备的数据连接'],
 ['K','控制点检','核对控制对象与策略配置，不下发指令'],
]
export const inspectionTopics = [
 ['E01','主设备电气接口与回路','光伏、储能的电气接口与回路对应'],
 ['E02','保护接地接口','设备 PE 接口及适用依据'],
 ['E03','并网点计量接口','计量位置、CT 方向与信号接口'],
 ['E04','外部配电与保护接口','主配电、汇流与外部保护接口'],
 ['C01','零馈表与 iEMS 通信','计量数据到主控制器的连接'],
 ['C02','光伏通信总线','公共总线与各逆变器的通信支路'],
 ['C03','储能通信网络','网络设备与各储能单元的连接'],
 ['C04','iEMS 接入与网络边界','单台 iEMS 的网络接入及公共接口'],
 ['K01','主控权限与对象映射','指令目标、设备身份与反馈对象'],
 ['K02','零馈控制配置','计量反馈、目标值及失联处理'],
 ['K03','光伏限功率配置','功率基准、指令来源与反馈单位'],
 ['K04','储能运行配置','充放电方向、SOC 边界与模式'],
]

// Presentation mapping only: keep immutable checklist IDs and existing evidence.
export function topicFor(item:CheckItem,model:Model):string {
 const nodes=item.node_ids.map(id=>model.nodes.find(n=>n.node_id===id))
 const has=(type:string)=>nodes.some(n=>n?.node_type===type)
 if(item.id.endsWith(':earth'))return 'E02'
 if(item.id.endsWith(':metering'))return 'E03'
 if(item.stage==='CONTROL'){
  if(item.id.endsWith(':zero-export'))return 'K02'
  if(item.title==='控制对象映射')return 'K01'
  if(has('PV_INVERTER'))return 'K03'
  if(has('BESS'))return 'K04'
  return 'K01'
 }
 const edge=model.edges.find(e=>e.edge_id===item.target_id)
 const ports=model.ports.filter(p=>[edge?.from_port_id,edge?.to_port_id].includes(p.port_id))
 if(item.stage==='COMMUNICATION'){
  if(ports.some(p=>p.domain==='ANALOG_IO'))return 'E03'
  if(has('METER'))return 'C01'
  if(has('PV_INVERTER')||item.detail.includes('PV_RS485'))return 'C02'
  if(has('BESS'))return 'C03'
  return 'C04'
 }
 if(has('PV_INVERTER')||has('BESS'))return 'E01'
 if(has('METER'))return 'E03'
 return 'E04'
}

export function objectName(item:CheckItem,model:Model){
 const device=item.node_ids.map(id=>model.nodes.find(n=>n.node_id===id)).find(n=>['PV_INVERTER','BESS'].includes(n?.node_type||''))
 return device?.name||item.name
}
