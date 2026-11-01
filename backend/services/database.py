import json
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

active_connection = ContextVar('banking_transaction', default=None)


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


class ManagedConnection(sqlite3.Connection):
    """sqlite3's default context manager commits but does not close."""
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS workflows (
                  workflow_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                  task_id TEXT, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                  token_hash TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                  actor_role TEXT NOT NULL, session_id TEXT NOT NULL, expires_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS simulated_accounts (
                  actor_id TEXT PRIMARY KEY, balance_cents INTEGER NOT NULL CHECK(balance_cents >= 0),
                  reserved_cents INTEGER NOT NULL CHECK(reserved_cents >= 0));
                CREATE TABLE IF NOT EXISTS simulated_entries (
                  workflow_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                  amount_cents INTEGER NOT NULL, recipient TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS simulated_objects (
                  actor_id TEXT NOT NULL, object_id TEXT NOT NULL, status TEXT NOT NULL,
                  PRIMARY KEY(actor_id, object_id));
            ''')

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None, factory=ManagedConnection)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA synchronous=FULL')
        return conn

    @contextmanager
    def transaction(self):
        conn = self.connect()
        token = active_connection.set((self.path, conn))
        try:
            conn.execute('BEGIN IMMEDIATE')
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            active_connection.reset(token)
            conn.close()
