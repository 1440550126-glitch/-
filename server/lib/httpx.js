import fs from 'node:fs';
import path from 'node:path';
import { userFromToken } from './auth.js';
import { now } from './util.js';

export class ApiError extends Error {
  constructor(status, message, extra = {}) {
    super(message);
    this.status = status;
    this.extra = extra;
  }
}
export const bad = (msg, extra) => new ApiError(400, msg, extra);
export const denied = (msg = '没有权限', extra) => new ApiError(403, msg, extra);
export const notFound = (msg = '内容不存在或已删除') => new ApiError(404, msg);

// ---- 简单限流（内存令牌桶：单实例足够，集群化后换 Redis） ----
const buckets = new Map();
export function rateLimit(key, limit, windowMs) {
  const nowTs = now();
  let b = buckets.get(key);
  if (!b || nowTs > b.reset) {
    b = { count: 0, reset: nowTs + windowMs };
    buckets.set(key, b);
  }
  b.count++;
  if (buckets.size > 50000) buckets.clear();
  return b.count <= limit;
}

// ---- 路由 ----
const routes = [];
export function route(method, pattern, handler, opts = {}) {
  const keys = [];
  const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, (m) => {
    keys.push(m.slice(1));
    return '([^/]+)';
  }) + '$');
  routes.push({ method, regex, keys, handler, opts });
}
export const GET = (p, h, o) => route('GET', p, h, o);
export const POST = (p, h, o) => route('POST', p, h, o);
export const PUT = (p, h, o) => route('PUT', p, h, o);
export const PATCH = (p, h, o) => route('PATCH', p, h, o);
export const DEL = (p, h, o) => route('DELETE', p, h, o);

function readBody(req, maxBytes = 128 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > maxBytes) { reject(bad('内容太长了')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      if (!chunks.length) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch { reject(bad('请求格式错误')); }
    });
    req.on('error', reject);
  });
}

const SEC_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'same-origin',
  'X-Frame-Options': 'DENY'
};

export function sendJSON(res, status, obj) {
  if (res.writableEnded) return;
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...SEC_HEADERS
  });
  res.end(body);
}

export async function handleApi(req, res, pathname, query) {
  const found = routes.filter((r) => r.regex.test(pathname));
  if (!found.length) return sendJSON(res, 404, { ok: false, error: '接口不存在' });
  const r = found.find((x) => x.method === req.method);
  if (!r) return sendJSON(res, 405, { ok: false, error: '方法不允许' });

  const ip = (req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'ip').toString().split(',')[0].trim();
  const ctx = { req, res, ip, query, params: {}, body: {}, user: null };
  const m = pathname.match(r.regex);
  r.keys.forEach((k, i) => { ctx.params[k] = decodeURIComponent(m[i + 1]); });

  try {
    const token = (req.headers.authorization || '').replace(/^Bearer\s+/i, '') || query.get('token') || '';
    ctx.user = userFromToken(token);

    // 限流：登录用户按用户维度（移动网络共享出口 IP），匿名按 IP；
    // 对局内动作（发言/投票/夜间行动/聊天）天然高频，独立计桶
    const isWrite = req.method !== 'GET';
    const isGameOp = isWrite && pathname.startsWith('/api/rooms/');
    // 远程控制 Mac：点击/方向键/音量等天然高频（口令鉴权·单用户），独立计桶放宽
    const isRemoteOp = isWrite && pathname.startsWith('/api/remote/');
    const rateKey = ctx.user ? `u:${ctx.user.id}` : `ip:${ip}`;
    const bucket = isRemoteOp ? 'rc' : isGameOp ? 'g' : isWrite ? 'w' : 'r';
    const limit = isRemoteOp ? 300 : isGameOp ? 150 : isWrite ? (ctx.user ? 80 : 30) : 300;
    if (!rateLimit(`${rateKey}:${bucket}`, limit, 60_000)) {
      return sendJSON(res, 429, { ok: false, error: '操作太频繁了，休息一下吧' });
    }

    if (r.opts.auth && !ctx.user) throw new ApiError(401, '请先登录');
    if (r.opts.auth && ctx.user.status === 'banned') {
      throw new ApiError(403, `账号已被限制使用${ctx.user.banned_reason ? '：' + ctx.user.banned_reason : ''}`, { banned: true, until: ctx.user.banned_until });
    }
    if (r.opts.admin && (!ctx.user || ctx.user.role !== 'admin')) throw denied('需要管理员权限');

    if (isWrite && req.headers['content-type']?.includes('json')) ctx.body = await readBody(req, r.opts.maxBody || 128 * 1024);

    const result = await r.handler(ctx);
    if (result === undefined) return;          // SSE 等自管理响应
    sendJSON(res, 200, { ok: true, data: result });
  } catch (e) {
    if (e instanceof ApiError) {
      sendJSON(res, e.status, { ok: false, error: e.message, ...e.extra });
    } else {
      console.error('[api]', pathname, e);
      sendJSON(res, 500, { ok: false, error: '服务器开小差了，请稍后再试' });
    }
  }
}

// ---- SSE ----
export function openSSE(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-store',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no'
  });
  res.write(': hi\n\n');
  const timer = setInterval(() => { if (!res.writableEnded) res.write(': ping\n\n'); }, 25_000);
  const client = {
    closed: false,
    send(event, data) {
      if (this.closed || res.writableEnded) return;
      res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    },
    close() {
      if (this.closed) return;
      this.closed = true;
      clearInterval(timer);
      try { res.end(); } catch { /* already closed */ }
    }
  };
  req.on('close', () => { client.closed = true; clearInterval(timer); client.onclose?.(); });
  return client;
}

// ---- 静态文件 ----
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json'
};

export function serveStatic(res, rootDir, urlPath) {
  let rel = urlPath.replace(/^\/+/, '');
  if (!rel) rel = 'index.html';
  const full = path.normalize(path.join(rootDir, rel));
  if (!full.startsWith(rootDir)) { res.writeHead(403); res.end(); return true; }
  let file = full;
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    // SPA 回退到 index.html
    file = path.join(rootDir, 'index.html');
    if (!fs.existsSync(file)) return false;
  }
  const ext = path.extname(file);
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=300',
    ...SEC_HEADERS,
    ...(ext === '.html' ? {
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data:; connect-src 'self'; media-src 'self'; font-src 'self'; " +
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    } : {})
  });
  fs.createReadStream(file).pipe(res);
  return true;
}
