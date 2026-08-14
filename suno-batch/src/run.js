// 终端入口：读 CSV → (大模型补全) → Playwright 填表并生成 → 挂机循环。
// 用法：
//   node src/run.js [tasks.csv]         正式挂机（终端热键 p/s/q）
//   --dry-run       只填表不点生成（验证选择器/内容，安全）
//   --inspect       打开浏览器停住，手动核对页面/选择器
//   --generate-only 只跑大模型生成内容并落盘，不开浏览器
//   --login-only    只打开浏览器登录一次（持久化登录态）
//   --login-all     多账号：逐个打开登录（ACCOUNTS 每个目录一个号）
//   --download      挂机同时自动下载生成好的音频到 var/downloads/
//   --rotate        多账号轮换（额度耗尽自动切下一个号；ACCOUNTS 配多个时默认开）
//   --quality       生成后按时长/状态质检，跑坏的自动重排生成
//   --playlist      生成后把歌加入 SUNO 站内歌单（best-effort）
//   --retry-only    只补跑之前失败的
// 想要网页控制台见 src/panel.js；每日定时见 src/scheduler.js。
import { resolve, join } from 'node:path';
import { existsSync } from 'node:fs';
import { config } from './config.js';
import { readTasks, loadDone, loadFailed, recordResult, writePlaylistIndex } from './tasks.js';
import { generate } from './llm.js';
import * as suno from './suno.js';
import { createControl, log } from './control.js';
import { runBatch } from './engine.js';
import { openSession, listAccounts, loginAll } from './session.js';
import { assignPlaylists } from './playlist.js';
import { reviewQuality } from './quality.js';

const args = process.argv.slice(2);
const has = f => args.includes(f);
const csvArg = args.find(a => !a.startsWith('--'));
const CSV = resolve(config.root, csvArg || 'tasks.csv');
const RESULTS = join(config.root, 'var', 'results.jsonl');

// 把 engine 事件映射成终端日志（保持原有观感）
function consoleReport(event, d) {
  if (event === 'start') { log(`开始挂机（共 ${d.total} 首）。热键：p 暂停/继续 · s 跳过等待 · q 退出。${d.dryRun ? '【dry-run】' : ''}`); return; }
  if (event === 'done') { log(`收尾：成功 ${d.ok} · 失败/未确认 ${d.fail}。进度存 ${RESULTS}（续跑自动跳过成功项）。`); return; }
  if (event === 'download') { log(`📥 已下载：${d.title || d.id}`); return; }
  if (event === 'harvest-done') { log(`📥 下载收尾，共 ${d.total} 个音频`); return; }
  if (event === 'playlist') { log(d.ok ? `🗂 已加入歌单「${d.playlist}」：${d.title}` : `🗂 未能归类：${d.title}`); return; }
  if (event === 'playlist-done') { log(`🗂 歌单归类：成功 ${d.ok} · 未成 ${d.miss}`); return; }
  if (event === 'quality') { log(d.ok ? `🔎 质检通过：${d.title}` : `🔎 质检不合格，已重排：${d.title}（${d.reasons}）`); return; }
  if (event === 'quality-done') { log(`🔎 质量回捞：合格 ${d.good} · 重排 ${d.requeued} · 未捕获 ${d.unknown}`); return; }
  if (event === 'log') { log(d.message); return; }
  if (event !== 'song') return;
  const tag = `[${d.i}/${d.total}]`;
  if (d.phase === 'generating') log(`${tag} ✍️  生成内容：${d.theme || ''}`);
  else if (d.phase === 'filling') { log(`${tag} 🎵 ${d.title || '(无题)'} | 曲风：${d.style} | 歌单：${d.playlist}${d.instrumental ? ' | 器乐' : ''}`); if (d.warnings?.length) log(`${tag} ⚠  ${d.warnings.join('；')}`); }
  else if (d.phase === 'retry') log(`${tag} ↻ 第 ${d.attempt}/${d.max} 次重试：${d.message}`);
  else if (d.phase === 'rotate') log(`${tag} 🔁 额度耗尽，已切换账号，续跑本首`);
  else if (d.phase === 'submitted') log(`${tag} ✅ 已提交生成${d.credits ? ` · ${d.credits}` : ''}`);
  else if (d.phase === 'dry') log(`${tag} ✓ 已填表（dry-run，未生成）`);
  else if (d.phase === 'credits') log(`${tag} 🛑 额度不足：${d.message}。已暂停——充值后按 p 继续，或 q 退出。`);
  else if (d.phase === 'error') log(`${tag} ❌ ${d.message}`);
}

async function main() {
  if (has('--login-only')) {
    const { context, page } = await suno.launch();
    await suno.gotoCreate(page);
    if (await suno.isLoginWall(page)) {
      log('请在弹出的浏览器窗口完成登录…');
      const ok = await suno.waitForLogin(page, () => log('仍在等待登录…'));
      log(ok ? '✅ 登录成功，登录态已保存，下次直接挂机。' : '❌ 超时未登录。');
    } else log('✅ 已是登录态。');
    await context.close();
    return;
  }

  // 多账号：逐个打开让你登录（ACCOUNTS 里每个目录一个号）
  if (has('--login-all')) {
    const accounts = listAccounts();
    log(`共 ${accounts.length} 个账号目录：${accounts.map(a => a.name).join('、')}`);
    await loginAll(m => log(m));
    log('全部账号登录流程结束。');
    return;
  }

  if (!existsSync(CSV)) {
    log(`❌ 找不到任务表：${CSV}`);
    log(`   先复制模板：cp tasks.example.csv tasks.csv，然后填写。`);
    process.exit(1);
  }

  const all = readTasks(CSV);
  const done = loadDone(RESULTS);
  let pending;
  if (has('--retry-only')) {
    const failed = loadFailed(RESULTS);
    pending = all.filter(t => failed.has(t.id) && !done.has(t.id));
    log(`重试模式：只跑之前失败的 ${pending.length} 首。`);
  } else {
    pending = all.filter(t => !done.has(t.id));
    log(`任务表 ${all.length} 首，已完成 ${done.size} 首，本次待处理 ${pending.length} 首。`);
  }
  if (!pending.length) { log('没有待处理任务。要重跑请删除 var/results.jsonl。'); return; }

  if (has('--generate-only')) {
    for (const t of pending) {
      try {
        const s = await generate(t);
        recordResult(RESULTS, { id: t.id, status: 'generated', ...s });
        log(`📝 ${s.title || '(无题)'} | ${s.style}${s.warnings?.length ? ` | ⚠ ${s.warnings.join('；')}` : ''}`);
      } catch (e) { log(`⚠️  生成失败 [${t.theme}]：${e.message}`); }
    }
    log(`✅ 生成完成，内容已写入 ${RESULTS}（status=generated）。审阅后正式挂机会重新生成缺字段。`);
    return;
  }

  if (has('--inspect')) {
    const { context, page } = await suno.launch();
    await suno.gotoCreate(page);
    log('🔍 inspect 模式：浏览器已停在创作页。核对输入框后按 Ctrl+C 退出。');
    await page.waitForTimeout(10 * 60_000);
    await context.close();
    return;
  }

  const dryRun = has('--dry-run');
  const download = has('--download') || String(process.env.DOWNLOAD).toLowerCase() === 'true';
  const rotate = has('--rotate') || config.accounts.length > 1;
  const sess = await openSession({ download, rotate, onLog: m => log(m) });
  if (rotate) log(`🔁 多账号轮换：${sess.accounts.map(a => a.name).join(' → ')}（额度耗尽自动切换）`);
  if (download) log('📥 已开启自动下载：音频将按歌单存入 var/downloads/');

  const ctl = createControl();
  const submitted = [];
  const report = (ev, d) => { if (ev === 'song' && d.phase === 'submitted') submitted.push({ id: d.id, title: d.title, playlist: d.playlist }); consoleReport(ev, d); };
  await runBatch({ session: sess.session, rotate: sess.rotate, ctl, report, pending, dryRun, resultsPath: RESULTS });

  if (has('--quality') && submitted.length && !dryRun) {
    log('质量回捞：按时长/状态筛查，跑坏的自动重排…');
    reviewQuality(submitted, sess.getClips(), RESULTS, report);
  }
  if (has('--playlist') && submitted.length && !dryRun) {
    log('归类到 SUNO 歌单（best-effort，失效不影响其它）…');
    await assignPlaylists(sess.session.page, submitted, report);
  }
  const idx = writePlaylistIndex(RESULTS, join(config.root, 'var', 'playlists.md'));
  if (idx) log(`🗂 歌单索引已更新：${idx}`);

  ctl.stop();
  await sess.close();
}

main().catch(e => { console.error('致命错误：', e); process.exit(1); });
