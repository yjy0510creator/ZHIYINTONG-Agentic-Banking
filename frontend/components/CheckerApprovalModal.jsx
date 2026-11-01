import {useState} from 'react';
import {bankingRequest} from './bankingClient';

export default function CheckerApprovalModal({workflow,onUpdate,onClose,onExecute}) {
  const [password,setPassword]=useState(''),[reason,setReason]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function review(decision) {
    setBusy(true);setError('');
    try {
      const login=await bankingRequest('/api/dev/login',{username:'checker',password},'');
      const next=await bankingRequest(`/api/workflows/${workflow.workflow_id}/human-review`,{decision,reason,plan_hash:workflow.plan_hash},login.access_token);
      setPassword('');onUpdate(next);
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function submit() {
    try {onUpdate(await bankingRequest(`/api/workflows/${workflow.workflow_id}/submit-review`,{}));} catch(e){setError(e.message);}
  }
  return <div className="modal-backdrop"><section className="mfa-modal" role="dialog" aria-modal="true" aria-label="高风险交易 · 双人复核">
    <button className="modal-close" onClick={onClose} aria-label="关闭复核">×</button>
    <h2>高风险交易 · 双人复核</h2><p className="soft-note">仅建立本机人工复核任务，未联系真实银行客服。</p>
    <dl className="text-[12px] leading-6">
      <dt>交易金额 / 对象</dt><dd>¥ {workflow.amount_cents/100} / {workflow.recipient}</dd>
      <dt>风险 / 沙箱</dt><dd>{workflow.permission_level} / {workflow.sandbox?.sandbox_status}</dd>
      <dt>Maker / Checker</dt><dd>{workflow.actor_id} / {workflow.checker_id || '尚未审批'}</dd>
      <dt>审批状态 / 时间</dt><dd>{workflow.state} / {workflow.reviewed_at || '—'}</dd>
      <dt>审批意见</dt><dd>{workflow.review_reason || '—'}</dd>
    </dl>
    {workflow.state==='PENDING_HUMAN_REVIEW' && <button className="primary-button" onClick={submit}>提交主管复核</button>}
    {workflow.state==='AWAITING_CHECKER' && <div className="space-y-3 mt-3">
      <input type="password" aria-label="独立主管开发口令" placeholder="独立主管开发口令" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="off"/>
      <textarea aria-label="人工审核意见" placeholder="人工审核意见" value={reason} onChange={e=>setReason(e.target.value)} maxLength={500}/>
      <div className="flex gap-2"><button className="primary-button" disabled={busy||!reason.trim()} onClick={()=>review('APPROVE')}>主管批准</button><button className="danger-button" disabled={busy||!reason.trim()} onClick={()=>review('REJECT')}>主管拒绝</button></div>
    </div>}
    {workflow.state==='APPROVED' && <button className="primary-button" onClick={onExecute}>执行已授权模拟交易</button>}
    {workflow.state==='REJECTED' && <p role="alert">审批拒绝；本工作流永久禁止执行。</p>}
    {error && <p role="alert">{error}</p>}
  </section></div>;
}
