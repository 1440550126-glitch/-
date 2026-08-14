// 批量核心循环，被 run.js（终端）、panel.js（网页）、scheduler.js（定时）共用。
// 通过 ctl（暂停/退出/等待）与 report(event,data)（进度上报）解耦具体界面。
import { config } from './config.js';
import { generate } from './llm.js';
import { classify } from './tagger.js';
import * as suno from './suno.js';
import { recordResult } from './tasks.js';

const jitter = ms => Math.round(ms * (0.85 + Math.random() * 0.3)); // ±~15% 抖动，更像真人
const sleep = ms => new Promise(r => setTimeout(r, ms));

// 尝试「填表 + 生成 + 判定接受」，返回 { done:'ok'|'credits'|'error', ...}
async function attemptOnce(page, song, dryRun) {
  await suno.gotoCreate(page);
  const { clicked } = await suno.fillSong(page, song, { dryRun });
  if (!clicked) return { done: 'dry' };
  const r = await suno.waitAccepted(page);
  if (r.accepted) return { done: 'ok' };
  if (r.outOfCredits) return { done: 'credits', message: r.message };
  return { done: 'error', message: r.message };
}

// ctl: { state:{paused,quit,skipWait}, waitIfPaused():Promise, sleep(ms,label):Promise }
// report: (event, data) => void   事件：start / song / done
// harvest: 可选 { registerTitle, flush, drain }；limit>0 时本轮最多生成 limit 首（每日额度用）
export async function runBatch({ page, ctl, report, pending, dryRun = false, resultsPath, harvest = null, limit = 0 }) {
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
      song.playlist = classify(t, song);           // 自动归类到歌单/标签
      harvest?.registerTitle(song.title, song.playlist);
      report('song', { ...base, phase: 'filling', title: song.title, style: song.style, instrumental: song.instrumental, playlist: song.playlist, warnings: song.warnings || [] });

      // 提交 + 失败自动重试（额度不足不算重试，走暂停）
      let res, attempt = 0;
      for (;;) {
        res = await attemptOnce(page, song, dryRun);
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
        const credits = await suno.readCredits(page);
        report('song', { ...base, phase: 'submitted', title: song.title, playlist: song.playlist, credits });
        recordResult(resultsPath, { id: t.id, status: 'ok', ...song });
        if (harvest) await harvest.flush(report);
      } else if (res.done === 'credits') {
        report('song', { ...base, phase: 'credits', title: song.title, message: res.message });
        recordResult(resultsPath, { id: t.id, status: 'skipped_credits', ...song });
        ctl.state.paused = true;                    // 额度不足自动暂停
        await ctl.waitIfPaused();                    // 等用户充值后继续
        i--; continue;                               // 恢复后重试当前这首
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

  if (harvest) await harvest.drain(report);
  report('done', { ok, fail });
  return { ok, fail };
}
