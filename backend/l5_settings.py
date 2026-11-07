"""Validate the typed L5 extension inside the baseline's open node.attributes field.
The catalogue is a candidate checklist, never an approved manufacturer specification.
"""
import ipaddress
import json
import math
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'config/l5-catalog.json').read_text(encoding='utf-8'))
DEFINITIONS = {p['key']: p for p in CATALOG['parameters']}

def applicable(model, node):
    domains = {p['domain'] for p in model['ports'] if p['node_id'] == node['node_id']}
    modes, features = set(model['project']['operation_modes']), set(model['project']['energy_features'])
    return [d for d in DEFINITIONS.values()
            if (not d['node_types'] or node['node_type'] in d['node_types'])
            and (not d['domains'] or domains.intersection(d['domains']))
            and (not d['modes'] or modes.intersection(d['modes']))
            and (not d['features'] or features.intersection(d['features']))]

def validate_settings(model):
    errors, warnings = [], []
    assets = {a['asset_id']: a for a in model['device_assets']}
    models = {d['model_id']: d for d in model['device_models']}
    required = {'planned','actual','reference_doc','model_id','master_data_version','template_version'}
    for node in model['nodes']:
        asset = assets.get(node['device_asset_id'])
        device = models.get(asset['model_id']) if asset else None
        records = node.get('attributes', {}).get('l5_settings', {})
        if not isinstance(records, dict):
            errors.append(f'L5 {node["node_id"]}: settings must be an object')
            continue
        active = {d['key'] for d in applicable(model, node)} if device else set()
        if active:
            warnings.append(f'L5 {node["node_id"]}: {len(active)} candidate settings require model-specific manufacturer confirmation')
        for key, entry in records.items():
            path = f'L5 {node["node_id"]}.{key}'
            if key not in DEFINITIONS or not isinstance(entry, dict) or set(entry) != required:
                errors.append(f'{path}: invalid setting record')
                continue
            if not all(isinstance(entry[k], str) for k in required - {'planned','actual'}):
                errors.append(f'{path}: invalid provenance')
                continue
            if key not in active:
                warnings.append(f'{path}: no longer applicable; retained for history')
            if not device or (entry['model_id'],entry['master_data_version'],entry['template_version']) != (device['model_id'],device['master_data_version'],CATALOG['version']):
                warnings.append(f'{path}: model/template version changed; reconfirm before use')
            d = DEFINITIONS[key]
            for phase in ('planned','actual'):
                value = entry[phase]
                if value is None or value == '':
                    continue
                if d['type'] in ('number','integer'):
                    valid = type(value) in (int,float) and math.isfinite(value)
                    valid = valid and (d['type'] != 'integer' or value == int(value))
                    valid = valid and ('min' not in d or value >= d['min']) and ('max' not in d or value <= d['max'])
                else:
                    valid = isinstance(value,str) and len(value) <= 2000
                    if valid and d['type'] == 'ipv4':
                        try: ipaddress.IPv4Address(value)
                        except ipaddress.AddressValueError: valid = False
                if not valid:
                    errors.append(f'{path}.{phase}: invalid {d["type"]} value')
        for phase in ('planned','actual'):
            low = records.get('soc_min', {}).get(phase) if isinstance(records.get('soc_min', {}), dict) else None
            high = records.get('soc_max', {}).get(phase) if isinstance(records.get('soc_max', {}), dict) else None
            if type(low) in (int,float) and type(high) in (int,float) and low > high:
                errors.append(f'L5 {node["node_id"]}.{phase}: SOC minimum exceeds maximum')
    return errors,warnings
