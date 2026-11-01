"""Live HTTP financial-security acceptance; isolated server/ledger, no mocks."""
import concurrent.futures
import json
import sqlite3
import sys
import uuid
from pathlib import Path
import httpx
import pytest

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND/'tests'))
sys.path.insert(0,str(BACKEND))
from test_banking_v3 import Server
from services.audit_service import AuditService, digest


def test_financial_security_acceptance(tmp_path):
    out=BACKEND/'test-results/security-acceptance'
    out.mkdir(parents=True,exist_ok=True)
    evidence={'requests':[], 'checks':{}, 'database':str(tmp_path/'banking.db')}
    s=Server(tmp_path);s.start()
    def record(c,method,path,body=None,expected=200):
        r=c.request(method,path,json=body)
        try:data=r.json()
        except ValueError:data=r.text
        evidence['requests'].append({'method':method,'path':path,'request':body,'status':r.status_code,'response':data})
        assert r.status_code==expected,(path,r.status_code,r.text)
        return data
    def rows(w=None):
        with sqlite3.connect(s.db) as db:
            db.row_factory=sqlite3.Row
            return [dict(x) for x in db.execute('SELECT * FROM audit_events '+('WHERE workflow_id=? ' if w else '')+'ORDER BY sequence', (w['workflow_id'],) if w else ())]
    def check(n,detail):evidence['checks'][str(n)]={'result':'PASS','detail':detail}
    def op(c,w,name,body=None,expected=200):
        return record(c,'POST',f"/api/workflows/{w['workflow_id']}/{name}",body or {},expected)
    def new(c,amount):
        return record(c,'POST','/api/transactions',{'action':'transfer.simulate','amount':amount,'recipient':'demo-recipient','idempotency_key':str(uuid.uuid4())},201)
    def run(c,w,expected=200):return op(c,w,'execute',{'idempotency_key':w['idempotency_key']},expected)
    def mfa(c,w):
        op(c,w,'maker-confirm',{'confirmed':True})
        return op(c,w,'mfa/verify',{'consent':True,'method':'simulated_face'})
    def review(c,w,decision,expected=200):return op(c,w,'human-review',{'decision':decision,'plan_hash':w['plan_hash'],'reason':'Financial security acceptance: '+decision},expected)
    def no_started(w):assert not any(x['action'] in {'execution_started','execution_completed'} for x in rows(w))
    try:
        headers=s.login()
        with httpx.Client(base_url=s.url,headers=headers,timeout=30,trust_env=False) as maker, httpx.Client(base_url=s.url,headers=s.login('customer2'),timeout=30,trust_env=False) as customer, httpx.Client(base_url=s.url,headers=s.login('checker'),timeout=30,trust_env=False) as supervisor:
            w=new(maker,'8800');run(maker,w,403);no_started(w)
            op(maker,w,'maker-confirm',{'confirmed':True});run(maker,w,403);no_started(w)
            w=op(maker,w,'mfa/verify',{'consent':True,'method':'simulated_face'})
            assert w['state']=='APPROVED'; first=run(maker,w); assert first['state']=='COMPLETED'
            check(1,{'workflow':w['workflow_id'],'pre_MFA':403,'post_MFA':200,'state':first['state']})
            big=mfa(maker,new(maker,'50001'));assert big['state']=='PENDING_HUMAN_REVIEW'
            run(maker,big,403);no_started(big)
            check(2,{'workflow':big['workflow_id'],'state':big['state'],'execution_started':0})
            big=op(maker,big,'submit-review');assert big['state']=='AWAITING_CHECKER'
            review(maker,big,'APPROVE',403);no_started(big);check(3,'Maker approval HTTP 403')
            review(customer,big,'APPROVE',403);no_started(big);check(4,'Different customer approval HTTP 403')
            big=review(supervisor,big,'APPROVE');assert big['state']=='APPROVED'
            no_started(big)
            result=run(maker,big);assert result['state']=='COMPLETED'
            actions=[x['action'] for x in rows(big)]
            assert actions.index('mfa_verified')<actions.index('human_review_completed')<actions.index('execution_started')<actions.index('execution_completed')
            check(5,{'workflow':big['workflow_id'],'checker':big['checker_id'],'state':result['state'],'events':actions})
            rejected=mfa(maker,new(maker,'50001'));rejected=op(maker,rejected,'submit-review')
            rejected=review(supervisor,rejected,'REJECT');assert rejected['state']=='REJECTED'
            run(maker,rejected,403);review(supervisor,rejected,'APPROVE',403)
            op(maker,rejected,'maker-confirm',{'confirmed':True},403)
            op(maker,rejected,'mfa/verify',{'consent':True},403)
            op(maker,rejected,'submit-review',{},403);no_started(rejected)
            check(6,{'workflow':rejected['workflow_id'],'state':'REJECTED','all_reactivation_attempts':403})
            replay=new(maker,'8800');replay=mfa(maker,replay)
            before=record(maker,'GET','/api/simulation/account')['account']['balance_cents']
            path=f"/api/workflows/{replay['workflow_id']}/execute"
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results=list(pool.map(lambda _:maker.post(path,json={'idempotency_key':replay['idempotency_key']}),range(8)))
            for r in results:evidence['requests'].append({'method':'POST','path':path,'request':{'idempotency_key':replay['idempotency_key']},'status':r.status_code,'response':r.json()})
            assert all(r.status_code==200 and r.json()==results[0].json() for r in results)
            after=record(maker,'GET','/api/simulation/account')['account']['balance_cents']
            with sqlite3.connect(s.db) as db:count=db.execute('SELECT count(*) FROM simulated_entries WHERE workflow_id=?',(replay['workflow_id'],)).fetchone()[0]
            assert before-after==880000 and count==1
            conflict={'action':'transfer.simulate','amount':'8801','recipient':'demo-recipient','idempotency_key':replay['idempotency_key']}
            record(maker,'POST','/api/transactions',conflict,409)
            check(7,{'parallel_requests':8,'balance_delta_cents':before-after,'ledger_entries':count})
            # Real MCP tools/call and old frontend preflight cannot authorize writes.
            pre=record(maker,'GET','/api/simulation/account')
            blocked=record(maker,'POST','/api/actions/authorize',{'action_type':'transfer.execute','user_confirmed':True,'mfa_verified':True})
            assert blocked['decision']=='BLOCK'
            old=record(maker,'POST','/api/actions/authorize',{'action_type':'wealth.subscribe','user_confirmed':True,'mfa_verified':True})
            assert old['decision']!='ALLOW'
            h={'Accept':'application/json, text/event-stream'}
            init=maker.post('/mcp/',headers=h,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'security-acceptance','version':'1'}}})
            assert init.status_code==200
            if init.headers.get('mcp-session-id'):h['Mcp-Session-Id']=init.headers['mcp-session-id']
            h['MCP-Protocol-Version']='2025-03-26'
            maker.post('/mcp/',headers=h,json={'jsonrpc':'2.0','method':'notifications/initialized'})
            for i,(name,args,marker) in enumerate([('transfer_execute',{'amount':8800,'recipient_is_known':True},'funds_moved'),('wealth_subscription_request',{},'order_submitted'),('card_freeze_request',{},'card_status_changed'),('subscription_cancel_request',{'subscription_id':'S01'},'merchant_contacted')]):
                r=maker.post('/mcp/',headers=h,json={'jsonrpc':'2.0','id':i+2,'method':'tools/call','params':{'name':name,'arguments':args}})
                evidence['requests'].append({'method':'POST','path':'/mcp/','tool':name,'status':r.status_code,'response':r.text})
                assert r.status_code==200
                data=json.loads(next(line[6:] for line in r.text.splitlines() if line.startswith('data: '))) if r.text.startswith('event:') else r.json()
                result=data['result'].get('structuredContent')
                if result is None:result=json.loads(data['result']['content'][0]['text'])
                assert result[marker] is False
            assert record(maker,'GET','/api/simulation/account')==pre
            check(10,'Legacy true MFA flags do not grant ALLOW; real transfer.execute preflight BLOCK; four live MCP write-like tools return no side effect; balance/objects unchanged. Static sink review documented separately.')
            history=rows();history_api=record(maker,'GET','/api/audit-logs?limit=500')
        s.stop();s.start()
        with httpx.Client(base_url=s.url,headers=headers,timeout=30,trust_env=False) as maker:
            assert rows()==history
            assert record(maker,'GET','/api/audit-logs?limit=500')==history_api
            run(maker,rejected,403);no_started(rejected)
            check(8,{'events_retained':len(history),'comparison':'all fields identical after actual process restart','rejected_still_blocked':True})
        with sqlite3.connect(s.db) as db:
            db.row_factory=sqlite3.Row
            audit=AuditService.__new__(AuditService)
            tip=audit.verify(db)
            with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE audit_events SET status='FORGED'")
            with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM audit_events')
        check(9,{'verified_events':len(rows()),'tip':tip,'update_delete':'both rejected'})
        evidence['audit_events']=rows()
    finally:
        s.stop()
        (out/'http-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')


def test_default_balance_must_not_bypass_reserves(tmp_path):
    s=Server(tmp_path,initial_balance='10000');s.start();evidence=[]
    try:
        with httpx.Client(base_url=s.url,headers=s.login(),timeout=30,trust_env=False) as c:
            for amount in ['8800','50001']:
                r=c.post('/api/transactions',json={'action':'transfer.simulate','amount':amount,'recipient':'demo-recipient','idempotency_key':str(uuid.uuid4())})
                evidence.append({'amount':amount,'status':r.status_code,'response':r.json()})
                assert r.status_code==201
                w=r.json();assert w['state']=='FAILED'
                assert any(v['passed'] is False for v in w['sandbox']['validation_results'])
                denied=c.post(f"/api/workflows/{w['workflow_id']}/execute",json={'idempotency_key':w['idempotency_key']})
                evidence.append({'operation':'execute','status':denied.status_code,'response':denied.json()})
                assert denied.status_code==403
                events=c.get('/api/audit-logs',params={'workflow_id':w['workflow_id']}).json()['items']
                assert not any(x['action']=='execution_started' for x in events)
    finally:
        s.stop()
        (BACKEND/'test-results/security-acceptance/default-balance-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
