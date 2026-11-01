import asyncio
import json
import os
import time
from pathlib import Path
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from .database import Database
from .auth_service import AuthService, Actor, current_actor
from .audit_service import AuditService, AuditUnavailable
from .idempotency_service import IdempotencyService
from .execution_gateway import ExecutionGateway

db = Database(os.getenv('BANKING_DB_PATH',str(Path(__file__).resolve().parents[1]/'data'/'zhiyintong_audit.db')))
audit = AuditService(db)
auth = AuthService(db)
gateway = ExecutionGateway(db,audit,IdempotencyService(db))
router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LoginRequest(StrictModel):
    username: Literal['maker','checker','customer2']
    password: str = Field(min_length=1,max_length=256)


class TransactionRequest(StrictModel):
    action: Literal['wealth.subscribe','transfer.simulate','card.freeze','subscription.cancel']
    amount: str = Field(default='0',max_length=24)
    recipient: str = Field(min_length=1,max_length=64)
    idempotency_key: UUID


class ExecuteRequest(StrictModel):
    idempotency_key: UUID


class ApprovalRequest(StrictModel):
    decision: Literal['APPROVE','REJECT']
    reason: str = Field(min_length=1,max_length=500)
    plan_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class ConfirmationRequest(StrictModel):
    confirmed: bool


def principal():
    actor = current_actor.get()
    if not actor: raise HTTPException(401,'Authentication required')
    return actor


class IdentityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if not (path.startswith('/api/') or path.startswith('/mcp')) or path=='/api/dev/login' or request.method=='OPTIONS':
            return await call_next(request)
        started=time.perf_counter()
        try:
            actor=auth.authenticate(request.headers.get('authorization'))
        except HTTPException as exc:
            try:
                audit.append(Actor('anonymous','unauthenticated','no-session'),'authentication_rejected',
                             status='REJECTED',reason=str(exc.detail),metadata={'path':path},
                             duration_ms=(time.perf_counter()-started)*1000)
            except AuditUnavailable:
                return JSONResponse({'detail':'Audit unavailable; access denied'},status_code=503)
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        token=current_actor.set(actor)
        try:
            if path.startswith('/api/stream/'):
                task_id=path.rsplit('/',1)[-1]
                with db.connect() as conn:
                    row=conn.execute('SELECT actor_id FROM workflows WHERE task_id=?',(task_id,)).fetchone()
                if not row or (row['actor_id']!=actor.actor_id and actor.actor_role!='supervisor'):
                    raise HTTPException(404,'Task stream not found for this identity')
            # Financial request pre-audit: storage failure prevents reaching the handler.
            if request.method=='POST':
                audit.append(actor,'request_received',metadata={'path':path})
            response=await call_next(request)
            if request.method=='POST' and not (path.startswith('/api/workflows/') and path.endswith('/execute') and response.status_code<400):
                action='security_screened' if path in {'/api/security-check','/api/analyze'} else 'api_request_completed'
                audit.append(actor,action,status='SUCCESS' if response.status_code<400 else 'REJECTED',
                             duration_ms=(time.perf_counter()-started)*1000,metadata={'path':path,'http_status':response.status_code})
            return response
        except AuditUnavailable:
            return JSONResponse({'detail':'Audit unavailable; writes are blocked'},status_code=503)
        except HTTPException as exc:
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        finally:
            current_actor.reset(token)


@router.post('/api/dev/login')
def login(body: LoginRequest):
    try:
        token,actor=auth.login(body.username,body.password)
    except HTTPException as exc:
        audit.append(Actor('anonymous','unauthenticated','no-session'),'development_login_rejected',
                     status='REJECTED',reason=str(exc.detail))
        raise
    audit.append(actor,'development_login',metadata={'simulation_only':True})
    return {'access_token':token,'actor_id':actor.actor_id,'actor_role':actor.actor_role,'development_only':True}


@router.get('/api/session')
def session():
    return {**vars(principal()),'development_only':True}


@router.post('/api/transactions',status_code=201)
def prepare(body: TransactionRequest):
    try:
        return gateway.prepare(principal(),body.action,body.amount,body.recipient,str(body.idempotency_key))
    except ValueError as exc:
        raise HTTPException(422,str(exc))


@router.get('/api/workflows/{workflow_id}')
def workflow(workflow_id: str):
    return gateway.act(principal(),workflow_id,'read')


@router.post('/api/workflows/{workflow_id}/maker-confirm')
def maker_confirm(workflow_id: str,body: ConfirmationRequest):
    return gateway.act(principal(),workflow_id,'confirm',confirmed=body.confirmed)


@router.post('/api/workflows/{workflow_id}/submit-review')
def submit_review(workflow_id: str):
    return gateway.act(principal(),workflow_id,'submit-review')


@router.post('/api/workflows/{workflow_id}/human-review')
def human_review(workflow_id: str,body: ApprovalRequest):
    return gateway.act(principal(),workflow_id,body.decision,reason=body.reason,plan_hash=body.plan_hash)


@router.get('/api/simulation/account')
def account():
    with db.connect() as conn:
        actor=principal()
        row=conn.execute('SELECT * FROM simulated_accounts WHERE actor_id=?',(actor.actor_id,)).fetchone()
        objects=[dict(x) for x in conn.execute('SELECT object_id,status FROM simulated_objects WHERE actor_id=?',(actor.actor_id,))]
    return {'account':dict(row) if row else None,'objects':objects,'simulated_only':True}


@router.get('/api/audit-logs')
def audit_logs(limit: int=Query(100,ge=1,le=500),cursor: int=Query(0,ge=0),workflow_id: str|None=None,
               actor_id: str|None=None,permission_level: Literal['GREEN','YELLOW','RED']|None=None,status: str|None=None):
    return audit.list(principal(),limit,cursor,workflow_id=workflow_id,actor_id=actor_id,
                      permission_level=permission_level,status=status)


async def persistent_events(request,actor,cursor,workflow_id=None,workflow_events=False):
    idle=0
    while not await request.is_disconnected():
        # Enforce expiry and production revocation during long-lived streams.
        auth.authenticate(request.headers.get('authorization'))
        batch=audit.list(actor,100,cursor,workflow_id=workflow_id)
        for item in batch['items']:
            cursor=item['sequence']
            metadata=json.loads(item['metadata_json'])
            payload={**item,'timestamp':item['timestamp_utc'],'metadata':metadata}
            name=item['action'] if workflow_events else 'audit_event'
            yield f"id: {cursor}\nevent: {name}\ndata: {json.dumps(payload,ensure_ascii=False)}\n\n"
        if not batch['items']:
            idle+=1
            if idle%30==0: yield ': keep-alive\n\n'
            await asyncio.sleep(.5)


def stream_response(request,actor,cursor,workflow_id=None,workflow_events=False):
    try: cursor=max(cursor,int(request.headers.get('last-event-id','0')))
    except ValueError: raise HTTPException(422,'Invalid Last-Event-ID')
    return StreamingResponse(persistent_events(request,actor,cursor,workflow_id,workflow_events),
                             media_type='text/event-stream',headers={'Cache-Control':'no-cache, no-transform','X-Accel-Buffering':'no'})


@router.get('/api/audit-stream')
def audit_stream(request: Request,cursor: int=Query(0,ge=0),workflow_id: str|None=None):
    return stream_response(request,principal(),cursor,workflow_id)


@router.get('/api/workflows/{workflow_id}/stream')
def workflow_stream(workflow_id: str,request: Request,cursor: int=Query(0,ge=0)):
    gateway.act(principal(),workflow_id,'read')
    return stream_response(request,principal(),cursor,workflow_id,True)
