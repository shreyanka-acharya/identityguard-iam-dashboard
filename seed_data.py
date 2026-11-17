"""Deterministic synthetic enterprise dataset for local IAM demonstrations."""
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from iam import connect, initialize

DEPARTMENTS = ['Engineering','IT','Finance','HR','Sales','Marketing','Operations','Legal','Security','Customer Success']
APPLICATIONS = [
    ('Microsoft 365','Productivity','Standard'),
    ('Salesforce','CRM','Standard'),
    ('Workday','HRIS','Sensitive'),
    ('ServiceNow','ITSM','Sensitive'),
    ('GitHub Enterprise','Developer','Sensitive'),
    ('AWS Console','Cloud','Privileged'),
    ('Snowflake','Analytics','Sensitive'),
    ('Jira','Collaboration','Standard'),
    ('Slack','Communication','Standard'),
    ('CyberArk','PAM','Privileged'),
    ('Okta Admin','Identity','Privileged'),
    ('Power BI','Analytics','Standard'),
]
FIRST = ['Ava','Noah','Mia','Liam','Sophia','Ethan','Isla','Oliver','Aria','Lucas','Amara','Leo','Zoe','Elijah','Nora','Kai','Priya','Maya','Theo','Iris','Jade','Aiden','Ella','Milo','Riya']
LAST = ['Patel','Chen','Rivera','Brooks','Kim','Singh','Garcia','Nguyen','Shah','Brown','Williams','Lee','Davis','Johnson','Khan','Martin','Wilson','Taylor','Ali','Lopez']
ROLES = ['Viewer','Employee','Manager','Administrator']


def setup_schema(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS applications(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
      category TEXT NOT NULL, sensitivity TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS entitlements(
      id INTEGER PRIMARY KEY, identity_id INTEGER NOT NULL REFERENCES identities(id),
      application_id INTEGER NOT NULL REFERENCES applications(id),
      access_level TEXT NOT NULL, granted_at TEXT NOT NULL,
      last_used_at TEXT, UNIQUE(identity_id,application_id));
    CREATE TABLE IF NOT EXISTS access_requests(
      id INTEGER PRIMARY KEY, identity_id INTEGER NOT NULL REFERENCES identities(id),
      application_id INTEGER NOT NULL REFERENCES applications(id),
      requested_level TEXT NOT NULL, status TEXT NOT NULL,
      requested_at TEXT NOT NULL, decided_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_entitlements_identity ON entitlements(identity_id);
    CREATE INDEX IF NOT EXISTS idx_requests_status ON access_requests(status);
    """)


def seed_enterprise(path=None, count=500):
    """Add synthetic demo identities only once; preserve existing local data."""
    if not 1 <= count <= 5000:
        raise ValueError('count must be between 1 and 5000')
    if path is None:
        from iam import DB_PATH
        path = DB_PATH
    initialize(path)
    rng = random.Random(20261117)
    now = datetime.now(timezone.utc)
    with connect(path) as db:
        setup_schema(db)
        for name, category, sensitivity in APPLICATIONS:
            db.execute('INSERT OR IGNORE INTO applications(name,category,sensitivity) VALUES (?,?,?)',
                       (name,category,sensitivity))
        existing = db.execute("SELECT 1 FROM identities WHERE email LIKE '%@identityguard.example' LIMIT 1").fetchone()
        if existing:
            return False
        app_ids = {r['name']:r['id'] for r in db.execute('SELECT id,name FROM applications')}
        for i in range(count):
            first = FIRST[i % len(FIRST)]
            last = LAST[(i * 7 + i // len(FIRST)) % len(LAST)]
            department = DEPARTMENTS[i % len(DEPARTMENTS)]
            role = rng.choices(ROLES,weights=[8,70,19,3])[0]
            status = rng.choices(['Active','Disabled'],weights=[92,8])[0]
            created = now - timedelta(days=rng.randint(30,1400))
            email = f'{first.lower()}.{last.lower()}.{i+1:04d}@identityguard.example'
            cur = db.execute('INSERT INTO identities(name,email,department,role,status,created_at) VALUES (?,?,?,?,?,?)',
                             (f'{first} {last}',email,department,role,status,created.isoformat()))
            identity_id = cur.lastrowid
            apps = {'Microsoft 365','Slack'}
            if department in ('Engineering','IT','Security'): apps.add('GitHub Enterprise')
            if department == 'Sales': apps.add('Salesforce')
            if department == 'HR': apps.add('Workday')
            if department in ('Finance','Operations'): apps.add('Power BI')
            apps.update(rng.sample([a[0] for a in APPLICATIONS],rng.randint(0,3)))
            for app in sorted(apps):
                level = 'Admin' if (role=='Administrator' and rng.random()<0.45) else rng.choice(['Read','Standard','Editor'])
                last_used = None if rng.random()<0.13 else (now-timedelta(days=rng.randint(1,180))).isoformat()
                db.execute('INSERT INTO entitlements(identity_id,application_id,access_level,granted_at,last_used_at) VALUES (?,?,?,?,?)',
                           (identity_id,app_ids[app],level,(created+timedelta(days=1)).isoformat(),last_used))
            if i % 4 == 0:
                app = rng.choice(APPLICATIONS)[0]
                request_date = now - timedelta(days=rng.randint(0,90))
                state = rng.choices(['Pending','Approved','Rejected'],weights=[35,45,20])[0]
                decided = None if state=='Pending' else (request_date+timedelta(days=2)).isoformat()
                db.execute('INSERT INTO access_requests(identity_id,application_id,requested_level,status,requested_at,decided_at) VALUES (?,?,?,?,?,?)',
                           (identity_id,app_ids[app],'Standard',state,request_date.isoformat(),decided))
    return True


def enterprise_summary(path=None):
    if path is None:
        from iam import DB_PATH
        path = DB_PATH
    with connect(path) as db:
        setup_schema(db)
        def scalar(sql):
            return db.execute(sql).fetchone()[0]
        return {
            'applications':scalar('SELECT COUNT(*) FROM applications'),
            'assignments':scalar('SELECT COUNT(*) FROM entitlements'),
            'pending':scalar("SELECT COUNT(*) FROM access_requests WHERE status='Pending'"),
            'orphaned_access':scalar("""SELECT COUNT(*) FROM entitlements e
                 JOIN identities i ON i.id=e.identity_id WHERE i.status='Disabled'"""),
            'stale_access':scalar("""SELECT COUNT(*) FROM entitlements e
                 JOIN identities i ON i.id=e.identity_id
                 WHERE i.status='Active' AND (e.last_used_at IS NULL
                 OR julianday('now')-julianday(e.last_used_at)>90)"""),
        }


def enterprise_table(table, path=None):
    if path is None:
        from iam import DB_PATH
        path = DB_PATH
    queries = {
        'entitlements':"""SELECT i.name AS employee,i.department,i.status AS identity_status,
           a.name AS application,a.sensitivity,e.access_level,e.last_used_at
           FROM entitlements e JOIN identities i ON e.identity_id=i.id
           JOIN applications a ON e.application_id=a.id ORDER BY i.id,e.id""",
        'requests':"""SELECT r.id,i.name AS employee,i.department,a.name AS application,
           r.requested_level,r.status,r.requested_at
           FROM access_requests r JOIN identities i ON r.identity_id=i.id
           JOIN applications a ON r.application_id=a.id ORDER BY r.id DESC""",
        'applications':'SELECT name,category,sensitivity FROM applications ORDER BY name',
    }
    if table not in queries:
        raise ValueError('Unknown table')
    with connect(path) as db:
        setup_schema(db)
        return [dict(r) for r in db.execute(queries[table])]


if __name__ == '__main__':
    created = seed_enterprise()
    print('Seeded synthetic enterprise data.' if created else 'Synthetic enterprise data already present; no changes made.')
    print(enterprise_summary())
