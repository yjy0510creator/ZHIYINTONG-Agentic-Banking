import json
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from .database import canonical, utcnow


class IdempotencyService:
    def __init__(self, db):
        with db.connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS idempotency_records (
                scope TEXT NOT NULL, idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
                status TEXT NOT NULL, response_json TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                PRIMARY KEY(scope, idempotency_key))''')

    def reserve(self, conn, scope, key, request_hash):
        row = conn.execute('SELECT * FROM idempotency_records WHERE scope=? AND idempotency_key=?', (scope, key)).fetchone()
        if row:
            if row['request_hash'] != request_hash:
                raise HTTPException(409, 'Idempotency key is bound to another request')
            return json.loads(row['response_json']) if row['response_json'] else None
        conn.execute('INSERT INTO idempotency_records VALUES (?,?,?,?,?,?,?)',
                     (scope, key, request_hash, 'PENDING', None, utcnow(),
                      (datetime.now(timezone.utc)+timedelta(days=3650)).isoformat()))
        return None

    def complete(self, conn, scope, key, response):
        conn.execute('UPDATE idempotency_records SET status=?, response_json=? WHERE scope=? AND idempotency_key=?',
                     ('COMPLETED', canonical(response), scope, key))
