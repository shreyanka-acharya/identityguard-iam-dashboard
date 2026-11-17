"""Local demo IAM operations. Not a production authorization system."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).with_name('identityguard.db')
ROLES = ('Viewer', 'Employee', 'Manager', 'Administrator')


def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def initialize(path=DB_PATH):
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS identities (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          department TEXT NOT NULL, role TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('Active','Disabled')),
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, identity_id INTEGER,
          details TEXT NOT NULL
        );
        ''')
        if not db.execute('SELECT 1 FROM identities LIMIT 1').fetchone():
            for name, email, dept, role in [
                ('Ava Patel','ava@example.test','Engineering','Employee'),
                ('Noah Chen','noah@example.test','Finance','Manager'),
                ('Mia Rivera','mia@example.test','IT','Administrator'),
                ('Liam Brooks','liam@example.test','HR','Viewer')]:
                db.execute('INSERT INTO identities(name,email,department,role,status,created_at) VALUES (?,?,?,?,?,?)',
                           (name,email,dept,role,'Active',now()))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def log(db, action, identity_id, details):
    db.execute('INSERT INTO audit_events(timestamp,actor,action,identity_id,details) VALUES (?,?,?,?,?)',
               (now(),'local-demo-admin',action,identity_id,details))


def identities(path=DB_PATH):
    with connect(path) as db:
        return [dict(r) for r in db.execute('SELECT * FROM identities ORDER BY id')]


def events(path=DB_PATH):
    with connect(path) as db:
        return [dict(r) for r in db.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT 100')]


def joiner(name, email, department, role, path=DB_PATH):
    name, email, department = name.strip(), email.strip().lower(), department.strip()
    if not name or not department or '@' not in email or role not in ROLES:
        raise ValueError('Provide a name, valid-looking email, department, and allowed role.')
    with connect(path) as db:
        cur = db.execute('INSERT INTO identities(name,email,department,role,status,created_at) VALUES (?,?,?,?,?,?)',
                         (name,email,department,role,'Active',now()))
        log(db,'JOINER',cur.lastrowid,f'Created identity; role={role}; department={department}')
        return cur.lastrowid


def mover(identity_id, department, role, path=DB_PATH):
    department = department.strip()
    if not department or role not in ROLES:
        raise ValueError('Invalid department or role.')
    with connect(path) as db:
        row = db.execute('SELECT * FROM identities WHERE id=?',(identity_id,)).fetchone()
        if row is None or row['status'] != 'Active':
            raise ValueError('Active identity not found.')
        db.execute('UPDATE identities SET department=?,role=? WHERE id=?',(department,role,identity_id))
        log(db,'MOVER',identity_id,f"{row['department']}/{row['role']} -> {department}/{role}")


def leaver(identity_id, path=DB_PATH):
    with connect(path) as db:
        row = db.execute('SELECT * FROM identities WHERE id=?',(identity_id,)).fetchone()
        if row is None or row['status'] != 'Active':
            raise ValueError('Active identity not found.')
        db.execute("UPDATE identities SET status='Disabled' WHERE id=?",(identity_id,))
        log(db,'LEAVER',identity_id,'Disabled local demo identity')


def access_findings(path=DB_PATH):
    return [r for r in identities(path) if r['role'] == 'Administrator' and r['status'] == 'Active']
