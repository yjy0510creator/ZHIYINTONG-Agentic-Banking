"""Final independent audit. No requests to live 8000/8011 and no production DB writes.
Policy revision test changes only the declared policy version in a disposable process.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
import httpx
import pytest
from test_banking_v3 import Server,BACKEND

OUT=BACKEND/'test-results/final-security-audit'


class RevisionServer(Server):
    version='trust-engine-3.0'
    def start(self):
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{self.port}'
        env={**os.environ,'APP_ENV':'development','BANKING_DB_PATH':str(self.db),'OPENAI_API_KEY':'',
             'SIMULATED_INITIAL_BALANCE':'2000000','DEV_MAKER_PASSWORD':'test-maker-password-0000001',
             'DEV_CHECKER_PASSWORD':'test-checker-password-00001','DEV_CUSTOMER2_PASSWORD':'test-customer-password-0001',
             'DEMO_MFA_ENABLED':'true','PYTHONUTF8':'1','FINAL_TEST_VERSION':self.version,'FINAL_TEST_PORT':str(self.port)}
        code="import os; from agent_runtime import TrustDecision; TrustDecision.model_fields['policy_version'].default=os.environ['FINAL_TEST_VERSION']; TrustDecision.model_rebuild(force=True); import main,uvicorn; uvicorn.run(main.app,host='127.0.0.1',port=int(os.environ['FINAL_TEST_PORT']))"
        self.log=open(self.log_path,'ab')
        self.process=subprocess.Popen([sys.executable,'-c',code],cwd=BACKEND,env=env,stdout=self.log,stderr=self.log)
        for _ in range(150):
            try:
                if httpx.get(self.url+'/health',timeout=1,trust_env=False).status_code==200:return
            except httpx.HTTPError:pass
            if self.process.poll() is not None:break
            time.sleep(.1)
        raise RuntimeError(self.log_path.read_text(errors='replace'))


class AuditCase:
    def __init__(self,s):
        self.s=s;self.records=[];self.wids=[];self.notes=[]
        self.c=httpx.Client(base_url=s.url,headers=s.login(),trust_env=False,timeout=30)
        self.checker=s.login('checker');self.customer=s.login('customer2')
    def call(self,path,body=None,headers=None,method='POST'):
        r=self.c.request(method,path,json=body,headers=headers)
        self.records.append({'method':method,'path':path,'request':body,'principal':'checker' if headers==self.checker else 'customer2' if headers==self.customer else 'maker_or_explicit_headers','status':r.status_code,'response':r.json()})
        return r
    def op(self,w,op,body=None,headers=None):return self.call(f"/api/workflows/{w['workflow_id']}/{op}",body or {},headers)
    def create(self,amount='50001'):
        r=self.call('/api/transactions',{'action':'transfer.simulate','amount':amount,'recipient':'demo-recipient','idempotency_key':str(uuid.uuid4())})
        assert r.status_code==201,r.text
        w=r.json();self.wids.append(w['workflow_id']);assert w['state']=='SANDBOX_PASSED';return w
    def mfa(self,w):
        assert self.op(w,'maker-confirm',{'confirmed':True}).status_code==200
        r=self.op(w,'mfa/verify',{'consent':True,'method':'simulated_face'});assert r.status_code==200
        w=r.json();assert w['state']=='PENDING_HUMAN_REVIEW';return w
    def pending(self):
        w=self.mfa(self.create());r=self.op(w,'submit-review');assert r.status_code==200;return r.json()
    def review(self,w,decision='APPROVE',headers=None,plan_hash=None):
        return self.op(w,'human-review',{'decision':decision,'reason':'Independent final security audit','plan_hash':plan_hash or w['plan_hash']},headers or self.checker)
    def approved(self):
        w=self.pending();r=self.review(w);assert r.status_code==200;return r.json()
    def execute(self,w,headers=None,extra=None):return self.op(w,'execute',{'idempotency_key':w['idempotency_key'],**(extra or {})},headers)
    def events(self,w):
        with sqlite3.connect(self.s.db) as c:
            c.row_factory=sqlite3.Row
            return [dict(x) for x in c.execute('SELECT * FROM audit_events WHERE workflow_id=? ORDER BY sequence',(w['workflow_id'],))]
    def no_execution(self,w):
        with sqlite3.connect(self.s.db) as c:assert c.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(w['workflow_id'],)).fetchone()[0]==0
        assert not any(x['action'] in {'execution_started','execution_completed'} for x in self.events(w))


@pytest.fixture
def case(tmp_path,request):
    s=RevisionServer(tmp_path);s.start();h=AuditCase(s)
    try:yield h
    finally:
        h.c.close();s.stop();OUT.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(s.db) as c:
            c.row_factory=sqlite3.Row
            events=[dict(x) for x in c.execute('SELECT * FROM audit_events ORDER BY sequence')]
            entries=[dict(x) for x in c.execute('SELECT * FROM simulated_entries')]
        filename=request.node.name.replace('[','_').replace(']','')+'.json'
        (OUT/filename).write_text(json.dumps({'test':request.node.name,'database':str(s.db),'workflows':h.wids,'notes':h.notes,'requests':h.records,'audit_events':events,'ledger_entries':entries},ensure_ascii=False,indent=2),encoding='utf-8')


def test_01_without_checker(case):
    w=case.mfa(case.create());assert case.execute(w).status_code==403;case.no_execution(w)
    assert case.op(w,'submit-review').status_code==200
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_02_maker_self_review(case):
    w=case.pending();assert case.review(w,headers=dict(case.c.headers)).status_code==403
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_03_checker_rejection(case):
    w=case.pending();r=case.review(w,'REJECT');assert r.status_code==200 and r.json()['state']=='REJECTED'
    assert case.execute(w).status_code==403
    assert case.review(w).status_code==403
    case.no_execution(w)


@pytest.mark.parametrize('channel',['http_extra_amount','isolated_storage_tamper'])
def test_04_amount_changed_after_approval(case,channel):
    w=case.approved()
    if channel=='http_extra_amount':assert case.execute(w,extra={'amount':'50002'}).status_code==422
    else:
        # Fault injection only into this test's disposable SQLite; never the live ledger.
        with sqlite3.connect(case.s.db) as c:
            data=json.loads(c.execute('SELECT payload FROM workflows WHERE workflow_id=?',(w['workflow_id'],)).fetchone()[0]);data['amount_cents']=5000200
            c.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(data),w['workflow_id']))
        case.notes.append('Only disposable database amount changed; old plan_hash/approval kept.')
        assert case.execute(w).status_code==409
    case.no_execution(w)


def test_05_direct_http_and_spoofed_identity(case):
    w=case.pending()
    assert case.execute(w,headers={'Authorization':'','X-Actor-ID':'dev-checker','X-Role':'supervisor'}).status_code==401
    assert case.execute(w,headers={'X-Actor-ID':'dev-checker','X-Role':'supervisor'}).status_code==403
    assert case.execute(w).status_code==403;case.no_execution(w)


def test_06_old_approval_replay(case):
    old=case.approved();new=case.pending()
    assert case.review(new,plan_hash=old['plan_hash']).status_code==409
    assert case.review(old).status_code==409
    assert case.execute(new).status_code==403;case.no_execution(new)
    assert case.execute(old).status_code==200
    assert case.review(old).status_code==409
    again=case.execute(old);assert again.status_code==200 # cached result, not another execution
    with sqlite3.connect(case.s.db) as c:assert c.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(old['workflow_id'],)).fetchone()[0]==1


def test_07_concurrent_execution(case):
    w=case.approved();path=f"/api/workflows/{w['workflow_id']}/execute";body={'idempotency_key':w['idempotency_key']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:case.c.post(path,json=body),range(8)))
    for r in results:case.records.append({'method':'POST','path':path,'request':body,'status':r.status_code,'response':r.json()})
    assert all(r.status_code==200 and r.json()==results[0].json() for r in results)
    with sqlite3.connect(case.s.db) as c:
        assert c.execute('SELECT count(*),sum(amount_cents) FROM simulated_entries WHERE workflow_id=?',(w['workflow_id'],)).fetchone()==(1,5000100)
    events=case.events(w);assert sum(e['action']=='execution_started' for e in events)==1
    assert sum(e['action']=='execution_completed' for e in events)==1


def test_08_mfa_incomplete(case):
    w=case.create();assert case.op(w,'maker-confirm',{'confirmed':True}).status_code==200
    assert case.execute(w).status_code==403
    assert case.review(w).status_code==409;case.no_execution(w)


def test_09_independent_authenticated_role_required(case):
    w=case.pending()
    assert case.review(w,headers=case.customer).status_code==403
    # Forged body identity is schema-rejected; forged headers cannot replace a principal.
    r=case.op(w,'human-review',{'decision':'APPROVE','reason':'forged','plan_hash':w['plan_hash'],'reviewer_id':'dev-checker'})
    assert r.status_code==422
    assert case.review(w,headers={**case.customer,'X-Role':'supervisor','X-Actor-ID':'dev-checker'}).status_code==403
    assert case.review(w).status_code==200
    assert case.execute(w,headers=case.customer).status_code==403
    assert case.execute(w).status_code==200


def test_10_policy_version_change_invalidates_approval(case):
    w=case.approved();old_hash=w['approved_hash']
    case.c.close();case.s.stop();case.s.version='trust-engine-final-audit-vNext';case.s.start()
    case.c=httpx.Client(base_url=case.s.url,headers=case.s.login(),trust_env=False,timeout=30)
    result=case.execute(w)
    case.notes.append({'old_approved_hash':old_hash,'new_declared_policy_version':case.s.version,'expected':'403/409 and no execution; an old approval must bind its policy version','actual_status':result.status_code})
    # This is intentionally a security requirement, never relaxed to match current behavior.
    assert result.status_code in {403,409},'Old approval remained executable after declared policy-version change'
    case.no_execution(w)


@pytest.mark.parametrize('field,value',[('amount_cents',5000200),('recipient','another-recipient'),('workflow_id','a'*32),('policy_version','new-policy')])
def test_11_approval_digest_binds_required_fields(field,value):
    from services.sandbox_service import SandboxService
    w={'workflow_id':'b'*32,'actor_id':'maker','action':'transfer.simulate','amount_cents':5000100,'recipient':'demo-recipient','nodes':[],'edges':[],'idempotency_key':str(uuid.uuid4()),'permission_level':'RED','policy_version':'old-policy'}
    before=SandboxService.plan_hash(w);w[field]=value;after=SandboxService.plan_hash(w)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/f'digest-{field}.json').write_text(json.dumps({'field':field,'before':before,'after':after,'expected':'different','actual_equal':before==after}),encoding='utf-8')
    assert before!=after,f'Approval digest does not bind {field}'
