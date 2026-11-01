export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const getToken = () => typeof window === 'undefined' ? '' : sessionStorage.getItem('banking-session') || '';
export async function bankingRequest(path, body, token = getToken()) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

// Header-authenticated SSE with replay cursor, abort, and reconnect. Tokens never enter URLs.
export class AuthenticatedEventSource {
  constructor(url) {
    this.url = url; this.listeners = {}; this.cursor = ''; this.closed = false;
    this.controller = new AbortController(); this.run();
  }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  close() { this.closed = true; this.controller.abort(); clearTimeout(this.timer); }
  async run() {
    try {
      const response = await fetch(this.url, { signal: this.controller.signal,
        headers: { Authorization: `Bearer ${getToken()}`, ...(this.cursor ? { 'Last-Event-ID': this.cursor } : {}) } });
      if (!response.ok) throw new Error(`SSE HTTP ${response.status}`);
      this.onopen?.();
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
      while (!this.closed) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
        let end;
        while ((end = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
          let name = 'message', data = [], id;
          block.split('\n').forEach(line => {
            if (line.startsWith('event:')) name = line.slice(6).trim();
            if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
            if (line.startsWith('id:')) id = line.slice(3).trim();
          });
          if (id) this.cursor = id;
          if (data.length) (this.listeners[name] || []).forEach(fn => fn({ data: data.join('\n'), lastEventId: this.cursor }));
        }
      }
    } catch (error) { if (!this.closed) this.onerror?.(error); }
    if (!this.closed) this.timer = setTimeout(() => this.run(), 1500);
  }
}
