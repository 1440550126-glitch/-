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
  let zoom = 1, panX = 60, panY = 40;
  let selected = null;          // {kind, id}

  const vp = h('div', { class: 'flow-vp' });
  const world = h('div', { class: 'flow-world' });
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'flow-edges');
  const nodeLayer = h('div', {});
  world.append(svg, nodeLayer);
  vp.append(world);
  root.append(vp);

  const nodeEls = new Map();    // id -> element
  const edgeEls = new Map();    // id -> {hit, line}
  let tempPath = null;

  // ---------- 视图 ----------
  function applyView() {
    world.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
    onView?.(zoom);
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
  function mountNode(n) {
    const el = h('div', { class: `ql-node node-${n.type}`, dataset: { id: n.id } });
    el.style.left = n.x + 'px';
    el.style.top = n.y + 'px';
    el.append(renderNode(n));
    if (sourcePort(n)) el.append(h('span', { class: 'flow-port out', dataset: { node: n.id }, title: '拖到分镜节点上建立关联' }));
    if (targetPort(n)) el.append(h('span', { class: 'flow-port in', title: '接收角色/场景/道具关联' }));
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
  function mountEdge(e) {
    const hit = document.createElementNS(SVG_NS, 'path');
    hit.setAttribute('class', 'hit');
    hit.dataset.id = e.id;
    const line = document.createElementNS(SVG_NS, 'path');
    line.setAttribute('class', 'edge');
    svg.append(hit, line);
    edgeEls.set(e.id, { hit, line });
  }
  function refreshEdges() {
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
    nodeEls.clear();
    edgeEls.clear();
    nodes.forEach(mountNode);
    edges.forEach(mountEdge);
    requestAnimationFrame(refreshEdges);
  }

  // ---------- 选择 ----------
  function select(sel) {
    selected = sel;
    for (const [id, el] of nodeEls) el.classList.toggle('sel', sel?.kind === 'node' && sel.id === id);
    refreshEdges();
    onSelect?.(sel);
  }

  // ---------- 交互 ----------
  let drag = null; // {mode:'pan'|'node'|'link', ...}
  vp.addEventListener('pointerdown', (e) => {
    if (e.button === 2) return;
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
      const p = screenToWorld(e.clientX, e.clientY);
      drag = { mode: 'node', n, dx: p.x - n.x, dy: p.y - n.y, sx: e.clientX, sy: e.clientY, moved: false };
      nodeEl.style.zIndex = 10;
    } else {
      drag = { mode: 'pan', sx: e.clientX, sy: e.clientY, px: panX, py: panY, moved: false };
      vp.classList.add('panning');
    }
    vp.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  });

  vp.addEventListener('pointermove', (e) => {
    if (!drag) return;
    if (Math.abs(e.clientX - drag.sx) + Math.abs(e.clientY - drag.sy) > 4) drag.moved = true;
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
    if (d.mode === 'link') {
      tempPath?.remove();
      tempPath = null;
      const targetEl = document.elementFromPoint(e.clientX, e.clientY)?.closest?.('.ql-node');
      if (targetEl) {
        const to = nodes.find((n) => n.id === targetEl.dataset.id);
        if (to && canLink(d.from, to) && !edges.some((x) => x.from === d.from.id && x.to === to.id)) {
          const edge = { id: 'e' + Math.random().toString(36).slice(2, 10), from: d.from.id, to: to.id };
          edges.push(edge);
          mountEdge(edge);
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
    setData({ nodes: ns, edges: es, viewport }) {
      nodes = ns || [];
      edges = es || [];
      if (viewport) { zoom = viewport.zoom || 1; panX = viewport.x ?? 60; panY = viewport.y ?? 40; }
      rebuild();
      applyView();
      if (!viewport) requestAnimationFrame(() => fit());
    },
    getData: () => ({ nodes, edges, viewport: { zoom, x: panX, y: panY } }),
    getNodes: () => nodes,
    getEdges: () => edges,
    getSelected: () => selected,
    findNode: (id) => nodes.find((n) => n.id === id),
    addNode(n) {
      nodes.push(n);
      mountNode(n);
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
    refreshNode, refreshEdges, fit,
    zoomBy: (f) => setZoom(zoom * f),
    getZoom: () => zoom,
    centerWorld: () => screenToWorld(vp.getBoundingClientRect().left + vp.clientWidth / 2, vp.getBoundingClientRect().top + vp.clientHeight / 2),
    destroy: () => { edgeClickGuard.disconnect(); vp.remove(); }
  };
}
