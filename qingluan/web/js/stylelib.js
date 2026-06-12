// 风格库选择器（项目页 / 画布页共用）
import { GET } from './api.js';
import { h, icon, modal, stagger } from './ui.js';

let cache = null;
export async function loadStyles() {
  if (!cache) cache = await GET('/api/styles');
  return cache;
}

function hues(name) {
  let x = 0;
  for (const ch of name) x = (x * 31 + ch.codePointAt(0)) >>> 0;
  return [x % 360, (x % 360 + 48) % 360];
}

/** 展示用短名：预设名原样，自定义提示词截断 */
export const shortStyle = (style) => {
  const s = String(style || '').trim();
  if (!s) return '默认风格';
  return s.length > 9 ? s.slice(0, 8) + '…' : s;
};

export async function openStylePicker({ current = '', onPick }) {
  const { cats, styles } = await loadStyles();
  let cat = '';
  const body = h('div');
  const grid = h('div', { class: 'style-grid' });

  const pick = (value, close) => { onPick?.(value); close(); };

  const m = modal({
    title: h('span', { html: `${icon('wand')} 风格库 <small style="font-weight:400;color:var(--ink3);font-size:12px;margin-left:6px">选中后，新生成的图与视频自动套用该风格提示词</small>` }),
    wide: true,
    body,
    actions: []
  });

  const tabs = h('div', { class: 'tabs', style: { marginBottom: '14px' } });
  const tabBtn = (id, label) => h('button', {
    class: `tab ${cat === id ? 'on' : ''}`,
    onclick: (e) => { cat = id; tabs.querySelectorAll('.tab').forEach((t) => t.classList.remove('on')); e.currentTarget.classList.add('on'); renderGrid(); }
  }, label);
  tabs.append(tabBtn('', '全部'), ...cats.map((c) => tabBtn(c.id, c.name)));

  function customCard() {
    return h('div', { class: 'style-card custom', onclick: () => {
      const isPreset = styles.some((s) => s.name === current);
      const ta = h('textarea', { class: 'textarea', rows: 4, value: isPreset ? '' : current, placeholder: '自定义风格提示词，例如：美式复古好莱坞胶片质感，琥珀色调，高对比布光…' });
      body.innerHTML = '';
      body.append(
        h('label', { class: 'fld' }, '自定义风格提示词'), ta,
        h('div', { class: 'm-actions' },
          h('button', { class: 'btn', onclick: () => { body.innerHTML = ''; body.append(tabs, grid); } }, '返回'),
          h('button', { class: 'btn accent', onclick: () => pick(ta.value.trim(), m.close) }, '使用该风格')));
      ta.focus();
    } }, h('span', { html: icon('pencil', 22) }), h('b', { style: { fontSize: '13px' } }, '自定义风格提示词'));
  }

  function renderGrid() {
    grid.innerHTML = '';
    grid.append(
      h('div', { class: `style-card custom ${!current ? 'on' : ''}`, onclick: () => pick('', m.close) },
        h('span', { html: icon('x', 20) }), h('b', { style: { fontSize: '13px' } }, '默认（不指定风格）')),
      customCard());
    for (const s of styles.filter((s) => !cat || s.cat === cat)) {
      const [h1, h2] = hues(s.name);
      grid.append(h('div', {
        class: `style-card ${current === s.name ? 'on' : ''}`,
        title: s.prompt,
        style: { background: `linear-gradient(135deg, hsl(${h1},48%,30%), hsl(${h2},55%,52%))` },
        onclick: () => pick(s.name, m.close)
      },
        h('span', { class: 'cat' }, cats.find((c) => c.id === s.cat)?.name || s.cat),
        current === s.name ? h('span', { class: 'sel-mark', html: icon('check', 15) }) : null,
        h('b', {}, s.name)));
    }
    stagger(grid, 18);
  }

  renderGrid();
  body.append(tabs, grid);
}
