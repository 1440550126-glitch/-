// 画布编辑器：节点式短剧编排（深色全屏）
import { GET, POST, PATCH } from '../api.js';
import { h, icon, toast, debounce, confirmDlg, escHtml, modal, isVideoUrl } from '../ui.js';
import { nav } from '../main.js';
import { createGraph } from '../flow/graph.js';
import { runBatchGenerate } from '../batch.js';
import { openStylePicker, shortStyle } from '../stylelib.js';
import { openConsistency } from '../consistency.js';

const TYPE_CN = { character: '角色', scene: '场景', prop: '道具', shot: '分镜', note: '便签' };
const TYPE_ICON = { character: 'user', scene: 'image', prop: 'box', shot: 'film', note: 'pencil' };

export async function renderCanvas(page, params) {
  let canvas = await GET(`/api/canvases/${params.id}`);
  const projectId = canvas.project_id || '';
  let project = projectId ? await GET(`/api/projects/${projectId}`).catch(() => null) : null;

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
        <div class="n-head">${icon('film', 13)}<b>SHOT ${String(d.order || '?').padStart(2, '0')}</b>${d.ep ? `<span class="tagx" style="color:#7fd8c9">E${d.ep}</span>` : ''}<span class="tagx">${d.duration || 5}s</span>${d.shot_type ? `<span class="tagx">${escHtml(d.shot_type)}</span>` : ''}</div>
        ${media(inner)}${status}
        <div class="n-act">${escHtml(d.action || '')}</div>
        ${d.dialogue ? `<div class="n-dlg">「${escHtml(d.dialogue)}」</div>` : ''}
        <div class="n-foot">${d.camera ? `<span class="tagx">${escHtml(d.camera)}</span>` : ''}${d.audio ? '<span class="tagx" title="已配音">🔊</span>' : ''}</div>`;
      return wrap;
    }
    const varStrip = n.type === 'character' && d.variants?.length
      ? `<div class="n-variants">${d.variants.slice(0, 6).map((v) => `<img src="${escHtml(v.url)}" title="${escHtml(v.emotion)}" draggable="false">`).join('')}</div>`
      : '';
    wrap.innerHTML = `${head}${media(img || `<div class="gen-hint">${icon(TYPE_ICON[n.type], 20)}<span>未生成</span></div>`)}${varStrip}
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

  let miniReady = false;   // graph 构造期间 onView 先于小地图就绪触发
  const graph = createGraph(main, {
    renderNode: nodeContent,
    onChange: () => { pushHistory(); scheduleSave(); if (miniReady) drawMini(); },
    onSelect: (sel) => renderInspector(sel),
    onView: (z) => { pct.textContent = Math.round(z * 100) + '%'; if (miniReady) drawMini(); }
  });

  // ---------- 小地图（节点缩略 + 视口框，点击/拖拽导航） ----------
  const NODE_SIZE = { character: [178, 270], scene: [212, 190], prop: [212, 190], shot: [264, 310], note: [200, 110] };
  const NODE_COLOR = { character: '#54c2b4', scene: '#8a9bc0', prop: '#c9a44d', shot: '#e08a6e', note: '#bdb27a' };
  const mini = h('canvas', { class: 'cv-minimap', width: 188, height: 124 });
  let miniMap = null;     // {sx, sy, ox, oy} 世界→小地图换算
  function drawMini() {
    const ctx = mini.getContext('2d');
    const W = mini.width, H = mini.height;
    ctx.clearRect(0, 0, W, H);
    const nodes = graph.getNodes();
    if (!nodes.length) { miniMap = null; return; }
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    const view = graph.getViewRect();
    for (const n of nodes) {
      const [w, hh] = NODE_SIZE[n.type] || [200, 160];
      x1 = Math.min(x1, n.x, view.x); y1 = Math.min(y1, n.y, view.y);
      x2 = Math.max(x2, n.x + w, view.x + view.w); y2 = Math.max(y2, n.y + hh, view.y + view.h);
    }
    const pad = 8;
    const s = Math.min((W - pad * 2) / (x2 - x1), (H - pad * 2) / (y2 - y1));
    const ox = pad - x1 * s, oy = pad - y1 * s;
    miniMap = { s, ox, oy };
    for (const n of nodes) {
      const [w, hh] = NODE_SIZE[n.type] || [200, 160];
      ctx.fillStyle = NODE_COLOR[n.type] || '#999';
      ctx.globalAlpha = 0.85;
      ctx.fillRect(n.x * s + ox, n.y * s + oy, Math.max(2, w * s), Math.max(2, hh * s));
    }
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(255,255,255,.85)';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(view.x * s + ox, view.y * s + oy, view.w * s, view.h * s);
  }
  const miniNav = (e) => {
    if (!miniMap) return;
    const r = mini.getBoundingClientRect();
    graph.panTo((e.clientX - r.left) / miniMap.s - miniMap.ox / miniMap.s, (e.clientY - r.top) / miniMap.s - miniMap.oy / miniMap.s);
  };
  mini.addEventListener('pointerdown', (e) => {
    miniNav(e);
    const move = (ev) => miniNav(ev);
    const up = () => { removeEventListener('pointermove', move); removeEventListener('pointerup', up); };
    addEventListener('pointermove', move);
    addEventListener('pointerup', up);
  });

  // ---------- 撤销 / 重做（结构快照：节点+连线+涂鸦） ----------
  const history = [];
  let histIdx = -1;
  let restoring = false;
  const snapshot = () => {
    const d = graph.getData();
    return JSON.stringify({ nodes: d.nodes, edges: d.edges, doodles: d.doodles });
  };
  function pushHistory() {
    if (restoring) return;
    clearTimeout(pushHistory._t);
    pushHistory._t = setTimeout(() => {
      const snap = snapshot();
      if (history[histIdx] === snap) return;
      history.splice(histIdx + 1);
      history.push(snap);
      if (history.length > 60) history.shift();
      histIdx = history.length - 1;
      syncHistBtns();
    }, 350);
  }
  function restore(snap) {
    restoring = true;
    const d = JSON.parse(snap);
    graph.setData({ ...d, viewport: graph.getData().viewport });
    restoring = false;
    renderInspector(null);
    scheduleSave();
  }
  function undo() {
    if (histIdx <= 0) return;
    histIdx--;
    restore(history[histIdx]);
    syncHistBtns();
  }
  function redo() {
    if (histIdx >= history.length - 1) return;
    histIdx++;
    restore(history[histIdx]);
    syncHistBtns();
  }
  function syncHistBtns() {
    undoBtn.disabled = histIdx <= 0;
    redoBtn.disabled = histIdx >= history.length - 1;
  }
  const undoBtn = h('button', { class: 'btn sm', title: '撤销 (⌘Z)', html: icon('undo', 15), onclick: undo, disabled: true });
  const redoBtn = h('button', { class: 'btn sm', title: '重做 (⌘⇧Z)', html: icon('redo', 15), onclick: redo, disabled: true });

  // ---------- 保存 ----------
  const doSave = async () => {
    savedHint.textContent = '保存中…';
    try {
      const data = graph.getData();
      await PATCH(`/api/canvases/${canvas.id}`, { nodes: data.nodes, edges: data.edges, doodles: data.doodles, viewport: data.viewport, name: nameIn.value.trim() || canvas.name });
      savedHint.textContent = '已保存';
    } catch (e) { savedHint.textContent = '保存失败'; toast(e.message, 'err'); }
  };
  const scheduleSave = debounce(doSave, 800);
  const markDirty = () => { savedHint.textContent = '未保存'; pushHistory(); scheduleSave(); };

  // ---------- 服务器媒体状态合并（生成结果回写画布时同步到本地） ----------
  async function syncMedia() {
    try {
      const fresh = await GET(`/api/canvases/${canvas.id}`);
      const byId = new Map(fresh.nodes.map((n) => [n.id, n]));
      for (const n of graph.getNodes()) {
        const remote = byId.get(n.id);
        if (!remote) continue;
        const r = remote.data || {};
        const varsChanged = JSON.stringify(r.variants || []) !== JSON.stringify(n.data.variants || []);
        if (r.image !== n.data.image || r.video !== n.data.video || r.audio !== n.data.audio || r.task_status !== n.data.task_status || varsChanged) {
          graph.updateNodeData(n.id, { image: r.image, video: r.video, audio: r.audio, task_id: r.task_id, task_status: r.task_status, ...(varsChanged ? { variants: r.variants || [] } : {}) });
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

  // ---------- 涂鸦笔（手绘批注，随画布保存） ----------
  const DD_COLORS = ['#54c2b4', '#ff7a5c', '#ffd166', '#f4f7fb'];
  const DD_WIDTHS = [['细', 2.5], ['中', 4.5], ['粗', 8]];
  const dd = { open: false, color: DD_COLORS[0], width: 4.5, tool: 'pen' };
  const doodleBar = h('div', { class: 'doodlebar', style: { display: 'none' } });
  let ddHinted = false;

  function applyTool() {
    graph.setTool(dd.open ? dd.tool : null, { color: dd.color, width: dd.width });
  }
  function renderDoodleBar() {
    doodleBar.innerHTML = '';
    doodleBar.append(
      ...DD_COLORS.map((c) => h('span', {
        class: `sw ${dd.color === c && dd.tool === 'pen' ? 'on' : ''}`, style: { background: c }, title: '画笔颜色',
        onclick: () => { dd.color = c; dd.tool = 'pen'; renderDoodleBar(); applyTool(); }
      })),
      h('span', { class: 'sep' }),
      ...DD_WIDTHS.map(([label, w]) => h('button', {
        class: `btn xs ${dd.width === w ? 'on' : ''}`,
        onclick: () => { dd.width = w; dd.tool = 'pen'; renderDoodleBar(); applyTool(); }
      }, label)),
      h('span', { class: 'sep' }),
      h('button', {
        class: `btn xs ${dd.tool === 'eraser' ? 'on' : ''}`, title: '橡皮：点/划掉笔迹',
        onclick: () => { dd.tool = dd.tool === 'eraser' ? 'pen' : 'eraser'; renderDoodleBar(); applyTool(); }
      }, '橡皮'),
      h('button', {
        class: 'btn xs', onclick: async () => {
          if (!graph.getDoodles().length) return;
          if (!await confirmDlg('清空画布上的全部涂鸦？')) return;
          graph.clearDoodles();
        }
      }, '清空'),
      h('button', { class: 'btn xs', onclick: () => toggleDoodle(false) }, `${'完成'} (Esc)`));
  }
  function toggleDoodle(open) {
    dd.open = open;
    doodleBar.style.display = open ? '' : 'none';
    if (open) renderDoodleBar();
    applyTool();
    ddBtn.classList.toggle('accent', open);
    if (open && !ddHinted) { ddHinted = true; toast('涂鸦模式：直接在画布上画，颜色/粗细在上方切换，D 键随时进出'); }
  }
  const ddBtn = h('button', { class: 'btn sm', title: '涂鸦笔 (D)：在画布上手绘批注', onclick: () => toggleDoodle(!dd.open) });
  ddBtn.innerHTML = `${icon('pencil', 15)} 涂鸦`;

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
    undoBtn, redoBtn,
    h('button', { class: 'btn sm', onclick: addNodeMenu, html: `${icon('plus', 15)} 节点` }),
    ddBtn,
    h('button', { class: 'btn sm', onclick: autoLayout, html: `${icon('layout', 15)} 整理` }),
    project ? (() => {
      const b = h('button', {
        class: 'btn sm', title: project.style ? `当前风格：${project.style}` : '选择画面风格',
        onclick: () => openStylePicker({
          current: project.style, onPick: async (style) => {
            project = await PATCH(`/api/projects/${projectId}`, { style });
            b.innerHTML = `${icon('wand', 15)} ${shortStyle(project.style)}`;
            toast(style ? `风格已设为「${shortStyle(style)}」` : '已恢复默认风格', 'ok');
          }
        })
      });
      b.innerHTML = `${icon('wand', 15)} ${shortStyle(project.style)}`;
      return b;
    })() : null,
    projectId ? h('button', { class: 'btn sm', title: '画面一致性体检', onclick: () => openConsistency({ projectId, canvasId: canvas.id, onFixed: () => syncMedia() }), html: `${icon('check', 15)} 体检` }) : null,
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
    if (s.kind === 'multi') {
      const ids = s.ids;
      const alignBtn = (label, fn) => h('button', { class: 'btn sm', onclick: () => graph.nudgeNodes(ids, fn) }, label);
      const sel = () => ids.map((id) => graph.findNode(id)).filter(Boolean);
      inspectorBox.append(h('div', { class: 'inspector' },
        h('h4', { html: `${icon('layers', 15)} 已选 ${ids.length} 个节点` }),
        h('p', { style: { fontSize: '12px', color: 'rgba(223,230,240,.55)', marginBottom: '10px' } },
          '拖动任一选中节点可整组移动；Shift+点击增减选择。'),
        h('div', { class: 'row2' },
          alignBtn('左对齐', (() => { const x = Math.min(...sel().map((n) => n.x)); return (n) => { n.x = x; }; })()),
          alignBtn('顶对齐', (() => { const y = Math.min(...sel().map((n) => n.y)); return (n) => { n.y = y; }; })())),
        h('div', { class: 'row2', style: { marginTop: '8px' } },
          alignBtn('竖向等距', (() => { const list = sel().sort((a, b) => a.y - b.y); const y0 = list[0]?.y || 0; let i = 0; const idx = new Map(list.map((n) => [n.id, i++])); return (n) => { n.y = y0 + idx.get(n.id) * 360; }; })()),
          alignBtn('横向等距', (() => { const list = sel().sort((a, b) => a.x - b.x); const x0 = list[0]?.x || 0; let i = 0; const idx = new Map(list.map((n) => [n.id, i++])); return (n) => { n.x = x0 + idx.get(n.id) * 320; }; })())),
        h('button', { class: 'btn danger', style: { marginTop: '14px', width: '100%' }, onclick: async () => {
          if (!await confirmDlg(`删除选中的 ${ids.length} 个节点？关联连线一并删除。`)) return;
          graph.removeSelected();
        } }, `删除 ${ids.length} 个节点`)));
      return;
    }
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
      const row2 = h('div', { class: 'row2' });
      row2.append(bind(h('input', { class: 'input', value: d.camera || '', placeholder: '运镜' }), 'camera'));
      row2.append(bind(h('select', { class: 'select', title: '角色情绪：有表情集时自动用对应表情定妆照作参考' },
        ['', '冷酷', '愤怒', '狂喜', '悲伤', '微笑', '惊恐', '魅惑', '羞涩'].map((v) => h('option', { value: v, selected: v === (d.emotion || '') }, v || '情绪·无'))), 'emotion'));
      fld('运镜 / 情绪', row2);
      fld('首帧提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.image_prompt || '' }), 'image_prompt', { rerender: false }));
      fld('视频提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.video_prompt || '' }), 'video_prompt', { rerender: false }));
    } else {
      fld('名称', bind(h('input', { class: 'input', value: d.name || '' }), 'name'));
      if (n.type === 'character') fld('身份', bind(h('input', { class: 'input', value: d.role || '' }), 'role'));
      fld('描述', bind(h('textarea', { class: 'textarea', rows: 3, value: d.desc || '' }), 'desc', { rerender: false }));
      fld('形象提示词', bind(h('textarea', { class: 'textarea', rows: 3, value: d.prompt || '' }), 'prompt', { rerender: false }));
    }

    // 角色表情集（对标小云雀角色多情绪变体）
    if (n.type === 'character') {
      const exBox = h('div', { style: { marginTop: '4px' } });
      exBox.append(h('label', { class: 'fld' }, `表情集${d.variants?.length ? `（${d.variants.length}）` : ''}`));
      if (d.variants?.length) {
        exBox.append(h('div', { class: 'var-grid' }, d.variants.map((v) =>
          h('div', { class: 'var-item', title: `${v.emotion} · 点击设为主形象`, onclick: () => {
            graph.updateNodeData(n.id, { image: v.url });
            markDirty();
            renderInspector(sel);
            toast(`主形象已切换为「${v.emotion}」`, 'ok');
          } }, h('img', { src: v.url }), h('span', {}, v.emotion)))));
      }
      if (projectId) {
        const exBtn = h('button', { class: 'btn', style: { width: '100%', marginTop: '8px' }, onclick: async () => {
          exBtn.disabled = true;
          exBtn.innerHTML = `${icon('loader')} 生成表情集…`;
          scheduleSave.flush();
          try {
            await POST('/api/ai/expressions', { project_id: projectId, node_id: n.id });
            await syncMedia();
            renderInspector(sel);
            toast('表情集已生成（6 种情绪），已入资产库', 'ok');
          } catch (e2) {
            toast(e2.message, 'err');
            exBtn.disabled = false;
            exBtn.innerHTML = `${icon('spark', 15)} 生成表情集`;
          }
        } });
        exBtn.innerHTML = `${icon('spark', 15)} ${d.variants?.length ? '重新生成表情集' : '生成表情集（6 种情绪）'}`;
        exBox.append(exBtn);
      } else {
        exBox.append(h('p', { style: { fontSize: '12px', color: 'rgba(223,230,240,.5)' } }, '表情集需要画布关联项目（从剧本解析创建）'));
      }
      box.append(exBox);
    }

    // 媒体与生成
    if (n.type !== 'note') {
      const prev = h('div', { class: 'media-prev' });
      const m = d.video || d.image;
      if (m) prev.append(isVideoUrl(m) ? h('video', { src: m, controls: true, poster: d.image || undefined }) : h('img', { src: m }));
      box.append(prev);
      if (d.audio) box.append(h('audio', { src: d.audio, controls: true, style: { width: '100%', marginTop: '8px', height: '32px' } }));
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
        if (d.dialogue?.trim()) {
          const dubBtn2 = h('button', { class: 'btn', onclick: async () => {
            dubBtn2.disabled = true;
            dubBtn2.innerHTML = `${icon('loader')} 配音中…`;
            scheduleSave.flush();
            try {
              await POST('/api/ai/dub', { project_id: projectId, node_id: n.id });
              await syncMedia();
              renderInspector(sel);
              toast('配音完成，放映室自动同步播放', 'ok');
            } catch (e2) {
              toast(e2.message, 'err');
              dubBtn2.disabled = false;
              dubBtn2.innerHTML = `🔊 ${d.audio ? '重新配音' : '生成配音'}`;
            }
          } });
          dubBtn2.innerHTML = `🔊 ${d.audio ? '重新配音' : '生成配音'}`;
          acts.append(dubBtn2);
        }
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
    if ((e.metaKey || e.ctrlKey) && (e.key === 'z' || e.key === 'Z')) {
      e.preventDefault();
      return e.shiftKey ? redo() : undo();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'y') { e.preventDefault(); return redo(); }
    if (e.key === 'd' || e.key === 'D') return toggleDoodle(!dd.open);
    if (e.key === 'Escape') {
      if (dd.open) return toggleDoodle(false);
      return graph.clearSelection();
    }
    if (e.key === 'Delete' || e.key === 'Backspace') {
      const ids = graph.getMulti();
      if (ids.length) {
        if (!await confirmDlg(`删除选中的 ${ids.length} 个节点？关联连线一并删除。`)) return;
        return graph.removeSelected();
      }
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
  main.append(zoombar, mini, inspectorBox, doodleBar);
  page.append(shell);

  graph.setData({ nodes: canvas.nodes, edges: canvas.edges, doodles: canvas.doodles || [], viewport: canvas.viewport });
  pushHistory();           // 初始快照（撤销的回退底座）
  miniReady = true;
  requestAnimationFrame(drawMini);
  if ((canvas.nodes || []).some((n) => n.data?.task_status === 'running')) syncMedia();

  return () => {
    clearInterval(pollTimer);
    document.removeEventListener('keydown', onKey);
    scheduleSave.flush();
    graph.destroy();
  };
}
