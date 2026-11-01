import { useEffect, useRef, useState } from 'react';
import { API_BASE, bankingRequest, AuthenticatedEventSource } from './bankingClient';

export default function AuditConsole({workflowId}) {
  const [items,setItems]=useState([]), [level,setLevel]=useState(''), [onlyWorkflow,setOnlyWorkflow]=useState(false);
  const [connection,setConnection]=useState('连接中'); const listRef=useRef(null);
  useEffect(()=>{
    let cancelled=false, source; let cursor=0;
    const filter=onlyWorkflow && workflowId ? `&workflow_id=${encodeURIComponent(workflowId)}` : '';
    const merge=batch=>{ if(!cancelled) setItems(old=>Array.from(new Map([...old,...batch].map(x=>[x.event_id,x])).values()).sort((a,b)=>a.sequence-b.sequence).slice(-500)); };
    async function catchUp() {
      try {
        for (;;) {
          const data=await bankingRequest(`/api/audit-logs?limit=100&cursor=${cursor}${filter}`);
          if(cancelled)return; merge(data.items); cursor=data.next_cursor;
          if(data.items.length<100)break;
        }
      } catch(e) { if(!cancelled)setConnection(`未连接：${e.message}`); }
    }
    function connect() {
      source?.close(); cursor=0; setItems([]); catchUp();
      source=new AuthenticatedEventSource(`${API_BASE}/api/audit-stream?cursor=0${filter}`);
      source.onopen=()=>{setConnection('实时连接');catchUp();};
      source.onerror=()=>{setConnection('重连中 · API 补偿');catchUp();};
      source.addEventListener('audit_event',e=>merge([JSON.parse(e.data)]));
    }
    connect(); window.addEventListener('banking-auth-changed',connect);
    return()=>{cancelled=true;source?.close();window.removeEventListener('banking-auth-changed',connect);};
  },[workflowId,onlyWorkflow]);
  useEffect(()=>{ if(listRef.current) listRef.current.scrollTop=listRef.current.scrollHeight; },[items.length]);
  return <div id="audit-panel" className="surface audit-card">
    <div className="section-title">操作审计控制台</div><div className="section-caption">REAL-TIME AUDIT TRAIL</div>
    <div className="section-caption">RED ALLOW ≠ 最终执行授权；请核对同一工作流的 MFA、审批与执行事件。</div>
    <div className="section-caption" role="status">{connection}</div>
    <select aria-label="审计权限过滤" value={level} onChange={e=>setLevel(e.target.value)} className="text-[10px] mt-2">
      <option value="">全部权限</option>{['GREEN','YELLOW','RED'].map(x=><option key={x}>{x}</option>)}
    </select>
    <label className="text-[9px] block mt-2"><input type="checkbox" checked={onlyWorkflow} onChange={e=>setOnlyWorkflow(e.target.checked)} /> 当前工作流</label>
    <div ref={listRef} className="audit-list" style={{maxHeight:420,overflow:'auto'}}>
      {items.filter(x=>!level||x.permission_level===level).map(x=><details className="audit-row" style={{display:'block'}} key={x.event_id}>
        <summary><span className={`permission-pill permission-${x.permission_level.toLowerCase()}`}>{x.permission_level}</span> {x.action}<br/>{x.actor_id} · {x.status} · {Number(x.duration_ms).toFixed(1)} ms<br/>{new Date(x.timestamp_utc).toLocaleString('zh-CN')}</summary>
        {x.action==='trust_decision' && <p className="text-[10px]">TrustEngine 局部策略判定；ALLOW 不代表最终执行许可，仍须通过沙箱、Maker MFA 及必要的独立 Checker 审批。</p>}
        {['execution_started','execution_completed'].includes(x.action) && <p className="text-[10px]">网关授权后的独立模拟账本事件；不是实际银行交易。</p>}
        <p>{x.intent || '—'}</p><p>{x.reason}</p><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(x,null,2)}</pre>
      </details>)}
      {!items.length && <div className="audit-empty">暂无后端审计记录。请先登录。</div>}
    </div>
  </div>;
}
