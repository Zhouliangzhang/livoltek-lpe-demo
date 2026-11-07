"""SQLite transactions; immutable documents and optimistic current-version pointer."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return uuid4().hex

class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.db() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions(project TEXT, revision INTEGER, body TEXT, created TEXT,
                PRIMARY KEY(project,revision));
            CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, kind TEXT, project TEXT, body TEXT, created TEXT);
            ''')

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def projects(self):
        with self.db() as c:
            return [dict(r) for r in c.execute('SELECT * FROM projects ORDER BY id')]

    def get(self, project, revision=None):
        with self.db() as c:
            if revision is None:
                row = c.execute('SELECT revision FROM projects WHERE id=?', (project,)).fetchone()
                if not row:
                    raise KeyError(project)
                revision = row['revision']
            row = c.execute('SELECT * FROM revisions WHERE project=? AND revision=?', (project,revision)).fetchone()
            if not row:
                raise KeyError(project)
            return {'revision':revision, 'model':json.loads(row['body']), 'created':row['created']}

    def save(self, model, expected):
        project = model['project']['project_id']
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT revision FROM projects WHERE id=?', (project,)).fetchone()
            current = row['revision'] if row else 0
            if current != expected:
                raise ValueError('Revision conflict; reload the latest saved project')
            rev = current + 1
            model['baseline'].update(baseline_id=f'{project}-R{rev}', version=str(rev), status='DRAFT', content_hash=None)
            c.execute('INSERT INTO revisions VALUES(?,?,?,?)', (project,rev,json.dumps(model),now()))
            c.execute('INSERT OR REPLACE INTO projects VALUES(?,?)', (project,rev))
        return self.get(project)

    def history(self, project):
        with self.db() as c:
            return [dict(r) for r in c.execute('SELECT revision,created FROM revisions WHERE project=? ORDER BY revision DESC',(project,))]

    def add(self, kind, project, body):
        record = {'id':uid(), 'kind':kind, 'project':project, 'created':now(), **body}
        with self.db() as c:
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(record['id'],kind,project,json.dumps(record),record['created']))
        return record

    def records(self, kind, project):
        with self.db() as c:
            return [json.loads(r['body']) for r in c.execute('SELECT body FROM records WHERE kind=? AND project=? ORDER BY rowid DESC',(kind,project))]

    def record(self, id):
        with self.db() as c:
            r = c.execute('SELECT body FROM records WHERE id=?',(id,)).fetchone()
            if not r:
                raise KeyError(id)
            return json.loads(r['body'])
