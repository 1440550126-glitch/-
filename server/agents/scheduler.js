// 灵阵 · 定时触发器调度器：让团队按计划自动执行任务（对标并超越扣子的定时任务）
// 与 AI 暖场调度同构：setInterval 轮询到期触发器，逐个发起运行。
// 防滥用：最小间隔 30 分钟、单用户最多 5 个启用触发器、每轮限发数量；成本仍受引擎每日预算闸门约束。
import { q } from '../lib/db.js';
import { now, dayCN, clamp, jparse } from '../lib/util.js';
import { startTeamRun } from './engine.js';

export const MIN_INTERVAL_MIN = 30;
export const MAX_TRIGGERS = 5;

// 计算下一次触发时间
export function computeNext(trigger, from = now()) {
  if (trigger.schedule_kind === 'daily') {
    const h = clamp(trigger.at_hour, 0, 23), m = clamp(trigger.at_minute, 0, 59);
    let t = new Date(`${dayCN(from)}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00+08:00`).getTime();
    if (t <= from) t += 86400_000;                 // 今天已过 → 明天
    return t;
  }
  const mins = Math.max(MIN_INTERVAL_MIN, Number(trigger.interval_min) || MIN_INTERVAL_MIN);
  return from + mins * 60_000;
}

// 触发一次（更新调度状态）；团队已删/空则自动停用
export function fireTrigger(trigger, { advance = true } = {}) {
  const team = q.get('SELECT * FROM teams WHERE id = ?', trigger.team_id);
  const members = team ? (jparse(team.member_ids, []) || []) : [];
  if (!team || !members.length) {
    q.run('UPDATE agent_triggers SET enabled = 0, updated_at = ? WHERE id = ?', now(), trigger.id);
    return null;
  }
  const runId = startTeamRun(team, trigger.task, trigger.owner_id, 'trigger');
  q.run(
    `UPDATE agent_triggers SET last_run_at = ?, last_run_id = ?, run_count = run_count + 1,
       ${advance ? 'next_run_at = ?,' : ''} updated_at = ? WHERE id = ?`,
    ...(advance ? [now(), runId, computeNext(trigger), now(), trigger.id] : [now(), runId, now(), trigger.id])
  );
  return runId;
}

// 执行所有到期触发器
export function runDueTriggers(limit = 5) {
  const due = q.all('SELECT * FROM agent_triggers WHERE enabled = 1 AND next_run_at <= ? ORDER BY next_run_at LIMIT ?', now(), limit);
  let fired = 0;
  for (const t of due) {
    try { if (fireTrigger(t)) fired++; }
    catch (e) { console.warn('[trigger] fire failed', t.id, e.message); }
  }
  return fired;
}

let timer = null;
export function startTriggerLoop(intervalMs = 30_000) {
  if (timer) return;
  timer = setInterval(() => {
    try { runDueTriggers(); } catch (e) { console.warn('[trigger] tick', e.message); }
  }, intervalMs);
  if (timer.unref) timer.unref();
  console.log('  ⏰ 灵阵：定时触发器调度已启动');
}
