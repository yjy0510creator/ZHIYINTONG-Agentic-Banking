import React, {useEffect,useRef,useState} from 'react';
import ReactECharts from 'echarts-for-react';
import {createPortal} from 'react-dom';
import {bankingRequest, API_BASE, AuthenticatedEventSource} from './bankingClient';
import styles from './IntelligencePanels.module.css';

const money=v=>v==null?'数据不足':`¥${(v/100).toLocaleString('zh-CN',{maximumFractionDigits:2})}`;
function ErrorLine({error,busy}) {return <>{busy&&<p role="status">正在读取服务端数据…</p>}{error&&<p role="alert" className={styles.error}>{error}</p>}</>;}
function Json({data}) {return <pre className={styles.json}>{JSON.stringify(data,null,2)}</pre>;}
function Panel({title,id,children}) {return <details id={id} className={`surface ${styles.panel}`}><summary>{title}</summary>{children}</details>;}
function download(data,name) {const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}

export function AssistantInsights({workflowId}) {
  const [decision,setDecision]=useState(null),[open,setOpen]=useState(false),[report,setReport]=useState(null),[income,setIncome]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const lock=useRef(false);
  useEffect(()=>{setDecision(null);setReport(null);},[workflowId]);
  async function request(kind) {
    if(lock.current)return;lock.current=true;setBusy(true);setError('');
    try {
      if(kind==='decision'){setDecision(await bankingRequest(`/api/workflows/${workflowId}/decision`));setOpen(true);}
      else setReport(await bankingRequest('/api/financial/health-report',{monthly_income:income===''?null:income,scenario_id:sessionStorage.getItem('banking-twin-scenario')||null}));
    }catch(e){setError(e.message);}finally{lock.current=false;setBusy(false);}
  }
  return <Panel title="决策解释与财务健康报告" id="decision-center">
    <p>只展示可审计依据，不展示隐藏思维链，也不生成虚构置信度。</p>
    <div className={styles.actions}><button className="secondary-button" disabled={!workflowId||busy} onClick={()=>request('decision')}>为什么这样决策？</button>
      <label>月收入假设（可留空）<input aria-label="健康报告月收入" type="number" min="0" value={income} onChange={e=>setIncome(e.target.value)}/></label>
      <button className="secondary-button" disabled={busy} onClick={()=>request('report')}>生成财务健康报告</button></div>
    {!workflowId&&<p>先完成一次金融任务，即可查看节点解释。</p>}<ErrorLine error={error} busy={busy}/>
    {report&&<div id="financial-health-print"><h3>模拟财务健康报告</h3><div className={styles.metrics}>{report.metrics.map(m=><article key={m.name}><small>{m.name}</small><strong>{m.value==null?'数据不足':m.unit==='分'?money(m.value):`${m.value} ${m.unit}`}</strong><p>{m.formula}</p></article>)}</div>
      {report.risks.map(x=><p key={x}>{x}</p>)}{report.recommendations.map(x=><p key={x}>建议：{x}</p>)}{report.limitations.map(x=><small key={x} className={styles.line}>{x}</small>)}
      <div className={styles.actions}><button className="secondary-button" onClick={()=>download(report,'financial-health.json')}>导出 JSON</button><button className="secondary-button" onClick={()=>window.print()}>打印报告</button></div></div>}
    {open&&decision&&typeof document!=='undefined'&&createPortal(<div className={styles.overlay} onClick={()=>setOpen(false)}><section className={styles.drawer} role="dialog" aria-modal="true" aria-label="决策解释抽屉" onClick={e=>e.stopPropagation()}>
      <button className="secondary-button" autoFocus onClick={()=>setOpen(false)}>关闭解释</button><h2>为什么这样决策？</h2><p>{decision.intent}</p>
      <p>语义来源：{decision.model_status}</p><p>AI 建议：{decision.ai_suggestion}</p><p>安全引擎最终状态：{decision.safety_engine_decision}</p><p>{decision.decision_reason}</p>
      <h3>触发规则</h3>{decision.triggered_rules.map((x,i)=><span className={styles.tag} key={i}>{x}</span>)}<h3>逐 DAG 节点依据</h3>
      {decision.evidence.map(n=><details key={n.node_id}><summary>{n.node_id} · {n.action} · {n.permission_level}</summary><p>{n.reason}</p><p>{n.status} · 金额：{n.amount??'不适用'}</p></details>)}
      <h3>模拟资金计算依据</h3><Json data={decision.calculation}/>{decision.limitations.map(x=><p key={x}>{x}</p>)}</section></div>,document.body)}
  </Panel>;
}

export function TwinPanel() {
  const [form,setForm]=useState({new_spending:'0',expected_income:'0',extra_expense:'0',spending_day:10,income_day:25,known_income:[],known_expense:[]});
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[active,setActive]=useState(false);
  const generation=useRef(0);
  useEffect(()=>{if(!active)return;const id=++generation.current;const timer=setTimeout(async()=>{setBusy(true);setError('');try{const next=await bankingRequest('/api/financial/digital-twin/simulate',form);if(id===generation.current){setResult(next);sessionStorage.setItem('banking-twin-scenario',next.scenario_id);}}catch(e){if(id===generation.current)setError(e.message);}finally{if(id===generation.current)setBusy(false);}},500);return()=>{clearTimeout(timer);generation.current++;};},[form,active]);
  useEffect(()=>{const restore=async()=>{const id=sessionStorage.getItem('banking-twin-scenario');if(id)try{const saved=await bankingRequest(`/api/financial/digital-twin/${id}`);setResult(saved);if(saved.inputs)setForm(saved.inputs);}catch{sessionStorage.removeItem('banking-twin-scenario');}};restore();window.addEventListener('banking-auth-changed',restore);return()=>window.removeEventListener('banking-auth-changed',restore);},[]);
  const labels={new_spending:'新增消费（元）',expected_income:'预计收入（元）',extra_expense:'额外支出（元）',spending_day:'消费发生日（未来第几日）',income_day:'预计收入日'};
  return <Panel title="个人财务数字孪生 · 30天模拟" id="digital-twin-panel"><p>余额来自服务端模拟账本。预留是安全边界，不重复扣款；没有历史预测。修改后自动重新计算。</p>
    <div className={styles.grid}>{Object.entries(labels).map(([k,label])=><label key={k}>{label}<input aria-label={label} type="number" min={k.endsWith('day')?1:0} max={k.endsWith('day')?30:100000000} step={k.endsWith('day')?1:0.01} value={form[k]} onChange={e=>{setForm({...form,[k]:k.endsWith('day')?Number(e.target.value):e.target.value});setActive(true);}}/></label>)}</div>
    {['known_income','known_expense'].map(k=><div key={k}><h4>{k==='known_income'?'已知模拟收入':'已知模拟支出'}</h4>{form[k].map((x,i)=><div className={styles.actions} key={i}><label>第几日<input aria-label={`${k}-${i}-day`} type="number" min="1" max="30" value={x.day} onChange={e=>{setForm({...form,[k]:form[k].map((v,j)=>j===i?{...v,day:Number(e.target.value)}:v)});setActive(true);}}/></label><label>金额<input aria-label={`${k}-${i}-amount`} type="number" min="0" value={x.amount} onChange={e=>{setForm({...form,[k]:form[k].map((v,j)=>j===i?{...v,amount:e.target.value}:v)});setActive(true);}}/></label><button onClick={()=>{setForm({...form,[k]:form[k].filter((_,j)=>i!==j)});setActive(true);}}>移除</button></div>)}<button className="secondary-button" onClick={()=>setForm({...form,[k]:[...form[k],{day:1,amount:'0'}]})}>添加{k==='known_income'?'收入':'支出'}</button></div>)}
    <button className="primary-button" disabled={busy} onClick={()=>{setActive(true);setForm({...form});}}>运行模拟</button><ErrorLine error={error} busy={busy}/>
    {result&&<><p>当前余额 {money(result.balance_cents)} · 安全边界 {money(result.reserve_cents)}</p><ReactECharts style={{height:290}} option={{tooltip:{trigger:'axis'},color:['#79a8c9','#2a94c4','#e28d9e'],legend:{top:0,data:result.scenarios.map(x=>x.name)},grid:{top:48,left:65,right:25,bottom:40},xAxis:{type:'category',data:result.scenarios[0].points.map(x=>x.day+'日')},yAxis:{type:'value',name:'模拟余额 / 元'},series:result.scenarios.map(x=>({name:x.name,type:'line',data:x.points.map(p=>p.balance_cents/100),markLine:{symbol:'none',label:{position:'insideEndTop',formatter:'保护性预留'},lineStyle:{color:'#7b8fa1',type:'dashed'},data:[{yAxis:result.reserve_cents/100,name:'安全边界'}]}}))}}/>
      <div className={styles.metrics}>{result.scenarios.map(x=><article key={x.name}><strong>{x.name}</strong><p>最低余额 {money(x.min_balance_cents)}</p><p>最大安全缺口 {money(x.gap_cents)}</p><small>{x.assumptions}</small></article>)}</div>{result.assumptions.map(x=><small className={styles.line} key={x}>{x}</small>)}</>}
  </Panel>;
}

export function FraudPanel({workflow,onRisk}) {
  const [amount,setAmount]=useState('50001'),[recipient,setRecipient]=useState('demo-recipient'),[threshold,setThreshold]=useState('50000');
  const [risk,setRisk]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');const lock=useRef(false),key=useRef(null);
  async function assess(){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{key.current=key.current||crypto.randomUUID();const r=await bankingRequest('/api/security/fraud-assess',{amount,recipient,threshold,idempotency_key:workflow?.idempotency_key||key.current,workflow_id:workflow?.workflow_id||null});setRisk(r);if(r.requires_human_review)onRisk();}catch(e){setError(e.message);}finally{lock.current=false;setBusy(false);}}
  useEffect(()=>{if(workflow?.action==='transfer.simulate'){setAmount(String(workflow.amount_cents/100));setRecipient(workflow.recipient);}},[workflow?.workflow_id]);
  return <Panel title="智能反诈中心 · 本地规则评估"><p>仅评估，不创建转账、不发放执行许可；用户阈值只用于本次评估。既有 MFA / HITL 网关规则不受影响。</p>
    <div className={styles.grid}><label>评估金额<input aria-label="反诈评估金额" type="number" value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>模拟收款对象<input aria-label="反诈收款对象" value={recipient} onChange={e=>setRecipient(e.target.value)}/></label><label>本次交易阈值<input aria-label="反诈阈值" type="number" value={threshold} onChange={e=>setThreshold(e.target.value)}/></label></div>
    <button className="secondary-button" disabled={busy} onClick={assess}>评估风险</button><ErrorLine error={error} busy={busy}/>
    {risk&&<div className={risk.risk_level==='HIGH'?styles.risk:styles.result}><strong>{risk.risk_level} · {risk.permission_decision}</strong>{risk.risk_factors.map(x=><p key={x.rule}><b>{x.rule}</b>：{x.explanation}</p>)}<p>{risk.recommended_action}</p><p>人工核查：{risk.requires_human_review?'需要；未自动提交审批':'不因本次评估触发'}</p></div>}
  </Panel>;
}

export function TracePanel({workflowId}) {
  const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');const lock=useRef(false);
  async function load(){if(!workflowId||lock.current)return;lock.current=true;setBusy(true);setError('');try{let cursor=0,events=[],next,node_states={};do{next=await bankingRequest(`/api/workflows/${workflowId}/trace?cursor=${cursor}`);events.push(...next.events);node_states={...node_states,...next.node_states};cursor=next.next_cursor;}while(next.events.length===500);setData({...next,events,node_states,elapsed_ms:events.length>1?new Date(events[events.length-1].timestamp)-new Date(events[0].timestamp):0});}catch(e){setError(e.message);}finally{lock.current=false;setBusy(false);}}
  useEffect(()=>{setData(null);},[workflowId]);
  return <Panel title="Agent 全链路只读回放"><button className="secondary-button" disabled={!workflowId||busy} onClick={load}>读取持久化时间线</button><ErrorLine busy={busy} error={error}/>{!workflowId&&<p>暂无工作流。</p>}
    {data&&<><p>只读历史，不重执行资金操作。{data.events.length} 条事件；时间线跨度 {(data.elapsed_ms/1000).toFixed(2)} 秒（包含等待审批）。</p><p>节点校验事件不是资金执行；资金动作以 EXECUTION_COMPLETED 为准。</p><div className={styles.timeline}>{data.events.map(x=><details key={x.event_id}><summary>{x.event} · {x.status}<small className={styles.line}>{x.timestamp} · {x.duration_ms.toFixed(1)}ms · {x.actor_id}</small></summary>{x.reason&&<p>{x.reason}</p>}<Json data={x.details}/></details>)}</div><details><summary>DAG 节点状态</summary><Json data={data.node_states}/></details></>}
  </Panel>;
}
