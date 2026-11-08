"""Engineering contract: original schema plus explicit semantic checks."""
import copy
import json
import hashlib
import importlib.util
import json
from .l5_settings import validate_settings
from .m1_identity import identity_errors
from .m1_strategy import STRATEGY_SCHEMA, strategy_checks
from .m1_metering import METERING_SCHEMA, metering_checks
from .m1_electrical import DRAFT_SCHEMA, electrical_errors
from .m1_network import NETWORK_SCHEMA, network_errors
from .m1_communication_settings import SETTINGS_SCHEMA, settings_checks
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'baselines'

def load(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))

spec = importlib.util.spec_from_file_location('baseline_validator', BASE / 'validate_demo.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
SCHEMA = load('engineering-model.schema.json')
# Workbench extension; preserve the vendor baseline schema unchanged.
SCHEMA['properties']['project']['properties']['system_boundary'] = json.loads((Path(__file__).with_name('m1_boundary_schema.json')).read_text(encoding='utf-8'))

SCHEMA['properties']['project']['properties']['electrical_drafts'] = DRAFT_SCHEMA

SCHEMA['properties']['project']['properties']['network_drafts'] = NETWORK_SCHEMA
SCHEMA['properties']['project']['properties']['communication_settings'] = SETTINGS_SCHEMA
SCHEMA['properties']['project']['properties']['metering_settings'] = METERING_SCHEMA
SCHEMA['properties']['project']['properties']['operating_strategies'] = STRATEGY_SCHEMA
SCHEMA['properties']['device_models']['items']['properties']['communication_templates'] = {
    'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['id', 'version', 'master_data_version', 'domain', 'reference_doc', 'status', 'values'],
        'properties': {
            **{key: {'type': 'string', 'minLength': 1} for key in ('id', 'version', 'master_data_version', 'reference_doc')},
            'domain': {'enum': ['RS485', 'ETHERNET', 'CAN']},
            'status': {'enum': ['DRAFT', 'APPROVED']},
            'values': {'type': 'object', 'additionalProperties': {'type': ['string', 'number', 'null']}}
        }
    }
}

def digest(model):
    data = copy.deepcopy(model)
    for key in ('view_layout', 'baseline', 'review_records'):
        data.pop(key, None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def validate(model):
    errors = [f'{"/".join(map(str, e.path))}: {e.message}' for e in
              Draft202012Validator(SCHEMA, format_checker=FormatChecker()).iter_errors(model)]
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': []}
    errors += legacy.semantic_errors(model) + legacy.system_semantic_errors(model) + identity_errors(model) + electrical_errors(model) + network_errors(model)
    communication_errors, warnings = settings_checks(model)
    metering_errors, metering_warnings = metering_checks(model)
    strategy_errors, strategy_warnings = strategy_checks(model)
    errors += strategy_errors
    warnings += strategy_warnings
    errors += metering_errors
    warnings += metering_warnings
    errors += communication_errors
    sets = {}
    for collection, key in [('nodes','node_id'), ('ports','port_id'), ('edges','edge_id'),
                            ('device_assets','asset_id'), ('device_models','model_id'),
                            ('parameters','parameter_id'), ('interface_bindings','binding_id'),
                            ('telemetry_bindings','binding_id'), ('test_scopes','test_id'), ('diagnostic_paths','path_id')]:
        ids = [x[key] for x in model.get(collection, [])]
        sets[collection] = set(ids)
        if len(ids) != len(set(ids)):
            errors.append(f'Duplicate ID in {collection}')
    nodes = {x['node_id']: x for x in model['nodes']}
    ports = {x['port_id']: x for x in model['ports']}
    boundary = model['project'].get('system_boundary')
    if boundary:
        domain_ids = [d['id'] for d in boundary['domains']]
        if len(domain_ids) != len(set(domain_ids)):
            errors.append('控制域编号不能重复')
        for d in boundary['domains']:
            for field, kind in [('pcc_id', 'PCC'), ('controller_id', 'EMS')]:
                if d[field] and nodes.get(d[field], {}).get('node_type') != kind:
                    errors.append(f'控制域 {d["id"]} 的 {field} 引用无效')
        if boundary['timezone'] not in ('', 'Africa/Johannesburg', 'Asia/Shanghai', 'Europe/Berlin', 'Europe/London', 'America/New_York', 'Australia/Sydney', 'UTC'):
            errors.append('项目时区无效')
    for n in nodes.values():
        engineering = n.get('attributes', {}).get('engineering')
        if engineering is None:
            continue
        if not isinstance(engineering, dict):
            errors.append('电气结构工程信息格式无效')
            continue
        if engineering.get('basis_status') != 'PENDING':
            errors.append('结构资料引用须保持待核验，不能直接标记批准')
        if engineering.get('voltage_level') not in ('LV', 'MV'):
            errors.append('结构设计电压等级无效')
        if n['node_type'] in ('FEEDER', 'BREAKER') and not str(engineering.get('circuit_id', '')).strip():
            errors.append('馈线和断路器需要回路编号')
        if n['node_type'] not in ('PCC', 'TRANSFORMER_ZONE') and not n.get('parent_node_id'):
            errors.append('电气结构需要明确所属结构')
        parent = nodes.get(n.get('parent_node_id'))
        if parent and (parent.get('device_asset_id') or parent['node_type'] not in ('PCC','TRANSFORMER_ZONE','TRANSFORMER','LV_BUS','MV_BUS','FEEDER','BREAKER')):
            errors.append('电气结构必须归属有效的电气结构对象')
    for node in nodes.values():
        seen = set()
        current = node
        while current:
            if current['node_id'] in seen:
                errors.append(f'Parent cycle: {node["node_id"]}')
                break
            seen.add(current['node_id'])
            current = nodes.get(current['parent_node_id'])
    for edge in model['edges']:
        a, b = ports.get(edge['from_port_id']), ports.get(edge['to_port_id'])
        if not a or not b:
            continue
        if a['node_id'] == b['node_id']:
            errors.append(f'Self connection: {edge["edge_id"]}')
        if edge['edge_type'] == 'COMMUNICATION' and a['domain'] != b['domain']:
            errors.append(f'Protocol port mismatch: {edge["edge_id"]}; model a gateway explicitly')
        if edge['edge_type'] == 'CONTROL' and (a['role'] == 'IN' or b['role'] == 'OUT'):
            errors.append(f'Control direction mismatch: {edge["edge_id"]}')
        if edge['edge_type'] == 'ELECTRICAL':
            for key in ('voltage', 'phases'):
                av, bv = a.get('attributes', {}).get(key), b.get('attributes', {}).get(key)
                if av is not None and bv is not None and av != bv:
                    errors.append(f'{key} mismatch: {edge["edge_id"]}')
    owners = {'NODE': sets['nodes'], 'PORT': sets['ports'], 'EDGE': sets['edges'],
              'ASSET': sets['device_assets'], 'PROJECT': {model['project']['project_id']}}
    for p in model['parameters']:
        if p['owner_id'] not in owners[p['scope']]:
            errors.append(f'Unknown parameter owner: {p["parameter_id"]}')
        if p['criticality'] == 'SAFETY_CRITICAL' and not p['approved']:
            warnings.append(f'Missing approved parameter: {p["name"]}')
    for b in model['telemetry_bindings']:
        if b['target_id'] not in owners[b['target_type']]:
            errors.append(f'Unknown telemetry target: {b["binding_id"]}')
    for a in model['device_assets']:
        if a['sn_status'] == 'VERIFIED' and not a['serial_number']:
            errors.append(f'Verified serial number missing: {a["asset_id"]}')
    for b in model.get('interface_bindings', []):
        if b['verification_status'] != 'VERIFIED' or not b.get('point_ref'):
            warnings.append(f'Unverified interface: {b["binding_id"]}')
    for key in model['view_layout']['positions']:
        if key not in nodes:
            errors.append(f'Layout references missing node: {key}')
    if model['baseline']['status'] != 'DRAFT':
        errors.append('Demo model writes must remain DRAFT; review decisions are separate records')
    setting_errors, setting_warnings = validate_settings(model)
    errors += setting_errors
    warnings += setting_warnings
    return {'valid': not errors, 'errors': list(dict.fromkeys(errors)), 'warnings': warnings}

def pilot():
    m = load('lv01-mixed-vendors.engineering-model.json')
    positions = {'PCC_01': (40,180), 'LV_BUS_01': (300,180), 'PV_01': (40,30),
                 'BREAKER_PV': (300,30), 'BESS_01': (40,350), 'BREAKER_BESS': (300,350),
                 'LOAD_01': (560,180), 'EMS_01': (820,180), 'METER_01': (560,350), 'PV_TP_01': (560,30)}
    m['view_layout']['positions'] = {k: {'x':v[0], 'y':v[1]} for k,v in positions.items()}
    m['view_layout']['layer_visibility'] = dict.fromkeys(['ELECTRICAL','COMMUNICATION','CONTROL'], True)
    for a in m['device_assets']:
        own = a['asset_id'] in ('ASSET_BESS_01', 'ASSET_EMS_01')
        a.setdefault('equipment_origin', 'LIVOLTEK' if own else 'THIRD_PARTY')
        a.setdefault('modeling_level', 'L1_FULL' if own else 'L2_INTERFACE')
        a.setdefault('responsibility_owner', 'EPC installation; manufacturer product support')
        a.setdefault('authorization', {'read_allowed':False, 'write_allowed':False, 'test_execution_allowed':False})
    for d in m['device_models']:
        if d['model_id'] in ('MODEL_BESS_DEMO_125_261','MODEL_EMS_DEMO'):
            d['manufacturer'] = 'LIVOLTEK (illustrative demo)'
    return m
