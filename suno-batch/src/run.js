// 主入口：读 CSV → (大模型补全) → Playwright 填表并生成 → 挂机循环。
// 用法：
//   node src/run.js [tasks.csv]         正式挂机
//   --dry-run       只填表不点生成（验证选择器/内容，安全）
//   --inspect       打开浏览器停住，让你手动核对页面/选择器
//   --generate-only 只跑大模型生成内容并落盘，不开浏览器
//   --login-only    只打开浏览器让你登录一次（持久化登录态）
import { resolve, join } from 'node:path';
import { existsSync } from 'node:fs';
import { config } from './config.js';
import { readTasks, loadDone, recordResult, taskId } from './tasks.js';
import { generate } from './llm.js';
import * as suno from './suno.js';
import { createControl, log } from './control.js';

const args = process.argv.slice(2);
const has = f => args.includes(f);
const csvArg = args.find(a => !a.startsWith('--'));
const CSV = resolve(config.root, csvArg || 'tasks.csv');
const RESULTS = join(config.root, 'var', 'results.jsonl');

const jitter = ms => Math.round(ms * (0.85 + Math.random() * 0.3)); // ±~15% 抖动

async function main() {
  // --login-only：单纯登录一次
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

  // --generate-only：只生成内容并落盘，方便先审歌词再挂机
  if (has('--generate-only')) {
    for (const t of pending) {
      try {
        const s = await generate(t);
        recordResult(RESULTS, { id: t.id, status: 'generated', ...s });
        log(`📝 ${s.title || '(无题)'} | ${s.style}`);
      } catch (e) { log(`⚠️  生成失败 [${t.theme}]：${e.message}`); }
    }
    log(`✅ 生成完成，内容已写入 ${RESULTS}（status=generated）。审阅后正式挂机会重新生成缺字段，如需沿用请填回 CSV。`);
    return;
  }

  const dryRun = has('--dry-run');
  const inspect = has('--inspect');
  const { context, page } = await suno.launch();

  await suno.gotoCreate(page);
  if (await suno.isLoginWall(page)) {
    log('检测到未登录，请在浏览器窗口完成登录…');
    const ok = await suno.waitForLogin(page, () => log('仍在等待登录…'));
    if (!ok) { log('❌ 超时未登录，退出。'); await context.close(); return; }
  }

  if (inspect) {
    log('🔍 inspect 模式：浏览器已停在创作页。核对输入框后按 Ctrl+C 退出。');
    await page.waitForTimeout(10 * 60_000);
    await context.close();
    return;
  }

  const ctl = createControl();
  log(`开始挂机（共 ${pending.length} 首）。热键：p 暂停/继续 · s 跳过等待 · q 退出。${dryRun ? '【dry-run：只填不生成】' : ''}`);

  let ok = 0, fail = 0;
  for (let i = 0; i < pending.length; i++) {
    if (ctl.state.quit) break;
    await ctl.waitIfPaused();
    if (ctl.state.quit) break;

    const t = pending[i];
    const tag = `[${i + 1}/${pending.length}]`;
    try {
      const song = await generate(t);
      log(`${tag} 🎵 ${song.title || '(无题)'} | 曲风：${song.style}${song.instrumental ? ' | 器乐' : ''}`);
      song.instrumental = t.instrumental;

      await suno.gotoCreate(page);
      const { clicked } = await suno.fillSong(page, song, { dryRun });

      if (!clicked) {
        log(`${tag} ✓ 已填表（dry-run，未生成）`);
        recordResult(RESULTS, { id: t.id, status: 'dry', ...song });
      } else {
        const r = await suno.waitAccepted(page);
        if (r.accepted) {
          ok++;
          const credits = await suno.readCredits(page);
          log(`${tag} ✅ 已提交生成${credits ? ` · ${credits}` : ''}`);
          recordResult(RESULTS, { id: t.id, status: 'ok', ...song });
        } else if (r.outOfCredits) {
          log(`${tag} 🛑 额度不足：${r.message}。暂停挂机——充值/等待后按 p 继续，或 q 退出。`);
          recordResult(RESULTS, { id: t.id, status: 'skipped_credits', ...song });
          ctl.state.paused = true;
          await ctl.waitIfPaused();
          i--; // 恢复后重试这一首
          continue;
        } else {
          fail++;
          log(`${tag} ⚠️  未确认提交：${r.message}`);
          recordResult(RESULTS, { id: t.id, status: 'error', message: r.message, ...song });
        }
      }
    } catch (e) {
      fail++;
      log(`${tag} ❌ 失败：${e.message}`);
      recordResult(RESULTS, { id: t.id, status: 'error', message: e.message });
    }

    if (i < pending.length - 1 && !ctl.state.quit) {
      await ctl.sleep(jitter(config.timing.betweenSongsMs));
    }
  }

  ctl.stop();
  log(`收尾：成功 ${ok} · 失败/未确认 ${fail}。进度已存 ${RESULTS}（续跑会自动跳过成功项）。`);
  await context.close();
}

main().catch(e => { console.error('致命错误：', e); process.exit(1); });
