// 终端入口：读 CSV → (大模型补全) → Playwright 填表并生成 → 挂机循环。
// 用法：
//   node src/run.js [tasks.csv]         正式挂机（终端热键 p/s/q）
//   --dry-run       只填表不点生成（验证选择器/内容，安全）
//   --inspect       打开浏览器停住，手动核对页面/选择器
//   --generate-only 只跑大模型生成内容并落盘，不开浏览器
//   --login-only    只打开浏览器登录一次（持久化登录态）
//   --download      挂机同时自动下载生成好的音频到 var/downloads/
// 想要网页控制台见 src/panel.js（node src/panel.js）。
import { resolve, join } from 'node:path';
import { existsSync } from 'node:fs';
import { config } from './config.js';
import { readTasks, loadDone, recordResult } from './tasks.js';
import { generate } from './llm.js';
import * as suno from './suno.js';
import { createControl, log } from './control.js';
import { runBatch } from './engine.js';
import { attachHarvest } from './harvest.js';

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
  if (event !== 'song') return;
  const tag = `[${d.i}/${d.total}]`;
  if (d.phase === 'generating') log(`${tag} ✍️  生成内容：${d.theme || ''}`);
  else if (d.phase === 'filling') { log(`${tag} 🎵 ${d.title || '(无题)'} | 曲风：${d.style}${d.instrumental ? ' | 器乐' : ''}`); if (d.warnings?.length) log(`${tag} ⚠  ${d.warnings.join('；')}`); }
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

  if (!existsSync(CSV)) {
    log(`❌ 找不到任务表：${CSV}`);
    log(`   先复制模板：cp tasks.example.csv tasks.csv，然后填写。`);
    process.exit(1);
  }

  const all = readTasks(CSV);
  const done = loadDone(RESULTS);
  const pending = all.filter(t => !done.has(t.id));
  log(`任务表 ${all.length} 首，已完成 ${done.size} 首，本次待处理 ${pending.length} 首。`);
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

  const dryRun = has('--dry-run');
  const { context, page } = await suno.launch();
  await suno.gotoCreate(page);
  if (await suno.isLoginWall(page)) {
    log('检测到未登录，请在浏览器窗口完成登录…');
    const ok = await suno.waitForLogin(page, () => log('仍在等待登录…'));
    if (!ok) { log('❌ 超时未登录，退出。'); await context.close(); return; }
  }

  if (has('--inspect')) {
    log('🔍 inspect 模式：浏览器已停在创作页。核对输入框后按 Ctrl+C 退出。');
    await page.waitForTimeout(10 * 60_000);
    await context.close();
    return;
  }

  const harvest = (has('--download') || String(process.env.DOWNLOAD).toLowerCase() === 'true')
    ? attachHarvest(context, page) : null;
  if (harvest) log('📥 已开启自动下载：生成好的音频将存入 var/downloads/');

  const ctl = createControl();
  await runBatch({ page, ctl, report: consoleReport, pending, dryRun, resultsPath: RESULTS, harvest });
  ctl.stop();
  await context.close();
}

main().catch(e => { console.error('致命错误：', e); process.exit(1); });
