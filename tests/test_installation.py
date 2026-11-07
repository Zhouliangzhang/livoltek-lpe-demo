from backend.sop import seed_templates, generate
from backend.domain import pilot

def test_installation_workflow_is_blocked_versioned_and_dependency_ordered():
    plan=generate(pilot(),1,seed_templates())
    tasks={t['task_id']:t for t in plan['tasks']}
    order=[t['task_id'] for t in plan['tasks']]
    assert 'INSTALL-POSITION' not in tasks and 'RULE-BESS-PREP' not in tasks
    for key in ['EARTH','POWER','COMMS','PREPOWER']:
        t=tasks['INSTALL-'+key]
        assert t['readiness']=='BLOCKED'
        assert len(t['installation_steps'])==3
        assert t['template_snapshot']['source_document_ref'] is None
        assert any(m.startswith('vendor installation: ') for m in t['missing_inputs'])
        assert all(order.index(d)<order.index(t['task_id']) for d in t['depends_on'])
    assert order.index('INSTALL-PREPOWER')<order.index('RULE-ENERGIZATION-REVIEW')


def test_template_upgrade_preserves_existing_versions(tmp_path):
    from backend.main import create_app
    from backend.store import Store
    path=str(tmp_path/'upgrade.db')
    db=Store(path)
    old=seed_templates()[0].copy()
    old['version']=4
    old['title']='Existing reviewed title'
    db.add('template','catalog',old)
    create_app(path)
    first=db.records('template','catalog')
    assert len(first)==8
    assert next(t for t in first if t['template_id']==old['template_id'])['version']==4
    create_app(path)
    assert len(db.records('template','catalog'))==8
