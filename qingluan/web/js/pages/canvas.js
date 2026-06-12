// 画布编辑器：节点式短剧编排（深色全屏）
import { GET, POST, PATCH } from '../api.js';
import { h, icon, toast, debounce, confirmDlg, escHtml, modal, isVideoUrl } from '../ui.js';
import { nav } from '../main.js';
import { createGraph } from '../flow/graph.js';
import { runBatchGenerate } from '../batch.js';

const TYPE_CN = { character: '角色', scene: '场景', prop: '道具', shot: '分镜', note: '便签' };
const TYPE_ICON = { character: 'user', scene: 'image', prop: 'box', shot: 'film', note: 'pencil' };

export async function renderCanvas(page, params) {
  let canvas = await GET(`/api/canvases/${params.id}`);
  const projectId = canvas.project_id || '';

  // ---------- 节点模板 ----------
  function media(html, ratioClass = '') {
    return `<div class="n-media ${ratioClass}">${html}</div>`;
  }
  function nodeContent(n) {
    const d = n.data || {};
    const wrap = h('div');
    const img = d.image ? `<img src="${escHtml(d.image)}" draggable="false">` : '';
    const head = `<div class="n-head">${icon(TYPE_ICON[n.type] || 'box', 13)}<b>${escHtml(d.name || TYPE_CN[n.type])}</b>${n.type === 'character' && d.role ? `<span class="tagx">${escHtml(d.role)}</span>` : ''}</div>`;

    if (n.type === 'note') {
      wrap.innerHTML = `<div class="note-tx">${escHtml(d.text || '双击右侧属性栏编辑便签…')}</div>`;
      return wrap;
    }
    if (n.type === 'shot') {
      const status = d.task_status === 'running'
        ? '<span class="n-status"><span class="pill orange pulse">视频生成中</span></span>'
        : d.video ? '<span class="n-status"><span class="pill green">已出片</span></span>' : '';
      const inner = d.video
        ? (isVideoUrl(d.video) ? `<video src="${escHtml(d.video)}" controls preload="metadata" ${d.image ? `poster="${escHtml(d.image)}"` : ''}></video>` : `<img src="${escHtml(d.video)}" draggable="false">`)
        : img || `<div class="gen-hint">${icon('image', 20)}<span>未生成首帧</span></div>`;
      wrap.innerHTML = `
        <div class="n-head">${icon('film', 13)}<b>SHOT ${String(d.order || '?').padStart(2, '0')}</b><span class="tagx">${d.duration || 5}s</span>${d.shot_type ? `<span class="tagx">${escHtml(d.shot_type)}</span>` : ''}</div>
        ${media(inner)}${status}
        <div class="n-act">${escHtml(d.action || '')}</div>
        ${d.dialogue ? `<div class="n-dlg">「${escHtml(d.dialogue)}」</div>` : ''}
        <div class="n-foot">${d.camera ? `<span class="tagx">${escHtml(d.camera)}</span>` : ''}</div>`;
      return wrap;
    }
    wrap.innerHTML = `${head}${media(img || `<div class="gen-hint">${icon(TYPE_ICON[n.type], 20)}<span>未生成</span></div>`)}
      <div class="n-foot"><span class="tagx">${TYPE_CN[n.type]}</span>${d.desc ? `<span title="${escHtml(d.desc)}">${escHtml(String(d.desc).slice(0, 16))}…</span>` : ''}</div>`;
    return wrap;
  }

  // ---------- 骨架 ----------
  const savedHint = h('span', { class: 'cv-saved' }, '已保存');
  const nameIn = h('input', { class: 'name-in', value: canvas.name, onblur: () => scheduleSave(), oninput: () => savedHint.textContent = '未保存' });
  const pct = h('span', { class: 'pct' }, '100%');
  const shell = h('div', { class: 'cv-shell' });
  const main = h('div', { class: 'cv-main' });
  const inspectorBox = h('div');

  const graph = createGraph(main, {
    renderNode: nodeContent,
    onChange: () => scheduleSave(),
    onSelect: (sel) => renderInspector(sel),
    onView: (z) => { pct.textContent = Math.round(z * 100) + '%'; }
  });

  // ---------- 保存 ----------
  const doSave = async () => {
    savedHint.textContent = '保存中…';
    try {
      const data = graph.getData();
      await PATCH(`/api/canvases/${canvas.id}`, { nodes: data.nodes, edges: data.edges, viewport: data.viewport, name: nameIn.value.trim() || canvas.name });
      savedHint.textContent = '已保存';
    } catch (e) { savedHint.textContent = '保存失败'; toast(e.message, 'err'); }
  };
  const scheduleSave = debounce(doSave, 800);
  const markDirty = () => { savedHint.textContent = '未保存'; scheduleSave(); };

  // ---------- 服务器媒体状态合并（生成结果回写画布时同步到本地） ----------
  async function syncMedia() {
    try {
      const fresh = await GET(`/api/canvases/${canvas.id}`);
      const byId = new Map(fresh.nodes.map((n) => [n.id, n]));
      for (const n of graph.getNodes()) {
        const remote = byId.get(n.id);
        if (!remote) continue;
        const r = remote.data || {};
        if (r.image !== n.data.image || r.video !== n.data.video || r.task_status !== n.data.task_status) {
          graph.updateNodeData(n.id, { image: r.image, video: r.video, task_id: r.task_id, task_status: r.task_status });
          if (sel?.kind === 'node' && sel.id === n.id) renderInspector(sel);
        }
      }
    } catch { /* noop */ }
  }
  const pollTimer = setInterval(async () => {
    const running = graph.getNodes().filter((n) => n.data?.task_status === 'running' && n.data.task_id);
    for (const n of running) { try { await GET(`/api/ai/task/${n.data.task_id}`); } catch { /* noop */ } }
    if (running.length) await syncMedia();
  }, 3000);

  // ---------- 工具栏 ----------
  function addNodeMenu() {
    const c = graph.centerWorld();
    const mk = (type, data) => {
      graph.addNode({ id: 'n' + Math.random().toString(36).slice(2, 11), type, x: Math.round(c.x - 110), y: Math.round(c.y - 80), data });
      markDirty();
      document.querySelector('.modal-mask')?.remove();
    };
    const item = (type, label, desc) => h('button', { class: 'btn', style: { justifyContent: 'flex-start' }, onclick: () => mk(type, defaults(type)) },
      h('span', { html: icon(TYPE_ICON[type]) }), h('span', {}, label, h('small', { style: { color: 'var(--ink3)', marginLeft: '8px', fontWeight: 400 } }, desc)));
    const order = graph.getNodes().filter((n) => n.type === 'shot').length + 1;
    function defaults(type) {
      if (type === 'shot') return { order, name: `镜头 ${order}`, action: '', dialogue: '', shot_type: '中景', camera: '固定机位', duration: 5, image_prompt: '', video_prompt: '', image: '', video: '', task_id: '', task_status: '' };
      if (type === 'note') return { text: '备注…' };
      return { name: `新${TYPE_CN[type]}`, desc: '', prompt: '', image: '', ...(type === 'character' ? { role: '角色' } : {}) };
    }
    modal({
      title: '添加节点',
      body: h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px' } },
        item('character', '角色', '人物形象，可生成肖像'),
        item('scene', '场景', '环境空镜'),
        item('prop', '道具', '关键物品'),
        item('shot', '分镜', '镜头：首帧图 + 视频'),
        item('note', '便签', '画布备注')),
      actions: []
    });
  }

  function autoLayout() {
    // 与服务端 buildGraph 一致：左区 场景/道具，中区 角色，右区 分镜，各自折列
    const left = [], mid = [], right = [], notes = [];
    for (const n of graph.getNodes()) {
      if (n.type === 'scene' || n.type === 'prop') left.push(n);
      else if (n.type === 'character') mid.push(n);
      else if (n.type === 'shot') right.push(n);
      else notes.push(n);
    }
    right.sort((a, b) => (a.data.order || 0) - (b.data.order || 0));
    const placeZone = (list, x0, colW, perCol, yStep) => {
      list.forEach((n, i) => {
        n.x = x0 + Math.floor(i / perCol) * colW;
        n.y = 60 + (i % perCol) * yStep;
        const el = document.querySelector(`.ql-node[data-id="${n.id}"]`);
        if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
      });
      return x0 + Math.max(1, Math.ceil(list.length / perCol)) * colW;
    };
    let x = placeZone(left, 60, 270, 6, 230) + 80;
    x = placeZone(mid, x, 240, 4, 300) + 90;
    x = placeZone(right, x, 310, 5, 350) + 80;
    placeZone(notes, x, 240, 6, 160);
    graph.refreshEdges();
    graph.fit();
    markDirty();
  }

  const batchBtn = h('button', { class: 'btn accent', onclick: () => {
    batchBtn.disabled = true;
    scheduleSave.flush();
    runBatchGenerate(canvas.id, { onNode: () => syncMedia(), onDone: () => { batchBtn.disabled = false; syncMedia(); } });
  } });
  batchBtn.innerHTML = `${icon('wand')} 一键生成`;

  const top = h('div', { class: 'cv-top' },
    h('button', { class: 'btn sm', html: icon('back'), title: '返回', onclick: async () => { scheduleSave.flush(); nav(projectId ? `/project/${projectId}` : '/assets/canvas'); } }),
    nameIn, savedHint,
    h('span', { class: 'grow' }),
    h('button', { class: 'btn sm', onclick: addNodeMenu, html: `${icon('plus', 15)} 节点` }),
    h('button', { class: 'btn sm', onclick: autoLayout, html: `${icon('layout', 15)} 整理` }),
    projectId ? h('button', { class: 'btn sm', onclick: () => nav(`/project/${projectId}`), html: `${icon('film', 15)} 剧本` }) : null,
    batchBtn);

  const zoombar = h('div', { class: 'cv-zoombar' },
    h('button', { class: 'btn sm ghost', html: icon('zoomout', 15), onclick: () => graph.zoomBy(0.85), style: { color: '#dfe6f0' } }),
    pct,
    h('button', { class: 'btn sm ghost', html: icon('zoomin', 15), onclick: () => graph.zoomBy(1.18), style: { color: '#dfe6f0' } }),
    h('button', { class: 'btn sm ghost', html: icon('fit', 15), title: '适配全部 (F)', onclick: () => graph.fit(), style: { color: '#dfe6f0' } }));

  // ---------- 属性面板 ----------
  let sel = null;
  function renderInspector(s) {
    sel = s;
    inspectorBox.innerHTML = '';
    if (!s) return;
    if (s.kind === 'edge') {
      inspectorBox.append(h('div', { class: 'inspector' },
        h('h4', { html: `${icon('link', 15)} 关联` }),
        h('p', { style: { fontSize: '12.5px', color: 'rgba(223,230,240,.6)' } }, '角色/场景/道具 → 分镜 的引用关系。'),
        h('button', { class: 'btn danger', style: { marginTop: '12px', width: '100%' }, onclick: () => { graph.removeSelected(); } }, '删除关联')));
      return;
    }
    const n = graph.findNode(s.id);
    if (!n) return;
    const d = n.data;
    const box = h('div', { class: 'inspector' });
    const fld = (label, el) => { box.append(h('label', { class: 'fld' }, label), el); return el; };
    const bind = (el, key, { num = false, rerender = true } = {}) => {
      el.addEventListener('input', () => {
        graph.updateNodeData(n.id, { [key]: num ? Number(el.value) : el.value }, { rerender: false });
        markDirty();
      });
      el.addEventListener('change', () => rerender && graph.refreshNode(n.id));
      el.addEventListener('blur', () => rerender && graph.refreshNode(n.id));
      return el;
    };

    box.append(h('h4', { html: `${icon(TYPE_ICON[n.type], 15)} ${TYPE_CN[n.type]}属性` }));

    if (n.type === 'note') {
      fld('内容', bind(h('textarea', { class: 'textarea', rows: 5, value: d.text || '' }), 'text'));
    } else if (n.type === 'shot') {
      fld('画面动作', bind(h('textarea', { class: 'textarea', rows: 3, value: d.action || '' }), 'action'));
      fld('台词', bind(h('input', { class: 'input', value: d.dialogue || '' }), 'dialogue'));
      const row = h('div', { class: 'row2' });
      row.append(bind(h('select', { class: 'select' }, ['远景', '全景', '中景', '近景', '特写'].map((v) => h('option', { value: v, selected: v === d.shot_type }, v))), 'shot_type'));
      row.append(bind(h('input', { class: 'input', type: 'number', min: 2, max: 12, value: d.duration || 5, title: '时长(秒)' }), 'duration', { num: true }));
      fld('景别 / 时长(秒)', row);
      fld('运镜', bind(h('input', { class: 'input', value: d.camera || '' }), 'camera'));
      fld('首帧提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.image_prompt || '' }), 'image_prompt', { rerender: false }));
      fld('视频提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.video_prompt || '' }), 'video_prompt', { rerender: false }));
    } else {
      fld('名称', bind(h('input', { class: 'input', value: d.name || '' }), 'name'));
      if (n.type === 'character') fld('身份', bind(h('input', { class: 'input', value: d.role || '' }), 'role'));
      fld('描述', bind(h('textarea', { class: 'textarea', rows: 3, value: d.desc || '' }), 'desc', { rerender: false }));
      fld('形象提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.prompt || '' }), 'prompt', { rerender: false }));
    }

    // 媒体与生成
    if (n.type !== 'note') {
      const prev = h('div', { class: 'media-prev' });
      const m = d.video || d.image;
      if (m) prev.append(isVideoUrl(m) ? h('video', { src: m, controls: true, poster: d.image || undefined }) : h('img', { src: m }));
      box.append(prev);
      const acts = h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' } });
      const genImgBtn = h('button', { class: 'btn accent', onclick: async () => {
        const prompt = n.type === 'shot' ? d.image_prompt : d.prompt;
        if (!prompt?.trim()) return toast('先填提示词', 'err');
        genImgBtn.disabled = true;
        genImgBtn.innerHTML = `${icon('loader')} 出图中…`;
        scheduleSave.flush();
        try {
          await POST('/api/ai/image', { prompt, name: d.name, kind: n.type === 'shot' ? 'frame' : n.type, project_id: projectId, node_id: n.id, ratio: canvas.ratio, tab: n.type === 'character' ? 'character' : '' });
          await syncMedia();
          renderInspector(sel);
          toast('出图完成', 'ok');
        } catch (e) { toast(e.message, 'err'); }
        genImgBtn.disabled = false;
        genImgBtn.innerHTML = `${icon('image', 15)} ${d.image ? '重新出图' : '生成图片'}`;
      } });
      genImgBtn.innerHTML = `${icon('image', 15)} ${d.image ? '重新出图' : n.type === 'shot' ? '生成首帧' : '生成图片'}`;
      acts.append(genImgBtn);
      if (n.type === 'shot') {
        const genVidBtn = h('button', { class: 'btn accent', onclick: async () => {
          const prompt = d.video_prompt || d.action;
          if (!prompt?.trim()) return toast('先填视频提示词或画面动作', 'err');
          genVidBtn.disabled = true;
          genVidBtn.innerHTML = `${icon('loader')} 任务创建中…`;
          scheduleSave.flush();
          try {
            await POST('/api/ai/video', { prompt, image_url: d.image || '', duration: d.duration || 5, ratio: canvas.ratio, project_id: projectId, node_id: n.id, name: d.name, order: d.order });
            await syncMedia();
            toast('视频任务已创建，完成后自动回填', 'ok');
          } catch (e) { toast(e.message, 'err'); }
          genVidBtn.disabled = false;
          genVidBtn.innerHTML = `${icon('video', 15)} ${d.video ? '重新出片' : '生成视频'}`;
        } });
        genVidBtn.innerHTML = `${icon('video', 15)} ${d.video ? '重新出片' : '生成视频'}`;
        acts.append(genVidBtn);
      }
      acts.append(h('button', { class: 'btn danger', onclick: async () => {
        if (!await confirmDlg(`删除${TYPE_CN[n.type]}「${d.name || ''}」？关联连线一并删除。`)) return;
        graph.removeSelected();
      } }, `${TYPE_CN[n.type]}删除`));
      box.append(acts);
    } else {
      box.append(h('button', { class: 'btn danger', style: { marginTop: '12px', width: '100%' }, onclick: () => graph.removeSelected() }, '删除便签'));
    }
    inspectorBox.append(box);
  }

  // ---------- 快捷键 ----------
  const onKey = async (e) => {
    if (e.target.closest('input, textarea, select')) return;
    if (e.key === 'Delete' || e.key === 'Backspace') {
      const s = graph.getSelected();
      if (!s) return;
      if (s.kind === 'node') {
        const n = graph.findNode(s.id);
        if (!await confirmDlg(`删除${TYPE_CN[n.type]}「${n.data.name || ''}」？`)) return;
      }
      graph.removeSelected();
    }
    if (e.key === 'f' || e.key === 'F') graph.fit();
    if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); scheduleSave.flush(); }
  };
  document.addEventListener('keydown', onKey);

  shell.append(top, main);
  main.append(zoombar, inspectorBox);
  page.append(shell);

  graph.setData({ nodes: canvas.nodes, edges: canvas.edges, viewport: canvas.viewport });
  if ((canvas.nodes || []).some((n) => n.data?.task_status === 'running')) syncMedia();

  return () => {
    clearInterval(pollTimer);
    document.removeEventListener('keydown', onKey);
    scheduleSave.flush();
    graph.destroy();
  };
}
