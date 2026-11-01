"""Real loopback HTTP/SSE integration tests against an isolated SQLite simulation ledger.
No bank APIs or model APIs are contacted. No HTTP handler is mocked.
"""
import concurrent.futures
import hashlib
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

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


class Server:
    def __init__(self,path,environment='development',initial_balance='2000000'):
        self.db=path/'banking.db'
        self.environment=environment
        self.initial_balance=initial_balance
        self.log_path=path/'server.log'
        self.process=None

    def start(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); self.port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{self.port}'
        env={**os.environ,'APP_ENV':self.environment,'BANKING_DB_PATH':str(self.db),
             'OPENAI_API_KEY':'','SIMULATED_INITIAL_BALANCE':self.initial_balance,
             'DEV_MAKER_PASSWORD':'test-maker-password-0000001',
             'DEV_CHECKER_PASSWORD':'test-checker-password-00001',
             'DEV_CUSTOMER2_PASSWORD':'test-customer-password-0001',
             'MCP_ALLOWED_HOSTS':f'127.0.0.1:{self.port},localhost:{self.port}',
             'DEMO_MFA_ENABLED':'true','PYTHONUTF8':'1'}
        self.log=open(self.log_path,'ab')
        self.process=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1','--port',str(self.port)],
                                      cwd=BACKEND,env=env,stdout=self.log,stderr=self.log)
        for _ in range(100):
            try:
                if httpx.get(self.url+'/health',timeout=1).status_code==200:return
            except httpx.HTTPError:pass
            if self.process.poll() is not None:break
            time.sleep(.1)
        raise RuntimeError(self.log_path.read_text(errors='replace'))

    def stop(self):
        if self.process:
            self.process.terminate();self.process.wait(timeout=15);self.log.close()

    def login(self,user='maker'):
        passwords={'maker':'test-maker-password-0000001','checker':'test-checker-password-00001','customer2':'test-customer-password-0001'}
        r=httpx.post(self.url+'/api/dev/login',json={'username':user,'password':passwords[user]})
        assert r.status_code==200,r.text
        return {'Authorization':'Bearer '+r.json()['access_token']}


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    s=Server(tmp_path_factory.mktemp('http-banking'));s.start()
    yield s
    s.stop()


@pytest.fixture
def client(server):
    with httpx.Client(base_url=server.url,headers=server.login(),timeout=20) as c:yield c


def prepare(c,amount='100',action='wealth.subscribe',recipient='P01',key=None):
    body={'action':action,'amount':amount,'recipient':recipient,'idempotency_key':key or str(uuid.uuid4())}
    r=c.post('/api/transactions',json=body);assert r.status_code==201,r.text
    return r.json(),body


def transition(c,w,op,body=None):
    return c.post(f"/api/workflows/{w['workflow_id']}/{op}",json=body or {})


def authorize(c,w):
    r=transition(c,w,'maker-confirm',{'confirmed':True});assert r.status_code==200,r.text
    if w['permission_level']=='RED':
        r=transition(c,w,'mfa/verify',{'consent':True,'method':'simulated_face'});assert r.status_code==200,r.text
    return r.json()


def execute(c,w):
    return transition(c,w,'execute',{'idempotency_key':w['idempotency_key']})


def pending_review(c):
    w,_=prepare(c,'50000.01');w=authorize(c,w)
    assert w['state']=='PENDING_HUMAN_REVIEW'
    r=transition(c,w,'submit-review');assert r.status_code==200,r.text
    return r.json()


def test_01_green_bills(client):
    r=client.post('/api/analyze',json={'prompt':'请分析消费账单','scenario_key':'bills'})
    assert r.status_code==202,r.text
    with client.stream('GET','/api/stream/'+r.json()['task_id']) as stream:
        text='\n'.join(stream.iter_lines())
    assert 'event: task_completed' in text and 'bill_chart' in text


def test_02_yellow_requires_confirmation(client):
    w,_=prepare(client,'0','subscription.cancel','S01')
    assert execute(client,w).status_code==403
    assert transition(client,w,'maker-confirm',{'confirmed':False}).status_code==409


def test_03_red_requires_mfa(client):
    w,_=prepare(client)
    transition(client,w,'maker-confirm',{'confirmed':True})
    assert execute(client,w).status_code==403


@pytest.mark.parametrize('amount',['100','50000'])
def test_04_normal_red_threshold(client,amount):
    w,_=prepare(client,amount);w=authorize(client,w)
    assert w['state']=='APPROVED'
    r=execute(client,w);assert r.status_code==200,r.text
    assert r.json()['state']=='COMPLETED'


def test_05_large_red_hitl(client):
    w,_=prepare(client,'50000.01');w=authorize(client,w)
    assert w['state']=='PENDING_HUMAN_REVIEW'
    assert execute(client,w).status_code==403


def test_06_maker_cannot_self_approve(client):
    w=pending_review(client)
    r=transition(client,w,'human-review',{'decision':'APPROVE','reason':'self','plan_hash':w['plan_hash']})
    assert r.status_code==403


def test_07_checker_requires_supervisor(client,server):
    w=pending_review(client)
    r=client.post(f"/api/workflows/{w['workflow_id']}/human-review",headers=server.login('customer2'),
                  json={'decision':'APPROVE','reason':'other customer','plan_hash':w['plan_hash']})
    assert r.status_code==403


def test_08_rejection_is_terminal(client,server):
    w=pending_review(client)
    r=client.post(f"/api/workflows/{w['workflow_id']}/human-review",headers=server.login('checker'),
                  json={'decision':'REJECT','reason':'test rejection','plan_hash':w['plan_hash']})
    assert r.status_code==200,r.text
    assert execute(client,w).status_code==403
    assert transition(client,w,'maker-confirm',{'confirmed':True}).status_code==403


def test_09_sandbox_failure_blocks(client):
    w,_=prepare(client,'99999999')
    assert w['sandbox']['sandbox_status']=='rejected'
    assert execute(client,w).status_code==403


def test_10_repeated_key_exact_result(client,server):
    w,body=prepare(client);w=authorize(client,w)
    first=execute(client,w);second=execute(client,w)
    assert first.status_code==second.status_code==200
    assert first.json()==second.json()
    with sqlite3.connect(server.db) as conn:
        assert conn.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(w['workflow_id'],)).fetchone()[0]==1


def test_11_key_conflict(client):
    w,body=prepare(client);body['amount']='101'
    assert client.post('/api/transactions',json=body).status_code==409


def test_12_concurrent_replay(client,server):
    key=str(uuid.uuid4());body={'action':'wealth.subscribe','amount':'77','recipient':'P01','idempotency_key':key}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        prepared=list(pool.map(lambda _:client.post('/api/transactions',json=body),range(8)))
    assert all(r.status_code==201 for r in prepared)
    assert len({r.json()['workflow_id'] for r in prepared})==1
    w=authorize(client,prepared[0].json())
    before=client.get('/api/simulation/account').json()['account']['balance_cents']
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:execute(client,w),range(8)))
    assert all(r.status_code==200 for r in results),[(r.status_code,r.text) for r in results]
    assert all(r.json()==results[0].json() for r in results)
    after=client.get('/api/simulation/account').json()['account']['balance_cents']
    assert before-after==7700


def test_13_process_restart_persistence(tmp_path):
    s=Server(tmp_path);s.start()
    try:
        headers=s.login()
        with httpx.Client(base_url=s.url,headers=headers) as c:
            w,_=prepare(c);w=authorize(c,w);first=execute(c,w).json()
            history=c.get('/api/audit-logs').json()['items']
        s.stop();s.start()
        with httpx.Client(base_url=s.url,headers=headers) as c:
            assert execute(c,w).json()==first
            assert c.get('/api/audit-logs').json()['items'][:len(history)]==history
    finally:s.stop()


def test_14_hash_chain_and_append_only(server):
    from services.database import Database
    from services.audit_service import AuditService
    a=AuditService(Database(server.db));assert len(a.verify())==64
    with sqlite3.connect(server.db) as conn:
        with pytest.raises(sqlite3.IntegrityError):conn.execute("UPDATE audit_events SET status='fake'")
        with pytest.raises(sqlite3.IntegrityError):conn.execute('DELETE FROM audit_events')


def test_15_real_sse_review_and_audit(client,server):
    w=pending_review(client)
    with client.stream('GET',f"/api/workflows/{w['workflow_id']}/stream") as response:
        assert response.status_code==200
        events=[]
        for line in response.iter_lines():
            if line.startswith('event:'):events.append(line)
            if line=='event: maker_checker_required':break
        assert 'event: hitl_required' in events
    with client.stream('GET','/api/audit-stream',params={'workflow_id':w['workflow_id']}) as response:
        for line in response.iter_lines():
            if line.startswith('data:'):
                data=json.loads(line[5:]);assert data['actor_id']=='dev-maker' and 'timestamp' in data;break


def test_16_history_after_new_client(client,server):
    w,_=prepare(client)
    with httpx.Client(base_url=server.url,headers=server.login()) as fresh:
        history=fresh.get('/api/audit-logs',params={'workflow_id':w['workflow_id']}).json()
        assert history['items']
        assert fresh.get('/api/workflows/'+w['workflow_id']).json()['plan_hash']==w['plan_hash']


@pytest.mark.parametrize('scenario',['travel','transfer','bills','wealth','card','subscriptions'])
def test_17_six_original_scenarios(client,scenario):
    r=client.post('/api/analyze',json={'prompt':'测试原有业务场景','scenario_key':scenario});assert r.status_code==202,r.text
    result=r.json();assert result['nodes'] and result['ui_cards']
    with client.stream('GET','/api/stream/'+result['task_id']) as response:
        data='\n'.join(response.iter_lines())
    assert 'event: task_completed' in data and 'event: dag_snapshot' in data
    if scenario=='travel':assert len(result['nodes'])==20


def test_18_production_denies_development_identity(tmp_path):
    s=Server(tmp_path,'production');s.start()
    try:
        assert httpx.post(s.url+'/api/dev/login',json={'username':'maker','password':'test-maker-password-0000001'}).status_code==403
        assert httpx.get(s.url+'/api/audit-logs',headers={'X-Actor-ID':'admin','X-Role':'supervisor'}).status_code==503
    finally:s.stop()


def test_supervisor_success_and_binding(client,server):
    w=pending_review(client)
    endpoint=f"/api/workflows/{w['workflow_id']}/human-review"
    assert client.post(endpoint,headers=server.login('checker'),json={'decision':'APPROVE','reason':'wrong hash','plan_hash':'0'*64}).status_code==409
    r=client.post(endpoint,headers=server.login('checker'),json={'decision':'APPROVE','reason':'verified simulation','plan_hash':w['plan_hash']})
    assert r.status_code==200,r.text
    assert execute(client,w).status_code==200
    assert client.get('/api/audit-logs',params={'workflow_id':w['workflow_id'],'actor_id':'dev-checker'}).json()['items']


def test_identity_spoof_and_legacy_mfa_flag(client,server):
    w,_=prepare(client)
    assert client.get('/api/workflows/'+w['workflow_id'],headers=server.login('customer2')).status_code==403
    r=client.post('/api/actions/authorize',json={'action_type':'wealth.subscribe','user_confirmed':True,'mfa_verified':True})
    assert r.json()['decision']!='ALLOW'
    r=transition(client,w,'human-review',{'decision':'APPROVE','reason':'forged','plan_hash':w['plan_hash'],'reviewer_id':'supervisor'})
    assert r.status_code==422


def test_dag_and_plan_tamper(client,server):
    w,_=prepare(client);w=authorize(client,w)
    with sqlite3.connect(server.db) as conn:
        altered=dict(w);altered['amount_cents']=1
        conn.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(altered),w['workflow_id']))
    assert execute(client,w).status_code==409


def test_audit_failure_rolls_back_ledger(client,server):
    w,_=prepare(client);w=authorize(client,w)
    before=client.get('/api/simulation/account').json()['account']['balance_cents']
    with sqlite3.connect(server.db) as conn:
        conn.execute("CREATE TRIGGER fail_result BEFORE INSERT ON audit_events WHEN NEW.action='execution_completed' BEGIN SELECT RAISE(ABORT,'injected disk failure'); END")
    try:
        assert execute(client,w).status_code==503
        assert client.get('/api/simulation/account').json()['account']['balance_cents']==before
        with sqlite3.connect(server.db) as conn:
            assert conn.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(w['workflow_id'],)).fetchone()[0]==0
    finally:
        with sqlite3.connect(server.db) as conn:conn.execute('DROP TRIGGER fail_result')
    assert execute(client,w).status_code==200


def test_health_openapi(client):
    assert client.get('/health').json()['version']=='3.0.0'
    paths=client.get('/openapi.json').json()['paths']
    assert '/api/audit-stream' in paths and '/api/workflows/{workflow_id}/human-review' in paths


@pytest.mark.parametrize('amount',['NaN','Infinity','-1','0.001'])
def test_reject_invalid_money(client,amount):
    r=client.post('/api/transactions',json={'action':'wealth.subscribe','amount':amount,'recipient':'P01','idempotency_key':str(uuid.uuid4())})
    assert r.status_code==422


@pytest.mark.parametrize('kind',['cycle','missing_dependency'])
def test_dag_validation_at_execution(client,server,kind):
    from services.sandbox_service import SandboxService
    w,_=prepare(client);w=authorize(client,w)
    w['nodes'][0]['dependencies']=['N02' if kind=='cycle' else 'MISSING']
    w['plan_hash']=SandboxService.plan_hash(w)
    with sqlite3.connect(server.db) as conn:
        conn.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',(json.dumps(w),w['workflow_id']))
    assert execute(client,w).status_code==409


def test_unknown_recipient_rejected(client):
    w,_=prepare(client,'100','transfer.simulate','untrusted-recipient')
    assert w['state']=='FAILED'


def test_audit_redaction_and_tamper_detection(tmp_path):
    from services.database import Database
    from services.audit_service import AuditService,AuditUnavailable
    from services.auth_service import Actor
    db=Database(tmp_path/'audit.db');a=AuditService(db);actor=Actor('test','customer','session')
    a.append(actor,'redaction',intent='password=secretvalue card 6222123456789012',metadata={'otp':'123456','password':'secretvalue'})
    row=a.list(actor)['items'][0]
    assert 'secretvalue' not in json.dumps(row) and '6222123456789012' not in json.dumps(row)
    with db.connect() as conn:
        conn.execute('DROP TRIGGER audit_no_update')
        conn.execute("UPDATE audit_events SET action='tampered'")
    with pytest.raises(AuditUnavailable):a.verify()
    with pytest.raises(AuditUnavailable):a.append(actor,'blocked')


def test_execution_rechecks_current_balance(client,server):
    w,_=prepare(client,'100');w=authorize(client,w)
    with sqlite3.connect(server.db) as conn:
        before=conn.execute("SELECT balance_cents FROM simulated_accounts WHERE actor_id='dev-maker'").fetchone()[0]
        conn.execute("UPDATE simulated_accounts SET balance_cents=reserved_cents WHERE actor_id='dev-maker'")
    try:assert execute(client,w).status_code==409
    finally:
        with sqlite3.connect(server.db) as conn:conn.execute("UPDATE simulated_accounts SET balance_cents=? WHERE actor_id='dev-maker'",(before,))


def test_sse_resume_review_event(client,server):
    w=pending_review(client)
    history=client.get('/api/audit-logs',params={'workflow_id':w['workflow_id']}).json()
    cursor=history['next_cursor']
    r=client.post(f"/api/workflows/{w['workflow_id']}/human-review",headers=server.login('checker'),
                  json={'decision':'APPROVE','reason':'resume test','plan_hash':w['plan_hash']})
    assert r.status_code==200
    with client.stream('GET',f"/api/workflows/{w['workflow_id']}/stream",headers={'Last-Event-ID':str(cursor)}) as response:
        saw_event=False
        for line in response.iter_lines():
            if line.startswith('id:'):assert int(line[3:])>cursor
            if line=='event: human_review_completed':saw_event=True
            if line.startswith('data:') and saw_event:
                assert json.loads(line[5:])['actor_id']=='dev-checker';break


def test_mcp_tools_remain_available(client):
    headers={'Accept':'application/json, text/event-stream'}
    r=client.post('/mcp/',headers=headers,json={'jsonrpc':'2.0','id':1,'method':'initialize',
        'params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'integration-test','version':'1'}}})
    assert r.status_code==200,r.text
    session=r.headers.get('mcp-session-id')
    if session:headers['Mcp-Session-Id']=session
    headers['MCP-Protocol-Version']='2025-03-26'
    client.post('/mcp/',headers=headers,json={'jsonrpc':'2.0','method':'notifications/initialized'})
    r=client.post('/mcp/',headers=headers,json={'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})
    assert r.status_code==200,r.text
    assert 'account_get_overview' in r.text and 'transfer_execute' in r.text


def test_original_travel_authorization_chain(client):
    r=client.post('/api/analyze',json={'prompt':'下个月旅游，保证房贷，剩余理财','scenario_key':'travel'})
    assert r.status_code==202
    w=r.json();key=str(uuid.uuid4())
    assert transition(client,w,'request-investment',{'idempotency_key':key}).status_code==409
    assert transition(client,w,'confirm',{'confirmed':True}).status_code==200
    r=transition(client,w,'request-investment',{'idempotency_key':key});assert r.status_code==200,r.text
    w=r.json();assert w['state']=='AWAITING_MAKER_MFA'
    assert execute(client,w).status_code==403
    assert transition(client,w,'mfa/verify',{'consent':True}).status_code==200
    assert execute(client,w).status_code==200
