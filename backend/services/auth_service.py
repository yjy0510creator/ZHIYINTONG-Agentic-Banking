import hashlib
import hmac
import os
import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass
from fastapi import HTTPException


@dataclass(frozen=True)
class Actor:
    actor_id: str
    actor_role: str
    session_id: str


current_actor = ContextVar('authenticated_actor', default=None)


class AuthService:
    def __init__(self, db):
        self.db = db

    def login(self, username, password):
        if os.getenv('APP_ENV') != 'development':
            raise HTTPException(403, 'Development login is disabled in production')
        users = {'maker': ('dev-maker', 'customer', 'DEV_MAKER_PASSWORD'),
                 'checker': ('dev-checker', 'supervisor', 'DEV_CHECKER_PASSWORD'),
                 'customer2': ('dev-customer2', 'customer', 'DEV_CUSTOMER2_PASSWORD')}
        user = users.get(username)
        expected = os.getenv(user[2], '') if user else ''
        if not user or len(expected) < 16 or not hmac.compare_digest(password, expected):
            raise HTTPException(401, 'Invalid development credentials')
        token = secrets.token_urlsafe(32)
        actor = Actor(user[0], user[1], secrets.token_hex(16))
        with self.db.transaction() as conn:
            conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',
                         (hashlib.sha256(token.encode()).hexdigest(), actor.actor_id, actor.actor_role,
                          actor.session_id, time.time()+3600))
        return token, actor

    def authenticate(self, authorization):
        # No production identity adapter exists yet: default deny, including development tokens.
        if os.getenv('APP_ENV') != 'development':
            raise HTTPException(503, 'Production identity provider is not configured; access denied')
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Independent authenticated session required')
        token = authorization[7:]
        with self.db.connect() as conn:
            row = conn.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?',
                               (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            raise HTTPException(401, 'Session invalid or expired')
        return Actor(row['actor_id'], row['actor_role'], row['session_id'])
