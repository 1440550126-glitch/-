// LingCraft · API 客户端：与主站共用 jl_token；首次操作自动游客登录（一句话就出效果，不设登录门槛）。
export const TOKEN_KEY = 'jl_token';
export const getToken = () => localStorage.getItem(TOKEN_KEY) || '';
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiErr extends Error {
  constructor(message, extra = {}, status = 0) { super(message); this.extra = extra; this.status = status; }
}

async function raw(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined
  }).catch(() => { throw new ApiErr('网络好像断开了'); });
  let json = {};
  try { json = await res.json(); } catch { /* empty */ }
  if (!json.ok) { const { ok, error, ...extra } = json; throw new ApiErr(error || '出错了，稍后再试', extra, res.status); }
  return json.data;
}

// 401 时自动补一次游客登录再重试（设备号持久化，账号可复用）
export async function api(method, url, body) {
  try { return await raw(method, url, body); }
  catch (e) {
    if (e.status !== 401) throw e;
    const dev = localStorage.getItem('lc_device') || '';
    const d = await raw('POST', '/api/auth/guest', { device_id: dev });
    if (d.device_id) localStorage.setItem('lc_device', d.device_id);
    setToken(d.token);
    return raw(method, url, body);
  }
}
export const GET = (u) => api('GET', u);
export const POST = (u, b) => api('POST', u, b ?? {});
export const DEL = (u) => api('DELETE', u);
