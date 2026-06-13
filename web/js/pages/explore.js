// 句灵 · 无限放大：从一句话/情绪出发，逐层「丝滑放大」下钻，AI 现生成更深的世界
import { POST } from '../api.js';
import { h, toast } from '../ui.js';
import { nav } from '../router.js';

const MOTIF_PAL = {
  city: { bg: ['#1b2138', '#2a3358'], acc: '#8ea8ff', ink: '#eaf0ff' },
  nature: { bg: ['#15301f', '#234a33'], acc: '#7fdca8', ink: '#eafff2' },
  cosmos: { bg: ['#161235', '#241a4a'], acc: '#b09bff', ink: '#efeaff' },
  heart: { bg: ['#2e1626', '#46233c'], acc: '#ff8fb3', ink: '#ffe9f2' },
  memory: { bg: ['#2a2318', '#3f3422'], acc: '#e0b878', ink: '#fff4e2' },
  abstract: { bg: ['#1c1d2e', '#2a2c48'], acc: '#9d8cff', ink: '#eee9ff' }
};
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

export function renderExplore(page) {
  page.classList.add('no-nav', 'zoom-page');
  const crumbs = h('div', { class: 'zoom-crumbs' });
  const stage = h('div', { class: 'zoom-stage' });
  page.append(
    h('div', { class: 'topbar', style: { padding: '8px 12px', flexShrink: 0 } },
      h('button', { class: 'icon-btn', onclick: () => (path.length > 1 ? zoomOut() : nav('/feed')) }, '←'),
      h('div', { style: { flex: 1, minWidth: 0 } }, h('h1', { style: { fontSize: '16px' } }, '无限放大'), crumbs),
      h('button', { class: 'icon-btn', onclick: restart }, '✕')
    ),
    stage
  );

  let path = [];      // 已下钻的帧栈（含 title/blurb/hotspots/motif）
  let busy = false;
  let curEl = null;

  function renderCrumbs() {
    crumbs.innerHTML = '';
    if (!path.length) { crumbs.textContent = '一句话，一个无限世界'; return; }
    path.forEach((f, i) => {
      crumbs.append(h('span', {
        class: `zc ${i === path.length - 1 ? 'cur' : ''}`,
        onclick: () => jumpTo(i)
      }, f.title));
      if (i < path.length - 1) crumbs.append(h('span', { class: 'zc-sep' }, '›'));
    });
  }

  function frameEl(frame, fromScale, origin) {
    const pal = MOTIF_PAL[frame.motif] || MOTIF_PAL.abstract;
    const el = h('div', {
      class: 'zoom-frame',
      style: {
        background: `radial-gradient(120% 90% at 50% 18%, ${pal.acc}33, transparent 60%), linear-gradient(160deg, ${pal.bg[0]}, ${pal.bg[1]})`,
        color: pal.ink, transformOrigin: origin || '50% 50%', transform: `scale(${fromScale})`, opacity: '0'
      }
    });
    // 程序化氛围层（散落 emoji，无图片资源）
    const mote = (frame.hotspots[0]?.emoji) || '✦';
    const bgGlyphs = h('div', { class: 'zoom-glyphs' });
    let s = (frame.title.length * 97 + frame.depth * 31 + 7) >>> 0;
    const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
    for (let i = 0; i < 10; i++) {
      bgGlyphs.append(h('span', { style: { left: `${(rnd() * 92).toFixed(1)}%`, top: `${(rnd() * 88).toFixed(1)}%`, fontSize: `${(16 + rnd() * 34) | 0}px`, opacity: (0.05 + rnd() * 0.12).toFixed(2) } }, mote));
    }
    el.append(bgGlyphs,
      h('div', { class: 'zoom-depth' }, `第 ${frame.depth + 1} 层${frame.by === 'local' ? '' : ' · AI'}`),
      h('div', { class: 'zoom-title' }, frame.title),
      h('div', { class: 'zoom-blurb' }, frame.blurb),
      h('div', { class: 'zoom-hint' }, '点任意一处，继续放大 ↓')
    );
    const hots = h('div', { class: 'zoom-hots' });
    for (const hsItem of frame.hotspots) {
      const btn = h('button', { class: 'zoom-hot', style: { borderColor: pal.acc + '66', boxShadow: `0 0 16px ${pal.acc}33` }, onclick: () => zoomInto(hsItem, btn) },
        h('span', { class: 'zh-emoji' }, hsItem.emoji), h('span', {}, hsItem.label));
      hots.append(btn);
    }
    el.append(hots);
    return el;
  }

  function show(frame, fromScale = 0.6, origin) {
    stage.innerHTML = '';
    const el = frameEl(frame, fromScale, origin);
    stage.append(el);
    curEl = el;
    requestAnimationFrame(() => requestAnimationFrame(() => { el.style.transform = 'scale(1)'; el.style.opacity = '1'; }));
  }

  function loader() {
    stage.innerHTML = '';
    stage.append(h('div', { class: 'zoom-loader' }, h('div', { class: 'mascot', style: { fontSize: '34px' } }, '🔮'), h('div', {}, '正在放大…')));
  }

  function originPct(btn) {
    const sr = stage.getBoundingClientRect(); const br = btn.getBoundingClientRect();
    const x = ((br.left + br.width / 2 - sr.left) / sr.width * 100).toFixed(1);
    const y = ((br.top + br.height / 2 - sr.top) / sr.height * 100).toFixed(1);
    return `${x}% ${y}%`;
  }

  async function fetchFrame(focus) {
    const { frame } = await POST('/api/zoom', { path: path.map((f) => f.title), focus });
    return frame;
  }

  async function zoomInto(hs, btn) {
    if (busy) return; busy = true;
    const origin = originPct(btn);
    if (curEl) { curEl.style.transformOrigin = origin; curEl.style.transform = 'scale(3.4)'; curEl.style.opacity = '0'; }
    try {
      const [frame] = await Promise.all([fetchFrame(hs.label), delay(460)]);
      path.push(frame); renderCrumbs(); show(frame, 0.5);
    } catch (e) { toast(e.message, 'warn'); if (path.length) show(path[path.length - 1], 1); }
    busy = false;
  }

  function zoomOut() {
    if (busy || path.length <= 1) return;
    path.pop(); renderCrumbs(); show(path[path.length - 1], 1.5);
  }
  function jumpTo(i) {
    if (busy || i >= path.length - 1) return;
    path = path.slice(0, i + 1); renderCrumbs(); show(path[i], 1.5);
  }

  async function start(seed) {
    busy = true; path = []; renderCrumbs(); loader();
    try {
      const { frame } = await POST('/api/zoom', { path: [], focus: seed });
      path = [frame]; renderCrumbs(); show(frame, 0.7);
    } catch (e) { toast(e.message, 'warn'); restart(); }
    busy = false;
  }

  function restart() {
    path = []; busy = false; renderCrumbs();
    stage.innerHTML = '';
    const input = h('input', { class: 'input', maxlength: 40, placeholder: '输入一个词或一句话…' });
    const go = () => { const v = input.value.trim(); if (v) start(v); };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
    const chips = h('div', { class: 'zoom-seeds' });
    for (const s of ['此刻', '孤独', '巴黎的夜', '童年的夏天', '星空之下', '想你']) {
      chips.append(h('button', { class: 'chip', onclick: () => start(s) }, s));
    }
    stage.append(h('div', { class: 'zoom-intro' },
      h('div', { class: 'zoom-intro-title' }, '一句话，一个无限世界'),
      h('div', { class: 'zoom-intro-sub' }, '写下一个词或一种心情，然后一层层放大它——\n每深入一层，句灵都会为你展开更深的风景。'),
      h('div', { style: { display: 'flex', gap: '8px', width: '100%', maxWidth: '320px' } },
        input, h('button', { class: 'btn', style: { flexShrink: 0 }, onclick: go }, '放大')),
      chips
    ));
  }

  restart();
}
