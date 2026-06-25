// 爆款工厂 · API 客户端
export class ApiErr extends Error { constructor(message, status = 0) { super(message); this.status = status; } }

export async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined
  }).catch(() => { throw new ApiErr('网络好像断开了'); });
  let json = {};
  try { json = await res.json(); } catch { /* empty */ }
  if (!json.ok) throw new ApiErr(json.error || '出错了，稍后再试', res.status);
  return json.data;
}
export const GET = (u) => api('GET', u);
export const POST = (u, b) => api('POST', u, b ?? {});
export const DEL = (u) => api('DELETE', u);

let bootCache = null;
export async function bootstrap(force = false) {
  if (!bootCache || force) bootCache = await GET('/api/bootstrap');
  return bootCache;
}

export async function pollTask(taskId, { intervalMs = 2500, tries = 60 } = {}) {
  for (let i = 0; i < tries; i++) {
    const t = await GET(`/api/task/${taskId}`);
    if (t.status === 'succeeded' || t.status === 'failed') return t;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { status: 'running' };
}
