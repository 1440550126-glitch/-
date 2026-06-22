// 魔镜魔镜 · 独立静态服务器（零依赖 Node 22+）
// 纯客户端应用：所有美颜/瘦身/录制都在浏览器本地完成，服务端只发静态文件。
// 注意：摄像头需要安全环境——localhost 可直接用，部署到公网需 HTTPS。
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.MIRROR_PORT) || 3100;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

// 相机应用需要的 CSP/权限策略：允许 blob/data 用于拍照与录像回放
const CSP =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; " +
  "font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'";

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  let rel = decodeURIComponent(u.pathname).replace(/^\/+/, '') || 'index.html';
  let full = path.normalize(path.join(__dirname, rel));
  if (!full.startsWith(__dirname)) { res.writeHead(403); return res.end('forbidden'); }
  if (!fs.existsSync(full) || fs.statSync(full).isDirectory()) full = path.join(__dirname, 'index.html');

  const ext = path.extname(full);
  const headers = {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'same-origin',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=300'
  };
  if (ext === '.html') {
    headers['Content-Security-Policy'] = CSP;
    headers['Permissions-Policy'] = 'camera=(self), microphone=(self)';
  }
  res.writeHead(200, headers);
  fs.createReadStream(full).pipe(res);
});

server.listen(PORT, () => {
  console.log(`\n  🪞 魔镜魔镜 已启动`);
  console.log(`  📱 打开    http://localhost:${PORT}`);
  console.log(`  🔒 隐私    画面只在本地处理，绝不上传`);
  console.log(`  ⚠️  公网部署需 HTTPS，摄像头才能开启\n`);
});

process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));
