// 青鸾 · 节点图引擎（零依赖）：平移 / 缩放 / 节点拖拽 / 端口连线 / 选择
// 数据模型：node {id, type, x, y, data:{...}}  edge {id, from, to}
import { h } from '../ui.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export function createGraph(root, {
  renderNode,            // (node) => HTMLElement 节点内容
  onChange,              // 结构变化（移动/增删/连线）
  onSelect,              // ({kind:'node'|'edge', id} | null)
  onView,                // (zoom) 视图变化
  canLink = (from, to) => from.id !== to.id,
  sourcePort = (n) => n.type !== 'shot' && n.type !== 'note',
  targetPort = (n) => n.type === 'shot'
} = {}) {
  let nodes = [];
  let edges = [];
  let doodles = [];             // 涂鸦笔手绘批注 [{id,color,width,points:[[x,y]...]}]
  let tool = null;              // null | 'pen' | 'eraser'
  const toolOpts = { color: '#54c2b4', width: 3.5 };
  let zoom = 1, panX = 60, panY = 40;
  let selected = null;          // {kind, id}
  let multi = new Set();        // 框选多选的节点 id

  const vp = h('div', { class: 'flow-vp' });
  const world = h('div', { class: 'flow-world' });
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'flow-edges');
  const nodeLayer = h('div', {});
  // 涂鸦层独立 SVG，置于节点之上（批注覆盖一切，可被橡皮命中）
  const svgDd = document.createElementNS(SVG_NS, 'svg');
  svgDd.setAttribute('class', 'flow-edges dd-svg');
  svgDd.style.pointerEvents = 'none';
  world.append(svg, nodeLayer, svgDd);
  vp.append(world);
  root.append(vp);

  const nodeEls = new Map();    // id -> element
  const edgeEls = new Map();    // id -> {hit, line}
  let tempPath = null;

  // ---------- 视图 ----------
  function applyView() {
    world.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
    scheduleCull();
    onView?.(zoom, panX, panY);
  }

  // 视口剔除：大画布只显示可见节点（visibility 保留布局尺寸，连线锚点不受影响）
  let cullTimer = 0;
  function scheduleCull() {
    clearTimeout(cullTimer);
    cullTimer = setTimeout(cull, 90);
  }
  function cull() {
    if (nodes.length < 40) return;          // 小画布无需剔除
    const r = vp.getBoundingClientRect();
    const margin = 420 / zoom;
    const x1 = -panX / zoom - margin, y1 = -panY / zoom - margin;
    const x2 = (r.width - panX) / zoom + margin, y2 = (r.height - panY) / zoom + margin;
    for (const n of nodes) {
      const el = nodeEls.get(n.id);
      if (!el) continue;
      const w = el.offsetWidth || 220, hh = el.offsetHeight || 160;
      const visible = n.x < x2 && n.x + w > x1 && n.y < y2 && n.y + hh > y1;
      el.style.visibility = visible ? '' : 'hidden';
    }
  }
  function screenToWorld(cx, cy) {
    const r = vp.getBoundingClientRect();
    return { x: (cx - r.left - panX) / zoom, y: (cy - r.top - panY) / zoom };
  }
  function setZoom(z, cx, cy) {
    const r = vp.getBoundingClientRect();
    cx = cx ?? r.left + r.width / 2;
    cy = cy ?? r.top + r.height / 2;
    const before = screenToWorld(cx, cy);
    zoom = Math.min(2.5, Math.max(0.12, z));
    panX = cx - r.left - before.x * zoom;
    panY = cy - r.top - before.y * zoom;
    applyView();
  }
  function fit() {
    if (!nodes.length) { zoom = 1; panX = 80; panY = 60; return applyView(); }
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const n of nodes) {
      const el = nodeEls.get(n.id);
      x1 = Math.min(x1, n.x); y1 = Math.min(y1, n.y);
      x2 = Math.max(x2, n.x + (el?.offsetWidth || 220));
      y2 = Math.max(y2, n.y + (el?.offsetHeight || 160));
    }
    const r = vp.getBoundingClientRect();
    const pad = 70;
    zoom = Math.min(1.15, Math.max(0.12, Math.min((r.width - pad * 2) / (x2 - x1), (r.height - pad * 2) / (y2 - y1))));
    panX = (r.width - (x2 - x1) * zoom) / 2 - x1 * zoom;
    panY = (r.height - (y2 - y1) * zoom) / 2 - y1 * zoom;
    applyView();
  }

  // ---------- 节点渲染 ----------
  function mountNode(n, pop = false) {
    const el = h('div', { class: `ql-node node-${n.type}`, dataset: { id: n.id } });
    el.style.left = n.x + 'px';
    el.style.top = n.y + 'px';
    el.append(renderNode(n));
    if (sourcePort(n)) el.append(h('span', { class: 'flow-port out', dataset: { node: n.id }, title: '拖到分镜节点上建立关联' }));
    if (targetPort(n)) el.append(h('span', { class: 'flow-port in', title: '接收角色/场景/道具关联' }));
    if (pop) {
      el.classList.add('pop');
      el.addEventListener('animationend', () => el.classList.remove('pop'), { once: true });
    }
    nodeLayer.append(el);
    nodeEls.set(n.id, el);
    return el;
  }
  function refreshNode(id) {
    const n = nodes.find((x) => x.id === id);
    const el = nodeEls.get(id);
    if (!n || !el) return;
    el.innerHTML = '';
    el.append(renderNode(n));
    if (sourcePort(n)) el.append(h('span', { class: 'flow-port out', dataset: { node: n.id }, title: '拖到分镜节点上建立关联' }));
    if (targetPort(n)) el.append(h('span', { class: 'flow-port in' }));
    el.classList.toggle('sel', selected?.kind === 'node' && selected.id === id);
    requestAnimationFrame(refreshEdges);
  }

  // ---------- 边渲染 ----------
  function anchor(n, side) {
    const el = nodeEls.get(n.id);
    const w = el?.offsetWidth || 220;
    const hh = el?.offsetHeight || 160;
    return side === 'out' ? { x: n.x + w, y: n.y + hh / 2 } : { x: n.x, y: n.y + hh / 2 };
  }
  function pathD(a, b) {
    const dx = Math.min(170, Math.max(46, Math.abs(b.x - a.x) * 0.45));
    return `M ${a.x} ${a.y} C ${a.x + dx} ${a.y}, ${b.x - dx} ${b.y}, ${b.x} ${b.y}`;
  }
  function mountEdge(e, animate = false) {
    const hit = document.createElementNS(SVG_NS, 'path');
    hit.setAttribute('class', 'hit');
    hit.dataset.id = e.id;
    const line = document.createElementNS(SVG_NS, 'path');
    line.setAttribute('class', 'edge' + (animate ? ' draw' : ''));
    line.setAttribute('pathLength', '1');
    svg.append(hit, line);
    edgeEls.set(e.id, { hit, line });
  }

  // ---------- 涂鸦层 ----------
  function smoothPath(pts) {
    if (!pts.length) return '';
    if (pts.length < 3) {
      const a = pts[0], b = pts[pts.length - 1];
      return `M ${a[0]} ${a[1]} L ${b[0] + 0.01} ${b[1] + 0.01}`;
    }
    let d = `M ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i][0] + pts[i + 1][0]) / 2;
      const my = (pts[i][1] + pts[i + 1][1]) / 2;
      d += ` Q ${pts[i][0]} ${pts[i][1]} ${mx} ${my}`;
    }
    return d;
  }
  function mountDoodle(dd) {
    const p = document.createElementNS(SVG_NS, 'path');
    p.setAttribute('class', 'dd-stroke');
    p.dataset.id = dd.id;
    p.setAttribute('stroke', dd.color);
    p.setAttribute('stroke-width', dd.width);
    p.setAttribute('d', smoothPath(dd.points));
    p.style.pointerEvents = 'stroke';
    svgDd.append(p);
    return p;
  }
  function eraseAt(cx, cy) {
    const p = screenToWorld(cx, cy);
    const hit = doodles.find((d) => {
      const tol = Math.max(14 / zoom, d.width * 1.6);
      return d.points.some(([x, y]) => (x - p.x) ** 2 + (y - p.y) ** 2 < tol * tol);
    });
    if (!hit) return;
    doodles = doodles.filter((d) => d.id !== hit.id);
    svgDd.querySelector(`path[data-id="${hit.id}"]`)?.remove();
    onChange?.();
  }
  function refreshEdges() {
    scheduleCull();
    const byId = new Map(nodes.map((n) => [n.id, n]));
    for (const e of edges) {
      const els = edgeEls.get(e.id);
      const from = byId.get(e.from);
      const to = byId.get(e.to);
      if (!els || !from || !to) continue;
      const d = pathD(anchor(from, 'out'), anchor(to, 'in'));
      els.hit.setAttribute('d', d);
      els.line.setAttribute('d', d);
      els.line.classList.toggle('sel', selected?.kind === 'edge' && selected.id === e.id);
    }
  }

  function rebuild() {
    nodeLayer.innerHTML = '';
    svg.innerHTML = '';
    svgDd.innerHTML = '';
    nodeEls.clear();
    edgeEls.clear();
    nodes.forEach((n) => mountNode(n));
    edges.forEach((e) => mountEdge(e));
    doodles.forEach(mountDoodle);
    requestAnimationFrame(refreshEdges);
  }

  // ---------- 选择 ----------
  function select(sel) {
    selected = sel;
    if (multi.size) { multi.clear(); refreshMsel(); }
    for (const [id, el] of nodeEls) el.classList.toggle('sel', sel?.kind === 'node' && sel.id === id);
    refreshEdges();
    onSelect?.(sel);
  }
  function refreshMsel() {
    for (const [id, el] of nodeEls) el.classList.toggle('msel', multi.has(id));
  }
  function setMulti(ids) {
    selected = null;
    for (const [, el] of nodeEls) el.classList.remove('sel');
    multi = new Set(ids);
    refreshMsel();
    refreshEdges();
    onSelect?.(multi.size ? { kind: 'multi', ids: [...multi] } : null);
  }

  // ---------- 交互 ----------
  let drag = null; // {mode:'pan'|'node'|'link', ...}
  vp.addEventListener('pointerdown', (e) => {
    if (e.button === 2) return;
    // 涂鸦模式优先：画笔起笔 / 橡皮擦除
    if (tool === 'pen') {
      const p = screenToWorld(e.clientX, e.clientY);
      const dd = { id: 'd' + Math.random().toString(36).slice(2, 10), color: toolOpts.color, width: toolOpts.width, points: [[Math.round(p.x), Math.round(p.y)]] };
      drag = { mode: 'doodle', dd, el: mountDoodle(dd), last: p };
      vp.setPointerCapture?.(e.pointerId);
      return e.preventDefault();
    }
    if (tool === 'eraser') {
      drag = { mode: 'erase' };
      eraseAt(e.clientX, e.clientY);
      vp.setPointerCapture?.(e.pointerId);
      return e.preventDefault();
    }
    const portEl = e.target.closest?.('.flow-port.out');
    const nodeEl = e.target.closest?.('.ql-node');
    if (portEl) {
      const from = nodes.find((n) => n.id === portEl.dataset.node);
      tempPath = document.createElementNS(SVG_NS, 'path');
      tempPath.setAttribute('class', 'temp');
      svg.append(tempPath);
      drag = { mode: 'link', from, sx: e.clientX, sy: e.clientY, moved: false };
    } else if (nodeEl) {
      if (e.target.closest('button, input, textarea, select, video, a')) return; // 让交互控件正常工作
      const n = nodes.find((x) => x.id === nodeEl.dataset.id);
      if (e.shiftKey) {
        // Shift+点节点：加入/移出多选
        multi.has(n.id) ? multi.delete(n.id) : multi.add(n.id);
        setMulti([...multi]);
        return e.preventDefault();
      }
      const p = screenToWorld(e.clientX, e.clientY);
      if (multi.has(n.id)) {
        // 成组拖动
        drag = {
          mode: 'group', px: p.x, py: p.y, sx: e.clientX, sy: e.clientY, moved: false,
          starts: [...multi].map((id) => { const m = nodes.find((x) => x.id === id); return { n: m, x0: m.x, y0: m.y }; })
        };
      } else {
        drag = { mode: 'node', n, dx: p.x - n.x, dy: p.y - n.y, sx: e.clientX, sy: e.clientY, moved: false };
        nodeEl.style.zIndex = 10;
      }
    } else if (e.shiftKey) {
      // Shift+拖背景：框选
      drag = { mode: 'marquee', sx: e.clientX, sy: e.clientY, box: h('div', { class: 'flow-marquee' }) };
      vp.append(drag.box);
    } else {
      drag = { mode: 'pan', sx: e.clientX, sy: e.clientY, px: panX, py: panY, moved: false };
      vp.classList.add('panning');
    }
    vp.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  });

  vp.addEventListener('pointermove', (e) => {
    if (!drag) return;
    if (drag.mode === 'doodle') {
      const p = screenToWorld(e.clientX, e.clientY);
      const dx = p.x - drag.last.x, dy = p.y - drag.last.y;
      if (dx * dx + dy * dy > (1.6 / zoom) ** 2) {
        drag.dd.points.push([Math.round(p.x), Math.round(p.y)]);
        drag.el.setAttribute('d', smoothPath(drag.dd.points));
        drag.last = p;
      }
      return;
    }
    if (drag.mode === 'erase') return eraseAt(e.clientX, e.clientY);
    if (drag.mode === 'marquee') {
      const r = vp.getBoundingClientRect();
      const x = Math.min(drag.sx, e.clientX) - r.left, y = Math.min(drag.sy, e.clientY) - r.top;
      Object.assign(drag.box.style, {
        left: x + 'px', top: y + 'px',
        width: Math.abs(e.clientX - drag.sx) + 'px', height: Math.abs(e.clientY - drag.sy) + 'px'
      });
      return;
    }
    if (Math.abs(e.clientX - drag.sx) + Math.abs(e.clientY - drag.sy) > 4) drag.moved = true;
    if (drag.mode === 'group') {
      const p = screenToWorld(e.clientX, e.clientY);
      const dx = p.x - drag.px, dy = p.y - drag.py;
      for (const s of drag.starts) {
        s.n.x = Math.round(s.x0 + dx);
        s.n.y = Math.round(s.y0 + dy);
        const el = nodeEls.get(s.n.id);
        if (el) { el.style.left = s.n.x + 'px'; el.style.top = s.n.y + 'px'; }
      }
      refreshEdges();
      return;
    }
    if (drag.mode === 'pan') {
      panX = drag.px + (e.clientX - drag.sx);
      panY = drag.py + (e.clientY - drag.sy);
      applyView();
    } else if (drag.mode === 'node') {
      const p = screenToWorld(e.clientX, e.clientY);
      drag.n.x = Math.round(p.x - drag.dx);
      drag.n.y = Math.round(p.y - drag.dy);
      const el = nodeEls.get(drag.n.id);
      el.style.left = drag.n.x + 'px';
      el.style.top = drag.n.y + 'px';
      refreshEdges();
    } else if (drag.mode === 'link') {
      const p = screenToWorld(e.clientX, e.clientY);
      tempPath.setAttribute('d', pathD(anchor(drag.from, 'out'), p));
    }
  });

  vp.addEventListener('pointerup', (e) => {
    if (!drag) return;
    vp.classList.remove('panning');
    const d = drag;
    drag = null;
    if (d.mode === 'doodle') {
      doodles.push(d.dd);
      onChange?.();
      return;
    }
    if (d.mode === 'erase') return;
    if (d.mode === 'marquee') {
      const a = screenToWorld(Math.min(d.sx, e.clientX), Math.min(d.sy, e.clientY));
      const b = screenToWorld(Math.max(d.sx, e.clientX), Math.max(d.sy, e.clientY));
      d.box.remove();
      const hits = nodes.filter((n) => {
        const el = nodeEls.get(n.id);
        const w = el?.offsetWidth || 200, hh = el?.offsetHeight || 150;
        return n.x < b.x && n.x + w > a.x && n.y < b.y && n.y + hh > a.y;
      }).map((n) => n.id);
      setMulti(hits);
      return;
    }
    if (d.mode === 'group') {
      if (d.moved) onChange?.();
      return;
    }
    if (d.mode === 'link') {
      tempPath?.remove();
      tempPath = null;
      const targetEl = document.elementFromPoint(e.clientX, e.clientY)?.closest?.('.ql-node');
      if (targetEl) {
        const to = nodes.find((n) => n.id === targetEl.dataset.id);
        if (to && canLink(d.from, to) && !edges.some((x) => x.from === d.from.id && x.to === to.id)) {
          const edge = { id: 'e' + Math.random().toString(36).slice(2, 10), from: d.from.id, to: to.id };
          edges.push(edge);
          mountEdge(edge, true);
          refreshEdges();
          onChange?.();
        }
      }
      return;
    }
    if (d.mode === 'node') {
      nodeEls.get(d.n.id).style.zIndex = '';
      if (d.moved) onChange?.();
      else select({ kind: 'node', id: d.n.id });
      return;
    }
    if (d.mode === 'pan' && !d.moved) {
      const hitEdge = e.target.closest?.('path.hit');
      if (hitEdge) select({ kind: 'edge', id: hitEdge.dataset.id });
      else select(null);
    }
  });

  vp.addEventListener('wheel', (e) => {
    e.preventDefault();
    const factor = Math.pow(1.0016, -e.deltaY * (e.ctrlKey ? 2.2 : 1));
    setZoom(zoom * factor, e.clientX, e.clientY);
  }, { passive: false });

  svg.style.pointerEvents = 'none';
  // 边的命中路径需要接收事件
  const edgeClickGuard = new MutationObserver(() => { svg.querySelectorAll('path.hit').forEach((p) => p.style.pointerEvents = 'stroke'); });
  edgeClickGuard.observe(svg, { childList: true });

  applyView();

  return {
    el: vp,
    setData({ nodes: ns, edges: es, doodles: ds, viewport }) {
      nodes = ns || [];
      edges = es || [];
      doodles = ds || [];
      if (viewport) { zoom = viewport.zoom || 1; panX = viewport.x ?? 60; panY = viewport.y ?? 40; }
      rebuild();
      applyView();
      if (!viewport) requestAnimationFrame(() => fit());
    },
    getData: () => ({ nodes, edges, doodles, viewport: { zoom, x: panX, y: panY } }),
    // 涂鸦笔
    setTool(t, opts) {
      tool = t;
      if (opts) Object.assign(toolOpts, opts);
      vp.classList.toggle('doodling', t === 'pen');
      vp.classList.toggle('erasing', t === 'eraser');
    },
    getTool: () => tool,
    getDoodles: () => doodles,
    clearDoodles() {
      doodles = [];
      svgDd.innerHTML = '';
      onChange?.();
    },
    getNodes: () => nodes,
    getEdges: () => edges,
    getSelected: () => selected,
    findNode: (id) => nodes.find((n) => n.id === id),
    addNode(n) {
      nodes.push(n);
      mountNode(n, true);
      select({ kind: 'node', id: n.id });
      onChange?.();
    },
    updateNodeData(id, patch, { rerender = true } = {}) {
      const n = nodes.find((x) => x.id === id);
      if (!n) return;
      Object.assign(n.data, patch);
      if (rerender) refreshNode(id);
    },
    removeSelected() {
      if (multi.size) {
        const ids = multi;
        nodes = nodes.filter((n) => !ids.has(n.id));
        edges = edges.filter((e) => !ids.has(e.from) && !ids.has(e.to));
        rebuild();
        setMulti([]);
        onChange?.();
        return true;
      }
      if (!selected) return false;
      if (selected.kind === 'node') {
        const id = selected.id;
        nodes = nodes.filter((n) => n.id !== id);
        edges = edges.filter((e) => e.from !== id && e.to !== id);
        rebuild();
      } else {
        edges = edges.filter((e) => e.id !== selected.id);
        rebuild();
      }
      select(null);
      onChange?.();
      return true;
    },
    getMulti: () => [...multi],
    clearSelection: () => select(null),
    /** 批量调整节点（对齐/分布等）：fn(node) 就地修改 x/y */
    nudgeNodes(ids, fn) {
      for (const id of ids) {
        const n = nodes.find((x) => x.id === id);
        if (!n) continue;
        fn(n);
        const el = nodeEls.get(id);
        if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
      }
      refreshEdges();
      onChange?.();
    },
    refreshNode, refreshEdges, fit,
    zoomBy: (f) => setZoom(zoom * f),
    getZoom: () => zoom,
    /** 小地图导航：把世界坐标 (wx, wy) 移到视口中心 */
    panTo(wx, wy) {
      const r = vp.getBoundingClientRect();
      panX = r.width / 2 - wx * zoom;
      panY = r.height / 2 - wy * zoom;
      applyView();
    },
    getViewRect() {
      const r = vp.getBoundingClientRect();
      return { x: -panX / zoom, y: -panY / zoom, w: r.width / zoom, h: r.height / zoom };
    },
    centerWorld: () => screenToWorld(vp.getBoundingClientRect().left + vp.clientWidth / 2, vp.getBoundingClientRect().top + vp.clientHeight / 2),
    destroy: () => { edgeClickGuard.disconnect(); vp.remove(); }
  };
}
