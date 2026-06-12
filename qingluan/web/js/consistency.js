// 画面一致性体检面板（项目页 / 画布页共用）
import { GET } from './api.js';
import { h, icon, modal, toast } from './ui.js';
import { runBatchGenerate } from './batch.js';

export async function openConsistency({ projectId, canvasId, onFixed }) {
  let report;
  try { report = await GET(`/api/projects/${projectId}/consistency`); }
  catch (e) { return toast(e.message, 'err'); }

  const body = h('div');
  const { close } = modal({ title: h('span', { html: `${icon('check')} 画面一致性体检` }), wide: true, body, actions: [] });

  function render(r) {
    body.innerHTML = '';
    const color = r.score >= 85 ? 'var(--ok)' : r.score >= 60 ? 'var(--warn)' : 'var(--err)';
    body.append(
      h('div', { style: { display: 'flex', gap: '18px', alignItems: 'center', marginBottom: '14px' } },
        h('div', { style: { width: '84px', height: '84px', borderRadius: '50%', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', border: `5px solid ${color}`, font: '700 26px var(--font)', color } }, r.score),
        h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
          h('span', { class: 'pill teal' }, `角色定妆 ${r.stats.characters_ready}`),
          h('span', { class: 'pill teal' }, `场景图 ${r.stats.scenes_ready}`),
          h('span', { class: 'pill' }, `分镜首帧 ${r.stats.shots_framed}`),
          h('span', { class: 'pill' }, `风格：${String(r.stats.style).slice(0, 12)}`),
          h('span', { class: 'pill gold', title: '项目级生成种子：同项目所有出图共用，重生成更稳定' }, `种子 ${r.seed}`))),
      r.issues.length
        ? h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '42vh', overflowY: 'auto' } },
          r.issues.map((it) => h('div', { style: { padding: '10px 12px', borderRadius: '10px', background: it.level === 'err' ? 'var(--accent2-soft)' : 'var(--bg2)', fontSize: '13px' } },
            h('b', { style: { color: it.level === 'err' ? 'var(--err)' : 'var(--warn)' } }, it.level === 'err' ? '必须修复 · ' : '建议 · '),
            it.text,
            it.fix ? h('div', { style: { fontSize: '12px', color: 'var(--ink3)', marginTop: '2px' } }, `→ ${it.fix}`) : null)))
        : h('div', { class: 'empty' }, h('p', {}, '没有发现一致性风险，可以放心批量生成 ✓')),
      h('div', { class: 'm-actions' },
        h('button', { class: 'btn', onclick: () => close() }, '关闭'),
        h('button', {
          class: 'btn accent', onclick: (e) => {
            const b = e.currentTarget;
            b.disabled = true;
            close();
            runBatchGenerate(canvasId, {
              includeVideos: false,
              onDone: async () => {
                onFixed?.();
                openConsistency({ projectId, canvasId, onFixed });   // 修复后复检
              }
            });
          }
        }, '一键补齐缺失画面（先定妆照后首帧）')));
  }
  render(report);
}
