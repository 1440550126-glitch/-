// 灵境AI · 短剧创作工坊 服务端入口（零依赖 Node 22+：node:sqlite / fetch / http）
import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

// 复用仓库根目录 .env（与主应用一致的配置入口，没有就跳过）
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..', '..');
try { process.loadEnvFile(path.join(ROOT, '.env')); } catch { /* 无 .env 也能跑 */ }
try { process.loadEnvFile(path.join(ROOT, 'lingjing', '.env')); } catch { /* 可选的子应用独立配置 */ }

const { handleApi, serveStatic } = await import('./lib/httpx.js');
const { getSetting, setSetting, UPLOAD_DIR } = await import('./lib/db.js');
const { token32 } = await import('./lib/util.js');
const { arkEnabled, cfg } = await import('./lib/ark.js');

// 路由注册（导入即注册）
await import('./routes/studio.js');
await import('./routes/ai.js');
await import('./routes/agent.js');

const WEB_DIR = path.join(__dirname, '..', 'web');
const PORT = Number(process.env.LINGJING_PORT || process.env.QINGLUAN_PORT) || 4399;

// 首次启动生成 Agent Token
if (!getSetting('agent_token', '')) setSetting('agent_token', token32());

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  const pathname = u.pathname;
  if (pathname.startsWith('/api/')) return handleApi(req, res, pathname, u.searchParams);
  if (pathname.startsWith('/uploads/')) {
    if (serveStatic(res, UPLOAD_DIR, pathname.slice('/uploads/'.length), { spa: false })) return;
    res.writeHead(404); return res.end('not found');
  }
  if (serveStatic(res, WEB_DIR, pathname)) return;
  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('404');
});

server.listen(PORT, () => {
  const c = cfg();
  console.log(`\n  🐦 灵境AI · 短剧创作工坊 已启动`);
  console.log(`  🎬 工作台      http://localhost:${PORT}`);
  console.log(`  🤖 Agent API   http://localhost:${PORT}/api/agent/v1/openapi.json`);
  console.log(`  🔌 MCP 服务器  node ${path.join(__dirname, '..', 'mcp', 'server.mjs')}`);
  console.log(`  🧠 模型        ${arkEnabled() ? `火山方舟（${c.modelChat} | ${c.modelImage} | ${c.modelVideo}）` : '未配置方舟 Key（本地引擎模式，全流程可体验，零成本）'}\n`);
});

process.on('SIGINT', () => { console.log('\nbye~'); process.exit(0); });
process.on('SIGTERM', () => process.exit(0));
