"""Server-owned policy revision and immutable authorization snapshots.

Activation and financial execution use the same SQLite BEGIN IMMEDIATE lock.
There is deliberately no HTTP policy-update endpoint.
"""
import hashlib
import json
import os
import threading
from pathlib import Path
from agent_runtime import TrustDecision, trust_engine
from .audit_service import digest
from .auth_service import Actor
from .database import canonical, utcnow
from .sandbox_service import SandboxService

MFA_TTL_SECONDS = 300
HITL_THRESHOLD_CENTS = 5000000


def compiled_policy():
    root = Path(__file__).resolve().parents[1]
    material = {
        'sources': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                    ('agent_runtime.py', 'services/policy_service.py', 'services/execution_gateway.py',
                     'services/sandbox_service.py', 'services/database.py', 'services/api_v3.py',
                     'services/audit_service.py', 'services/idempotency_service.py')},
        'levels': trust_engine.ACTION_LEVELS,
        'connectors': sorted(trust_engine.ALLOWED_CONNECTORS),
        'targets': {k: sorted(v) for k,v in SandboxService.TARGETS.items()},
        'mfa_ttl_seconds': MFA_TTL_SECONDS, 'hitl_threshold_cents': HITL_THRESHOLD_CENTS,
        'environment': os.getenv('APP_ENV'),
        'simulated_mfa_enabled': os.getenv('DEMO_MFA_ENABLED','true').lower()=='true',
    }
    return {'policy_version': TrustDecision.model_fields['policy_version'].default,
            'policy_fingerprint': digest(material)}


def invalidate(conn, audit, w, current):
    if w['state'] in {'COMPLETED','REJECTED','FAILED','POLICY_STALE'}:
        return
    w.update(state='POLICY_STALE', maker_confirmed=False, mfa_verified=False,
             maker_authorization_digest=None, mfa_authorization_digest=None,
             checker_id=None, approved_hash=None, approved_authorization_digest=None,
             approved_policy_version=None, approved_policy_fingerprint=None,
             approved_plan_hash=None, approved_at=None, sandbox_valid=False,
             policy_stale_at=utcnow())
    audit.append(Actor('policy-service','system','policy-activation'), 'policy_stale', conn=conn,
                 workflow_id=w['workflow_id'], permission_level=w.get('permission_level','RED'),
                 status='REJECTED', reason='Policy changed; create a new workflow and obtain fresh authorization',
                 request_hash=w.get('authorization_digest'),
                 metadata={'old_policy_version':w.get('policy_version'), 'current_policy':current,
                           'state':'POLICY_STALE'})
    conn.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(canonical(w),w['workflow_id']))


class PolicyService:
    def __init__(self, db, audit):
        self.db, self.audit = db, audit
        self.local = compiled_policy()
        # Capture the registry at worker construction, without activating or changing data.
        # A worker first used after another deployment must never roll that deployment back.
        with db.connect() as conn:
            table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='active_policy'").fetchone()
            row = conn.execute('SELECT payload FROM active_policy WHERE singleton=1').fetchone() if table else None
            self.observed_at_boot = json.loads(row[0]) if row else None
        self._initialized = False
        self._initialization_lock = threading.RLock()

    def initialize(self):
        with self._initialization_lock:
            if self._initialized:return
            self._initialize()
            self._initialized = True

    def _initialize(self):
        with self.db.transaction() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS active_policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), payload TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS authorization_snapshots (workflow_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            conn.execute("CREATE TRIGGER IF NOT EXISTS snapshot_no_update BEFORE UPDATE ON authorization_snapshots BEGIN SELECT RAISE(ABORT,'authorization snapshot is immutable'); END")
            conn.execute("CREATE TRIGGER IF NOT EXISTS snapshot_no_delete BEFORE DELETE ON authorization_snapshots BEGIN SELECT RAISE(ABORT,'authorization snapshot is immutable'); END")
        self.activate()

    def activate(self):
        """Deployment-only activation. Old workers fail closed against this registry."""
        with self.db.transaction() as conn:
            row=conn.execute('SELECT payload FROM active_policy WHERE singleton=1').fetchone()
            old=json.loads(row[0]) if row else None
            if old and all(old[k]==v for k,v in self.local.items()):return
            if old != self.observed_at_boot:
                return  # A different deployment won activation; this worker fails closed.
            current={**self.local,'policy_generation':old['policy_generation']+1 if old else 1}
            self.audit.append(Actor('policy-service','system','policy-activation'),'policy_activated',conn=conn,
                              metadata={'previous':old,'current':current})
            conn.execute('INSERT INTO active_policy VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET payload=excluded.payload',(canonical(current),))
            for row in conn.execute('SELECT payload FROM workflows').fetchall():
                w=json.loads(row[0])
                if w.get('action'):invalidate(conn,self.audit,w,current)

    def current(self,conn):
        return json.loads(conn.execute('SELECT payload FROM active_policy WHERE singleton=1').fetchone()[0])

    def worker_matches(self,current):
        return all(current[k]==v for k,v in self.local.items())

    @staticmethod
    def snapshot(w):
        keys=('workflow_id','maker_id','transaction_amount','recipient','action_type','idempotency_key_hash',
              'policy_version','policy_fingerprint','policy_generation','plan_hash','sandbox_run_id','sandbox_result_hash')
        return {k:w[k] for k in keys}

    def seal(self,conn,w):
        w.update(maker_id=w['actor_id'],transaction_amount=w['amount_cents'],action_type=w['action'],
                 idempotency_key_hash=digest(w['idempotency_key']),sandbox_run_id=w['sandbox']['sandbox_run_id'],
                 sandbox_result_hash=digest(w['sandbox']),sandbox_valid=w['sandbox']['sandbox_status']=='passed')
        snap=self.snapshot(w)
        w['authorization_digest']=digest(snap)
        conn.execute('INSERT INTO authorization_snapshots VALUES (?,?)',(w['workflow_id'],canonical(snap)))

    def matches(self,conn,w):
        row=conn.execute('SELECT payload FROM authorization_snapshots WHERE workflow_id=?',(w['workflow_id'],)).fetchone()
        if not row:return False
        try:
            snap=self.snapshot(w)
            return (canonical(snap)==row[0] and digest(snap)==w['authorization_digest']
                    and w['maker_id']==w['actor_id'] and w['transaction_amount']==w['amount_cents']
                    and w['action_type']==w['action'] and w['idempotency_key_hash']==digest(w['idempotency_key'])
                    and w['sandbox_result_hash']==digest(w['sandbox'])
                    and w['sandbox_run_id']==w['sandbox']['sandbox_run_id']
                    and w['sandbox']['plan_hash']==w['plan_hash'])
        except (KeyError,TypeError):return False
