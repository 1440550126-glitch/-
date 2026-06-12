// 青鸾 · API 客户端
export class ApiErr extends Error {
  constructor(message, status = 0) { super(message); this.status = status; }
}

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
export const PATCH = (u, b) => api('PATCH', u, b);
export const DEL = (u) => api('DELETE', u);

let bootCache = null;
export async function bootstrap(force = false) {
  if (!bootCache || force) bootCache = await GET('/api/bootstrap');
  return bootCache;
}

/** 文件 → dataURL → 上传，返回资产 */
export function uploadFile(file, tab = 'material') {
  return new Promise((resolve, reject) => {
    if (file.size > 25 * 1024 * 1024) return reject(new ApiErr('文件超过 25MB'));
    const r = new FileReader();
    r.onload = () => POST('/api/upload', { name: file.name.replace(/\.[^.]+$/, ''), data: r.result, tab }).then(resolve, reject);
    r.onerror = () => reject(new ApiErr('读取文件失败'));
    r.readAsDataURL(file);
  });
}

/** 轮询任务直到结束。返回最终任务对象；onTick 每次轮询回调。 */
export async function pollUntilDone(taskId, { intervalMs = 2500, onTick, signal } = {}) {
  for (;;) {
    const t = await GET(`/api/ai/task/${taskId}`);
    onTick?.(t);
    if (t.status === 'succeeded' || t.status === 'failed') return t;
    if (signal?.aborted) return t;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
