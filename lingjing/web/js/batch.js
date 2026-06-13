// 一键生成编排器：角色/场景/道具出图 → 分镜首帧 → 分镜视频（前端驱动，可取消）
import { GET, POST, pollUntilDone } from './api.js';
import { h, toast } from './ui.js';

/**
 * @param {string} canvasId
 * @param {{onNode?:(nodeId:string)=>void, includeVideos?:boolean, episode?:string}} opts
 * episode：只处理该集的分镜节点（角色/场景/道具出图不受限）。返回 {cancel}
 */
export function runBatchGenerate(canvasId, { onNode, includeVideos = true, episode = '', onDone } = {}) {
  let cancelled = false;
  const bar = h('div', { class: 'batchbar' });
  const label = h('div', { class: 'row' });
  const prog = h('div', { class: 'progress' }, h('i', { style: { width: '0%' } }));
  const cancelBtn = h('button', { class: 'btn sm ghost', style: { color: '#fff' }, onclick: () => { cancelled = true; } }, '取消');
  bar.append(h('div', { class: 'row' }, label, h('span', { class: 'grow' }), cancelBtn), prog);
  document.body.append(bar);

  const setProgress = (done, total, text) => {
    label.textContent = text;
    prog.firstChild.style.width = total ? `${Math.round(done / total * 100)}%` : '0%';
  };

  (async () => {
    try {
      const canvas = await GET(`/api/canvases/${canvasId}`);
      const projectId = canvas.project_id || '';
      const inEpisode = (n) => !episode || n.type !== 'shot' || (n.data.episode || 'e1') === episode;
      const nodes = canvas.nodes.filter(inEpisode);
      const needImage = nodes.filter((n) => !n.data.image && n.type !== 'note' && (n.data.image_prompt || n.data.prompt));
      const shotsForVideo = includeVideos ? nodes.filter((n) => n.type === 'shot' && !n.data.video) : [];
      const total = needImage.length + shotsForVideo.length;
      if (!total) { toast('没有需要生成的内容（都已生成过）'); bar.remove(); onDone?.(); return; }
      let done = 0;

      // 阶段 1：严格两段出图——角色/场景/道具定妆照【全部完成】后才生成分镜首帧，
      // 保证每个首帧都能引用到定妆参考图（画面一致性）
      const runQueue = async (queue, label) => {
        await Promise.all(Array.from({ length: 2 }, async () => {
          while (queue.length && !cancelled) {
            const n = queue.shift();
            setProgress(done, total, `${label}：${n.data.name || n.type}（${done + 1}/${total}）`);
            try {
              await POST('/api/ai/image', {
                prompt: n.data.image_prompt || n.data.prompt, name: n.data.name,
                kind: n.type === 'shot' ? 'frame' : n.type, project_id: projectId, node_id: n.id
              });
              onNode?.(n.id);
            } catch (e) { toast(`${n.data.name || '节点'} 出图失败：${e.message}`, 'err'); }
            done++;
          }
        }));
      };
      await runQueue(needImage.filter((n) => n.type !== 'shot'), '定妆照');
      if (cancelled) { bar.remove(); toast('已取消'); onDone?.(); return; }
      await runQueue(needImage.filter((n) => n.type === 'shot'), '分镜首帧');
      if (cancelled) { bar.remove(); toast('已取消'); onDone?.(); return; }

      // 阶段 2：分镜视频（任务创建后并行轮询）
      const tasks = [];
      for (const n of shotsForVideo) {
        if (cancelled) break;
        const fresh = await GET(`/api/canvases/${canvasId}`);
        const cur = fresh.nodes.find((x) => x.id === n.id);
        setProgress(done, total, `创建视频任务：${n.data.name}`);
        try {
          const r = await POST('/api/ai/video', {
            prompt: n.data.video_prompt || n.data.action || n.data.name,
            image_url: cur?.data.image || '', duration: n.data.duration || 5,
            project_id: projectId, node_id: n.id, name: n.data.name, order: n.data.order
          });
          tasks.push({ node: n, taskId: r.taskId });
          onNode?.(n.id);
        } catch (e) { toast(`${n.data.name} 视频任务失败：${e.message}`, 'err'); done++; }
      }
      await Promise.all(tasks.map(async ({ node, taskId }) => {
        const t = await pollUntilDone(taskId, { signal: { get aborted() { return cancelled; } } });
        done++;
        setProgress(done, total, `视频完成 ${done}/${total}`);
        if (t.status === 'failed') toast(`${node.data.name} 生成失败：${t.error || ''}`, 'err');
        onNode?.(node.id);
      }));

      bar.remove();
      if (!cancelled) toast('一键生成完成 ✓', 'ok');
      onDone?.();
    } catch (e) {
      bar.remove();
      toast('批量生成中断：' + e.message, 'err');
      onDone?.();
    }
  })();

  return { cancel: () => { cancelled = true; } };
}
