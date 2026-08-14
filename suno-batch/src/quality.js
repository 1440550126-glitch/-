// 生成质量回捞：用 SUNO 返回的 clip 元数据（时长/状态/是否出音频）筛掉「明显跑坏」的，
// 把对应任务标记回 error(quality)，下次 --retry-only / 下一轮定时挂机会自动重新生成。
// 说明：这是基于元数据的可靠代理信号（时长过短、状态异常、无音频=典型的生成失败/截断）。
// 更进一步的「听内容判跑题」需要音频模型，属可选增强，这里不做武断判断。
import { config } from './config.js';
import { recordResult } from './tasks.js';

// 单个 clip 质检 → { pass, reasons, duration }
export function assess(clip) {
  const reasons = [];
  const dur = Number(clip.duration || 0);
  if (!clip.audio_url) reasons.push('无音频输出');
  if (clip.status && /error|fail|rejected|banned/i.test(clip.status)) reasons.push(`状态异常(${clip.status})`);
  if (dur > 0 && dur < config.quality.minSec) reasons.push(`时长过短 ${Math.round(dur)}s < ${config.quality.minSec}s`);
  if (dur > config.quality.maxSec) reasons.push(`时长异常 ${Math.round(dur)}s > ${config.quality.maxSec}s`);
  return { pass: reasons.length === 0, reasons, duration: dur };
}

// 归一化歌名用于匹配（SUNO 可能大小写/空白略变）
const norm = s => (s || '').trim().toLowerCase().replace(/\s+/g, ' ');

// 对本轮提交的任务做质检回捞。
// submitted: [{ id, title, playlist }]；clips: harvest.getClips()
// 一个任务对应的所有 clip 都不合格 → 标 error(quality) 以便重生成；有一个合格即算通过。
export function reviewQuality(submitted, clips, resultsPath, report = () => {}) {
  const byTitle = new Map();
  for (const c of clips) {
    const k = norm(c.title);
    if (!k) continue;
    if (!byTitle.has(k)) byTitle.set(k, []);
    byTitle.get(k).push(c);
  }
  let good = 0, requeued = 0, unknown = 0;
  for (const t of submitted) {
    const cs = byTitle.get(norm(t.title)) || [];
    if (!cs.length) { unknown++; continue; }         // 没捕获到 clip（可能生成未回传），不动它
    const verdicts = cs.map(assess);
    const anyPass = verdicts.some(v => v.pass);
    if (anyPass) { good++; report('quality', { title: t.title, ok: true }); }
    else {
      requeued++;
      const reasons = [...new Set(verdicts.flatMap(v => v.reasons))].join('；');
      // 覆盖为 error，使 loadDone(按最后状态) 不再视其为已完成 → 会被重排
      recordResult(resultsPath, { id: t.id, status: 'error', message: `质量回捞：${reasons}`, title: t.title, playlist: t.playlist });
      report('quality', { title: t.title, ok: false, reasons });
    }
  }
  report('quality-done', { good, requeued, unknown });
  return { good, requeued, unknown };
}
