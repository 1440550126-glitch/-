// 灵境AI · 工作流引擎：一键托管「剧本 → 解析 → 体检 → 出图 → 出片 → 配音 → 导出」
// 服务端逐步执行，实时进度可查询、可取消；不可用的步骤（TTS/ffmpeg 未配置）自动跳过不阻塞。
import { q } from './db.js';
import { uid, now, jparse } from './util.js';
import { bad } from './httpx.js';
import {
  getProject, generateScript, parseScript, checkConsistency, getCanvas,
  generateImage, createVideoTask, pollTask, generateDubbing
} from './pipeline.js';
import { ttsEnabled } from './tts.js';
import { ffmpegPath, exportEpisode } from './export.js';

const STEP_DEFS = [
  { name: 'script', label: '剧本' },
  { name: 'parse', label: '解析分镜' },
  { name: 'check', label: '一致性体检' },
  { name: 'images', label: '定妆照与首帧' },
  { name: 'qc', label: 'AIQC 质检' },
  { name: 'videos', label: '分镜视频' },
  { name: 'dub', label: '配音' },
  { name: 'export', label: '成片导出' }
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SKIP = (message) => Object.assign(new Error(message), { skip: true });

export function getWorkflow(id) {
  const w = q.get('SELECT * FROM workflows WHERE id = ?', id);
  if (!w) throw bad('工作流不存在');
  return { ...w, steps: jparse(w.steps, []) };
}
export function listWorkflows(projectId) {
  return q.all('SELECT id, project_id, episode, status, created_at, updated_at FROM workflows WHERE project_id = ? ORDER BY created_at DESC LIMIT 10', projectId);
}
export function cancelWorkflow(id) {
  const wf = getWorkflow(id);
  q.run('UPDATE workflows SET cancel = 1, updated_at = ? WHERE id = ?', now(), id);
  // 同步结束该项目仍在 running 的本地视频任务，让画布/任务中心停止无限轮询
  // （方舟远端任务已提交无法撤回，但本地不再轮询；前端会显示"已取消"）
  q.run(`UPDATE tasks SET status = 'failed', error = '工作流已取消', updated_at = ? WHERE project_id = ? AND kind = 'video' AND status IN ('queued','running')`, now(), wf.project_id);
  return { cancelling: true };
}

export function startWorkflow({ projectId, episode = '', steps = null }) {
  getProject(projectId);
  const running = q.get(`SELECT id FROM workflows WHERE project_id = ? AND status = 'running'`, projectId);
  if (running) throw bad(`该项目已有进行中的工作流（${running.id}），可先取消它`);
  const chosen = (Array.isArray(steps) && steps.length ? STEP_DEFS.filter((s) => steps.includes(s.name)) : STEP_DEFS)
    .map((s) => ({ ...s, status: 'pending', detail: '', ms: 0 }));
  if (!chosen.length) throw bad('没有可执行的步骤');
  const id = uid('wf');
  q.run('INSERT INTO workflows (id, project_id, episode, steps, created_at, updated_at) VALUES (?,?,?,?,?,?)',
    id, projectId, episode, JSON.stringify(chosen), now(), now());
  runWorkflow(id).catch((e) => {
    console.error('[workflow]', id, e);
    q.run(`UPDATE workflows SET status = 'failed', error = ?, updated_at = ? WHERE id = ? AND status = 'running'`,
      String(e.message).slice(0, 300), now(), id);
  });
  return getWorkflow(id);
}

async function runWorkflow(id) {
  const fresh = () => q.get('SELECT * FROM workflows WHERE id = ?', id);
  const steps = jparse(fresh().steps, []);
  const save = () => q.run('UPDATE workflows SET steps = ?, updated_at = ? WHERE id = ?', JSON.stringify(steps), now(), id);
  const finish = (status, error = '') =>
    q.run('UPDATE workflows SET status = ?, error = ?, updated_at = ? WHERE id = ?', status, error, now(), id);
  const cancelled = () => !!fresh().cancel;

  for (const st of steps) {
    if (cancelled()) {
      st.status = 'skipped';
      st.detail = '已取消';
      save();
      return finish('cancelled');
    }
    st.status = 'running';
    save();
    const t0 = now();
    try {
      st.detail = await execStep(st.name, fresh(), cancelled);
      st.status = 'done';
    } catch (e) {
      if (e.skip) {
        st.status = 'skipped';
        st.detail = e.message;
      } else {
        st.status = 'failed';
        st.detail = String(e.message).slice(0, 200);
        st.ms = now() - t0;
        save();
        return finish('failed', st.detail);
      }
    }
    st.ms = now() - t0;
    save();
  }
  finish(cancelled() ? 'cancelled' : 'succeeded');
}

async function execStep(name, wf, cancelled) {
  const projectId = wf.project_id;
  const episode = wf.episode || '';
  const project = () => getProject(projectId);
  const epShots = (c) => c.nodes.filter((n) => n.type === 'shot' && (!episode || (n.data.episode || 'e1') === episode));

  switch (name) {
    case 'script': {
      const p = project();
      if (p.script?.trim()) return '已有剧本，沿用';
      const r = await generateScript({ projectId, idea: p.idea || p.title, genre: p.genre });
      return `已生成（${r.script.length} 字${r.byLLM ? '' : '，本地引擎'}）`;
    }
    case 'parse': {
      const p = project();
      if (p.storyboard && p.canvas_id) return '已有分镜，沿用';
      const r = await parseScript({ projectId });
      return `${r.storyboard.characters.length} 角色 / ${r.storyboard.scenes.length} 场景 / ${r.storyboard.shots.length} 分镜`;
    }
    case 'check': {
      const r = checkConsistency(projectId);
      return `评分 ${r.score}（${r.issues.filter((i) => i.level === 'err').length} 项待修复，下一步自动补齐）`;
    }
    case 'images': {
      const p = project();
      if (!p.canvas_id) throw bad('没有画布');
      const c = getCanvas(p.canvas_id);
      // 严格两阶段：定妆照全部完成后才生成分镜首帧（画面一致性）
      const base = c.nodes.filter((n) => n.type !== 'shot' && n.type !== 'note' && !n.data.image && (n.data.prompt || n.data.image_prompt));
      const frames = epShots(c).filter((n) => !n.data.image && n.data.image_prompt);
      let done = 0;
      let failed = 0;
      for (const n of [...base, ...frames]) {
        if (cancelled()) break;
        try {
          await generateImage({
            prompt: n.data.image_prompt || n.data.prompt, name: n.data.name,
            kind: n.type === 'shot' ? 'frame' : n.type, projectId, nodeId: n.id
          });
          done++;
        } catch (e) { failed++; console.warn('[workflow] 出图失败：', n.data.name, e.message); }
      }
      if (!done && failed) throw bad(`出图全部失败（${failed} 张）`);
      return `生成 ${done} 张${failed ? `（失败 ${failed}）` : ''}${base.length + frames.length === 0 ? '（无需生成）' : ''}`;
    }
    case 'qc': {
      const { qcEnabled, qcNode, listQC, qcSummary } = await import('./qc.js');
      if (!qcEnabled()) throw SKIP('AIQC 已关闭（设置页可开启）');
      const c = getCanvas(project().canvas_id);
      const framed = epShots(c).filter((n) => n.data.image);
      if (!framed.length) return '无首帧可质检';
      // 出图阶段已自动质检过的帧不重复扫（省成本），只补扫没有记录的
      const scanned = new Set(listQC(projectId).map((r) => r.node_id));
      const todo = framed.filter((n) => !scanned.has(n.id));
      let fixed = 0;
      for (const n of todo.slice(0, 60)) {
        if (cancelled()) break;
        try { const r = await qcNode(projectId, n.id, { stage: 'image' }); if (r.fixed) fixed++; } catch { /* noop */ }
      }
      const s = qcSummary(projectId);
      return `已质检 ${framed.length} 帧（本步补扫 ${todo.length}，修正 ${fixed}）｜均分 ${s.avg_score}，待处理 ${s.open}（详见 🔬QC）`;
    }
    case 'videos': {
      const { getSetting } = await import('./db.js');
      const chain = getSetting('video_chain', false) === true;   // 接龙模式：上段尾帧→下段首帧
      const p = project();
      const c = getCanvas(p.canvas_id);
      const todo = epShots(c).filter((n) => !n.data.video).sort((a, b) => (a.data.order || 0) - (b.data.order || 0));
      if (!todo.length) return '已全部出片（无需生成）';

      if (chain) {
        // 顺序生成：每段等完成→抽尾帧→作为下一段首帧（画面连续）
        const { extractLastFrame } = await import('./export.js');
        let prevFrame = '';
        let okC = 0, failC = 0;
        for (const n of todo) {
          if (cancelled()) break;
          const firstFrame = prevFrame || n.data.image;
          let r;
          try {
            r = await createVideoTask({
              prompt: n.data.video_prompt || n.data.action || n.data.name, imageUrl: firstFrame,
              duration: n.data.duration, projectId, nodeId: n.id, name: n.data.name, order: n.data.order
            });
          } catch (e) { failC++; if (!okC && todo.indexOf(n) === 0) throw bad(e.message); continue; }
          // 等这一段完成
          const deadline = now() + 6 * 60_000;
          let t = await pollTask(r.taskId);
          while (t.status !== 'succeeded' && t.status !== 'failed' && now() < deadline && !cancelled()) { await sleep(2500); t = await pollTask(r.taskId); }
          if (t.status === 'succeeded') { okC++; prevFrame = extractLastFrame(t.result?.url) || n.data.image; }
          else { failC++; prevFrame = n.data.image; }   // 失败则重置接龙锚点
        }
        return `接龙完成 ${okC}/${todo.length}${failC ? `（失败 ${failC}）` : ''}${ffmpegPath() ? '' : '（无 ffmpeg，退化为各自首帧）'}`;
      }

      // 并行模式（默认）
      const tasks = [];
      let firstErr = '';
      for (const n of todo) {
        if (cancelled()) break;
        try {
          const r = await createVideoTask({
            prompt: n.data.video_prompt || n.data.action || n.data.name, imageUrl: n.data.image,
            duration: n.data.duration, projectId, nodeId: n.id, name: n.data.name, order: n.data.order
          });
          tasks.push(r.taskId);
        } catch (e) { if (!firstErr) firstErr = e.message; console.warn('[workflow] 视频任务失败：', n.data.name, e.message); }
      }
      if (!tasks.length) {
        if (todo.length && firstErr) throw bad(firstErr);
        return todo.length ? '视频任务全部创建失败' : '已全部出片（无需生成）';
      }
      const deadline = now() + 15 * 60_000;
      let ok = 0;
      let fail = 0;
      const pending = new Set(tasks);
      while (pending.size && now() < deadline && !cancelled()) {
        for (const tid of [...pending]) {
          const t = await pollTask(tid);
          if (t.status === 'succeeded') { ok++; pending.delete(tid); }
          else if (t.status === 'failed') { fail++; pending.delete(tid); }
        }
        if (pending.size) await sleep(2500);
      }
      return `完成 ${ok}/${tasks.length}${fail ? `（失败 ${fail}）` : ''}${pending.size ? `（${pending.size} 个超时仍在后台生成）` : ''}`;
    }
    case 'dub': {
      if (!ttsEnabled()) throw SKIP('未配置火山 TTS，已跳过（设置页可开启）');
      try {
        const r = await generateDubbing({ projectId, episode });
        return `配音 ${r.dubbed} 镜`;
      } catch (e) { throw SKIP(`配音跳过：${e.message.slice(0, 120)}`); }
    }
    case 'export': {
      if (!ffmpegPath()) throw SKIP('未检测到 ffmpeg，已跳过（安装后可一键导出）');
      try {
        const r = await exportEpisode({ projectId, episode });
        return `成片已导出：${r.url}（${r.shots} 镜）`;
      } catch (e) { throw SKIP(`导出跳过：${e.message.slice(0, 120)}`); }
    }
    default:
      throw SKIP('未知步骤');
  }
}
