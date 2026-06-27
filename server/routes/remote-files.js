// 远程控制 Mac · 文件传输接口（裸流，不走 handleApi 的 JSON 缓冲）
//   POST /api/remote/transfer/up?device=&name=   浏览器上传 → 暂存 → 通知 Mac 下载（recv_file）
//   GET  /api/remote/agent/transfer/:id          Mac agent 取走浏览器上传的文件（取后即删）
//   POST /api/remote/agent/upload?device=&name=   Mac agent 上传本机文件 → 暂存，回 { id }
//   GET  /api/remote/file/:id                     浏览器下载 Mac 传来的文件（取后即删）
import fs from 'node:fs';
import * as remote from '../lib/remote.js';
import * as tf from '../lib/transfer.js';

const PREFIXES = ['/api/remote/transfer/', '/api/remote/agent/transfer/', '/api/remote/file/'];
const isFileRoute = (p) => p === '/api/remote/agent/upload' || PREFIXES.some((x) => p.startsWith(x));

function tokenOf(req, query) {
  return (
    req.headers['x-remote-token'] ||
    (req.headers.authorization || '').replace(/^Bearer\s+/i, '') ||
    query.get('token') || ''
  ).toString().trim();
}
function json(res, status, obj) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(obj));
}
function sendFile(res, m, asAttachment) {
  res.writeHead(200, {
    'Content-Type': 'application/octet-stream',
    'Content-Length': m.size,
    'Cache-Control': 'no-store',
    ...(asAttachment ? { 'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(m.name)}` } : {})
  });
  const rs = fs.createReadStream(m.file);
  rs.pipe(res);
  rs.on('end', () => tf.remove(m.id));     // 取走即删
  rs.on('error', () => { try { res.end(); } catch { /* ignore */ } });
}
function recvToFile(req, res, t, done) {
  let size = 0, aborted = false;
  const ws = fs.createWriteStream(t.file);
  req.on('data', (c) => {
    size += c.length;
    if (size > tf.MAX_FILE) { aborted = true; try { ws.destroy(); } catch { /* ignore */ } tf.remove(t.id); req.destroy(); json(res, 413, { ok: false, error: '文件太大' }); return; }
    ws.write(c);
  });
  req.on('end', () => { if (aborted) return; ws.end(() => { tf.commit(t, size); done(); }); });
  req.on('error', () => { try { ws.destroy(); } catch { /* ignore */ } tf.remove(t.id); });
}

// 返回 true 表示已处理（包括错误响应）；false 表示不是文件路由，交回普通 API
export function handleRemoteFile(req, res, pathname, query) {
  if (!isFileRoute(pathname)) return false;
  if (!remote.remoteEnabled()) { json(res, 503, { ok: false, error: '远程控制未启用' }); return true; }
  if (!remote.checkToken(tokenOf(req, query))) { json(res, 401, { ok: false, error: '令牌无效' }); return true; }

  // 1) 浏览器 → 服务器（上传，准备推给 Mac）
  if (pathname === '/api/remote/transfer/up' && req.method === 'POST') {
    const device = query.get('device') || '';
    const t = tf.create(query.get('name') || 'file', device);
    recvToFile(req, res, t, () => {
      let id;
      try { id = remote.enqueueCommand(device, 'recv_file', { tid: t.id, name: t.name }); }
      catch (e) { tf.remove(t.id); return json(res, 409, { ok: false, error: e.message }); }
      json(res, 200, { ok: true, data: { id, transfer: t.id, name: t.name } });
    });
    return true;
  }
  // 2) 服务器 → Mac agent（agent 取走浏览器上传的文件）
  const dlAgent = pathname.match(/^\/api\/remote\/agent\/transfer\/([\w-]+)$/);
  if (dlAgent && req.method === 'GET') {
    const m = tf.get(dlAgent[1]);
    if (!m) { json(res, 404, { ok: false, error: '文件不存在或已过期' }); return true; }
    sendFile(res, m, false);
    return true;
  }
  // 3) Mac agent → 服务器（agent 上传本机文件给浏览器取）
  if (pathname === '/api/remote/agent/upload' && req.method === 'POST') {
    const t = tf.create(query.get('name') || 'file', query.get('device') || '');
    recvToFile(req, res, t, () => json(res, 200, { ok: true, data: { id: t.id, name: t.name } }));
    return true;
  }
  // 4) 浏览器 → 服务器（下载 Mac 传来的文件）
  const dlBrowser = pathname.match(/^\/api\/remote\/file\/([\w-]+)$/);
  if (dlBrowser && req.method === 'GET') {
    const m = tf.get(dlBrowser[1]);
    if (!m) { json(res, 404, { ok: false, error: '文件不存在或已过期' }); return true; }
    sendFile(res, m, true);
    return true;
  }

  json(res, 404, { ok: false, error: '未知传输接口' });
  return true;
}
