// 灵阵 · 安全网络访问：SSRF 防护（禁止内网 / 本机 / 元数据地址；含 DNS 解析校验）
// 被 web_fetch 工具与出站 Webhook 复用。
import dns from 'node:dns/promises';

// 单个 IP 字面量是否属于内网/环回/链路本地/元数据（含 IPv6 与 ::ffff: 映射）
export function isBlockedIp(ip) {
  const a = String(ip).toLowerCase();
  if (a === '::1' || a === '::') return true;
  if (/^f[cd]/.test(a)) return true;                  // fc00::/7 唯一本地地址
  if (a.startsWith('fe80')) return true;              // 链路本地
  const v4 = a.replace(/^::ffff:/, '');
  const m = v4.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const [w, x] = [Number(m[1]), Number(m[2])];
    if (w === 127 || w === 10 || w === 0 || (w === 192 && x === 168) || (w === 172 && x >= 16 && x <= 31) || (w === 169 && x === 254)) return true;
  }
  return false;
}
// 主机名字面量（域名直接拦特殊后缀；IP 字面量交给 isBlockedIp）
export function isBlockedHost(host) {
  const h = String(host).toLowerCase().replace(/^\[|\]$/g, '');
  if (h === 'localhost' || h.endsWith('.local') || h.endsWith('.internal')) return true;
  return isBlockedIp(h);
}
// 抓取前对单跳 URL 做完整校验：协议 + 主机名字面量 + DNS 解析后的所有地址。返回错误信息或 null
export async function assertSafeHop(u) {
  if (!['http:', 'https:'].includes(u.protocol)) return '只支持 http/https';
  if (isBlockedHost(u.hostname)) return '出于安全考虑，禁止访问内网 / 本机 / 元数据地址';
  try {
    const addrs = await dns.lookup(u.hostname, { all: true });
    if (addrs.some((a) => isBlockedIp(a.address))) return '该域名解析到内网 / 本机地址，已拒绝';
  } catch { return '域名解析失败'; }
  return null;
}

// 安全 fetch：手动跟随重定向（每跳重校验），防 302→内网绕过。返回 { resp, finalUrl }，不安全则抛错。
export async function safeFetch(rawUrl, { method = 'GET', headers = {}, body, timeoutMs = 8000, maxHops = 5, followRedirects = true } = {}) {
  let current;
  try { current = new URL(String(rawUrl)); } catch { throw new Error('无效的网址'); }
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    for (let hop = 0; hop < maxHops; hop++) {
      const blocked = await assertSafeHop(current);
      if (blocked) throw new Error(blocked);
      const resp = await fetch(current.href, { method, headers, body, signal: ctrl.signal, redirect: 'manual' });
      if (followRedirects && resp.status >= 300 && resp.status < 400 && resp.headers.get('location') && hop < maxHops - 1) {
        try { current = new URL(resp.headers.get('location'), current); } catch { throw new Error('重定向地址无效'); }
        continue;
      }
      return { resp, finalUrl: current };
    }
    throw new Error('重定向次数过多');
  } finally { clearTimeout(timer); }
}
