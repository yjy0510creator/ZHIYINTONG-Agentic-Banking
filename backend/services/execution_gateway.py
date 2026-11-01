import json
import os
import time
import uuid
from fastapi import HTTPException
from agent_runtime import AuthorizationContext, trust_engine
from .audit_service import digest
from .database import canonical, utcnow
from .sandbox_service import SandboxService
from .policy_service import PolicyService, invalidate, MFA_TTL_SECONDS, HITL_THRESHOLD_CENTS


class ExecutionGateway:
    def __init__(self, db, audit, idempotency):
        self.db, self.audit, self.idempotency = db, audit, idempotency
        self.sandbox = SandboxService()
        self.policy = PolicyService(db,audit)

    def load(self, conn, workflow_id, actor, reviewer=False):
        row = conn.execute('SELECT payload FROM workflows WHERE workflow_id=?', (workflow_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Workflow not found')
        w = json.loads(row['payload'])
        if w['actor_id'] != actor.actor_id and not (reviewer and actor.actor_role == 'supervisor'):
            raise HTTPException(403, 'Workflow belongs to a different principal')
        return w

    def save(self, conn, w):
        from .intelligence import save_decision
        save_decision(conn,w)
        conn.execute('INSERT INTO workflows VALUES (?,?,?,?) ON CONFLICT(workflow_id) DO UPDATE SET payload=excluded.payload',
                     (w['workflow_id'], w['actor_id'], w.get('task_id'), canonical(w)))

    def event(self, conn, actor, w, action, status='SUCCESS', started=None, **extra):
        self.audit.append(actor, action, conn=conn, workflow_id=w['workflow_id'], task_id=w.get('task_id'),
                          intent=w.get('intent'), permission_level=w.get('permission_level','GREEN'), status=status,
                          request_hash=w.get('authorization_digest',w.get('plan_hash')), idempotency_key_hash=digest(w.get('idempotency_key')),
                          duration_ms=(time.perf_counter()-started)*1000 if started else 0,
                          metadata={'state': w['state'], 'maker_id': w['actor_id'], **extra})

    def create_analysis(self, actor, workflow_id, task_id, nodes, edges, intent):
        w = {'workflow_id':workflow_id, 'task_id':task_id, 'actor_id':actor.actor_id, 'session_id':actor.session_id,
             'state':'CREATED', 'plan_confirmed':False, 'mfa_verified':False,
             'nodes':nodes, 'edges':edges, 'intent':intent, 'created_at':utcnow()}
        with self.db.transaction() as conn:
            self.save(conn,w)
            self.event(conn,actor,w,'intent_parsed')
            self.event(conn,actor,w,'agent_routed')
            self.event(conn,actor,w,'dag_validated')
        return w

    def prepare(self, actor, action, amount, recipient, key, workflow_id=None):
        started = time.perf_counter()
        cents = self.sandbox.cents(amount)
        self.policy.initialize()
        with self.db.transaction() as conn:
            # Keep old transfer.execute blocked. Only the new isolated simulation action is permitted.
            current = self.policy.current(conn)
            if not self.policy.worker_matches(current):
                raise HTTPException(409,'Worker policy is obsolete; use the current policy deployment')
            decision = trust_engine.authorize(action, AuthorizationContext(human_subject=actor.actor_id,session_id=actor.session_id),
                                              simulation_only=True)
            if decision.decision == 'BLOCK':
                raise HTTPException(403,decision.reason)
            fingerprint = digest({'actor':actor.actor_id,'action':action,'amount_cents':cents,'recipient':recipient,
                                  'workflow_id':workflow_id})
            cached = self.idempotency.reserve(conn,actor.actor_id+':prepare',key,fingerprint)
            if cached:
                old = self.load(conn,cached['workflow_id'],actor)
                self.check_snapshot(conn,old)
                return old
            if workflow_id:
                w = self.load(conn,workflow_id,actor)
                if not w.get('plan_confirmed') or w.get('action'):
                    raise HTTPException(409,'Plan must be confirmed and not already bound to a transaction')
            else:
                workflow_id = uuid.uuid4().hex
                w = {'workflow_id':workflow_id,'actor_id':actor.actor_id,'task_id':None,'session_id':actor.session_id,
                     'intent':'Independent simulation request', 'plan_confirmed':False,
                     'nodes':[{'task_id':'N01','dependencies':[]},{'task_id':'N02','dependencies':['N01']}],
                     'edges':[{'source':'N01','target':'N02'}], 'created_at':utcnow()}
            w.update(action=action,amount_cents=cents,recipient=recipient,idempotency_key=key,
                     permission_level=decision.permission_level,state='CREATED',mfa_verified=False,
                     maker_confirmed=False,checker_id=None,approved_hash=None,risk_flags=[])
            w.update(current)
            w['plan_hash'] = self.sandbox.plan_hash(w)
            # Configured seed is synthetic and only applies when an account is first created.
            balance = self.sandbox.cents(os.getenv('SIMULATED_INITIAL_BALANCE',os.getenv('DEMO_BALANCE','10000')))
            reserved = sum(self.sandbox.cents(os.getenv(k,d)) for k,d in
                           [('DEMO_MORTGAGE','3000'),('DEMO_DAILY_EXPENSE','2000'),('DEMO_MIN_LIQUIDITY','1000')])
            conn.execute('INSERT OR IGNORE INTO simulated_accounts VALUES (?,?,?)',(actor.actor_id,balance,reserved))
            self.event(conn,actor,w,'trust_decision',decision=decision.model_dump())
            self.event(conn,actor,w,'sandbox_started')
            w['sandbox'] = self.sandbox.validate(conn,w)
            w['state'] = 'SANDBOX_PASSED' if w['sandbox']['sandbox_status']=='passed' else 'FAILED'
            self.policy.seal(conn,w)
            self.event(conn,actor,w,'sandbox_completed' if w['state']=='SANDBOX_PASSED' else 'sandbox_rejected',
                       status='SUCCESS' if w['state']=='SANDBOX_PASSED' else 'REJECTED',started=started,
                       report=w['sandbox'])
            self.save(conn,w)
            self.idempotency.complete(conn,actor.actor_id+':prepare',key,{'workflow_id':workflow_id})
        return w

    def check_snapshot(self,conn,w):
        current = self.policy.current(conn)
        if (w['state']=='POLICY_STALE' or not self.policy.worker_matches(current)
                or any(w.get(k)!=v for k,v in current.items())):
            invalidate(conn,self.audit,w,current)
            # Persist only invalidation + its audit; no financial write has occurred.
            conn.commit()
            raise HTTPException(409,'POLICY_STALE: create a new workflow; previous authorizations are invalid')
        if not self.policy.matches(conn,w) or self.sandbox.plan_hash(w)!=w['plan_hash']:
            raise HTTPException(409,'Authorization snapshot mismatch; create a new workflow')

    @staticmethod
    def maker_binding(w, require_mfa=False):
        if (not w.get('maker_confirmed') or w.get('maker_confirmed_by')!=w['maker_id']
                or w.get('maker_authorization_digest')!=w['authorization_digest']):
            raise HTTPException(403,'Maker confirmation must bind the current authorization snapshot')
        if require_mfa and w['permission_level']=='RED':
            if (not w.get('mfa_verified') or w.get('mfa_verified_by')!=w['maker_id']
                    or w.get('mfa_authorization_digest')!=w['authorization_digest']
                    or not w.get('mfa_verified_at',0)<=time.time()<w.get('mfa_expires_at',0)):
                raise HTTPException(403,'Maker MFA missing, expired or bound to a different snapshot')

    def act(self, actor, workflow_id, operation, *, confirmed=False, plan_hash=None, reason=None, key=None):
        started = time.perf_counter()
        if operation!='read':
            self.policy.initialize()
        try:
            with self.db.transaction() as conn:
                w = self.load(conn,workflow_id,actor,reviewer=operation in {'APPROVE','REJECT','read'})
                if operation=='read':
                    return w
                if operation=='confirm-plan' and not w.get('action'):
                    if not confirmed:
                        raise HTTPException(409,'Explicit YELLOW confirmation required')
                    decision = trust_engine.authorize('plan.confirm',AuthorizationContext(human_subject=actor.actor_id,session_id=actor.session_id),user_confirmed=True)
                    if decision.decision!='ALLOW': raise HTTPException(403,decision.reason)
                    w['plan_confirmed']=True
                    self.event(conn,actor,w,'user_authorized')
                    self.save(conn,w)
                    return w
                if not w.get('action'):
                    raise HTTPException(409,'No independent transaction requested')
                self.check_snapshot(conn,w)
                if self.sandbox.plan_hash(w)!=w['plan_hash']:
                    raise HTTPException(409,'Plan changed; create a new workflow and obtain fresh approval')
                if w['state'] in {'REJECTED','FAILED'}:
                    raise HTTPException(403,'Terminal workflow cannot execute or be approved')
                if operation=='execute':
                    # Current identity, plan and TrustEngine are checked even when returning a cached result.
                    decision = trust_engine.authorize(w['action'],AuthorizationContext(human_subject=actor.actor_id,session_id=actor.session_id),
                        user_confirmed=w['maker_confirmed'],mfa_verified=w['mfa_verified'],simulation_only=True,risk_flags=w['risk_flags'])
                    self.event(conn,actor,w,'trust_decision',decision=decision.model_dump())
                    if decision.decision!='ALLOW': raise HTTPException(403,decision.reason)
                    if key != w['idempotency_key']: raise HTTPException(409,'Execution must use the original idempotency key')
                    cached = self.idempotency.reserve(conn,actor.actor_id+':execute',key,w['plan_hash'])
                    if cached: return cached
                    self.maker_binding(w,require_mfa=True)
                    if not w.get('sandbox_valid') or w['sandbox']['sandbox_status']!='passed':
                        raise HTTPException(409,'Original sandbox authorization is invalid')
                    self.event(conn,actor,w,'execution_requested')
                    report = self.sandbox.validate(conn,w)
                    self.event(conn,actor,w,'sandbox_completed' if report['sandbox_status']=='passed' else 'sandbox_rejected',report=report)
                    if report['sandbox_status']!='passed': raise HTTPException(409,'Execution-time sandbox validation rejected')
                    if w['state']!='APPROVED' or not w['maker_confirmed']:
                        raise HTTPException(403,'Maker authorization and Checker approval (when required) are mandatory')
                    if w['permission_level']=='RED' and not w['mfa_verified']:
                        raise HTTPException(403,'Independent Maker MFA required')
                    if w['amount_cents']>HITL_THRESHOLD_CENTS and (not w['checker_id'] or w['checker_id']==w['actor_id'] or w['approved_hash']!=w['plan_hash']
                        or w.get('checker_role')!='supervisor' or not w.get('approved_at')
                        or w.get('approved_authorization_digest')!=w['authorization_digest']
                        or w.get('approved_policy_version')!=w['policy_version']
                        or w.get('approved_policy_fingerprint')!=w['policy_fingerprint']
                        or w.get('approved_plan_hash')!=w['plan_hash']):
                        raise HTTPException(403,'Independent supervisor review required')
                    w['state']='EXECUTING'
                    self.event(conn,actor,w,'execution_started')
                    self.sandbox.execute(conn,w)
                    w['state']='COMPLETED'
                    w['status']='SIMULATED_SUCCESS'
                    w['simulated_only']=True
                    w['message']='独立模拟账本执行完成；未调用真实银行接口。'
                    self.event(conn,actor,w,'execution_completed',started=started)
                    # The successful execute response audit is part of the ledger commit.
                    # Middleware must not add a fallible success audit after this commit.
                    self.event(conn,actor,w,'api_request_completed',started=started,http_status=200)
                    self.save(conn,w)
                    self.idempotency.complete(conn,actor.actor_id+':execute',key,w)
                    return w
                if w['state']=='COMPLETED': raise HTTPException(409,'Completed workflow is immutable')
                if operation=='confirm':
                    if not confirmed or w['state']!='SANDBOX_PASSED': raise HTTPException(409,'Explicit Maker confirmation required')
                    w['maker_confirmed']=True
                    w.update(maker_confirmed_by=actor.actor_id,maker_confirmed_at=utcnow(),
                             maker_authorization_digest=w['authorization_digest'])
                    w['state']='AWAITING_MAKER_MFA' if w['permission_level']=='RED' else 'APPROVED'
                    self.event(conn,actor,w,'maker_confirmed')
                    if w['permission_level']=='RED': self.event(conn,actor,w,'mfa_required','WAITING_APPROVAL')
                elif operation=='mfa':
                    if os.getenv('APP_ENV')!='development' or os.getenv('DEMO_MFA_ENABLED','true').lower()!='true':
                        raise HTTPException(403,'Simulated MFA is disabled')
                    if not confirmed or w['state']!='AWAITING_MAKER_MFA': raise HTTPException(409,'Maker confirmation required before MFA')
                    self.maker_binding(w)
                    w['mfa_verified']=True
                    w.update(mfa_verified_by=actor.actor_id,mfa_verified_at=time.time(),
                             mfa_expires_at=time.time()+MFA_TTL_SECONDS,mfa_authorization_digest=w['authorization_digest'])
                    self.event(conn,actor,w,'mfa_verified',started=started)
                    if w['amount_cents']>HITL_THRESHOLD_CENTS:
                        w['state']='PENDING_HUMAN_REVIEW'
                        self.event(conn,actor,w,'hitl_required','WAITING_APPROVAL')
                    else: w['state']='APPROVED'
                elif operation=='submit-review':
                    if w['state']!='PENDING_HUMAN_REVIEW': raise HTTPException(409,'Workflow is not pending human review')
                    self.maker_binding(w,require_mfa=True)
                    w['state']='AWAITING_CHECKER'
                    self.event(conn,actor,w,'maker_checker_required','WAITING_APPROVAL')
                elif operation in {'APPROVE','REJECT'}:
                    if actor.actor_id==w['actor_id'] or actor.actor_role!='supervisor':
                        raise HTTPException(403,'Checker must be a different authenticated supervisor')
                    if w['state']!='AWAITING_CHECKER' or plan_hash!=w['plan_hash']:
                        raise HTTPException(409,'Review must bind the pending original plan hash')
                    self.maker_binding(w,require_mfa=True)
                    w.update(checker_id=actor.actor_id,approved_hash=w['plan_hash'] if operation=='APPROVE' else None,
                             state='APPROVED' if operation=='APPROVE' else 'REJECTED',review_reason=reason,reviewed_at=utcnow())
                    if operation=='APPROVE':
                        w.update(checker_role=actor.actor_role,approved_authorization_digest=w['authorization_digest'],
                                 approved_policy_version=w['policy_version'],approved_policy_fingerprint=w['policy_fingerprint'],
                                 approved_plan_hash=w['plan_hash'],approved_at=utcnow())
                    self.event(conn,actor,w,'human_review_completed',status=operation,started=started,reason=reason)
                else: raise HTTPException(400,'Unknown transition')
                self.save(conn,w)
                return w
        except HTTPException as exc:
            # Rejected request audit survives rollback, but no ledger mutation does.
            self.audit.append(actor,'execution_blocked' if operation=='execute' else 'authorization_rejected',
                              workflow_id=workflow_id,permission_level='RED',status='REJECTED',reason=str(exc.detail),
                              duration_ms=(time.perf_counter()-started)*1000)
            raise
