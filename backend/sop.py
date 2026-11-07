"""Deterministic, source-versioned manufacturer guidance. Never controls equipment."""
from .domain import load, digest

def seed_templates():
    pack = load('lv01-demo.sop-rules.json')
    texts = {
        'RULE-BESS-PREP': ('储能设备安装资料核对', '核对厂家手册版本、设备型号及安装空间设计，记录待确认项。具体数值须来自批准资料。', 'LIVOLTEK_DEVICE'),
        'RULE-METER-COMM': ('计量通信接口核对', '核对电表与 EMS 端口、通信映射及供应商文件；不执行参数写入。', 'THIRD_PARTY_INTERFACE'),
        'RULE-ENERGIZATION-REVIEW': ('上电前资料门禁', '提交 EPC 批准设计、安全许可及检查记录供复核；本 Demo 不允许上电。', 'EPC_DOCUMENT_CHECK'),
    }
    result = []
    for rule in pack['rules']:
        title, text, scope = texts[rule['rule_id']]
        result.append({'template_id':rule['sop_template_id'], 'version':1, 'status':'DRAFT',
                       'title':title, 'instructions':text, 'scope_type':scope,
                       'source_document_ref':rule['source_doc_ref'], 'rule':rule, 'demo_only':True})
    return result

def matches(rule, m):
    w = rule['when']
    if w.get('structure_code') and w['structure_code'] != m['project']['structure_code']:
        return False
    targets = [n for n in m['nodes'] if n['node_type'] == w.get('node_type_present')]
    if w.get('node_type_present') and not targets:
        return False
    if w.get('edge_type_present'):
        pmap = {p['port_id']:p['node_id'] for p in m['ports']}
        ids = {n['node_id'] for n in targets}
        edges = [e for e in m['edges'] if e['edge_type'] == w['edge_type_present']]
        if ids:
            edges = [e for e in edges if pmap[e['from_port_id']] in ids or pmap[e['to_port_id']] in ids]
        if not edges:
            return False
    # Required parameters are readiness requirements, not grounds to omit a safety gate.
    return True

def generate(model, revision, templates):
    tasks = []
    for t in templates:
        r = t['rule']
        if t['status'] == 'REJECTED' or not matches(r, model):
            continue
        if t['scope_type'] == 'LIVOLTEK_DEVICE':
            assets = {a['asset_id']:a for a in model['device_assets']}
            if not any(n['node_type'] == r['when'].get('node_type_present') and
                       assets.get(n['device_asset_id'],{}).get('equipment_origin') == 'LIVOLTEK'
                       for n in model['nodes']):
                continue
        missing = []
        for name in r['when'].get('required_parameter_names', []):
            if not any(p['name'] == name and p.get('approved') and p.get('reference_doc') for p in model['parameters']):
                missing.append(f'approved parameter / source: {name}')
        if not t.get('source_document_ref'):
            missing.append('approved manufacturer / EPC source document')
        if t['status'] != 'APPROVED':
            missing.append('template approval')
        tasks.append({'task_id':r['rule_id'], 'template_id':t['template_id'], 'template_version':t['version'],
                      'template_snapshot':t, 'title':t['title'], 'instructions':t['instructions'],
                      'scope_type':t['scope_type'], 'task_owner':'EPC', 'execution_authority':'SIMULATION_ONLY',
                      'work_package':r['work_package'], 'risk':r['risk'], 'depends_on':r['depends_on'],
                      'evidence_requirements':r['evidence_requirements'], 'missing_inputs':missing,
                      'readiness':'BLOCKED' if r['risk'] == 'SAFETY_CRITICAL' or missing else 'DRAFT_ONLY'})
    for a in model['device_assets']:
        if a.get('equipment_origin') != 'THIRD_PARTY':
            continue
        bindings = [b for b in model.get('interface_bindings',[]) if b['asset_id'] == a['asset_id']]
        missing = []
        if not bindings or any(b['verification_status'] != 'VERIFIED' or not b.get('point_ref') for b in bindings):
            missing.append('verified interface mapping and vendor documentation')
        tasks.append({'task_id':f'INTERFACE-{a["asset_id"]}', 'title':f'第三方接口资料核对 · {a["asset_id"]}',
                      'instructions':'核对必要接口资料、信号含义及责任主体；不生成第三方设备内部安装或维修工艺。',
                      'scope_type':'THIRD_PARTY_INTERFACE', 'task_owner':a.get('responsibility_owner','EPC'),
                      'execution_authority':'SIMULATION_ONLY', 'template_id':'INTERFACE-REVIEW', 'template_version':1,
                      'work_package':'WP04', 'risk':'MEDIUM', 'depends_on':[],
                      'evidence_requirements':['vendor_document','interface_map'], 'missing_inputs':missing,
                      'readiness':'BLOCKED' if missing else 'DRAFT_ONLY'})
    for n in model['nodes']:
        if n['node_type'] not in ('LOAD','PCC'):
            continue
        tasks.append({'task_id':'BOUNDARY-'+n['node_id'], 'title':'外部系统边界核对 · '+n['name'],
                      'instructions':'依据 EPC 设计核对边界连接点、额定参数及必要测量信息；边界节点不要求设备 SN。',
                      'scope_type':'EPC_DOCUMENT_CHECK', 'task_owner':'EPC', 'execution_authority':'SIMULATION_ONLY',
                      'template_id':'BOUNDARY-REVIEW', 'template_version':1, 'work_package':'WP01', 'risk':'LOW',
                      'depends_on':[], 'evidence_requirements':['design_reference','boundary_observation'],
                      'missing_inputs':['approved EPC boundary documentation'], 'readiness':'BLOCKED'})
    ordered, remaining = [], tasks[:]
    ids = {t['task_id'] for t in tasks}
    for t in tasks:
        absent = set(t['depends_on']) - ids
        if absent:
            t['missing_inputs'].append('missing dependency: '+', '.join(sorted(absent)))
            t['readiness'] = 'BLOCKED'
    while remaining:
        ready = [t for t in remaining if not (set(t['depends_on']) & {x['task_id'] for x in remaining})]
        if not ready:
            raise ValueError('SOP dependency cycle')
        ordered.extend(ready)
        remaining = [t for t in remaining if t not in ready]
    return {'revision':revision, 'baseline_id':model['baseline']['baseline_id'], 'engineering_hash':digest(model),
            'device_master_version':model['baseline']['device_master_version'], 'rule_pack_version':'SOP-DEMO-RULES/0.1',
            'system_context_baseline':model, 'mode':'SIMULATION', 'tasks':ordered}
