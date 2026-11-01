import json
import sqlite3
import uuid
import httpx
import pytest
from test_banking_v3 import Server,server,client,prepare,authorize,execute


def test_explanation_trace_and_replay_no_funds(client,server):
    r=client.post('/api/analyze',json={'prompt':'分析消费账单','scenario_key':'bills'});assert r.status_code==202
    wid=r.json()['workflow_id']
    with client.stream('GET','/api/stream/'+r.json()['task_id']) as stream:
        events='\n'.join(stream.iter_lines())
    assert 'task_completed' in events
    d=client.get(f'/api/workflows/{wid}/decision');assert d.status_code==200,d.text
    doc=d.json();assert doc['model_status']=='RULE_ENGINE_FALLBACK'
    assert doc['evidence'] and all(n['status']=='PLANNED_NOT_EXECUTED' for n in doc['evidence'])
    with sqlite3.connect(server.db) as c:
        assert c.execute('SELECT payload FROM decision_documents WHERE workflow_id=?',(wid,)).fetchone()
        before=c.execute('SELECT count(*) FROM simulated_entries').fetchone()[0]
    t=client.get(f'/api/workflows/{wid}/trace');assert t.status_code==200,t.text
    names=[e['event'] for e in t.json()['events']]
    for name in ['MASTER_AGENT_STARTED','INTENT_PARSED','DOMAIN_AGENT_SELECTED','MCP_TOOL_CALLED','DAG_NODE_STARTED','DAG_NODE_COMPLETED','AGENT_STREAM_EVENT']:assert name in names
    assert 'EXECUTION_STARTED' not in names
    assert client.get(f'/api/workflows/{wid}/trace',headers=server.login('customer2')).status_code==403
    with sqlite3.connect(server.db) as c:assert c.execute('SELECT count(*) FROM simulated_entries').fetchone()[0]==before


def test_digital_twin_exact_calculation_and_no_mutation(client,server):
    before=client.get('/api/simulation/account').json()
    r=client.post('/api/financial/digital-twin/simulate',json={'new_spending':'100','expected_income':'200','extra_expense':'50','spending_day':2,'income_day':4,'known_income':[{'day':1,'amount':'10'}],'known_expense':[{'day':1,'amount':'20'}]})
    assert r.status_code==200,r.text
    data=r.json();baseline=data['scenarios'][1];start=data['balance_cents']
    assert baseline['points'][0]['balance_cents']==start-1000
    assert baseline['points'][1]['balance_cents']==start-16000
    assert baseline['points'][3]['balance_cents']==start+4000
    assert len(baseline['points'])==30
    assert data['scenarios'][2]['points'][3]['balance_cents']==start-20500
    assert client.get('/api/simulation/account').json()==before
    assert client.get('/api/financial/digital-twin/'+data['scenario_id']).json()==data
    assert client.get('/api/financial/digital-twin/'+data['scenario_id'],headers=server.login('customer2')).status_code==404


def test_fraud_rules_binding_and_no_authorization(client):
    w,_=prepare(client,'50001','transfer.simulate','demo-recipient')
    body={'amount':'50002','recipient':'unknown','threshold':'50000','idempotency_key':w['idempotency_key'],'workflow_id':w['workflow_id']}
    r=client.post('/api/security/fraud-assess',json=body);assert r.status_code==200,r.text
    risk=r.json();assert risk['permission_decision']=='BLOCK'
    assert {'LARGE_AMOUNT','RECIPIENT_ALLOWLIST','USER_THRESHOLD','REPEATED_REQUEST','IDEMPOTENCY_CONFLICT','PLAN_MISMATCH','MAKER_MFA_MISSING'}<=set(risk['triggered_rules'])
    assert execute(client,w).status_code==403


def test_health_insufficient_data_and_cashflow(client,server):
    headers=server.login('customer2')
    r=client.post('/api/financial/health-report',headers=headers,json={});assert r.status_code==200,r.text
    metrics={m['name']:m for m in r.json()['metrics']}
    for name in ['月度收支比','用户提供月收入','支出集中度','未来30天最大安全缺口']:assert metrics[name]['status']=='INSUFFICIENT_DATA' and metrics[name]['value'] is None
    twin=client.post('/api/financial/digital-twin/simulate',json={'new_spending':'3000000'}).json()
    r=client.post('/api/financial/health-report',json={'scenario_id':twin['scenario_id'],'monthly_income':'1000'})
    assert r.status_code==200 and any('缺口' in x for x in r.json()['risks'])


@pytest.mark.parametrize('endpoint,body',[
    ('/api/financial/digital-twin/simulate',{'spending_day':31}),
    ('/api/financial/digital-twin/simulate',{'new_spending':'NaN'}),
    ('/api/financial/digital-twin/simulate',{'expected_income':'1.001'}),
    ('/api/financial/health-report',{'monthly_income':-1}),
    ('/api/security/fraud-assess',{'amount':100,'recipient':'x','idempotency_key':'bad'}),
    ('/api/financial/health-report',{'actor_id':'dev-checker'}),
])
def test_intelligence_validation(client,endpoint,body):assert client.post(endpoint,json=body).status_code==422


def test_persist_trace_scenarios_and_decisions_restart(tmp_path):
    s=Server(tmp_path);s.start()
    try:
        headers=s.login()
        with httpx.Client(base_url=s.url,headers=headers,timeout=30) as c:
            w,_=prepare(c);w=authorize(c,w);assert execute(c,w).status_code==200
            sid=c.post('/api/financial/digital-twin/simulate',json={}).json()['scenario_id']
            old=c.get(f"/api/workflows/{w['workflow_id']}/trace").json()['events']
        s.stop();s.start()
        with httpx.Client(base_url=s.url,headers=headers,timeout=30) as c:
            assert c.get('/api/financial/digital-twin/'+sid).status_code==200
            assert c.get(f"/api/workflows/{w['workflow_id']}/decision").json()['decision']=='COMPLETED'
            assert c.get(f"/api/workflows/{w['workflow_id']}/trace").json()['events'][:len(old)]==old
    finally:s.stop()


def test_technical_identifiers_are_not_account_numbers(tmp_path):
    from services.database import Database
    from services.audit_service import AuditService
    from services.auth_service import Actor
    a=AuditService(Database(tmp_path/'redaction.db'));actor=Actor('maker','customer','session')
    wid='81210a915684469b8fe1234567890123f'
    a.append(actor,'test',workflow_id=wid,request_hash='1'*64,metadata={'password':'secret','account_number':'6222021234567890123'})
    events=a.list(actor,workflow_id=wid)['items'];assert len(events)==1
    assert events[0]['request_hash']=='1'*64
    assert 'secret' not in events[0]['metadata_json'] and '6222021234567890123' not in events[0]['metadata_json']
    assert len(a.verify())==64
