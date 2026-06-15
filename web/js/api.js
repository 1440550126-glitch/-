// API 客户端：统一鉴权、错误结构、SSE
export function getToken() { return localStorage.getItem('jl_token') || ''; }
export function setToken(t) { t ? localStorage.setItem('jl_token', t) : localStorage.removeItem('jl_token'); }

export class ApiErr extends Error {
  constructor(message, extra = {}, status = 0) { super(message); this.extra = extra; this.status = status; }
}

export async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined
  }).catch(() => { throw new ApiErr('网络好像断开了，检查一下网络吧'); });
  let json = {};
  try { json = await res.json(); } catch { /* empty body */ }
  if (!json.ok) {
    const { ok, error, ...extra } = json;
    throw new ApiErr(error || '出错了，稍后再试', extra, res.status);
  }
  return json.data;
}
export const GET = (u) => api('GET', u);
export const POST = (u, b) => api('POST', u, b ?? {});
export const PUT = (u, b) => api('PUT', u, b ?? {});
export const PATCH = (u, b) => api('PATCH', u, b);
export const DEL = (u) => api('DELETE', u);

// SSE（EventSource 无法带 header，token 走查询参数）
export function sse(url, handlers) {
  const sep = url.includes('?') ? '&' : '?';
  const es = new EventSource(`${url}${sep}token=${encodeURIComponent(getToken())}`);
  for (const [event, fn] of Object.entries(handlers)) {
    es.addEventListener(event, (e) => {
      try { fn(JSON.parse(e.data)); } catch { /* 忽略坏帧 */ }
    });
  }
  return es;
}
