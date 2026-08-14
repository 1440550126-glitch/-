// 每日定时挂机：到点自动跑一轮（可限每日首数），跑完等到明天同一时刻再跑。长期挂着即可。
// 用法：node src/scheduler.js [tasks.csv] [--download] [--playlist] [--now]
//   --now 立即先跑一轮，再进入每日循环。Ctrl+C 退出。
// 时间取 .env 的 DAILY_AT（HH:MM，本地时区），每日上限取 DAILY_LIMIT。
import { resolve, join } from 'node:path';
import { existsSync } from 'node:fs';
import { config } from './config.js';
import { readTasks, loadDone, writePlaylistIndex } from './tasks.js';
import * as suno from './suno.js';
import { runBatch } from './engine.js';
import { attachHarvest } from './harvest.js';
import { assignPlaylists } from './playlist.js';
import { log } from './control.js';

const args = process.argv.slice(2);
const has = f => args.includes(f);
const csvArg = args.find(a => !a.startsWith('--'));
const CSV = resolve(config.root, csvArg || 'tasks.csv');
const RESULTS = join(config.root, 'var', 'results.jsonl');
const INDEX = join(config.root, 'var', 'playlists.md');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// 计算到下一个 HH:MM 的毫秒数
function msUntil(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  const now = new Date();
  const next = new Date(now);
  next.setHours(h || 0, m || 0, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next - now;
}

// 简单的 ctl（定时模式不做交互暂停，只支持退出）
let quitFlag = false;
process.on('SIGINT', () => { quitFlag = true; log('收到退出信号，本轮结束后停止。'); });
const ctl = {
  state: { get paused() { return false; }, set paused(_) {}, get quit() { return quitFlag; }, skipWait: false },
  async waitIfPaused() {},
  async sleep(ms) { const end = Date.now() + ms; while (Date.now() < end && !quitFlag) await sleep(Math.min(500, end - Date.now())); },
};

async function runOnce() {
  if (!existsSync(CSV)) { log(`❌ 找不到任务表：${CSV}`); return; }
  const pending = readTasks(CSV).filter(t => !loadDone(RESULTS).has(t.id));
  if (!pending.length) { log('没有待处理任务，跳过本轮。'); return; }
  const limit = config.daily.limit;
  log(`▶ 本轮开始：待处理 ${pending.length} 首${limit ? `，本轮上限 ${limit} 首` : ''}。`);

  const { context, page } = await suno.launch();
  try {
    await suno.gotoCreate(page);
    if (await suno.isLoginWall(page)) {
      log('⚠️ 未登录：请在浏览器窗口登录（首次需要；登录态会记住）…');
      if (!await suno.waitForLogin(page, () => log('仍在等待登录…'))) { log('❌ 超时未登录，跳过本轮。'); return; }
    }
    const harvest = (has('--download') || String(process.env.DOWNLOAD).toLowerCase() === 'true') ? attachHarvest(context, page) : null;
    const submitted = [];
    const report = (ev, d) => {
      if (ev === 'song') {
        if (d.phase === 'filling') log(`[${d.i}/${d.total}] 🎵 ${d.title} | ${d.style} | 歌单：${d.playlist}`);
        else if (d.phase === 'submitted') { log(`[${d.i}/${d.total}] ✅ 已提交${d.credits ? ' · ' + d.credits : ''}`); submitted.push({ title: d.title, playlist: d.playlist }); }
        else if (d.phase === 'retry') log(`[${d.i}/${d.total}] ↻ 第 ${d.attempt}/${d.max} 次重试：${d.message}`);
        else if (d.phase === 'credits') log(`[${d.i}/${d.total}] 🛑 额度不足：${d.message}`);
        else if (d.phase === 'error') log(`[${d.i}/${d.total}] ❌ ${d.message}`);
      } else if (ev === 'download') log(`📥 ${d.title || d.id}`);
      else if (ev === 'done') log(`本轮完成：成功 ${d.ok} · 失败 ${d.fail}`);
    };

    await runBatch({ page, ctl, report, pending, resultsPath: RESULTS, harvest, limit });

    if (has('--playlist') && submitted.length) {
      log('归类到 SUNO 歌单（best-effort）…');
      await assignPlaylists(page, submitted, report);
    }
    const idx = writePlaylistIndex(RESULTS, INDEX);
    if (idx) log(`🗂 歌单索引已更新：${idx}`);
  } finally {
    await context.close();
  }
}

async function main() {
  log(`⏰ 每日定时挂机已启动：每天 ${config.daily.at}${config.daily.limit ? ` · 每日上限 ${config.daily.limit} 首` : ''}。Ctrl+C 退出。`);
  if (has('--now')) { await runOnce(); }
  while (!quitFlag) {
    const ms = msUntil(config.daily.at);
    const next = new Date(Date.now() + ms);
    log(`下次运行：${next.toLocaleString('zh-CN')}（${Math.round(ms / 60000)} 分钟后）`);
    await ctl.sleep(ms);
    if (quitFlag) break;
    try { await runOnce(); } catch (e) { log(`本轮异常：${e.message}`); }
  }
  log('已停止。');
}

main().catch(e => { console.error('致命错误：', e); process.exit(1); });
