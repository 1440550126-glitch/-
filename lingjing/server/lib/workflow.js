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
  { name: 'expressions', label: '角色表情库' },
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

export function startWorkflow({ projectId, episode = '', steps = null, videoModel = '' }) {
  getProject(projectId);
  const running = q.get(`SELECT id FROM workflows WHERE project_id = ? AND status = 'running'`, projectId);
  if (running) throw bad(`该项目已有进行中的工作流（${running.id}），可先取消它`);
  const chosen = (Array.isArray(steps) && steps.length ? STEP_DEFS.filter((s) => steps.includes(s.name)) : STEP_DEFS)
    .map((s) => ({ ...s, status: 'pending', detail: '', ms: 0 }));
  if (!chosen.length) throw bad('没有可执行的步骤');
  const id = uid('wf');
  q.run('INSERT INTO workflows (id, project_id, episode, steps, video_model, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
    id, projectId, episode, JSON.stringify(chosen), String(videoModel || '').slice(0, 80), now(), now());
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
    case 'expressions': {
      const { getSetting } = await import('./db.js');
      if (getSetting('auto_expressions', false) !== true) throw SKIP('未开启「角色表情库自动生成」（设置页可开启）');
      const { generateExpressions } = await import('./pipeline.js');
      const c = getCanvas(project().canvas_id);
      // 给主要角色（主角/反派，最多 4 个）生成表情集，落到画布角色节点
      const mains = c.nodes.filter((n) => n.type === 'character' && /主角|反派/.test(n.data.role || '') && n.data.image && !/\.svg$/i.test(n.data.image)).slice(0, 4);
      if (!mains.length) return '无可生成表情的主要角色（需先有真实定妆照）';
      let made = 0;
      for (const n of mains) {
        if (cancelled()) break;
        try { const r = await generateExpressions({ projectId, nodeId: n.id, emotions: ['冷酷', '愤怒', '悲伤', '微笑', '惊恐'] }); made += r.variants.length; } catch (e) { console.warn('[workflow] 表情失败：', n.data.name, e.message); }
      }
      return `为 ${mains.length} 个主要角色生成表情库，共 ${made} 张`;
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
      const chain = getSetting('video_chain', true) !== false;   // 接龙模式：上段尾帧→下段首帧（默认开）
      const p = project();
      const c = getCanvas(p.canvas_id);
      const todo = epShots(c).filter((n) => !n.data.video).sort((a, b) => (a.data.order || 0) - (b.data.order || 0));
      if (!todo.length) return '已全部出片（无需生成）';

      if (chain) {
        // 严格顺序：一段一段来，每段等完成→抽尾帧→作为下一段首帧。
        // 仅在【同场景且顺序相邻】时接龙（连续动作）；换场/跳镜则回到本镜定妆首帧，避免把上一场景画面带进新场景。
        const { extractLastFrame } = await import('./export.js');
        const hasFF = !!ffmpegPath();
        let prevFrame = '', prevScene = '', prevOrder = -999;
        let okC = 0, failC = 0, chained = 0;
        for (const n of todo) {
          if (cancelled()) break;
          const continuous = !!prevFrame && n.data.scene === prevScene && (n.data.order || 0) === prevOrder + 1;
          const firstFrame = continuous ? prevFrame : (n.data.image || '');
          prevScene = n.data.scene; prevOrder = n.data.order || 0;
          if (!firstFrame) { failC++; prevFrame = ''; console.warn('[workflow] 跳过无首帧分镜：', n.data.name); continue; }
          let r;
          try {
            r = await createVideoTask({
              prompt: (n.data.video_prompt || n.data.action || n.data.name) + (continuous ? '，紧接上一镜，画面与角色无缝衔接、外观身高一致' : ''),
              imageUrl: firstFrame, duration: n.data.duration, projectId, nodeId: n.id, name: n.data.name, order: n.data.order, model: wf.video_model || ''
            });
          } catch (e) { failC++; prevFrame = ''; if (!okC && todo.indexOf(n) === 0) throw bad(e.message); continue; }
          if (continuous) chained++;
          // 阻塞等这一段真正完成，才能抽它的尾帧给下一段（这就是"一步一步"）
          const deadline = now() + 8 * 60_000;
          let t = await pollTask(r.taskId);
          while (t.status !== 'succeeded' && t.status !== 'failed' && now() < deadline && !cancelled()) { await sleep(2500); t = await pollTask(r.taskId); }
          if (t.status === 'succeeded') { okC++; prevFrame = hasFF ? extractLastFrame(t.result?.url) : ''; }
          else { failC++; prevFrame = ''; }   // 失败/超时 → 断开接龙，下一段用自己的首帧
        }
        return `顺序接龙 ${okC}/${todo.length}（尾帧衔接 ${chained} 处）${failC ? `，失败/跳过 ${failC}` : ''}${hasFF ? '' : '；未装 ffmpeg 无法抽尾帧，已退化为各镜独立首帧'}`;
      }

      // 并行模式（默认）
      const tasks = [];
      let firstErr = '';
      for (const n of todo) {
        if (cancelled()) break;
        try {
          const r = await createVideoTask({
            prompt: n.data.video_prompt || n.data.action || n.data.name, imageUrl: n.data.image,
            duration: n.data.duration, projectId, nodeId: n.id, name: n.data.name, order: n.data.order, model: wf.video_model || ''
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
      if (!ffmpegPath()) throw SKIP('未检测到 ffmpeg，已跳过（安装后可一键导出带配音/字幕的成片）');
      try {
        const r = await exportEpisode({ projectId, episode });
        return `成片已导出（${r.shots} 镜，混入配音 ${r.dubbed || 0}，烧录字幕 ${r.subbed || 0}）：${r.url}`;
      } catch (e) { throw SKIP(`导出跳过：${e.message.slice(0, 120)}`); }
    }
    default:
      throw SKIP('未知步骤');
  }
}
