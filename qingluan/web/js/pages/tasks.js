// 任务中心：全局生成任务视图（筛选 / 实时刷新 / 失败重试 / 强制重出）
import { GET, POST } from '../api.js';
import { h, icon, toast, modal, fmtTime, mediaEl, isVideoUrl, STATUS_CN, stagger } from '../ui.js';
import { nav } from '../main.js';

export async function renderTasks(page) {
  let kind = '';
  let status = '';
  const list = h('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } });

  const kindSel = h('select', { class: 'select', style: { width: '130px' }, onchange: (e) => { kind = e.target.value; load(); } },
    [['', '全部类型'], ['video', '视频'], ['image', '图片']].map(([v, l]) => h('option', { value: v }, l)));
  const statusSel = h('select', { class: 'select', style: { width: '130px' }, onchange: (e) => { status = e.target.value; load(); } },
    [['', '全部状态'], ['active', '进行中'], ['succeeded', '已完成'], ['failed', '失败']].map(([v, l]) => h('option', { value: v }, l)));

  async function load() {
    const rows = await GET(`/api/ai/tasks?kind=${kind}&status=${status}`);
    list.innerHTML = '';
    if (!rows.length) {
      list.append(h('div', { class: 'card empty' }, h('div', { html: icon('clock', 36) }), h('p', {}, '没有匹配的任务')));
      return;
    }
    for (const t of rows) list.append(row(t));
    stagger(list, 22);
  }

  function row(t) {
    const running = ['queued', 'running'].includes(t.status);
    const pillCls = t.status === 'succeeded' ? 'green' : t.status === 'failed' ? 'red' : 'orange pulse';
    const retryBtn = t.kind === 'video' ? h('button', {
      class: `btn sm ${t.status === 'failed' ? 'accent' : 'ghost'}`,
      title: t.status === 'failed' ? '用原参数重新创建任务' : '强制重出（忽略当前状态）',
      onclick: async (e) => {
        e.currentTarget.disabled = true;
        try {
          const r = await POST(`/api/ai/task/${t.id}/retry`, t.status === 'failed' ? {} : { force: true });
          toast(`已重新创建任务 ${r.taskId}`, 'ok');
          load();
        } catch (err) { toast(err.message, 'err'); e.currentTarget.disabled = false; }
      }
    }, t.status === 'failed' ? '重试' : '重出') : null;
    const viewBtn = t.result?.url ? h('button', {
      class: 'btn sm', onclick: () => modal({
        wide: true, title: t.params?.name || t.prompt.slice(0, 20),
        body: h('div', { style: { borderRadius: '12px', overflow: 'hidden', background: '#10161f' } },
          (() => { const el = mediaEl(t.result.url); el.style.width = '100%'; if (isVideoUrl(t.result.url)) el.autoplay = true; return el; })()),
        actions: [{ label: '关闭', kind: 'primary' }]
      })
    }, '查看') : null;
    return h('div', { class: 'card', style: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px' } },
      h('span', { html: icon(t.kind === 'video' ? 'video' : 'image', 18), style: { color: 'var(--ink3)', flex: 'none' } }),
      h('div', { style: { flex: 1, minWidth: 0 } },
        h('div', { style: { fontSize: '13.5px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, title: t.prompt }, t.params?.name ? `${t.params.name} · ${t.prompt}` : t.prompt),
        h('div', { style: { display: 'flex', gap: '6px', marginTop: '4px', alignItems: 'center', flexWrap: 'wrap' } },
          h('span', { class: `pill ${pillCls}` }, STATUS_CN[t.status] || t.status),
          h('span', { class: `pill ${t.provider === 'ark' ? 'teal' : ''}` }, t.provider),
          t.params?.model ? h('span', { class: 'pill' }, t.params.model) : null,
          t.params?.ref_images ? h('span', { class: 'pill', title: '一致性参考图数量' }, `参考 ×${t.params.ref_images}`) : null,
          t.error ? h('span', { style: { fontSize: '12px', color: 'var(--err)' }, title: t.error }, t.error.slice(0, 50)) : null,
          h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, fmtTime(t.created_at)))),
      t.project_id ? h('button', { class: 'btn sm ghost', title: '打开项目', html: icon('film', 14), onclick: () => nav(`/project/${t.project_id}`) }) : null,
      viewBtn, retryBtn);
  }

  // 有进行中任务时自动轮询（顺带推进本地模拟任务）
  const timer = setInterval(async () => {
    const running = [...list.querySelectorAll('.pill.orange')];
    if (!running.length) return;
    const rows = await GET('/api/ai/tasks?status=active').catch(() => []);
    for (const t of rows.slice(0, 10)) { try { await GET(`/api/ai/task/${t.id}`); } catch { /* noop */ } }
    await load();
  }, 3000);

  page.append(
    h('div', { class: 'topbar line' }, h('h1', {}, '任务中心'), h('span', { class: 'grow' }), kindSel, statusSel,
      h('button', { class: 'btn sm', html: `${icon('refresh', 14)} 刷新`, onclick: load })),
    h('div', { class: 'wrap', style: { marginTop: '16px' } }, list));
  await load();
  return () => clearInterval(timer);
}
