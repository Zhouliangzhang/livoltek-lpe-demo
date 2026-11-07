"""Draft contract validation for M1/M2 demo; pip install jsonschema."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

def semantic_errors(data):
    errors=[]
    nodes={x['node_id']:x for x in data['nodes']}
    ports={x['port_id']:x for x in data['ports']}
    assets={x['asset_id']:x for x in data['device_assets']}
    models={x['model_id']:x for x in data['device_models']}
    for typ,items,key in [('node',data['nodes'],'node_id'),('port',data['ports'],'port_id'),('edge',data['edges'],'edge_id'),('asset',data['device_assets'],'asset_id')]:
        ids=[x[key] for x in items]
        if len(ids)!=len(set(ids)):errors.append(f'Duplicate {typ} ID')
    for port in data['ports']:
        if port['node_id'] not in nodes:errors.append(f"Port references missing node {port['port_id']}")
    for edge in data['edges']:
        a=ports.get(edge['from_port_id']);b=ports.get(edge['to_port_id'])
        if not a or not b:errors.append(f"Edge references missing port {edge['edge_id']}");continue
        if edge['edge_type']=='ELECTRICAL' and (a['domain']!=b['domain'] or a['domain'] not in ('AC','DC')):errors.append(f"Electrical domain conflict {edge['edge_id']}")
        if edge['edge_type']=='COMMUNICATION' and (a['domain'] not in ('ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO') or b['domain'] not in ('ETHERNET','RS485','CAN','DIGITAL_IO','ANALOG_IO')):errors.append(f"Communication domain conflict {edge['edge_id']}")
        if edge['edge_type']=='CONTROL' and (a['domain']!='CONTROL_LOGICAL' or b['domain']!='CONTROL_LOGICAL'):errors.append(f"Control domain conflict {edge['edge_id']}")
    for node in data['nodes']:
        if node['device_asset_id'] and node['device_asset_id'] not in assets:errors.append(f"Node missing asset {node['node_id']}")
        if node['parent_node_id'] and node['parent_node_id'] not in nodes:errors.append(f"Node missing parent {node['node_id']}")
    for asset in assets.values():
        if asset['model_id'] not in models:errors.append(f"Asset missing model {asset['asset_id']}")
    sn=[x['serial_number'] for x in assets.values() if x['serial_number']]
    if len(sn)!=len(set(sn)):errors.append('Duplicate serial number')
    if data['project']['voltage_level']=='LV' and not data['project']['structure_code'].startswith('LV-'):errors.append('Voltage/structure mismatch')
    if data['baseline']['status']=='PUBLISHED' and (not data['baseline']['approved_by'] or not data['baseline']['content_hash']):errors.append('Published baseline missing approval/hash')
    return errors


def system_semantic_errors(d):
    errors=[]
    assets={x['asset_id']: x for x in d.get('device_assets',[])}
    bindings={x['binding_id']:x for x in d.get('interface_bindings',[])}
    for b in bindings.values():
        if b['asset_id'] not in assets:errors.append('Interface binding unknown asset: '+b['binding_id'])
        if b['direction'] in ('WRITE','READ_WRITE') and not b.get('authorization_ref'):
            errors.append('Writable interface lacking authorization: '+b['binding_id'])
    for a in assets.values():
        z=a.get('authorization',{})
        if (z.get('write_allowed') or z.get('test_execution_allowed')) and not z.get('approval_ref'):
            errors.append('Device authorized for write/test without approval: '+a['asset_id'])
    for t in d.get('test_scopes',[]):
        for x in t['targets']:
            if x not in assets:errors.append('Test unknown asset: '+x)
        for x in t.get('required_signals',[]):
            if x not in bindings:errors.append('Test unknown interface binding: '+x)
    for t in d.get('diagnostic_paths',[]):
        for x in t['target_assets']:
            if x not in assets:errors.append('Diagnostic unknown asset: '+x)
        for x in t.get('required_signals',[]):
            if x not in bindings:errors.append('Diagnostic unknown binding: '+x)
    return errors

if __name__=='__main__':
    samples=['lv01-demo.engineering-model.json','lv01-mixed-vendors.engineering-model.json']
    for filename in samples:
        d=load(filename)
        Draft202012Validator(load('engineering-model.schema.json'),format_checker=FormatChecker()).validate(d)
        issues=semantic_errors(d)
        issues.extend(system_semantic_errors(d))
        if issues: raise SystemExit(filename + ': ' + '; '.join(issues))
    Draft202012Validator(load('sop-rule-pack.schema.json')).validate(load('lv01-demo.sop-rules.json'))
    print('Schema checks for legacy and mixed-vendor samples: PASS')
    print('Semantic checks: PASS')
    print('Publication readiness: BLOCKED (draft data, missing approved engineering inputs and SOPs)')

