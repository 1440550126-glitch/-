// AI句灵 服务端入口：零依赖 Node 22+（内置 node:sqlite / fetch / http）
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { handleApi, serveStatic, GET } from './lib/httpx.js';
import { initSecret } from './lib/auth.js';
import { runSeed, seedSamplePosts } from './lib/seed.js';
import { startWarmupLoop, ensureWarmupAccounts } from './warmup/bot.js';
import { recoverOnBoot } from './game/core.js';
import { AVATARS, MEMBER_PLANS, REPORT_REASONS } from './lib/catalog.js';
import { llmEnabled } from './lib/llm.js';

// 路由注册（导入即注册）
import './routes/auth.js';
import './routes/users.js';
import './routes/posts.js';
import './routes/ai.js';
import './routes/shop.js';
import './routes/rooms.js';
import './routes/admin.js';
import './routes/agents.js';

import { seedLingArray, runAgentMigrations } from './agents/seed.js';
import { startTriggerLoop } from './agents/scheduler.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(__dirname, '..', 'web');
const ADMIN_DIR = path.join(__dirname, '..', 'admin');
const LINGZHEN_DIR = path.join(__dirname, '..', 'lingzhen');
const PORT = Number(process.env.PORT) || 3000;

GET('/api/health', async () => ({ status: 'ok', time: Date.now(), llm: llmEnabled() ? 'enabled' : 'local-fallback' }));

// 客户端启动需要的静态常量（头像、会员方案、举报原因、合规信息）
GET('/api/bootstrap', async () => ({
  app: { name: 'AI句灵', slogan: '让每一句话活过来', version: '0.1.0' },
  avatars: AVATARS,
  member_plans: MEMBER_PLANS,
  report_reasons: REPORT_REASONS,
  compliance: {
    icp: '（ICP备案号占位：沪ICP备XXXXXXXX号-1）',
    ai_notice: '本应用包含 AI 生成内容，均已标识；AI 暖场官为虚拟账号，不代表真实用户。',
    agreements: ['用户协议', '隐私政策', '社区规范', '未成年人保护说明']
  }
}));

initSecret();
recoverOnBoot();
runSeed();
ensureWarmupAccounts();
seedSamplePosts();
runAgentMigrations();
seedLingArray();
if (process.env.WARMUP_AUTOSTART !== '0') startWarmupLoop();
if (process.env.TRIGGER_AUTOSTART !== '0') startTriggerLoop();

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  const pathname = u.pathname;
  if (pathname.startsWith('/api/')) return handleApi(req, res, pathname, u.searchParams);
  if (pathname === '/admin' || pathname.startsWith('/admin/')) {
    const rel = pathname.replace(/^\/admin\/?/, '') || 'index.html';
    if (serveStatic(res, ADMIN_DIR, rel)) return;
  }
  // 灵阵 · AI 团队（独立站，复用同一后端 API）
  if (pathname === '/lingzhen' || pathname.startsWith('/lingzhen/')) {
    const rel = pathname.replace(/^\/lingzhen\/?/, '') || 'index.html';
    if (serveStatic(res, LINGZHEN_DIR, rel)) return;
  }
  if (serveStatic(res, WEB_DIR, pathname)) return;
  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('404');
});

// 生产环境安全自检
if (process.env.NODE_ENV === 'production') {
  if (!process.env.ADMIN_PASSWORD || process.env.ADMIN_PASSWORD === 'jvling-admin-2026') {
    console.warn('\n  ⚠️⚠️⚠️  生产环境正在使用默认管理员密码！请立即在 .env 中设置 ADMIN_PASSWORD 并重建管理员！\n');
  }
  if (!process.env.APP_SECRET) {
    console.warn('  ⚠️  建议在 .env 中显式设置 APP_SECRET（当前使用首次启动时自动生成并持久化的密钥）');
  }
}

server.listen(PORT, () => {
  console.log(`\n  ✨ AI句灵 已启动`);
  console.log(`  📱 用户端   http://localhost:${PORT}`);
  console.log(`  🛠  管理后台 http://localhost:${PORT}/admin`);
  console.log(`  🛰  灵阵独立站 http://localhost:${PORT}/lingzhen`);
  console.log(`  🤖 大模型   ${llmEnabled() ? '已接入 ' + process.env.LLM_PROVIDER : '未配置（本地规则引擎模式，零成本可完整体验）'}\n`);
});

process.on('SIGINT', () => { console.log('\nbye~'); process.exit(0); });
process.on('SIGTERM', () => process.exit(0));
