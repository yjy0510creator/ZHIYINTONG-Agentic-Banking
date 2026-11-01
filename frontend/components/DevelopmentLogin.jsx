import { useState, useEffect } from 'react';
import { bankingRequest } from './bankingClient';

export default function DevelopmentLogin() {
  const [password,setPassword] = useState(''); const [identity,setIdentity] = useState(null);
  const [error,setError] = useState(''); const [busy,setBusy] = useState(false);
  useEffect(() => { bankingRequest('/api/session').then(setIdentity).catch(() => {}); },[]);
  async function login(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await bankingRequest('/api/dev/login',{username:'maker',password},'');
      sessionStorage.setItem('banking-session',result.access_token); setIdentity(result); setPassword('');
      window.dispatchEvent(new Event('banking-auth-changed'));
    } catch(e) { setError(e.message); } finally { setBusy(false); }
  }
  return <div className="surface p-3 mb-3 text-[10px]">
    {identity ? <span>开发身份模拟 · {identity.actor_id} · {identity.actor_role} <button className="secondary-button" onClick={() => { sessionStorage.removeItem('banking-session');setIdentity(null);window.dispatchEvent(new Event('banking-auth-changed')); }}>退出</button></span>
      : <form onSubmit={login} className="flex flex-wrap items-center gap-2"><span>开发环境独立登录 · Maker</span>
        <input aria-label="Maker 开发口令" type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="本机开发口令" autoComplete="current-password" />
        <button className="secondary-button" disabled={busy}>登录模拟环境</button></form>}
    {error && <p role="alert">{error}</p>}
    <div className="section-caption">仅 APP_ENV=development 可用；不代表真实银行身份认证。</div>
  </div>;
}
