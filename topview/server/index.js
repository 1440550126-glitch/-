// 爆款工厂 · AI 电商带货视频 服务端入口（零依赖 Node 22+：node:sqlite / fetch / http）
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..', '..');
try { process.loadEnvFile(path.join(ROOT, '.env')); } catch { /* 无 .env 也能跑 */ }
try { process.loadEnvFile(path.join(ROOT, 'topview', '.env')); } catch { /* 可选的子应用独立配置 */ }

const { handleApi, serveStatic } = await import('./lib/httpx.js');
const { getSetting, setSetting, UPLOAD_DIR } = await import('./lib/db.js');
const { token32 } = await import('./lib/util.js');
const { llmEnabled, cfg } = await import('./lib/llm.js');

// 路由注册（导入即注册）
await import('./routes/studio.js');
await import('./routes/agent.js');

const WEB_DIR = path.join(__dirname, '..', 'web');
const PORT = Number(process.env.TOPVIEW_PORT) || 4499;

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
  console.log(`\n  🚀 爆款工厂 · AI 电商带货视频 已启动`);
  console.log(`  🛍  工作台      http://localhost:${PORT}`);
  console.log(`  🤖 Agent API   http://localhost:${PORT}/api/agent/v1/openapi.json`);
  console.log(`  🔌 MCP 服务器  node ${path.join(__dirname, '..', 'mcp', 'server.mjs')}`);
  console.log(`  🧠 模型        ${llmEnabled() ? `已接入（${c.modelChat} | ${c.modelImage} | ${c.modelVideo}）` : '本地引擎模式（未配置 Key，全流程可演示，零成本）'}\n`);
});

process.on('SIGINT', () => { console.log('\nbye~'); process.exit(0); });
process.on('SIGTERM', () => process.exit(0));
