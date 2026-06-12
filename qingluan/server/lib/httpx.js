// 青鸾 · 轻量 HTTP 框架（路由 / JSON / 静态文件，零依赖）
import fs from 'node:fs';
import path from 'node:path';
import { getSetting } from './db.js';

export class ApiError extends Error {
  constructor(status, message, extra = {}) {
    super(message);
    this.status = status;
    this.extra = extra;
  }
}
export const bad = (msg, extra) => new ApiError(400, msg, extra);
export const denied = (msg = '没有权限') => new ApiError(403, msg);
export const notFound = (msg = '内容不存在或已删除') => new ApiError(404, msg);

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
export const PATCH = (p, h, o) => route('PATCH', p, h, o);
export const DEL = (p, h, o) => route('DELETE', p, h, o);

function readBody(req, maxBytes) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > maxBytes) { reject(bad('内容太大了')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      if (!chunks.length) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch { reject(bad('请求格式错误：需要 JSON')); }
    });
    req.on('error', reject);
  });
}

const SEC_HEADERS = { 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'same-origin' };
// Agent API 允许浏览器侧 Agent 跨域调用（Bearer Token 鉴权，不依赖 Cookie，CORS 放开是安全的）
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization'
};

export function sendJSON(res, status, obj, cors = false) {
  if (res.writableEnded) return;
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...SEC_HEADERS,
    ...(cors ? CORS_HEADERS : {})
  });
  res.end(JSON.stringify(obj));
}

export async function handleApi(req, res, pathname, query) {
  const isAgentApi = pathname.startsWith('/api/agent/');
  if (req.method === 'OPTIONS') {
    res.writeHead(204, CORS_HEADERS);
    return res.end();
  }
  const found = routes.filter((r) => r.regex.test(pathname));
  if (!found.length) return sendJSON(res, 404, { ok: false, error: '接口不存在' }, isAgentApi);
  const r = found.find((x) => x.method === req.method);
  if (!r) return sendJSON(res, 405, { ok: false, error: '方法不允许' }, isAgentApi);

  const ctx = { req, res, query, params: {}, body: {} };
  const m = pathname.match(r.regex);
  r.keys.forEach((k, i) => { ctx.params[k] = decodeURIComponent(m[i + 1]); });

  try {
    if (r.opts.agent) {
      const bearer = (req.headers.authorization || '').replace(/^Bearer\s+/i, '') || query.get('token') || '';
      const expected = getSetting('agent_token', '');
      if (!expected || bearer !== expected) {
        throw new ApiError(401, '缺少或错误的 Agent Token（设置页可查看 / 重置）');
      }
    }
    if (req.method !== 'GET' && req.headers['content-type']?.includes('json')) {
      ctx.body = await readBody(req, r.opts.maxBytes || 512 * 1024);
    }
    const result = await r.handler(ctx);
    if (result === undefined) return;            // 自管理响应
    sendJSON(res, 200, { ok: true, data: result }, isAgentApi);
  } catch (e) {
    if (e instanceof ApiError) {
      sendJSON(res, e.status, { ok: false, error: e.message, ...e.extra }, isAgentApi);
    } else {
      console.error('[api]', pathname, e);
      sendJSON(res, 500, { ok: false, error: '服务器开小差了：' + (e.message || '未知错误') }, isAgentApi);
    }
  }
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
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.txt': 'text/plain; charset=utf-8'
};

export function serveStatic(res, rootDir, urlPath, { spa = true } = {}) {
  let rel = urlPath.replace(/^\/+/, '');
  if (!rel) rel = 'index.html';
  const full = path.normalize(path.join(rootDir, rel));
  if (!full.startsWith(rootDir)) { res.writeHead(403); res.end(); return true; }
  let file = full;
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    if (!spa) return false;
    file = path.join(rootDir, 'index.html');
    if (!fs.existsSync(file)) return false;
  }
  const ext = path.extname(file).toLowerCase();
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=600',
    ...SEC_HEADERS,
    ...(ext === '.html' ? {
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: blob: https:; media-src 'self' blob: data: https:; " +
        "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'"
    } : {})
  });
  fs.createReadStream(file).pipe(res);
  return true;
}
