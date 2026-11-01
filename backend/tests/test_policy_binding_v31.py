"""V3.1 live HTTP regression, disposable processes and databases only."""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import httpx
import pytest
from test_banking_v3 import Server, BACKEND
from test_final_security_audit import AuditCase
from services.audit_service import AuditService

OUT=BACKEND/'test-results/v31-policy-evidence'


class PolicyServer(Server):
    version='trust-engine-3.0'
    changed_rules=False
    pause_activation=False
    def start(self):
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{self.port}'
        env={**os.environ,'APP_ENV':'development','BANKING_DB_PATH':str(self.db),'OPENAI_API_KEY':'',
             'SIMULATED_INITIAL_BALANCE':'2000000','DEV_MAKER_PASSWORD':'test-maker-password-0000001',
             'DEV_CHECKER_PASSWORD':'test-checker-password-00001','DEV_CUSTOMER2_PASSWORD':'test-customer-password-0001',
             'DEMO_MFA_ENABLED':'true','PYTHONUTF8':'1','TEST_VERSION':self.version,
             'TEST_RULES':str(int(self.changed_rules)),'TEST_PAUSE':str(int(self.pause_activation)),
             'TEST_PATH':str(self.db.parent),'TEST_PORT':str(self.port)}
        code='''
import os,time
from pathlib import Path
from agent_runtime import TrustDecision,trust_engine
TrustDecision.model_fields['policy_version'].default=os.environ['TEST_VERSION']
TrustDecision.model_rebuild(force=True)
if os.environ['TEST_RULES']=='1': trust_engine.ACTION_LEVELS=dict(trust_engine.ACTION_LEVELS,**{'new.read':'GREEN'})
if os.environ['TEST_PAUSE']=='1':
 from services.audit_service import AuditService
 original=AuditService.append
 def append(self,actor,action,**kwargs):
  if action=='policy_activated':
   root=Path(os.environ['TEST_PATH']);(root/'activation-locked').write_text('locked')
   deadline=time.time()+30
   while not (root/'release-activation').exists():
    if time.time()>deadline: raise RuntimeError('test synchronization timeout')
    time.sleep(.01)
  return original(self,actor,action,**kwargs)
 AuditService.append=append
import main,uvicorn
if os.environ['TEST_PAUSE']=='1': main.gateway.policy.initialize()
uvicorn.run(main.app,host='127.0.0.1',port=int(os.environ['TEST_PORT']))
'''
        self.log=open(self.log_path,'ab')
        self.process=subprocess.Popen([sys.executable,'-c',code],cwd=BACKEND,env=env,stdout=self.log,stderr=self.log)
        for _ in range(400):
            try:
                if httpx.get(self.url+'/health',timeout=1,trust_env=False).status_code==200:return
            except httpx.HTTPError:pass
            if self.process.poll() is not None:break
            time.sleep(.1)
        raise RuntimeError(self.log_path.read_text(errors='replace'))


@pytest.fixture
def case(tmp_path,request):
    s=PolicyServer(tmp_path);s.start();h=AuditCase(s)
    try:yield h
    finally:
        h.c.close();s.stop();OUT.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(s.db) as c:
            c.row_factory=sqlite3.Row
            evidence={'test':request.node.name,'requests':h.records,'notes':h.notes,
                      'audit_events':[dict(r) for r in c.execute('SELECT * FROM audit_events ORDER BY sequence')],
                      'ledger_entries':[dict(r) for r in c.execute('SELECT * FROM simulated_entries')],
                      'accounts':[dict(r) for r in c.execute('SELECT * FROM simulated_accounts')],
                      'workflows':[json.loads(r[0]) for r in c.execute('SELECT payload FROM workflows')],
                      'chain_tip':AuditService.__new__(AuditService).verify(c)}
        (OUT/(request.node.name.replace('[','_').replace(']','')+'.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')


def restart(h,version='trust-engine-vNext',rules=False):
    h.c.close();h.s.stop();h.s.version=version;h.s.changed_rules=rules;h.s.start()
    h.c=httpx.Client(base_url=h.s.url,headers=h.s.login(),trust_env=False,timeout=30)
    h.checker=h.s.login('checker')


def balance(h):
    with sqlite3.connect(h.s.db) as c:return c.execute("SELECT balance_cents FROM simulated_accounts WHERE actor_id='dev-maker'").fetchone()[0]


def stale(h,w,before):
    r=h.execute(w);assert r.status_code in {403,409},r.text
    latest=h.call('/api/workflows/'+w['workflow_id'],method='GET').json()
    assert latest['state']=='POLICY_STALE'
    for key in ['maker_confirmed','mfa_verified','sandbox_valid']:assert latest[key] is False
    assert latest['approved_authorization_digest'] is None and latest['checker_id'] is None
    h.notes.append({'before_balance_cents':before,'after_balance_cents':balance(h),'state':latest['state'],'expected_balance_delta':0})
    assert balance(h)==before;h.no_execution(w)
    assert h.review(w).status_code in {403,409}
    assert h.op(w,'maker-confirm',{'confirmed':True}).status_code in {403,409}
    assert any(e['action']=='policy_stale' for e in h.events(w))
    with sqlite3.connect(h.s.db) as c:
        c.row_factory=sqlite3.Row;assert len(AuditService.__new__(AuditService).verify(c))==64


def test_normal_authorization_snapshot(case):
    w=case.approved()
    for k in ['policy_version','policy_fingerprint','plan_hash','authorization_digest','sandbox_run_id','sandbox_result_hash','transaction_amount','recipient','action_type','idempotency_key_hash','maker_id']:assert k in w
    assert w['maker_authorization_digest']==w['mfa_authorization_digest']==w['approved_authorization_digest']==w['authorization_digest']
    assert w['approved_policy_version']==w['policy_version'] and w['approved_policy_fingerprint']==w['policy_fingerprint']
    assert w['approved_plan_hash']==w['plan_hash'] and w['checker_id']!=w['maker_id'] and w['approved_at']
    assert case.execute(w).status_code==200


@pytest.mark.parametrize('stage',['created','maker','mfa','checker'])
def test_policy_change_at_each_stage(case,stage):
    w=case.create()
    if stage in {'maker','mfa','checker'}:assert case.op(w,'maker-confirm',{'confirmed':True}).status_code==200
    if stage in {'mfa','checker'}:assert case.op(w,'mfa/verify',{'consent':True}).status_code==200
    if stage=='checker':
        assert case.op(w,'submit-review').status_code==200
        assert case.review(w).status_code==200
    before=balance(case);restart(case);stale(case,w,before)


def test_fingerprint_change_same_version(case):
    w=case.approved();before=balance(case);restart(case,version=w['policy_version'],rules=True)
    stale(case,w,before)


def test_old_approval_digest(case):
    old=case.approved();w=case.approved()
    with sqlite3.connect(case.s.db) as c:
        w['approved_authorization_digest']=old['authorization_digest']
        c.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(w),w['workflow_id']))
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_old_idempotency_key_after_policy_change(case):
    w=case.approved();before=balance(case);restart(case);stale(case,w,before)
    r=case.call('/api/transactions',{'action':w['action'],'amount':'50001','recipient':w['recipient'],'idempotency_key':w['idempotency_key']})
    assert r.status_code==409;case.no_execution(w)


def test_concurrent_activation_wins_lock(case):
    w=case.approved();before=balance(case)
    updater=PolicyServer(case.s.db.parent);updater.version='trust-engine-concurrent-next';updater.pause_activation=True
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            activation=pool.submit(updater.start)
            deadline=time.time()+20
            while not (case.s.db.parent/'activation-locked').exists():
                assert time.time()<deadline;time.sleep(.01)
            execution=pool.submit(case.execute,w)
            time.sleep(.1);assert not execution.done()
            (case.s.db.parent/'release-activation').write_text('release')
            activation.result(timeout=30)
            assert execution.result(timeout=30).status_code==409
        stale(case,w,before)
    finally:updater.stop()


def test_stale_cannot_restore_after_version_revert(case):
    w=case.approved();before=balance(case);restart(case);stale(case,w,before)
    restart(case,version=w['policy_version']);stale(case,w,before)


def test_maker_self_approval(case):
    w=case.pending();assert case.review(w,headers=dict(case.c.headers)).status_code==403
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_checker_different_transaction(case):
    a=case.pending();b=case.pending()
    assert case.review(b,plan_hash=a['plan_hash']).status_code==409
    assert case.execute(b).status_code==403;case.no_execution(b)


@pytest.mark.parametrize('event',['execution_completed','api_request_completed'])
def test_audit_failure_rolls_back_every_effect(case,event):
    w=case.approved();before=balance(case)
    with sqlite3.connect(case.s.db) as c:c.execute(f"CREATE TRIGGER fail_completion BEFORE INSERT ON audit_events WHEN NEW.action='{event}' BEGIN SELECT RAISE(ABORT,'test disk failure'); END")
    assert case.execute(w).status_code==503
    assert balance(case)==before;case.no_execution(w)


def test_sandbox_mismatch(case):
    w=case.approved()
    w['sandbox']['plan_hash']='f'*64
    with sqlite3.connect(case.s.db) as c:c.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(w),w['workflow_id']))
    assert case.execute(w).status_code==409;case.no_execution(w)


def test_parallel_execution_once(case):
    w=case.approved();before=balance(case)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(lambda _:case.execute(w),range(8)))
    assert all(r.status_code==200 and r.json()==responses[0].json() for r in responses)
    assert before-balance(case)==5000100
    with sqlite3.connect(case.s.db) as c:assert c.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(w['workflow_id'],)).fetchone()[0]==1
    assert sum(e['action']=='execution_started' for e in case.events(w))==1


def test_expired_mfa(case):
    w=case.approved();w['mfa_expires_at']=time.time()-1
    with sqlite3.connect(case.s.db) as c:c.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(w),w['workflow_id']))
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_snapshot_append_only_and_client_override(case):
    w=case.create()
    with sqlite3.connect(case.s.db) as c:
        with pytest.raises(sqlite3.IntegrityError):c.execute("UPDATE authorization_snapshots SET payload='{}'")
        with pytest.raises(sqlite3.IntegrityError):c.execute('DELETE FROM authorization_snapshots')
    r=case.call('/api/transactions',{'action':'transfer.simulate','amount':'50001','recipient':'demo-recipient','idempotency_key':w['idempotency_key'],'policy_version':'forged'})
    assert r.status_code==422;case.no_execution(w)


def test_read_only_request_does_not_activate_policy(case):
    assert case.call('/api/workflows/not-found',method='GET').status_code==404
    with sqlite3.connect(case.s.db) as c:
        assert c.execute("SELECT name FROM sqlite_master WHERE name='active_policy'").fetchone() is None
        assert c.execute('SELECT count(*) FROM simulated_entries').fetchone()[0]==0


def test_dormant_old_worker_cannot_reactivate_old_policy(case):
    w=case.approved();before=balance(case)
    old=PolicyServer(case.s.db.parent);old.start()
    try:
        with httpx.Client(base_url=old.url,headers=old.login(),timeout=30,trust_env=False) as dormant:
            restart(case);stale(case,w,before)
            body={'action':'transfer.simulate','amount':'50001','recipient':'demo-recipient','idempotency_key':__import__('uuid').uuid4().hex}
            response=dormant.post('/api/transactions',json=body)
            case.records.append({'method':'POST','path':'/api/transactions (dormant old worker)','request':body,'status':response.status_code,'response':response.json()})
            assert response.status_code==409
            with sqlite3.connect(case.s.db) as c:
                current=json.loads(c.execute('SELECT payload FROM active_policy').fetchone()[0])
                assert current['policy_version']=='trust-engine-vNext'
            case.no_execution(w);assert balance(case)==before
    finally:old.stop()
