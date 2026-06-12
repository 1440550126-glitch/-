// 青鸾 · UI 工具：DOM 构建 / 图标 / Toast / Modal
export const escHtml = (s = '') => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** h('div', {class:'x', onclick}, child1, 'text') */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked' || k === 'disabled' || k === 'selected') el[k] = !!v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(9)) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(c));
  }
  return el;
}

// ---- 图标（线性，currentColor） ----
const P = (d) => d.split('|').map((x) => `<path d="${x}"/>`).join('');
const ICONS = {
  home: P('M3 10.5 12 3l9 7.5|M5 9.5V21h14V9.5|M9.5 21v-6h5v6'),
  folder: P('M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z'),
  robot: P('M12 3v3|M7 6.8h10a2.2 2.2 0 0 1 2.2 2.2v7A2.2 2.2 0 0 1 17 18.2H7A2.2 2.2 0 0 1 4.8 16V9A2.2 2.2 0 0 1 7 6.8Z|M9 11.4v1.4|M15 11.4v1.4|M9.4 18.5 8 21.5|M14.6 18.5 16 21.5'),
  settings: P('M12 8.6A3.4 3.4 0 1 0 12 15.4 3.4 3.4 0 0 0 12 8.6Z|M19.4 13.2a1.7 1.7 0 0 0 .34 1.88l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V19.4a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.1-1.56 1.7 1.7 0 0 0-1.89.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.88 1.7 1.7 0 0 0-1.56-1.03H4.6a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.1 1.7 1.7 0 0 0-.34-1.89l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.88.34h.01a1.7 1.7 0 0 0 1.03-1.56V4.6a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.88v.01a1.7 1.7 0 0 0 1.56 1.03h.17a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03Z'),
  plus: P('M12 5v14|M5 12h14'),
  spark: P('M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9Z|M19 15.5l.9 2.4 2.4.9-2.4.9-.9 2.4-.9-2.4-2.4-.9 2.4-.9Z'),
  film: P('M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z|M7 5v14|M17 5v14|M3 9h4|M3 15h4|M17 9h4|M17 15h4'),
  image: P('M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z|M8.5 11a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z|m21 15-4.5-4.5L7 20'),
  user: P('M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z|M4.5 21a7.5 7.5 0 0 1 15 0'),
  box: P('m12 2 8 4.5v9L12 22l-8-6.5v-9Z|M12 22V11.5|M4 6.5l8 5 8-5'),
  play: P('M7 4.8v14.4L19 12Z'),
  trash: P('M4 7h16|M9 7V4.8A.8.8 0 0 1 9.8 4h4.4a.8.8 0 0 1 .8.8V7|M6.5 7l.9 13h9.2l.9-13'),
  pencil: P('M16.6 3.6a2.1 2.1 0 0 1 3 3L8 18.2 4 19.8l1.6-4Z'),
  copy: P('M9 9h11v11H9Z|M5 15H4V4h11v1'),
  check: P('m4.5 12.5 5 5L19.5 7'),
  x: P('m5 5 14 14|M19 5 5 19'),
  link: P('M10 14a5 5 0 0 0 7.1 0l2.8-2.9A5 5 0 0 0 12.8 4l-1.3 1.3|M14 10a5 5 0 0 0-7.1 0l-2.8 2.9A5 5 0 0 0 11.2 20l1.3-1.3'),
  upload: P('M12 16V4|m6.5 9.5L12 4l5.5 5.5|M4 20h16'),
  search: P('M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z|m20 20-4-4'),
  fit: P('M4 9V4h5|M20 9V4h-5|M4 15v5h5|M20 15v5h-5'),
  zoomin: P('M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z|m20 20-4-4|M11 8.5v5|M8.5 11h5'),
  zoomout: P('M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z|m20 20-4-4|M8.5 11h5'),
  layout: P('M4 4h7v7H4Z|M13 4h7v4h-7Z|M13 11h7v9h-7Z|M4 14h7v6H4Z'),
  back: P('m11 5-7 7 7 7|M4 12h16'),
  send: P('m3.5 11.5 17-7-5 16-3.5-6.5Z|M12 13.5 20.5 4.5'),
  refresh: P('M20 8A8.5 8.5 0 0 0 5.5 6L4 8|M4 16a8.5 8.5 0 0 0 14.5 2l1.5-2|M4 3.5V8h4.5|M20 20.5V16h-4.5'),
  clock: P('M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z|M12 7v5l3.5 2'),
  video: P('M3.5 6.5h11a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 2 16V8a1.5 1.5 0 0 1 1.5-1.5Z|m16 10.5 6-3.5v10l-6-3.5'),
  terminal: P('M4 4.5h16a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1Z|m7 9 3 3-3 3|M12.5 15.5H17'),
  coins: P('M12 8.5c4.4 0 8-1.2 8-2.75S16.4 3 12 3 4 4.2 4 5.75 7.6 8.5 12 8.5Z|M4 5.75V18.3c0 1.5 3.6 2.7 8 2.7s8-1.2 8-2.7V5.75|M4 12c0 1.5 3.6 2.75 8 2.75S20 13.5 20 12'),
  wand: P('m6 18 9.5-9.5|M14 4l.8 2.2L17 7l-2.2.8L14 10l-.8-2.2L11 7l2.2-.8Z|M19 12l.5 1.5L21 14l-1.5.5L19 16l-.5-1.5L17 14l1.5-.5Z|M5 4l.5 1.5L7 6l-1.5.5L5 8l-.5-1.5L3 6l1.5-.5Z'),
  layers: P('m12 3 9 5-9 5-9-5Z|m4.5 12.5 7.5 4.2 7.5-4.2|m4.5 16.5 7.5 4.2 7.5-4.2'),
  dots: P('M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z|M5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z|M19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z'),
  external: P('M14 4h6v6|M20 4 11 13|M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5'),
  download: P('M12 4v12|m6.5 10.5 5.5 5.5 5.5-5.5|M4 20h16'),
  loader: P('M12 3a9 9 0 1 0 9 9'),
  undo: P('M8 5 4 9l4 4|M4 9h10.5a5.5 5.5 0 0 1 0 11H11'),
  redo: P('M16 5l4 4-4 4|M20 9H9.5a5.5 5.5 0 0 0 0 11H13')
};
export function icon(name, size = 17) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${name === 'loader' ? ' class="spin"' : ''}>${ICONS[name] || ''}</svg>`;
}
export const iconEl = (name, size) => h('span', { style: { display: 'inline-flex' }, html: icon(name, size) });

export const LOGO_SVG = `<svg viewBox="0 0 100 100" width="34" height="34"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e8c86"/><stop offset="1" stop-color="#54c2b4"/></linearGradient></defs><rect width="100" height="100" rx="24" fill="url(#lg)"/><path d="M22 62 Q40 30 64 34 Q80 37 84 24 Q83 44 70 50 Q84 52 88 46 Q83 62 66 60 Q52 59 44 66 Q38 71 38 80 L33 70 Q24 70 18 76 Q19 66 22 62 Z" fill="white"/><circle cx="66" cy="40" r="2.6" fill="#0e8c86"/></svg>`;

// ---- 手绘涂鸦点缀（路径 draw-in，非线性缓动） ----
const DOODLES = {
  underline: { w: 120, h: 14, d: 'M3 9 C 28 3, 52 13, 76 7 S 112 5, 117 8' },
  arrow: { w: 56, h: 44, d: 'M4 5 C 16 25, 31 36, 49 37 M41 29 L 50 37 L 40 42' },
  circle: { w: 132, h: 52, d: 'M70 7 C 28 4, 9 15, 10 27 C 11 41, 47 48, 85 45 C 117 42, 127 30, 119 18 C 111 9, 86 5, 64 8' },
  star: { w: 26, h: 26, d: 'M13 2 L 15.5 9.5 L 24 10 L 17.5 15 L 19.5 23 L 13 18.5 L 6.5 23 L 8.5 15 L 2 10 L 10.5 9.5 Z' },
  spark: { w: 34, h: 34, d: 'M17 3 V 11 M17 23 V 31 M3 17 H 11 M23 17 H 31 M8 8 L 13 13 M21 21 L 26 26 M26 8 L 21 13 M13 21 L 8 26' },
  squiggle: { w: 84, h: 18, d: 'M3 12 C 12 2, 20 16, 29 8 S 46 14, 55 7 S 74 13, 81 6' }
};
export function doodle(name, { color = '#e2543e', size = 0, delay = 200, width = 2.6, rotate = 0, style = {} } = {}) {
  const d = DOODLES[name];
  if (!d) return h('span');
  const w = size || d.w;
  const hh = Math.round(size ? size * d.h / d.w : d.h);
  return h('span', {
    class: 'dd', style: { transform: rotate ? `rotate(${rotate}deg)` : '', ...style },
    html: `<svg width="${w}" height="${hh}" viewBox="0 0 ${d.w} ${d.h}" fill="none" aria-hidden="true">
      <path d="${d.d}" pathLength="1" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" class="dd-path" style="animation-delay:${delay}ms"/></svg>`
  });
}

/** 列表错峰入场（非线性弹性） */
export function stagger(container, step = 45) {
  [...container.children].forEach((el, i) => el.style.setProperty('--i', i));
  container.style.setProperty('--stagger-step', step + 'ms');
  container.classList.remove('stagger');
  void container.offsetWidth;
  container.classList.add('stagger');
}

/** 3D 卡片倾斜（指针跟随，弹性回位） */
export function tilt3d(el, max = 5) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.classList.add('tilt3d');
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(720px) rotateX(${(-y * max).toFixed(2)}deg) rotateY(${(x * max).toFixed(2)}deg) translateY(-3px)`;
  });
  el.addEventListener('pointerleave', () => { el.style.transform = ''; });
}

// ---- Toast ----
function toastBox() {
  let box = document.querySelector('#overlays .toasts');
  if (!box) { box = h('div', { class: 'toasts' }); document.getElementById('overlays').append(box); }
  return box;
}
export function toast(msg, type = '') {
  const t = h('div', { class: `toast ${type}` }, h('span', { html: icon(type === 'err' ? 'x' : type === 'ok' ? 'check' : 'spark', 15) }), String(msg));
  toastBox().append(t);
  setTimeout(() => { t.style.transition = 'opacity .3s'; t.style.opacity = '0'; setTimeout(() => t.remove(), 320); }, type === 'err' ? 4200 : 2600);
}

// ---- Modal ----
export function modal({ title, body, actions = [], wide = false, onClose }) {
  const mask = h('div', { class: 'modal-mask' });
  const close = () => { mask.remove(); document.removeEventListener('keydown', esc); onClose?.(); };
  const esc = (e) => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', esc);
  mask.addEventListener('mousedown', (e) => { if (e.target === mask) close(); });
  const box = h('div', { class: `modal ${wide ? 'wide' : ''}` },
    title ? h('h3', {}, title) : null,
    body,
    actions.length ? h('div', { class: 'm-actions' }, actions.map((a) =>
      h('button', { class: `btn ${a.kind || ''}`, onclick: async (e) => { const r = await a.onClick?.(e); if (r !== false) close(); } }, a.label))) : null
  );
  mask.append(box);
  document.body.append(mask);
  return { close, box };
}
export function confirmDlg(text, { danger = true, okLabel = '确认' } = {}) {
  return new Promise((resolve) => {
    modal({
      title: '确认操作',
      body: h('p', { style: { color: 'var(--ink2)' } }, text),
      actions: [
        { label: '取消', onClick: () => resolve(false) },
        { label: okLabel, kind: danger ? 'danger' : 'primary', onClick: () => resolve(true) }
      ],
      onClose: () => resolve(false)
    });
  });
}

export async function copyText(text, tip = '已复制') {
  try { await navigator.clipboard.writeText(text); toast(tip, 'ok'); }
  catch {
    const ta = h('textarea', { value: text, style: { position: 'fixed', opacity: 0 } });
    document.body.append(ta); ta.select();
    document.execCommand('copy'); ta.remove(); toast(tip, 'ok');
  }
}

export function debounce(fn, ms = 600) {
  let t = null;
  const f = (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  f.flush = (...args) => { clearTimeout(t); fn(...args); };
  f.cancel = () => clearTimeout(t);
  return f;
}

export function fmtTime(ts) {
  const d = new Date(Number(ts));
  const diff = Date.now() - d;
  if (diff < 60_000) return '刚刚';
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`;
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export const STATUS_CN = { draft: '草稿', parsed: '已解析', generating: '生成中', done: '已完成', running: '生成中', succeeded: '完成', failed: '失败', queued: '排队中' };
export const isVideoUrl = (u = '') => /\.(mp4|webm)(\?|$)/i.test(u);

/** 视频/图片自适应预览元素（本地 SMIL svg 用 img 播放） */
export function mediaEl(url, { controls = true, poster = '' } = {}) {
  if (isVideoUrl(url)) {
    return h('video', { src: url, controls, playsinline: true, poster: poster || undefined, preload: 'metadata' });
  }
  return h('img', { src: url, loading: 'lazy', alt: '' });
}
