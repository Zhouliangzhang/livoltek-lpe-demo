import copy
import math
import os
import time
from pathlib import Path
from typing import Any, Literal
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from jsonschema import Draft202012Validator
from .domain import ROOT, SCHEMA, pilot, validate, digest, load
from .store import Store, now
from .sop import seed_templates, generate
from .installation_tracking import register_tracking
from .workbench import register_workbench
from .fleet import register_fleet
from .commissioning import register_commissioning
from .checklist import register_checklist, checklist, VERSION as CHECKLIST_VERSION

class Save(BaseModel):
    model: dict[str, Any]
    expected_revision: int = Field(ge=0)

class Review(BaseModel):
    target_id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    comment: str = Field(min_length=1)
    decision: Literal['COMMENT','UNDER_REVIEW','APPROVED','REJECTED'] = 'COMMENT'
    revision: int = Field(ge=1)

class TemplateEdit(BaseModel):
    expected_version: int
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    source_document_ref: str | None = None
    status: Literal['DRAFT','UNDER_REVIEW','APPROVED','REJECTED']
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    rule: dict[str, Any] | None = None

class Evidence(BaseModel):
    task_id: str
    result: Literal['PASS','FAIL','BLOCKED']
    reviewer: str = Field(min_length=1)
    evidence: dict[str,str]
    note: str = Field(min_length=1)

def flow_state(value, quality, timestamp, max_age, direction='FROM_TO', online=True, clock=None):
    age = (time.time() if clock is None else clock) - timestamp
    valid = online and quality == 'GOOD' and 0 <= age <= max_age and value is not None and math.isfinite(value)
    if direction not in ('FROM_TO','TO_FROM'):
        valid = False
    signed = value * (-1 if direction == 'TO_FROM' else 1) if valid else None
    return {'value':value if valid else None, 'available':valid, 'animate':valid and abs(signed) > 0.01,
            'reverse':valid and signed < 0, 'quality':quality, 'timestamp':timestamp, 'age_seconds':age}

def create_app(db_path=None):
    app = FastAPI(title='LIVOLTEK M1 + M2 — Simulation only')
    db = Store(db_path or os.environ.get('LPE_DB', str(ROOT / 'demo.db')))
    if not db.projects():
        db.save(pilot(), 0)
    existing_templates = {t['template_id'] for t in db.records('template', 'catalog')}
    for t in seed_templates():
        if t['template_id'] not in existing_templates:
            db.add('template','catalog',t)
    app.state.store = db
    register_tracking(app,db)
    register_checklist(app,db)
    register_commissioning(app,db)
    register_workbench(app,db)
    register_fleet(app,db)

    def project(id):
        try:
            return db.get(id)
        except KeyError:
            raise HTTPException(404, 'Project not found')

    def record(id, kind):
        try:
            r = db.record(id)
        except KeyError:
            raise HTTPException(404, 'Record not found')
        if r['kind'] != kind:
            raise HTTPException(404, 'Record type mismatch')
        return r

    def templates():
        latest = {}
        for t in db.records('template','catalog'):
            latest.setdefault(t['template_id'],t)
        return list(latest.values())

    @app.get('/api/health')
    def health():
        return {'status':'ok','mode':'SIMULATION','production_enabled':False}

    @app.get('/api/schema')
    def schema():
        return SCHEMA

    @app.get('/api/projects')
    def projects():
        return [{'id':p['id'],'revision':p['revision'],'name':db.get(p['id'])['model']['project']['name']} for p in db.projects()]

    @app.post('/api/validate')
    def check(model: dict):
        return validate(model)

    @app.get('/api/projects/{id}')
    def get_project(id: str, revision: int | None = None):
        try:
            return db.get(id, revision)
        except KeyError:
            raise HTTPException(404, 'Project/revision not found')

    @app.post('/api/projects')
    def save(body: Save):
        result = validate(body.model)
        if not result['valid']:
            raise HTTPException(422,result)
        try:
            return db.save(copy.deepcopy(body.model),body.expected_revision)
        except ValueError as e:
            raise HTTPException(409,str(e))

    @app.get('/api/projects/{id}/history')
    def history(id: str):
        project(id)
        return db.history(id)

    @app.get('/api/templates')
    def list_templates():
        return templates()

    @app.get('/api/templates/history')
    def template_history():
        return db.records('template','catalog')

    @app.post('/api/templates/{id}')
    def edit_template(id: str, body: TemplateEdit):
        old = next((t for t in templates() if t['template_id'] == id),None)
        if not old:
            raise HTTPException(404,'Template not found')
        if old['version'] != body.expected_version:
            raise HTTPException(409,'Template version conflict')
        if body.status == 'APPROVED' and not body.source_document_ref:
            raise HTTPException(422,'Approval requires a source reference; this remains demo-only')
        if body.rule is not None:
            rule_schema = load('sop-rule-pack.schema.json')['properties']['rules']['items']
            errors = [e.message for e in Draft202012Validator(rule_schema).iter_errors(body.rule)]
            if errors:
                raise HTTPException(422,errors)
            if body.rule['rule_id'] != old['rule']['rule_id'] or body.rule['sop_template_id'] != id:
                raise HTTPException(422,'Stable rule/template IDs cannot change')
        new = {k:v for k,v in old.items() if k not in ('id','kind','created','project')}
        new.update(body.model_dump(exclude={'expected_version','rule'}), version=old['version']+1)
        if body.rule is not None:
            new['rule'] = body.rule
        return db.add('template','catalog',new)

    @app.post('/api/projects/{id}/plans')
    def plan(id: str):
        p = project(id)
        result = validate(p['model'])
        if not result['valid']:
            raise HTTPException(422,result)
        try:
            return db.add('plan',id,{**generate(p['model'],p['revision'],templates()), 'checklist_items':checklist(p['model']), 'checklist_version':CHECKLIST_VERSION})
        except ValueError as e:
            raise HTTPException(422,str(e))

    @app.get('/api/projects/{id}/plans')
    def plans(id: str):
        p = project(id)
        return [{**r,'stale':r['engineering_hash'] != digest(p['model'])} for r in db.records('plan',id)]

    @app.post('/api/plans/{id}/publish')
    def publish(id: str):
        record(id,'plan')
        raise HTTPException(403,'Production release disabled: demo templates, permits and identity are not certified')

    @app.post('/api/plans/{id}/evidence')
    def evidence(id: str, body: Evidence):
        plan = record(id,'plan')
        current = project(plan['project'])
        if digest(current['model']) != plan['engineering_hash']:
            raise HTTPException(409,'Plan is stale; regenerate before recording new results')
        task = next((t for t in plan['tasks'] if t['task_id'] == body.task_id),None)
        if not task:
            raise HTTPException(404,'Task not found')
        if body.result == 'PASS':
            if task['readiness'] == 'BLOCKED':
                raise HTTPException(409,'Blocked tasks cannot pass')
            if any(not body.evidence.get(k,'').strip() for k in task['evidence_requirements']):
                raise HTTPException(422,'Required evidence missing')
            latest = {}
            for e in db.records('evidence',id):
                latest.setdefault(e['task_id'],e['result'])
            if any(latest.get(d) != 'PASS' for d in task['depends_on']):
                raise HTTPException(409,'Dependencies have not passed')
        return db.add('evidence',id,{**body.model_dump(),'mode':'SIMULATION'})

    @app.get('/api/plans/{id}/evidence')
    def evidence_list(id: str):
        record(id,'plan')
        return db.records('evidence',id)

    @app.post('/api/projects/{id}/reviews')
    def review(id: str, body: Review):
        p = project(id)
        if p['revision'] != body.revision:
            raise HTTPException(409,'Review must reference current saved revision')
        m = p['model']
        targets = {m['baseline']['baseline_id'],id}
        for key, field in [('nodes','node_id'),('ports','port_id'),('edges','edge_id'),('device_assets','asset_id'),('parameters','parameter_id')]:
            targets.update(x[field] for x in m[key])
        targets.update(t['template_id'] for t in templates())
        for plan in db.records('plan',id):
            targets.update(t['task_id'] for t in plan['tasks'])
        if body.target_id not in targets:
            raise HTTPException(422,'Unknown review target')
        return db.add('review',id,{**body.model_dump(),'mode':'SIMULATION','snapshot_hash':digest(m)})

    @app.get('/api/projects/{id}/reviews')
    def reviews(id: str):
        project(id)
        return db.records('review',id)

    @app.get('/api/projects/{id}/telemetry')
    def telemetry(id: str, scenario: Literal['normal','reverse','stale','missing','bad'] = 'normal'):
        p = project(id)
        timestamp = time.time() - (120 if scenario == 'stale' else 0)
        flows = {}
        edges = {e['edge_id']: e for e in p['model']['edges']}
        for b in p['model']['telemetry_bindings']:
            if b['target_type'] != 'EDGE' or b['measurement'] != 'ACTIVE_POWER':
                continue
            value = None if scenario == 'missing' else (-1 if scenario == 'reverse' else 1)*(24+round(4*math.sin(time.time()/8),1))
            if b.get('point_ref', '').startswith('SIM.CI20.'):
                profile = edges.get(b['target_id'], {}).get('attributes', {}).get('simulation_profile', {})
                candidate = profile.get('reverse' if scenario == 'reverse' else 'normal')
                value = candidate if scenario != 'missing' and type(candidate) in (int, float) and math.isfinite(candidate) else None
            flows[b['target_id']] = flow_state(value,'BAD' if scenario == 'bad' else 'GOOD',timestamp,b['max_age_seconds'],b['positive_direction'])
        return {'mode':'SIMULATION','generated_at':now(),'flows':flows}

    dist = ROOT / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/',StaticFiles(directory=dist,html=True),name='ui')
    return app

app = create_app()
