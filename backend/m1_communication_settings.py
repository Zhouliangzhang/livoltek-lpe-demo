"""Communication plans are environment scoped; saving never writes a controller."""
from ipaddress import IPv4Address, IPv4Network

SHARED = {'RS485': {'protocol', 'baud_rate', 'data_bits', 'parity', 'stop_bits'}, 'CAN': {'can_bitrate', 'can_protocol'}, 'ETHERNET': set()}
DEVICE = {'RS485': {'role', 'address'}, 'CAN': {'address'}, 'ETHERNET': {'protocol', 'tcp_port', 'ip_address', 'subnet_mask', 'gateway'}}
STR = {'type': 'string', 'maxLength': 10000}
VALUES = {'type': 'object', 'additionalProperties': STR}
ROW = {'type': 'object', 'additionalProperties': False,
       'required': ['id', 'domain', 'ports', 'signature', 'shared', 'devices', 'reference', 'status'],
       'properties': {'id': STR, 'domain': {'enum': list(SHARED)}, 'ports': {'type': 'array', 'items': STR, 'uniqueItems': True}, 'signature': STR, 'shared': VALUES, 'devices': {'type': 'object', 'additionalProperties': VALUES}, 'reference': STR, 'status': {'const': 'PENDING'}}}
SETTINGS_SCHEMA = {'type': 'object', 'additionalProperties': False, 'properties': {env: {'type': 'array', 'items': ROW} for env in ('OFFLINE', 'SIMULATION', 'REAL')}}

def settings_checks(model):
    errors, warnings = [], []
    ports = {p['port_id']: p for p in model['ports']}
    for env, rows in model['project'].get('communication_settings', {}).items():
        if len({r['id'] for r in rows}) != len(rows):
            errors.append(f'{env}: 同一总线设置重复')
        for row in rows:
            domain, shared = row['domain'], row['shared']
            if row['id'] != '|'.join(sorted(row['ports'])):
                errors.append('总线标识与端口集合不一致')
            if set(shared) - SHARED[domain]:
                errors.append('通信路径不适用这些公共参数')
            for key in ('baud_rate', 'can_bitrate'):
                if shared.get(key) and (not shared[key].isdigit() or int(shared[key]) <= 0):
                    errors.append('波特率 / 比特率必须为正整数，适用值待厂家确认')
            for key, choices in {'protocol': ('MODBUS_RTU', 'VENDOR'), 'parity': ('NONE', 'EVEN', 'ODD'), 'stop_bits': ('1', '1.5', '2'), 'data_bits': ('7', '8')}.items():
                if shared.get(key) and shared[key] not in choices:
                    errors.append(f'公共参数 {key} 无效')
            seen = set()
            for pid, values in row['devices'].items():
                if pid not in row['ports'] or pid not in ports or ports[pid]['domain'] != domain:
                    errors.append(f'{pid}: 设备接口与通信网络不匹配')
                if set(values) - DEVICE[domain]:
                    errors.append(f'{pid}: 设备参数冲突；公共参数必须在总线统一设置')
                role = values.get('role')
                if role and role not in ('MASTER', 'SLAVE', 'PEER'):
                    errors.append(f'{pid}: 接口角色无效')
                address = values.get('ip_address' if domain == 'ETHERNET' else 'address', '').strip()
                if domain != 'ETHERNET' and address.isdigit():
                    address = str(int(address))
                if address:
                    if address in seen:
                        errors.append(f'{pid}: 地址重复 {address}')
                    seen.add(address)
                if domain == 'RS485':
                    if role == 'MASTER' and address:
                        errors.append(f'{pid}: 主站不能填写从站地址')
                    if shared.get('protocol') == 'MODBUS_RTU' and address and (not address.isdigit() or not 1 <= int(address) <= 247):
                        errors.append(f'{pid}: Modbus 从站地址须为 1–247')
                if domain == 'ETHERNET':
                    if values.get('protocol') and values['protocol'] not in ('MODBUS_TCP', 'VENDOR'):
                        errors.append(f'{pid}: 以太网应用协议无效')
                    tcp = values.get('tcp_port', '')
                    if tcp and (not tcp.isdigit() or not 1 <= int(tcp) <= 65535):
                        errors.append(f'{pid}: 服务端口须为 1–65535')
                    for key in ('ip_address', 'subnet_mask', 'gateway'):
                        if values.get(key):
                            try:
                                IPv4Address(values[key])
                                if key == 'subnet_mask':
                                    IPv4Network('0.0.0.0/' + values[key])
                            except ValueError:
                                errors.append(f'{pid}: {key} 格式无效')
            if domain == 'RS485' and shared.get('protocol') == 'MODBUS_RTU' and sum(d.get('role') == 'MASTER' for d in row['devices'].values()) > 1:
                errors.append('同一 Modbus RTU 总线存在多个主站')
            warnings.append(f'{env} 通信计划 {row["id"]}: 厂家依据与现场读回待确认；不代表通信验证通过')
    return errors, warnings
