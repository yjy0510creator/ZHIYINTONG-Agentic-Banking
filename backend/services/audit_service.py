import hashlib
import json
import re
import uuid
from .database import canonical, utcnow, active_connection


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def redact(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if re.search(r'password|secret|token|otp|code|credential|authorization', k, re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?<!\d)\d[\d -]{10,24}\d(?!\d)', '[MASKED]', value)
        value = re.sub(r'(?i)(password|密码|验证码|otp|api[_ -]?key)\s*[:=：]?\s*\S+', r'\1=[REDACTED]', value)
        return value[:4000]
    return value


class AuditUnavailable(RuntimeError):
    pass


class AuditService:
    FIELDS = ('event_id timestamp_utc actor_id actor_role session_id workflow_id task_id action intent '
              'permission_level duration_ms status reason idempotency_key_hash request_hash previous_hash metadata_json').split()

    def __init__(self, db):
        self.db = db
        with db.connect() as conn:
            columns = ','.join(f'{k} TEXT' for k in self.FIELDS if k != 'duration_ms')
            conn.executescript(f'''
              CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, {columns}, duration_ms REAL NOT NULL,
                event_hash TEXT NOT NULL UNIQUE);
              CREATE UNIQUE INDEX IF NOT EXISTS audit_event_id ON audit_events(event_id);
              CREATE INDEX IF NOT EXISTS audit_workflow ON audit_events(workflow_id, sequence);
              CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
              CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
            ''')

    def verify(self, conn=None):
        if conn is None:
            with self.db.connect() as c:
                return self.verify(c)
        previous = '0' * 64
        for row in conn.execute('SELECT * FROM audit_events ORDER BY sequence'):
            data = {k: row[k] for k in self.FIELDS}
            if data['previous_hash'] != previous or digest(data) != row['event_hash']:
                raise AuditUnavailable('Audit integrity check failed; financial writes disabled')
            previous = row['event_hash']
        return previous

    def append(self, actor, action, *, conn=None, **fields):
        active = active_connection.get()
        if conn is None and active and active[0] == self.db.path:
            conn = active[1]
        if conn is None:
            try:
                with self.db.transaction() as c:
                    return self.append(actor, action, conn=c, **fields)
            except Exception as exc:
                raise AuditUnavailable('Audit storage unavailable') from exc
        try:
            previous = self.verify(conn)
            data = {k: None for k in self.FIELDS}
            data.update(event_id=uuid.uuid4().hex, timestamp_utc=utcnow(),
                        actor_id=actor.actor_id, actor_role=actor.actor_role,
                        session_id=actor.session_id, action=action, permission_level='GREEN',
                        duration_ms=0.0, status='SUCCESS', previous_hash=previous,
                        metadata_json=canonical(redact(fields.pop('metadata', {}))))
            for key, value in fields.items():
                if key in data and key not in {'actor_id','actor_role','session_id','event_id','previous_hash','timestamp_utc'}:
                    data[key] = value if key in {"workflow_id","task_id","request_hash","idempotency_key_hash"} and isinstance(value,str) and re.fullmatch(r"[a-fA-F0-9-]{16,64}",value) else redact(value)
            data['duration_ms'] = float(data['duration_ms'])
            event_hash = digest(data)
            names = self.FIELDS + ['event_hash']
            conn.execute(f"INSERT INTO audit_events ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                         [data[k] for k in self.FIELDS] + [event_hash])
            return data['event_id']
        except Exception as exc:
            raise AuditUnavailable('Audit write failed; transaction must roll back') from exc

    def list(self, actor, limit=100, cursor=0, **filters):
        where, args = ['sequence > ?'], [cursor]
        if actor.actor_role != 'supervisor':
            where.append('(actor_id = ? OR workflow_id IN (SELECT workflow_id FROM workflows WHERE actor_id = ?))')
            args.extend([actor.actor_id, actor.actor_id])
        for key in ('workflow_id', 'actor_id', 'permission_level', 'status'):
            if filters.get(key):
                where.append(f'{key} = ?'); args.append(filters[key])
        with self.db.connect() as conn:
            rows = [dict(r) for r in conn.execute(
                f"SELECT * FROM audit_events WHERE {' AND '.join(where)} ORDER BY sequence LIMIT ?",
                args + [limit])]
        return {'items': rows, 'next_cursor': rows[-1]['sequence'] if rows else cursor}
