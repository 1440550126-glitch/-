// AIQC 质检面板：展示每帧质检评分/问题/修正动作，给开发者逐条解决
import { GET, POST } from './api.js';
import { h, icon, toast, modal, fmtTime } from './ui.js';

const SEV = { high: { t: '严重', c: 'var(--err)' }, med: { t: '中等', c: 'var(--warn)' }, low: { t: '轻微', c: 'var(--ink3)' } };
const TYPE_CN = { anatomy: '解剖', consistency: '不一致', framing: '构图', clarity: '清晰度', uncanny: '恐怖谷', content: '内容' };

export async function openQC({ projectId, onFixed }) {
  const body = h('div');
  const { close } = modal({ title: h('span', { html: `${icon('check')} AIQC 质检报告` }), wide: true, body, actions: [] });
  let onlyOpen = false;

  async function render() {
    body.innerHTML = '';
    body.append(h('div', { class: 'empty', style: { padding: '20px' } }, h('div', { class: 'spinner', style: { margin: '0 auto' } })));
    let rep;
    try { rep = await GET(`/api/projects/${projectId}/qc${onlyOpen ? '?open=1' : ''}`); }
    catch (e) { body.innerHTML = ''; body.append(h('p', {}, e.message)); return; }
    const s = rep.summary;
    body.innerHTML = '';
    const color = s.avg_score >= 85 ? 'var(--ok)' : s.avg_score >= 70 ? 'var(--warn)' : 'var(--err)';
    body.append(
      h('div', { style: { display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' } },
        h('div', { style: { width: '72px', height: '72px', borderRadius: '50%', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', border: `5px solid ${color}`, font: '700 22px var(--font)', color } }, s.avg_score),
        h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
          h('span', { class: 'pill' }, `共 ${s.total} 条`),
          h('span', { class: `pill ${s.open ? 'red' : 'green'}` }, `待处理 ${s.open}`),
          h('span', { class: `pill ${s.vision ? 'teal' : ''}` }, s.vision ? '视觉模型质检' : '启发式质检（配方舟 Key 解锁视觉）')),
        h('span', { class: 'grow' }),
        h('label', { style: { fontSize: '12.5px', color: 'var(--ink2)', display: 'flex', gap: '5px', alignItems: 'center' } },
          h('input', { type: 'checkbox', checked: onlyOpen, onchange: (e) => { onlyOpen = e.target.checked; render(); } }), '只看待处理')));

    if (!rep.records.length) { body.append(h('div', { class: 'empty' }, h('p', {}, onlyOpen ? '没有待处理的质检问题 ✓' : '还没有质检记录，运行「全流程」或点分镜「质检」即可生成'))); return; }
    const list = h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '52vh', overflowY: 'auto' } });
    for (const r of rep.records) {
      list.append(h('div', { style: { padding: '10px 12px', borderRadius: '10px', background: r.passed ? 'var(--bg2)' : 'var(--accent2-soft)', opacity: r.resolved ? 0.55 : 1 } },
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
          h('b', { style: { fontSize: '13.5px' } }, `${r.stage === 'video' ? '出片前' : '出图'}·${r.target}`),
          h('span', { class: `pill ${r.score >= 85 ? 'green' : r.score >= 70 ? 'gold' : 'red'}` }, `${r.score}分`),
          r.passed ? h('span', { class: 'pill green' }, '通过') : h('span', { class: 'pill red' }, '需修复'),
          r.by_vision ? h('span', { class: 'pill teal' }, '👁视觉') : null,
          h('span', { class: 'grow' }),
          h('span', { style: { fontSize: '11px', color: 'var(--ink3)' } }, fmtTime(r.created_at))),
        r.issues.length ? h('div', { style: { marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' } },
          r.issues.map((it) => h('div', { style: { fontSize: '12.5px' } },
            h('b', { style: { color: (SEV[it.severity] || SEV.med).c } }, `[${TYPE_CN[it.type] || it.type}·${(SEV[it.severity] || SEV.med).t}] `),
            it.detail, it.fix ? h('span', { style: { color: 'var(--ink3)' } }, ` → 修正：${it.fix}`) : null))) : null,
        r.action ? h('div', { style: { fontSize: '12px', color: 'var(--accent-ink)', marginTop: '4px' } }, `⚙ Agent 已${r.action}`) : null,
        !r.passed && !r.resolved ? h('button', { class: 'btn xs', style: { marginTop: '6px' }, onclick: async () => { await POST(`/api/qc/${r.id}/resolve`); toast('已标记解决', 'ok'); render(); } }, '标记已解决') : null));
    }
    body.append(list);
  }
  await render();
}
