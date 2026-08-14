// 批量核心循环，被 run.js（终端）、panel.js（网页）、scheduler.js（定时）共用。
// 通过 ctl（暂停/退出/等待）与 report(event,data)（进度上报）解耦具体界面。
// 账号轮换：额度耗尽时调用 opts.rotate()；有下一个账号则切换续跑，否则暂停。
import { config } from './config.js';
import { generate } from './llm.js';
import { classify } from './tagger.js';
import * as suno from './suno.js';
import { recordResult } from './tasks.js';

const jitter = ms => Math.round(ms * (0.85 + Math.random() * 0.3)); // ±~15% 抖动，更像真人

// 尝试「填表 + 生成 + 判定接受」，返回 { done:'ok'|'dry'|'credits'|'error', ...}
async function attemptOnce(page, song, dryRun) {
  await suno.gotoCreate(page);
  const { clicked } = await suno.fillSong(page, song, { dryRun });
  if (!clicked) return { done: 'dry' };
  const r = await suno.waitAccepted(page);
  if (r.accepted) return { done: 'ok' };
  if (r.outOfCredits) return { done: 'credits', message: r.message };
  return { done: 'error', message: r.message };
}

// opts:
//   session?: 可变 { page, harvest }（多账号轮换用）；或直接 page/harvest（单账号）
//   rotate?: async () => newPage|null  额度耗尽时切换账号
//   ctl, report, pending, dryRun, resultsPath, limit
export async function runBatch(opts) {
  const { ctl, report, pending, dryRun = false, resultsPath, rotate, limit = 0 } = opts;
  const getPage = () => (opts.session ? opts.session.page : opts.page);
  const getHarvest = () => (opts.session ? opts.session.harvest : opts.harvest);

  const cap = limit > 0 ? Math.min(limit, pending.length) : pending.length;
  report('start', { total: cap, dryRun, limit });
  const maxRetries = config.retry.max;
  let ok = 0, fail = 0, produced = 0;

  for (let i = 0; i < pending.length; i++) {
    if (ctl.state.quit) break;
    if (limit > 0 && produced >= limit) { report('log', { message: `已达本轮上限 ${limit} 首，停止。` }); break; }
    await ctl.waitIfPaused();
    if (ctl.state.quit) break;

    const t = pending[i];
    const base = { i: produced + 1, total: cap, id: t.id, theme: t.theme };
    try {
      report('song', { ...base, phase: 'generating' });
      const song = await generate(t);
      song.instrumental = t.instrumental;
      song.playlist = classify(t, song);
      getHarvest()?.registerTitle(song.title, song.playlist);
      report('song', { ...base, phase: 'filling', title: song.title, style: song.style, instrumental: song.instrumental, playlist: song.playlist, warnings: song.warnings || [] });

      // 提交 + 失败自动重试（额度不足不算重试）
      let res, attempt = 0;
      for (;;) {
        res = await attemptOnce(getPage(), song, dryRun);
        if (res.done !== 'error' || attempt >= maxRetries) break;
        attempt++;
        report('song', { ...base, phase: 'retry', title: song.title, attempt, max: maxRetries, message: res.message });
        await ctl.sleep(config.retry.backoffMs, `第 ${attempt} 次重试前等待`);
        if (ctl.state.quit) break;
      }

      if (res.done === 'dry') {
        produced++; report('song', { ...base, phase: 'dry', title: song.title, playlist: song.playlist });
        recordResult(resultsPath, { id: t.id, status: 'dry', ...song });
      } else if (res.done === 'ok') {
        ok++; produced++;
        const credits = await suno.readCredits(getPage());
        report('song', { ...base, phase: 'submitted', title: song.title, playlist: song.playlist, credits });
        recordResult(resultsPath, { id: t.id, status: 'ok', ...song });
        await getHarvest()?.flush(report);
      } else if (res.done === 'credits') {
        // 先尝试切换账号；有下一个账号则续跑当前这首
        const np = rotate ? await rotate() : null;
        if (np) { report('song', { ...base, phase: 'rotate', title: song.title }); i--; continue; }
        report('song', { ...base, phase: 'credits', title: song.title, message: res.message });
        recordResult(resultsPath, { id: t.id, status: 'skipped_credits', ...song });
        ctl.state.paused = true;                    // 无更多账号 → 暂停等充值
        await ctl.waitIfPaused();
        i--; continue;
      } else {
        fail++;
        report('song', { ...base, phase: 'error', title: song.title, message: `重试 ${maxRetries} 次仍失败：${res.message}` });
        recordResult(resultsPath, { id: t.id, status: 'error', message: res.message, ...song });
      }
    } catch (e) {
      fail++;
      report('song', { ...base, phase: 'error', message: e.message });
      recordResult(resultsPath, { id: t.id, status: 'error', message: e.message });
    }

    const more = (limit > 0 ? produced < limit : true) && i < pending.length - 1;
    if (more && !ctl.state.quit) await ctl.sleep(jitter(config.timing.betweenSongsMs), '等待下一首');
  }

  await getHarvest()?.drain(report);
  report('done', { ok, fail });
  return { ok, fail };
}
