// 批量核心循环，被 run.js（终端）和 panel.js（网页）共用。
// 通过 ctl（暂停/退出/等待）与 report(event,data)（进度上报）解耦具体界面。
import { config } from './config.js';
import { generate } from './llm.js';
import * as suno from './suno.js';
import { recordResult } from './tasks.js';

const jitter = ms => Math.round(ms * (0.85 + Math.random() * 0.3)); // ±~15% 抖动，更像真人

// ctl: { state:{paused,quit,skipWait}, waitIfPaused():Promise, sleep(ms,label):Promise }
// report: (event, data) => void   事件：start / song / done
// harvest: 可选，{ flush(report), drain(report) }
export async function runBatch({ page, ctl, report, pending, dryRun = false, resultsPath, harvest = null }) {
  report('start', { total: pending.length, dryRun });
  let ok = 0, fail = 0;

  for (let i = 0; i < pending.length; i++) {
    if (ctl.state.quit) break;
    await ctl.waitIfPaused();
    if (ctl.state.quit) break;

    const t = pending[i];
    const base = { i: i + 1, total: pending.length, id: t.id, theme: t.theme };
    try {
      report('song', { ...base, phase: 'generating' });
      const song = await generate(t);
      song.instrumental = t.instrumental;
      report('song', { ...base, phase: 'filling', title: song.title, style: song.style, instrumental: song.instrumental, warnings: song.warnings || [] });

      await suno.gotoCreate(page);
      const { clicked } = await suno.fillSong(page, song, { dryRun });

      if (!clicked) {
        report('song', { ...base, phase: 'dry', title: song.title });
        recordResult(resultsPath, { id: t.id, status: 'dry', ...song });
      } else {
        const r = await suno.waitAccepted(page);
        if (r.accepted) {
          ok++;
          const credits = await suno.readCredits(page);
          report('song', { ...base, phase: 'submitted', title: song.title, credits });
          recordResult(resultsPath, { id: t.id, status: 'ok', ...song });
          if (harvest) await harvest.flush(report);
        } else if (r.outOfCredits) {
          report('song', { ...base, phase: 'credits', title: song.title, message: r.message });
          recordResult(resultsPath, { id: t.id, status: 'skipped_credits', ...song });
          ctl.state.paused = true;               // 额度不足自动暂停
          await ctl.waitIfPaused();               // 等用户充值后 p/继续
          i--;                                     // 恢复后重试当前这首
          continue;
        } else {
          fail++;
          report('song', { ...base, phase: 'error', title: song.title, message: r.message });
          recordResult(resultsPath, { id: t.id, status: 'error', message: r.message, ...song });
        }
      }
    } catch (e) {
      fail++;
      report('song', { ...base, phase: 'error', message: e.message });
      recordResult(resultsPath, { id: t.id, status: 'error', message: e.message });
    }

    if (i < pending.length - 1 && !ctl.state.quit) {
      await ctl.sleep(jitter(config.timing.betweenSongsMs), '等待下一首');
    }
  }

  if (harvest) await harvest.drain(report);
  report('done', { ok, fail });
  return { ok, fail };
}
