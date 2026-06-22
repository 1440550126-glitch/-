// 魔镜魔镜 · 界面控件（标签页 / 预设·滤镜胶囊 / 自定义滑杆 / 结果浮层 / 提示）
import { PRESETS, FILTERS, SLIDERS } from './presets.js';

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, cls, txt) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
};

export function createUI(store, cb) {
  // cb: { applyPreset(preset, intensity), getPresetSelection() }
  const sliderInputs = {};   // key -> [<input>...]（同一参数可能出现在多个标签页）
  const sliderVals = {};     // key -> [<span>...]
  let activePresetId = 'origin';
  let presetIntensity = 1;

  const tabContent = $('#tab-content');
  const panels = {};

  // —— 通用滑杆 ——
  function slider(key, name, min, max) {
    const row = el('label', 'slider');
    const head = el('div', 'slider-head');
    head.append(el('span', 'slider-name', name));
    const val = el('span', 'slider-val', '0');
    head.append(val);
    const input = el('input');
    input.type = 'range';
    input.min = String(Math.round(min * 100));
    input.max = String(Math.round(max * 100));
    input.step = '1';
    input.dataset.bipolar = min < 0 ? '1' : '0';
    input.addEventListener('input', () => {
      store.set(key, Number(input.value) / 100);
    });
    row.append(head, input);
    (sliderInputs[key] ||= []).push(input);
    (sliderVals[key] ||= []).push(val);
    return row;
  }

  // —— 胶囊（预设/滤镜）——
  function chip(label, emoji, onClick) {
    const b = el('button', 'chip');
    if (emoji) b.append(el('span', 'chip-emoji', emoji));
    b.append(el('span', 'chip-label', label));
    b.addEventListener('click', onClick);
    return b;
  }

  // 美颜：一键预设 + 强度
  function buildBeauty() {
    const wrap = el('div', 'tab-panel');
    const row = el('div', 'chip-row');
    PRESETS.forEach((p) => {
      const c = chip(p.name, p.emoji, () => {
        activePresetId = p.id;
        cb.applyPreset(p, presetIntensity);
        refresh();
      });
      c.dataset.preset = p.id;
      row.append(c);
    });
    const intensity = el('label', 'slider strength');
    const head = el('div', 'slider-head');
    head.append(el('span', 'slider-name', '一键强度'));
    const val = el('span', 'slider-val', '100%');
    head.append(val);
    const inp = el('input'); inp.type = 'range'; inp.min = '0'; inp.max = '150'; inp.value = '100';
    inp.addEventListener('input', () => {
      presetIntensity = Number(inp.value) / 100;
      val.textContent = inp.value + '%';
      const p = PRESETS.find((x) => x.id === activePresetId);
      if (p && p.id !== 'origin') { cb.applyPreset(p, presetIntensity); refresh(); }
    });
    intensity.append(head, inp);
    wrap.append(row, intensity);
    return wrap;
  }

  // 滤镜：色调胶囊 + 强度
  function buildFilter() {
    const wrap = el('div', 'tab-panel');
    const row = el('div', 'chip-row');
    FILTERS.forEach((f) => {
      const c = chip(f.name, '', () => { store.set('filter', f.id); refresh(); });
      c.dataset.filter = f.id;
      row.append(c);
    });
    wrap.append(row, slider('filterStrength', '滤镜强度', 0, 1));
    return wrap;
  }

  // 瘦身：一键瘦身 + 瘦脸/瘦身滑杆
  function buildSlim() {
    const wrap = el('div', 'tab-panel');
    const actions = el('div', 'chip-row');
    const one = chip('一键瘦身', '🪄', () => { store.patch({ slimFace: 0.30, slimBody: 0.18 }); refresh(); });
    one.classList.add('primary');
    const off = chip('关闭', '', () => { store.patch({ slimFace: 0, slimBody: 0 }); refresh(); });
    actions.append(one, off);
    wrap.append(actions, slider('slimFace', '瘦脸', 0, 1), slider('slimBody', '瘦身', 0, 1));
    const tip = el('p', 'tip', '把人/脸放在画面中间，瘦身效果最自然');
    wrap.append(tip);
    return wrap;
  }

  // 自定义：分组滑杆 + 恢复默认
  function buildCustom() {
    const wrap = el('div', 'tab-panel custom');
    SLIDERS.forEach((g) => {
      wrap.append(el('div', 'group-title', g.group));
      g.items.forEach((it) => wrap.append(slider(it.key, it.name, it.min, it.max)));
    });
    const reset = el('button', 'reset-btn', '恢复默认');
    reset.addEventListener('click', () => { store.reset(); activePresetId = 'origin'; refresh(); });
    wrap.append(reset);
    return wrap;
  }

  panels.beauty = buildBeauty();
  panels.filter = buildFilter();
  panels.slim = buildSlim();
  panels.custom = buildCustom();
  Object.values(panels).forEach((p) => { p.hidden = true; tabContent.append(p); });

  function showTab(name) {
    Object.entries(panels).forEach(([k, p]) => { p.hidden = k !== name; });
    document.querySelectorAll('.tabs button').forEach((b) => {
      b.classList.toggle('active', b.dataset.tab === name);
    });
  }

  // —— 把 store 状态反映到所有控件 ——
  function refresh() {
    const s = store.get();
    for (const [key, inputs] of Object.entries(sliderInputs)) {
      const v = s[key];
      const text = inputs[0].dataset.bipolar === '1'
        ? (v > 0 ? '+' : '') + Math.round(v * 100)
        : (key === 'filterStrength' ? Math.round(v * 100) + '%' : String(Math.round(v * 100)));
      inputs.forEach((inp) => { inp.value = String(Math.round(v * 100)); });
      (sliderVals[key] || []).forEach((span) => { span.textContent = text; });
    }
    document.querySelectorAll('[data-preset]').forEach((b) => {
      b.classList.toggle('active', b.dataset.preset === activePresetId);
    });
    document.querySelectorAll('[data-filter]').forEach((b) => {
      b.classList.toggle('active', b.dataset.filter === s.filter);
    });
  }

  store.subscribe(refresh);

  // —— 顶部提示 ——
  let toastTimer = 0;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 1800);
  }

  // —— 结果浮层（拍照/录像后预览）——
  function showResult(item, handlers) {
    const box = $('#result');
    box.innerHTML = '';
    const media = item.kind === 'photo' ? el('img', 'result-media') : el('video', 'result-media');
    media.src = item.url;
    if (item.kind === 'video') { media.controls = true; media.playsInline = true; media.loop = true; media.play?.().catch(() => {}); }
    const bar = el('div', 'result-bar');
    const retake = el('button', 'rbtn', '重拍');
    retake.addEventListener('click', () => { hideResult(); handlers.onRetake?.(); });
    const save = el('button', 'rbtn primary', '保存');
    save.addEventListener('click', () => handlers.onSave?.());
    const share = el('button', 'rbtn', '分享');
    share.addEventListener('click', () => handlers.onShare?.());
    bar.append(retake, save, share);
    box.append(media, bar);
    box.hidden = false;
  }
  function hideResult() {
    const box = $('#result');
    box.hidden = true;
    const v = box.querySelector('video');
    if (v) { v.pause(); }
    box.innerHTML = '';
  }

  function setThumb(url) {
    const t = $('#thumb');
    t.style.backgroundImage = url ? `url(${url})` : '';
    t.classList.toggle('has', !!url);
  }

  showTab('beauty');
  refresh();

  return { showTab, toast, showResult, hideResult, setThumb, refresh,
    get activePresetId() { return activePresetId; } };
}
