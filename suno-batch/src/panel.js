// 网页控制面板：本地 HTTP 服务 + SSE 实时进度 + 暂停/跳过/停止按钮 + 队列可视化。
// 用法：node src/panel.js [tasks.csv] [--dry-run] [--download]
// 打开 http://localhost:8787 控制挂机。零依赖（Node 内置 http）。
import http from 'node:http';
import { resolve, join } from 'node:path';
import { existsSync } from 'node:fs';
import { config } from './config.js';
import { readTasks, loadDone, loadFailed, writePlaylistIndex } from './tasks.js';
import * as suno from './suno.js';
import { runBatch } from './engine.js';
import { attachHarvest } from './harvest.js';
import { assignPlaylists } from './playlist.js';
import { PAGE } from './panel-page.js';

const args = process.argv.slice(2);
const has = f => args.includes(f);
const csvArg = args.find(a => !a.startsWith('--'));
const CSV = resolve(config.root, csvArg || 'tasks.csv');
const RESULTS = join(config.root, 'var', 'results.jsonl');
const PORT = Number(process.env.PANEL_PORT || 8787);

// ---- SSE 广播 + 滚动日志 ----
const clients = new Set();
const logBuf = [];
let snapshot = { phase: 'idle', done: 0, total: 0, current: null };

function broadcast(event, data) {
  const payload = JSON.stringify({ event, data, t: Date.now() });
  if (event === 'song' || event === 'log' || event === 'download') {
    logBuf.push(payload);
    if (logBuf.length > 200) logBuf.shift();
  }
  if (event === 'start') snapshot = { phase: 'running', done: 0, total: data.total, current: null };
  if (event === 'song') {
    if (data.phase === 'submitted' || data.phase === 'dry') snapshot.done++;
    snapshot.current = data;
  }
  if (event === 'done') snapshot.phase = 'done';
  for (const res of clients) { try { res.write(`data: ${payload}\n\n`); } catch {} }
}

// ---- 网页控制的 ctl ----
const state = { paused: false, quit: false, skipWait: false };
async function waitIfPaused() { while (state.paused && !state.quit) await new Promise(r => setTimeout(r, 300)); }
async function sleep(ms, label) {
  state.skipWait = false;
  const end = Date.now() + ms;
  while (Date.now() < end && !state.quit && !state.skipWait) {
    broadcast('wait', { left: Math.ceil((end - Date.now()) / 1000), label });
    await new Promise(r => setTimeout(r, 1000));
  }
  broadcast('wait', { left: 0, label });
}
const ctl = { state, waitIfPaused, sleep };

// ---- HTTP 服务 ----
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (url.pathname === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(PAGE);
  } else if (url.pathname === '/events') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    res.write(`data: ${JSON.stringify({ event: 'snapshot', data: snapshot })}\n\n`);
    for (const p of logBuf) res.write(`data: ${p}\n\n`);
    clients.add(res);
    req.on('close', () => clients.delete(res));
  } else if (url.pathname.startsWith('/cmd/') && req.method === 'POST') {
    const cmd = url.pathname.slice(5);
    if (cmd === 'pause') state.paused = true;
    else if (cmd === 'resume') state.paused = false;
    else if (cmd === 'skip') state.skipWait = true;
    else if (cmd === 'stop') { state.quit = true; state.paused = false; }
    broadcast('log', { message: `控制指令：${cmd}` });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, state }));
  } else {
    res.writeHead(404); res.end('not found');
  }
});

async function main() {
  if (!existsSync(CSV)) { console.error(`❌ 找不到任务表：${CSV}（先 cp tasks.example.csv tasks.csv）`); process.exit(1); }
  const all = readTasks(CSV);
  const done = loadDone(RESULTS);
  const pending = has('--retry-only')
    ? all.filter(t => loadFailed(RESULTS).has(t.id) && !done.has(t.id))
    : all.filter(t => !done.has(t.id));

  server.listen(PORT, () => {
    console.log(`\n🎛  控制面板已启动： http://localhost:${PORT}`);
    console.log(`   任务 ${all.length} · 已完成 ${done.size} · 待处理 ${pending.length}\n`);
  });

  if (!pending.length) { broadcast('log', { message: '没有待处理任务。删除 var/results.jsonl 可重跑。' }); return; }

  const { context, page } = await suno.launch();
  await suno.gotoCreate(page);
  if (await suno.isLoginWall(page)) {
    broadcast('log', { message: '⚠️ 未登录：请在弹出的浏览器窗口完成登录，面板会自动继续…' });
    const ok = await suno.waitForLogin(page, () => broadcast('log', { message: '仍在等待登录…' }));
    if (!ok) { broadcast('log', { message: '❌ 超时未登录。' }); return; }
  }

  const harvest = (has('--download') || String(process.env.DOWNLOAD).toLowerCase() === 'true')
    ? attachHarvest(context, page) : null;
  if (harvest) broadcast('log', { message: '📥 已开启自动下载（生成完成的音频将存入 var/downloads/）' });

  broadcast('log', { message: `开始挂机，共 ${pending.length} 首。${has('--dry-run') ? '【dry-run：只填不生成】' : ''}` });
  const submitted = [];
  const report = (ev, d) => { if (ev === 'song' && d.phase === 'submitted') submitted.push({ title: d.title, playlist: d.playlist }); broadcast(ev, d); };
  await runBatch({ page, ctl, report, pending, dryRun: has('--dry-run'), resultsPath: RESULTS, harvest });

  if (has('--playlist') && submitted.length && !has('--dry-run')) {
    broadcast('log', { message: '归类到 SUNO 歌单（best-effort）…' });
    await assignPlaylists(page, submitted, report);
  }
  const idx = writePlaylistIndex(RESULTS, join(config.root, 'var', 'playlists.md'));
  if (idx) broadcast('log', { message: `🗂 歌单索引已更新：${idx}` });

  broadcast('log', { message: '✅ 全部结束，可关闭此页与浏览器。' });
  await context.close();
}

main().catch(e => { console.error('致命错误：', e); broadcast('log', { message: '致命错误：' + e.message }); });
