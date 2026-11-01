"""Auditable deterministic financial intelligence. No banking/network writes."""
import json
import os
import uuid
from contextvars import ContextVar
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import Field, JsonValue
from .api_v3 import StrictModel, db, audit, gateway, principal
from .audit_service import digest, redact
from .database import canonical, utcnow

router=APIRouter()
trace_workflow=ContextVar('trace_workflow',default=None)


def initialize():
    with db.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS financial_scenarios (
          scenario_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, timestamp TEXT NOT NULL,
          request_json TEXT NOT NULL, response_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decision_documents (
          workflow_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')


class NodeEvidence(StrictModel):
    node_id: str
    action: str
    permission_level: str
    reason: str
    status: str
    amount: float | None=None


class Decision(StrictModel):
    decision_id: str
    workflow_id: str
    intent: str
    decision: str
    evidence: list[NodeEvidence]
    triggered_rules: list[str]
    permission_level: str
    risk_level: str
    decision_reason: str
    expected_effect: str
    limitations: list[str]
    data_source: str
    timestamp: str
    model_status: str
    ai_suggestion: str
    safety_engine_decision: str
    calculation: dict[str,JsonValue]


def decision_for(w):
    nodes=[]
    for n in w.get('nodes',[]):
        level=n.get('permission_level',w.get('permission_level','GREEN'))
        nodes.append(NodeEvidence(node_id=n.get('task_id',n.get('id','unknown')),
            action=n.get('action_type','transaction_dependency'),permission_level=level,
            reason={'GREEN':'只读或内部计算，不授权资金写入。','YELLOW':'必须由本人明确确认。','RED':'需要独立 Maker MFA；金额超过50000还须独立主管复核。'}.get(level,'未知权限拒绝'),
            status='PLANNED_NOT_EXECUTED',amount=n.get('amount')))
    rules=['SERVER_IDENTITY','LOCAL_SIMULATION_ONLY','SERVER_PERMISSION_POLICY','RESERVE_PROTECTION']
    if w.get('permission_level')=='RED':rules.append('MAKER_MFA')
    if w.get('amount_cents',0)>5000000:rules.append('INDEPENDENT_CHECKER_GT_50000')
    sandbox=w.get('sandbox',{})
    rules += [x['rule'] if 'rule' in x else x.get('check','validation') for x in sandbox.get('validation_results',[]) if not x['passed']]
    state=w.get('state','CREATED')
    if not w.get('action') and w.get('analysis_at'):state='ANALYSIS_COMPLETED_NO_TRANSACTION_AUTHORIZATION'
    return Decision(decision_id=digest({'workflow':w['workflow_id'],'state':state,'analysis':w.get('analysis_at')}),
        workflow_id=w['workflow_id'],intent=redact(w.get('intent','模拟金融任务')),decision=state,evidence=nodes,
        triggered_rules=rules,permission_level=w.get('permission_level','GREEN'),
        risk_level='HIGH' if w.get('amount_cents',0)>5000000 or state in {'FAILED','REJECTED'} else 'UNASSESSED',
        decision_reason='依据已持久化工作流状态、服务端权限规则与模拟沙箱校验；规划节点不代表已执行。',
        expected_effect='仅影响独立模拟账本。' if w.get('action') else '生成规划和业务卡片，无资金变动。',
        limitations=['无真实银行数据或资金转移','不提供隐藏思维链或模型置信度','DAG 节点为规划；真实执行以审计时间线为准'],
        data_source='server workflow + synthetic ledger + deterministic policy',timestamp=w.get('analysis_at',w.get('created_at',utcnow())),
        model_status=w.get('model_status','NOT_USED_RULE_ENGINE'),ai_suggestion=w.get('semantic_intent','未使用语义模型'),
        safety_engine_decision=state,calculation={'amount_cents':w.get('amount_cents',0),'planning_snapshot':w.get('planning_snapshot',{}),'sandbox':sandbox})


def save_decision(conn,w):
    doc=decision_for(w).model_dump()
    conn.execute('INSERT INTO decision_documents VALUES (?,?) ON CONFLICT(workflow_id) DO UPDATE SET payload=excluded.payload',(w['workflow_id'],canonical(doc)))


def trace(action,metadata=None,workflow_id=None,task_id=None,node_id=None,status='SUCCESS'):
    wid=workflow_id or trace_workflow.get()
    if not wid:return
    audit.append(principal(),action,workflow_id=wid,task_id=task_id,status=status,
                 metadata={'node_id':node_id,**(metadata or {})})


def persist_bus_event(task_id,event,data):
    with db.connect() as c:
        row=c.execute('SELECT workflow_id FROM workflows WHERE task_id=?',(task_id,)).fetchone()
    if row:
        trace('agent_stream_event',{'event':event,'payload':data},workflow_id=row['workflow_id'],task_id=task_id,
              status='FAILED' if event=='task_error' else 'SUCCESS')


class TraceEvent(StrictModel):
    sequence: int
    event_id: str
    timestamp: str
    event: str
    status: str
    duration_ms: float
    actor_id: str
    details: dict[str,JsonValue]
    reason: str | None=None


class TraceResponse(StrictModel):
    workflow_id: str
    read_only: Literal[True]=True
    events: list[TraceEvent]
    elapsed_ms: float
    node_states: dict[str,str]
    next_cursor: int


@router.get('/api/workflows/{workflow_id}/decision',response_model=Decision)
def explain(workflow_id:str):
    w=gateway.act(principal(),workflow_id,'read')
    audit.append(principal(),'decision_viewed',workflow_id=workflow_id)
    return decision_for(w)


@router.get('/api/workflows/{workflow_id}/trace',response_model=TraceResponse)
def replay(workflow_id:str,cursor:int=0):
    if cursor<0:raise HTTPException(422,'Invalid cursor')
    w=gateway.act(principal(),workflow_id,'read')
    batch=audit.list(principal(),500,cursor,workflow_id=workflow_id)
    names={'agent_routed':'DOMAIN_AGENT_SELECTED','hitl_required':'HUMAN_REVIEW_REQUESTED','human_review_completed':'HUMAN_REVIEW_COMPLETED'}
    events=[];states={n.get('task_id',n.get('id','unknown')):'PLANNED_NOT_EXECUTED' for n in w.get('nodes',[])}
    for x in batch['items']:
        details=json.loads(x['metadata_json']);name=names.get(x['action'],x['action'].upper())
        events.append(TraceEvent(sequence=x['sequence'],event_id=x['event_id'],timestamp=x['timestamp_utc'],event=name,status=x['status'],duration_ms=x['duration_ms'],actor_id=x['actor_id'],details=details,reason=x['reason']))
        if details.get('node_id'):states[details['node_id']]=name
    from datetime import datetime
    elapsed=(datetime.fromisoformat(events[-1].timestamp)-datetime.fromisoformat(events[0].timestamp)).total_seconds()*1000 if len(events)>1 else 0
    audit.append(principal(),'trace_viewed',workflow_id=workflow_id)
    return TraceResponse(workflow_id=workflow_id,events=events,elapsed_ms=elapsed,node_states=states,next_cursor=batch['next_cursor'])


Money=Decimal
class CashEvent(StrictModel):
    day: int=Field(ge=1,le=30)
    amount: Money=Field(ge=0,le=100000000,max_digits=11,decimal_places=2)


class TwinInput(StrictModel):
    new_spending: Money=Field(default=0,ge=0,le=100000000,max_digits=11,decimal_places=2)
    expected_income: Money=Field(default=0,ge=0,le=100000000,max_digits=11,decimal_places=2)
    extra_expense: Money=Field(default=0,ge=0,le=100000000,max_digits=11,decimal_places=2)
    spending_day: int=Field(default=10,ge=1,le=30)
    income_day: int=Field(default=25,ge=1,le=30)
    known_income: list[CashEvent]=Field(default_factory=list,max_length=100)
    known_expense: list[CashEvent]=Field(default_factory=list,max_length=100)


class DailyPoint(StrictModel):
    day:int
    date:str
    balance_cents:int
    gap_cents:int


class Scenario(StrictModel):
    name: str
    assumptions: str
    points:list[DailyPoint]
    min_balance_cents:int
    gap_cents:int


class TwinResponse(StrictModel):
    scenario_id:str
    status:Literal['SIMULATED']='SIMULATED'
    inputs:TwinInput|None=None
    balance_cents:int
    reserve_cents:int
    data_source:str
    scenarios:list[Scenario]
    assumptions:list[str]
    timestamp:str


def account_snapshot(actor,conn):
    row=conn.execute('SELECT * FROM simulated_accounts WHERE actor_id=?',(actor.actor_id,)).fetchone()
    if row:return row['balance_cents'],row['reserved_cents'],'persistent simulated ledger'
    balance=gateway.sandbox.cents(os.getenv('SIMULATED_INITIAL_BALANCE',os.getenv('DEMO_BALANCE','10000')))
    reserves=sum(gateway.sandbox.cents(os.getenv(k,v)) for k,v in [('DEMO_MORTGAGE','3000'),('DEMO_DAILY_EXPENSE','2000'),('DEMO_MIN_LIQUIDITY','1000')])
    return balance,reserves,'configured synthetic opening balance; no ledger history yet'


def calculate_twin(body,actor,conn):
    balance,reserve,source=account_snapshot(actor,conn);scenarios=[]
    for name,income_scale,expense_scale,delay in [('保守',Decimal('.8'),Decimal('1.1'),0),('基准',Decimal('1'),Decimal('1'),0),('压力',Decimal('.5'),Decimal('1.3'),5)]:
        current=balance;points=[]
        for day in range(1,31):
            incoming=sum(int(x.amount*100) for x in body.known_income if x.day==day)
            outgoing=sum(int(x.amount*100) for x in body.known_expense if x.day==day)
            if day==body.income_day+delay:incoming+=int(body.expected_income*100*income_scale)
            if day==body.spending_day:outgoing+=int((body.new_spending+body.extra_expense)*100*expense_scale)
            current+=incoming-outgoing
            points.append(DailyPoint(day=day,date=str(date.today()+timedelta(days=day)),balance_cents=current,gap_cents=max(0,reserve-current)))
        minimum=min([balance]+[x.balance_cents for x in points])
        scenarios.append(Scenario(name=name,assumptions=f'预计收入系数={income_scale}；新增/额外支出系数={expense_scale}；预计收入延后{delay}日；已知事件保持输入值。',points=points,min_balance_cents=minimum,gap_cents=max(0,reserve-minimum)))
    return TwinResponse(scenario_id=uuid.uuid4().hex,inputs=body,balance_cents=balance,reserve_cents=reserve,data_source=source,scenarios=scenarios,
        assumptions=['30天离散模拟；无历史数据推断','预留作为安全边界，不重复扣款；已知实际模拟支出请按日期输入','超过30天的延迟收入不计入窗口','不含利息、收益、随机预测或真实银行信息'],timestamp=utcnow())


@router.post('/api/financial/digital-twin/simulate',response_model=TwinResponse)
def simulate(body:TwinInput):
    actor=principal()
    with db.transaction() as conn:
        result=calculate_twin(body,actor,conn)
        conn.execute('INSERT INTO financial_scenarios VALUES (?,?,?,?,?)',(result.scenario_id,actor.actor_id,result.timestamp,body.model_dump_json(),result.model_dump_json()))
        audit.append(actor,'digital_twin_simulated',conn=conn,metadata={'scenario_id':result.scenario_id,'assumptions':result.assumptions})
    return result


@router.get('/api/financial/digital-twin/{scenario_id}',response_model=TwinResponse)
def saved_scenario(scenario_id:str):
    actor=principal()
    with db.connect() as c:row=c.execute('SELECT * FROM financial_scenarios WHERE scenario_id=? AND actor_id=?',(scenario_id,actor.actor_id)).fetchone()
    if not row:raise HTTPException(404,'Scenario not found for this identity')
    audit.append(actor,'digital_twin_viewed',metadata={'scenario_id':scenario_id})
    return TwinResponse.model_validate_json(row['response_json'])


class FraudInput(StrictModel):
    amount:Money=Field(ge=0,le=100000000,max_digits=11,decimal_places=2)
    recipient:str=Field(min_length=1,max_length=64)
    threshold:Money=Field(default=50000,gt=0,le=100000000,max_digits=11,decimal_places=2)
    idempotency_key:uuid.UUID
    workflow_id:str|None=Field(default=None,max_length=64)


class RiskFactor(StrictModel):
    rule:str
    explanation:str
    blocking:bool


class FraudResponse(StrictModel):
    risk_id:str
    risk_level:Literal['LOW','MEDIUM','HIGH']
    risk_factors:list[RiskFactor]
    triggered_rules:list[str]
    recommended_action:str
    permission_decision:Literal['BLOCK','REVIEW_REQUIRED','MFA_REQUIRED']
    requires_human_review:bool
    assessment_only:Literal[True]=True
    timestamp:str


@router.post('/api/security/fraud-assess',response_model=FraudResponse)
def assess(body:FraudInput):
    actor=principal();factors=[];amount=int(body.amount*100)
    def add(rule,reason,block=False):factors.append(RiskFactor(rule=rule,explanation=reason,blocking=block))
    with db.transaction() as c:
        balance,reserve,_=account_snapshot(actor,c)
        w=gateway.load(c,body.workflow_id,actor) if body.workflow_id else None
        if amount>5000000:add('LARGE_AMOUNT','超过50000元，必须独立主管审批。')
        if body.amount>body.threshold:add('USER_THRESHOLD','超过本次用户情景阈值，建议停止并复核。',True)
        if body.recipient!='demo-recipient':add('RECIPIENT_ALLOWLIST','收款对象不在独立模拟转账白名单。',True)
        if balance-amount<reserve:add('RESERVE_BREACH','扣款后余额低于保护性预留。',True)
        row=c.execute('SELECT payload FROM workflows WHERE actor_id=? AND json_extract(payload,\'$.idempotency_key\')=?',(actor.actor_id,str(body.idempotency_key))).fetchone()
        if row:
            old=json.loads(row['payload']);add('REPEATED_REQUEST','同一身份已经使用该幂等键；不可重复扣款。')
            if old.get('amount_cents')!=amount or old.get('recipient')!=body.recipient or old.get('action')!='transfer.simulate':add('IDEMPOTENCY_CONFLICT','原幂等键绑定不同交易内容。',True)
        if w and (w.get('amount_cents')!=amount or w.get('recipient')!=body.recipient or w.get('idempotency_key')!=str(body.idempotency_key)):add('PLAN_MISMATCH','评估输入与工作流绑定计划不同。',True)
        if not w or not w.get('mfa_verified'):add('MAKER_MFA_MISSING','尚无本工作流服务端 MFA 记录。')
        if w and w['state'] in {'FAILED','REJECTED'}:add('TERMINAL_STATE','工作流已终止，无法继续授权。',True)
        block=any(x.blocking for x in factors);human=amount>5000000 or block
        result=FraudResponse(risk_id=uuid.uuid4().hex,risk_level='HIGH' if human else 'MEDIUM',risk_factors=factors,triggered_rules=[x.rule for x in factors],recommended_action='停止本次请求，人工核查；不解除现有网关限制。' if human else '经真实服务端工作流完成 Maker MFA 后再请求模拟执行。',permission_decision='BLOCK' if block else 'REVIEW_REQUIRED' if human else 'MFA_REQUIRED',requires_human_review=human,timestamp=utcnow())
        audit.append(actor,'fraud_assessed',conn=c,workflow_id=body.workflow_id,permission_level='RED',status=result.permission_decision,metadata=result.model_dump())
    return result


class HealthInput(StrictModel):
    scenario_id:str|None=Field(default=None,max_length=64)
    monthly_income:Money|None=Field(default=None,ge=0,le=100000000,max_digits=11,decimal_places=2)


class Metric(StrictModel):
    name:str
    value:float|int|None
    unit:str
    formula:str
    status:Literal['AVAILABLE','INSUFFICIENT_DATA']


class HealthResponse(StrictModel):
    report_id:str
    status:Literal['SIMULATED_REPORT']='SIMULATED_REPORT'
    metrics:list[Metric]
    risks:list[str]
    recommendations:list[str]
    limitations:list[str]
    timestamp:str


@router.post('/api/financial/health-report',response_model=HealthResponse)
def health_report(body:HealthInput):
    actor=principal()
    with db.transaction() as c:
        balance,reserve,source=account_snapshot(actor,c)
        rows=c.execute('SELECT amount_cents,recipient FROM simulated_entries WHERE actor_id=?',(actor.actor_id,)).fetchall()
        total=sum(x['amount_cents'] for x in rows);groups={}
        for x in rows:groups[x['recipient']]=groups.get(x['recipient'],0)+x['amount_cents']
        scenario=None
        if body.scenario_id:
            row=c.execute('SELECT response_json FROM financial_scenarios WHERE scenario_id=? AND actor_id=?',(body.scenario_id,actor.actor_id)).fetchone()
            if not row:raise HTTPException(404,'Scenario not found')
            scenario=TwinResponse.model_validate_json(row['response_json'])
        def m(name,value,unit,formula):return Metric(name=name,value=value,unit=unit,formula=formula,status='AVAILABLE' if value is not None else 'INSUFFICIENT_DATA')
        metrics=[m('可用流动性',balance-reserve,'分','当前模拟余额 - 保护性预留'),m('储备覆盖率',round(balance/reserve,4) if reserve else None,'倍','当前模拟余额 / 保护性预留'),
            m('已记录模拟支出',total if rows else None,'分','当前账本全部模拟资金流出合计；不是月度消费'),
            m('支出集中度',round(max(groups.values())/total,4) if total else None,'比例','最大模拟收款对象流出 / 已记录模拟总流出'),
            m('用户提供月收入',int(body.monthly_income*100) if body.monthly_income is not None else None,'分','用户本次显式输入；未验证'),
            m('月度收支比',None,'比例','缺少完整月度历史收支，不能用演示流水推断'),
            m('未来30天最大安全缺口',max(x.gap_cents for x in scenario.scenarios) if scenario else None,'分','三种情景 max(预留 - 最低余额,0)')]
        risks=['历史收支数据不足，不生成综合评分。']
        if balance<reserve:risks.append('当前余额低于保护性预留。')
        if scenario and any(x.gap_cents for x in scenario.scenarios):risks.append('输入情景存在未来资金安全缺口。')
        result=HealthResponse(report_id=uuid.uuid4().hex,metrics=metrics,risks=risks,recommendations=['优先保障房贷、日常开销及最低流动性。','补充准确日期的模拟收入和支出后重新推演。'],limitations=[source,'仅本地模拟，不是投资建议或真实银行财务评级','收款对象集中度不是消费类别集中度；禁止据此推断真实消费习惯'],timestamp=utcnow())
        audit.append(actor,'health_report_generated',conn=c,metadata={'report_id':result.report_id,'metrics':len(metrics)})
    return result


initialize()
