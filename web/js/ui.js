// UI 工具库：DOM 构建、弹层、头像、预览卡、长按、吉祥物
import { avatarMeta, skinPayload, store } from './store.js';

// ---- DOM 构建 ----
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(9)) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

// ---- Toast ----
let toastWrap = null;
export function toast(msg, type = '') {
  if (!toastWrap) { toastWrap = h('div', { class: 'toast-wrap' }); document.body.append(toastWrap); }
  const t = h('div', { class: `toast ${type}` }, msg);
  toastWrap.append(t);
  const life = type === 'care' ? 6500 : 2400;
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 320); }, life);
}

// ---- 底部弹层 ----
export function sheet(build) {
  const overlays = document.getElementById('overlays');
  const mask = h('div', { class: 'sheet-mask' });
  const box = h('div', { class: 'sheet' }, h('div', { class: 'grab' }));
  const close = () => { mask.remove(); box.remove(); };
  mask.addEventListener('click', close);
  build(box, close);
  overlays.append(mask, box);
  return close;
}

export function confirmSheet(title, desc, actionText, onConfirm, danger = true) {
  sheet((box, close) => {
    box.append(
      h('h3', {}, title),
      h('p', { style: { fontSize: '13px', color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: '18px' } }, desc),
      h('button', {
        class: `btn block ${danger ? 'danger' : ''}`,
        onclick: async () => { close(); await onConfirm(); }
      }, actionText),
      h('button', { class: 'btn block ghost', style: { marginTop: '10px' }, onclick: close }, '再想想')
    );
  });
}

// ---- 时间 ----
export function timeAgo(ts) {
  const d = Date.now() - ts;
  if (d < 60_000) return '刚刚';
  if (d < 3600_000) return `${Math.floor(d / 60_000)} 分钟前`;
  if (d < 86400_000) return `${Math.floor(d / 3600_000)} 小时前`;
  if (d < 7 * 86400_000) return `${Math.floor(d / 86400_000)} 天前`;
  const t = new Date(ts);
  return `${t.getMonth() + 1}-${t.getDate()}`;
}

// ---- 头像（含头像框皮肤，纯外观） ----
export function avatarEl(user, size = 40) {
  const meta = avatarMeta(user?.avatar);
  const wrap = h('div', { class: 'avatar', style: { width: size + 'px', height: size + 'px' } },
    h('div', {
      class: 'blob',
      style: { background: `linear-gradient(135deg, ${meta.colors[0]}, ${meta.colors[1]})`, fontSize: Math.round(size * 0.26) + 'px' }
    }, meta.face)
  );
  const frameId = user?.equipped?.avatar_frame;
  const payload = frameId ? skinPayload(frameId) : null;
  if (payload?.ring) {
    wrap.append(h('div', {
      class: 'ring',
      style: { borderColor: 'transparent', background: `linear-gradient(135deg, ${payload.ring[0]}, ${payload.ring[1]}) border-box`, mask: 'linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)', maskComposite: 'exclude', WebkitMaskComposite: 'xor' }
    }));
    const deco = { ears: '🐱', star: '✦', aurora: '✨' }[payload.deco];
    if (deco) wrap.append(h('div', { class: 'deco' }, deco));
  }
  return wrap;
}

export const aiBadge = (label = 'AI 生成') => h('span', { class: 'badge-ai' }, '🤖 ', label);
export const memberBadge = () => h('span', { class: 'badge-member' }, 'VIP');

// ---- AI 预览卡 ----
const PATTERN_GLYPHS = { wind: '〰', rain: '💧', snow: '❄', petal: '🌸', star: '✦', firefly: '✧', spark: '✶', shard: '◆', cloud: '☁' };
export function previewCardEl(post, { compact = false } = {}) {
  const card = post.card || {};
  const bg = card.bg || ['#f1ecfb', '#fdeef6'];
  const el = h('div', {
    class: `preview-card ${card.layout || 'note'}`,
    style: { background: `linear-gradient(150deg, ${bg[0]}, ${bg[1]})`, color: card.ink || 'var(--ink)' }
  });
  // 氛围图案（种子化散布，轻巧无图片资源）
  const glyph = PATTERN_GLYPHS[card.pattern] || '✦';
  const pat = h('div', { class: 'pc-pattern' });
  let s = (card.seed || 7) >>> 0;
  const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
  const n = compact ? 5 : 8;
  for (let i = 0; i < n; i++) {
    pat.append(h('span', {
      style: {
        position: 'absolute', left: `${(rnd() * 92).toFixed(1)}%`, top: `${(rnd() * 86).toFixed(1)}%`,
        fontSize: `${(9 + rnd() * 13).toFixed(0)}px`, opacity: (0.18 + rnd() * 0.3).toFixed(2),
        transform: `rotate(${(rnd() * 60 - 30).toFixed(0)}deg)`
      }
    }, glyph));
  }
  el.append(pat, h('div', { class: 'pc-text' }, post.content));
  if (!compact) {
    el.append(h('div', { class: 'pc-meta' },
      card.emotion ? h('span', { class: 'pc-emo' }, `${card.emotion} · ${card.scene || ''}`) : null,
      h('span', { class: 'pc-hint' }, '👆 ', card.hint || '长按让它活过来')
    ));
  }
  // 作者装备的卡片边框皮肤（纯外观）
  const frameId = post.author?.equipped?.card_frame;
  const fp = frameId ? skinPayload(frameId) : null;
  if (fp?.gradient) {
    const frame = h('div', {
      class: 'pc-frame',
      style: {
        border: '2px solid transparent',
        background: `linear-gradient(135deg, ${fp.gradient[0]}, ${fp.gradient[1]}) border-box`,
        mask: 'linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)',
        WebkitMask: 'linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)',
        maskComposite: 'exclude', WebkitMaskComposite: 'xor',
        boxShadow: `0 0 18px ${fp.glow || 'transparent'}`
      }
    });
    el.append(frame);
    const decos = { sakura: ['🌸', '🌸'], bubbles: ['🫧', '🫧'], cloud: ['☁️', '🍦'], stars: ['✨', '🌙'], goldmoon: ['🌕', '✨'] }[fp.deco];
    if (decos) {
      el.append(h('div', { class: 'pc-frame' },
        h('span', { class: 'fd', style: { top: '-7px', left: '10px' } }, decos[0]),
        h('span', { class: 'fd', style: { bottom: '-7px', right: '10px' } }, decos[1])
      ));
    }
  }
  return el;
}

// ---- 长按 ----
export function longPress(el, fn, ms = 480) {
  let timer = null; let fired = false;
  const start = (e) => {
    fired = false;
    timer = setTimeout(() => { fired = true; fn(e); }, ms);
  };
  const cancel = () => { clearTimeout(timer); timer = null; };
  el.addEventListener('touchstart', start, { passive: true });
  el.addEventListener('touchmove', cancel, { passive: true });
  el.addEventListener('touchend', (e) => { if (fired) e.preventDefault(); cancel(); });
  el.addEventListener('mousedown', start);
  el.addEventListener('mousemove', cancel);
  el.addEventListener('mouseup', cancel);
  el.addEventListener('mouseleave', cancel);
  el.addEventListener('contextmenu', (e) => e.preventDefault());
}

// ---- 点赞爆裂 ----
export function burst(btn, color = '#ff8fb3') {
  const b = h('span', { class: 'burst' });
  for (let i = 0; i < 7; i++) {
    const a = (Math.PI * 2 * i) / 7;
    b.append(h('i', { style: { '--dx': `${Math.cos(a) * 22}px`, '--dy': `${Math.sin(a) * 22}px`, background: color } }));
  }
  btn.append(b);
  setTimeout(() => b.remove(), 650);
}

// ---- 吉祥物小句灵（SVG，会眨眼漂浮） ----
export function mascot(size = 92) {
  const el = h('div', { class: 'mascot' });
  el.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 100 100" fill="none">
    <defs><linearGradient id="mg${size}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#b9a6ff"/><stop offset="1" stop-color="#ff9ec6"/></linearGradient></defs>
    <path d="M50 9 C75 9 91 27 91 48 C91 73 71 89 50 91 C29 89 9 73 9 48 C9 27 25 9 50 9 Z" fill="url(#mg${size})" opacity="0.92"/>
    <path d="M50 9 C75 9 91 27 91 48" stroke="rgba(255,255,255,.65)" stroke-width="3" stroke-linecap="round"/>
    <circle class="eye" cx="38" cy="47" r="4.6" fill="#413a5c"/>
    <circle class="eye" cx="62" cy="47" r="4.6" fill="#413a5c"/>
    <circle cx="30" cy="56" r="4" fill="#ffb3cd" opacity=".75"/>
    <circle cx="70" cy="56" r="4" fill="#ffb3cd" opacity=".75"/>
    <path d="M43 60 Q50 66 57 60" stroke="#413a5c" stroke-width="3.4" fill="none" stroke-linecap="round"/>
    <path d="M48 4 Q50 -2 54 3 Q57 7 51 9 Q47 8 48 4 Z" fill="#9ee6c8"/>
  </svg>`;
  return el;
}

export function spinner() {
  return h('div', { class: 'empty' }, h('div', { class: 'mascot', style: { fontSize: '30px' } }, '🌸'), h('div', {}, '加载中…'));
}

export function emptyState(text, sub = '') {
  return h('div', { class: 'empty' }, mascot(72), h('div', { style: { marginTop: '10px' } }, text), sub ? h('div', { style: { fontSize: '11px', marginTop: '4px' } }, sub) : null);
}

export const rarityName = { normal: '普通', rare: '稀有', fine: '精致', epic: '史诗', legend: '传说', limited: '限定' };
export const fen = (f) => (f / 100).toFixed(f % 100 === 0 ? 0 : 1);
