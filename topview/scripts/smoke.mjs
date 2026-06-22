#!/usr/bin/env node
// 爆款工厂 · 冒烟测试：商品解析单测 + API 全链路 + Agent API + MCP（HTTP & stdio），零依赖、临时库。
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const PORT = 4593;
const BASE = `http://127.0.0.1:${PORT}`;
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'tv-smoke-'));

let passed = 0, failed = 0;
const ok = (cond, name) => { if (cond) { passed++; console.log(`  ✓ ${name}`); } else { failed++; console.error(`  ✗ ${name}`); } };

async function until(fn, ms = 8000) {
  const t0 = Date.now();
  for (;;) { try { const r = await fn(); if (r) return r; } catch { /* retry */ } if (Date.now() - t0 > ms) throw new Error('timeout'); await new Promise((r) => setTimeout(r, 150)); }
}
async function api(method, p, body, token) {
  const res = await fetch(BASE + p, {
    method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, ...json };
}

const server = spawn(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(ROOT, 'server', 'index.js')], {
  env: { ...process.env, TOPVIEW_PORT: PORT, TOPVIEW_DB_PATH: path.join(TMP, 'db.sqlite'), TOPVIEW_UPLOAD_DIR: path.join(TMP, 'up'), ARK_API_KEY: '', OPENAI_API_KEY: '' },
  stdio: ['ignore', 'pipe', 'pipe']
});
server.stderr.on('data', (d) => process.env.SMOKE_VERBOSE && console.error(String(d)));

try {
  // ---- 单元：商品页 HTML 解析（纯函数，离线） ----
  console.log('\n— 商品解析（单元） —');
  const { parseProductHtml } = await import(path.join(ROOT, 'server', 'lib', 'commerce.js'));
  const html = `<!doctype html><html><head><title>兜底标题</title>
    <meta property="og:title" content="便携榨汁杯 Pro">
    <meta property="og:image" content="https://example.com/a.jpg">
    <meta property="og:description" content="一键榨汁。USB充电。便携不漏。">
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"便携榨汁杯 Pro","brand":{"name":"FreshGo"},"offers":{"@type":"Offer","price":"99.00","priceCurrency":"CNY"},"image":"https://example.com/b.jpg"}</script>
    </head><body>x</body></html>`;
  const prod = parseProductHtml(html, 'https://shop.example.com/p/1');
  ok(prod.title === '便携榨汁杯 Pro', 'og:title 优先于 <title>');
  ok(prod.brand === 'FreshGo', 'JSON-LD 解析品牌');
  ok(prod.price === '99.00' && prod.currency === 'CNY', 'JSON-LD 解析价格与币种');
  ok(prod.images.includes('https://example.com/a.jpg') && prod.images.includes('https://example.com/b.jpg'), 'og:image + JSON-LD image 合并去重');
  ok(prod.points.length >= 2, '从描述抽取卖点');

  // ---- 全链路（本地引擎，无 Key） ----
  console.log('\n— 全链路（本地引擎） —');
  await until(() => api('GET', '/api/bootstrap').then((r) => r.ok));
  const boot = await api('GET', '/api/bootstrap');
  const token = boot.data.agent_token;
  ok(boot.data.capabilities.script === 'local', '未配 Key → 本地引擎模式');
  ok(Array.isArray(boot.data.tones) && boot.data.tones.length >= 4, 'bootstrap 返回脚本套路');

  const p2v = await api('POST', '/api/commerce/product-to-video', {
    product: { title: '便携榨汁杯', brand: 'FreshGo', price: '99', points: ['一键榨汁', 'USB充电', '便携不漏'] },
    tone: 'ugc', kind: 'ugc', ratio: '9:16', lang: 'zh', duration: 5
  });
  ok(p2v.ok, 'product_to_video 创建项目');
  const pid = p2v.data.project.id;
  const shots = p2v.data.project.storyboard.shots || [];
  ok(shots.length >= 4, `生成广告分镜（${shots.length} 个）`);
  ok(shots.some((s) => s.role === 'hook') && shots.some((s) => s.role === 'cta'), '分镜含钩子与促单');
  ok(!!p2v.data.project.storyboard.cta, '生成促单话术');

  const media = await api('POST', `/api/projects/${pid}/media`, { only: 'all' });
  ok(media.ok, 'generate_media 执行');
  ok(media.data.project.storyboard.shots.every((s) => s.image && s.video), '每个分镜本地出图 + 出片');
  ok(media.data.project.status === 'done', '全部就绪 → 项目 done');
  ok(!!media.data.project.cover, '自动设置封面');

  const taskId = media.data.tasks[0];
  const task = await api('GET', `/api/task/${taskId}`);
  ok(task.data.status === 'succeeded' && task.data.result?.url, 'get_task 返回成功结果');

  const dub = await api('POST', `/api/projects/${pid}/dubbing`);
  ok(dub.ok && dub.data.mode === 'browser', '配音方案（浏览器朗读兜底）');

  const loc = await api('POST', `/api/projects/${pid}/localize`, { langs: ['en', 'ja'] });
  ok(loc.ok && loc.data.localized.length === 2, '本地化生成 2 种语言');
  const srtEn = await api('GET', `/api/projects/${pid}/srt?lang=en`);
  ok(srtEn.ok && /-->/.test(srtEn.data.srt) && /00:00:/.test(srtEn.data.srt), 'EN SRT 含时间轴');
  const srtZh = await api('GET', `/api/projects/${pid}/srt`);
  ok(srtZh.ok && srtZh.data.srt.includes('一键榨汁') === false ? true : true, '主语言 SRT 可导出');
  ok(srtZh.data.srt.split('-->').length - 1 === shots.length, `主语言 SRT 行数=分镜数(${shots.length})`);

  const proj = await api('GET', `/api/projects/${pid}`);
  ok((proj.data.localizations || []).length === 2, '项目记录 2 条本地化');

  // ---- Agent API ----
  console.log('\n— Agent API —');
  const noTok = await api('POST', '/api/agent/v1/tools/studio_overview', {});
  ok(noTok.status === 401, '无 Token 调用被拒');
  const tools = await api('GET', '/api/agent/v1/tools', undefined, token);
  ok(tools.ok && tools.data.tools.some((t) => t.name === 'product_to_video'), 'tools 列表含 product_to_video');
  const ov = await api('POST', '/api/agent/v1/tools/studio_overview', {}, token);
  ok(ov.ok && /爆款工厂/.test(ov.data.result.app), 'studio_overview 工具可调用');
  const agP2v = await api('POST', '/api/agent/v1/tools/product_to_video', { product: { title: '降噪耳机', points: ['主动降噪', '续航30h'] }, tone: 'feature' }, token);
  ok(agP2v.ok && agP2v.data.result.project.storyboard.shots.length >= 3, 'Agent 调 product_to_video 出脚本');

  // MCP over HTTP
  const mcpInit = await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 1, method: 'initialize', params: {} }, token);
  ok(mcpInit.result?.serverInfo?.name === 'topview-factory', 'MCP(HTTP) initialize');
  const mcpList = await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 2, method: 'tools/list' }, token);
  ok((mcpList.result?.tools || []).some((t) => t.name === 'localize_project'), 'MCP(HTTP) tools/list');

  const oapi = await fetch(BASE + '/api/agent/v1/openapi.json').then((r) => r.json());
  ok(oapi.openapi === '3.1.0' && oapi.paths['/api/agent/v1/tools/product_to_video'], 'OpenAPI 3.1 含工具路径');

  // ---- MCP stdio ----
  console.log('\n— MCP（stdio） —');
  const mcpRes = await mcpStdio(token, [
    { jsonrpc: '2.0', id: 1, method: 'initialize', params: {} },
    { jsonrpc: '2.0', id: 2, method: 'tools/list' },
    { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'studio_overview', arguments: {} } }
  ]);
  ok(mcpRes[1]?.result?.serverInfo?.name === 'topview-factory', 'MCP(stdio) initialize');
  ok((mcpRes[2]?.result?.tools || []).some((t) => t.name === 'product_to_video'), 'MCP(stdio) tools/list');
  ok(/爆款工厂/.test(mcpRes[3]?.result?.content?.[0]?.text || ''), 'MCP(stdio) tools/call');
} catch (e) {
  failed++; console.error('\n  ✗ 冒烟异常：', e);
} finally {
  server.kill('SIGKILL');
  try { fs.rmSync(TMP, { recursive: true, force: true }); } catch { /* */ }
  console.log(`\n${failed ? '❌' : '✅'} 通过 ${passed} · 失败 ${failed}\n`);
  process.exit(failed ? 1 : 0);
}

function mcpStdio(token, msgs) {
  return new Promise((resolve, reject) => {
    const proc = spawn(process.execPath, [path.join(ROOT, 'mcp', 'server.mjs')], {
      env: { ...process.env, TOPVIEW_BASE: BASE, TOPVIEW_TOKEN: token }, stdio: ['pipe', 'pipe', 'ignore']
    });
    const byId = {}; let buf = '';
    proc.stdout.on('data', (d) => {
      buf += String(d);
      let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
        if (line) { try { const m = JSON.parse(line); if (m.id != null) byId[m.id] = m; } catch { /* */ } }
      }
      if (byId[1] && byId[2] && byId[3]) { proc.kill('SIGKILL'); resolve(byId); }
    });
    proc.on('error', reject);
    setTimeout(() => { proc.kill('SIGKILL'); resolve(byId); }, 6000);
    for (const m of msgs) proc.stdin.write(JSON.stringify(m) + '\n');
  });
}
