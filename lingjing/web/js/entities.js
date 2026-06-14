// 角色预选标注 + Agent 进化：解析后让用户校验"谁是角色/场景/道具"，校正即训练，全对则夸赞
import { GET, POST } from './api.js';
import { h, icon, modal, toast } from './ui.js';

const TYPES = [['character', '角色'], ['scene', '场景'], ['prop', '道具']];
const TYPE_CN = { character: '角色', scene: '场景', prop: '道具' };

export async function openEntityReview({ projectId, onApplied }) {
  let data;
  try { data = await GET(`/api/projects/${projectId}/entities`); }
  catch (e) { return toast(e.message, 'err'); }

  const body = h('div');
  const { close, box } = modal({ title: h('span', { html: `${icon('user')} 角色预选 · 请校验分类` }), wide: true, body });

  // name -> 暂存的新类型（仅记录被用户改动的）
  const staged = new Map();

  function brainBar(brain) {
    const pct = (brain.xp % 100);
    return h('div', { style: { padding: '10px 12px', borderRadius: '12px', background: 'var(--bg2)', marginBottom: '12px' } },
      h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '7px' } },
        h('span', { html: icon('spark') }),
        h('b', {}, `Agent 进化 · Lv.${brain.level} ${brain.title}`),
        h('span', { class: 'pill teal' }, `经验 ${brain.xp}`),
        brain.accuracy != null ? h('span', { class: 'pill green' }, `准确率 ${brain.accuracy}%`) : null,
        brain.streak ? h('span', { class: 'pill gold' }, `🔥 连续夸赞 ${brain.streak}`) : null,
        h('span', { class: 'pill' }, `已学会 ${brain.learned} 个`)),
      h('div', { class: 'progress' }, h('i', { style: { width: `${pct}%` } })),
      h('div', { style: { fontSize: '11px', color: 'var(--ink3)', marginTop: '5px' } }, '改一处分类＝纠正并教会 Agent（永久记住，下次自动应用）；全对就夸夸它，越用越准'));
  }

  function row(e) {
    const seg = h('div', { style: { display: 'flex', gap: '5px' } },
      TYPES.map(([val, label]) => {
        const b = h('button', { class: `chip ${e.type === val ? 'on' : ''}`, type: 'button' },
          label + (val === 'character' && e.role ? `·${e.role}` : ''));
        b.onclick = () => {
          seg.querySelectorAll('.chip').forEach((x) => x.classList.remove('on'));
          b.classList.add('on');
          if (val === e.type) staged.delete(e.name); else staged.set(e.name, val);
          syncFoot();
        };
        return b;
      }));
    const thumb = e.image
      ? h('img', { src: e.image, style: { width: '40px', height: '50px', objectFit: 'cover', borderRadius: '7px', flex: 'none', border: '1px solid var(--line)' } })
      : h('div', { style: { width: '40px', height: '50px', borderRadius: '7px', flex: 'none', background: 'var(--bg)', border: '1px dashed var(--line)' } });
    return h('div', { style: { display: 'flex', gap: '10px', alignItems: 'center', padding: '8px 10px', borderRadius: '10px', background: 'var(--card, #fff)', border: '1px solid var(--line)' } },
      thumb,
      h('div', { style: { flex: 1, minWidth: 0 } },
        h('div', { style: { display: 'flex', gap: '6px', alignItems: 'center' } },
          h('b', {}, e.name),
          e.gender ? h('span', { class: 'pill' }, e.gender) : null,
          e.learned ? h('span', { class: 'pill green', title: '你确认过这个分类' }, '✓ 已学会') : null),
        h('div', { style: { fontSize: '12px', color: 'var(--ink3)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, e.desc || '（无描述）')),
      seg);
  }

  const listWrap = h('div', { style: { display: 'flex', flexDirection: 'column', gap: '7px', maxHeight: '48vh', overflowY: 'auto' } });
  const foot = h('div', { class: 'm-actions' });

  function syncFoot() {
    foot.innerHTML = '';
    const n = staged.size;
    foot.append(
      h('button', { class: 'btn', onclick: () => close() }, '关闭'),
      h('button', {
        class: 'btn', disabled: !n,
        onclick: (ev) => submit({ moves: stagedMoves(), confirm: false, btn: ev.currentTarget })
      }, n ? `保存校正并训练（${n} 处）` : '保存校正并训练'),
      h('button', {
        class: 'btn accent',
        title: '分类全部正确：奖励 Agent 经验值',
        onclick: (ev) => submit({ moves: stagedMoves(), confirm: true, btn: ev.currentTarget })
      }, h('span', { html: `${icon('check')} ${n ? '修正并夸赞' : '全部正确 · 夸夸 Agent 👍'}` })));
  }
  const stagedMoves = () => [...staged.entries()].map(([name, to]) => ({ name, to }));

  async function submit({ moves, confirm, btn }) {
    btn.disabled = true;
    try {
      const r = await POST(`/api/projects/${projectId}/annotate`, { moves, confirm });
      const msgs = [];
      if (r.applied?.length) msgs.push(`已归位 ${r.applied.map((m) => `${m.name}→${TYPE_CN[m.to]}`).join('、')}`);
      if (r.praised) msgs.push(`👏 Agent 获得夸赞！Lv.${r.brain.level} ${r.brain.title}（经验 ${r.brain.xp}）`);
      toast(msgs.join('；') || '已记录', 'ok');
      onApplied?.(r);
      if (r.applied?.length) { data = await GET(`/api/projects/${projectId}/entities`); staged.clear(); render(); }
      else { head.replaceChildren(brainBar(r.brain)); syncFoot(); }
    } catch (e) { toast(e.message, 'err'); btn.disabled = false; }
  }

  const head = h('div');
  function render() {
    head.replaceChildren(brainBar(data.brain));
    listWrap.innerHTML = '';
    listWrap.append(
      h('div', { style: { fontSize: '12px', color: 'var(--ink2)', marginBottom: '3px' } },
        `共识别 ${data.counts.character} 角色 · ${data.counts.scene} 场景 · ${data.counts.prop} 道具${data.style ? ` ｜ 画风：${String(data.style).slice(0, 18)}（全片统一）` : ''}`),
      ...data.entities.map(row));
    syncFoot();
  }
  body.append(head, listWrap, foot);
  render();
  return { close, box };
}
