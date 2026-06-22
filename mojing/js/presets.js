// 魔镜魔镜 · 一键美颜预设 / 滤镜 / 自定义滑杆配置
import { DEFAULTS } from './store.js';

// 滤镜：id 必须与着色器 applyFilter 的编号一致
export const FILTERS = [
  { id: 'none',      name: '原图',   code: 0 },
  { id: 'fresh',     name: '清新',   code: 1 },
  { id: 'japan',     name: '日系',   code: 2 },
  { id: 'retro',     name: '复古',   code: 3 },
  { id: 'bw',        name: '黑白',   code: 4 },
  { id: 'film',      name: '电影感', code: 5 },
  { id: 'coolwhite', name: '冷白皮', code: 6 },
  { id: 'warm',      name: '暖阳',   code: 7 }
];
export const filterCode = (id) => (FILTERS.find((f) => f.id === id) || FILTERS[0]).code;

// 一键美颜预设：每档同时设置磨皮/美白/瘦身等多个维度
export const PRESETS = [
  { id: 'origin', name: '原图', emoji: '🚫', params: { ...DEFAULTS } },
  {
    id: 'natural', name: '自然', emoji: '🌿',
    params: { smooth: 0.35, whiten: 0.15, rosy: 0.15, brightness: 0.05, saturation: 0.05, sharpen: 0.12 }
  },
  {
    id: 'delicate', name: '精致', emoji: '✨',
    params: { smooth: 0.55, whiten: 0.30, rosy: 0.25, brightness: 0.08, saturation: 0.08, sharpen: 0.15, slimFace: 0.18 }
  },
  {
    id: 'net', name: '网红', emoji: '💖',
    params: { smooth: 0.72, whiten: 0.45, rosy: 0.30, brightness: 0.12, saturation: 0.12, temperature: 0.06, sharpen: 0.10, slimFace: 0.30, slimBody: 0.15 }
  },
  {
    id: 'mood', name: '氛围感', emoji: '🎬',
    params: { smooth: 0.40, whiten: 0.20, rosy: 0.20, contrast: 0.15, temperature: 0.12, vignette: 0.28, filter: 'film', filterStrength: 0.6 }
  },
  {
    id: 'cool', name: '冷白皮', emoji: '❄️',
    params: { smooth: 0.50, whiten: 0.42, rosy: 0.10, brightness: 0.10, temperature: -0.18, saturation: -0.05, filter: 'coolwhite', filterStrength: 0.7, slimFace: 0.15 }
  }
];

// 把预设按强度（0..1.5）应用到 store。强度缩放所有数值维度，但保留滤镜选择。
export function applyPreset(store, preset, intensity = 1) {
  const base = { ...DEFAULTS };
  for (const [k, v] of Object.entries(preset.params)) {
    if (typeof v === 'number') base[k] = Math.max(-1, Math.min(1, v * intensity));
    else base[k] = v; // filter id 等非数值
  }
  if (preset.params.filterStrength != null) {
    base.filterStrength = Math.min(1, preset.params.filterStrength * Math.max(0.4, intensity));
  }
  store.patch(base);
}

// 自定义修图滑杆：分组 + 量程（min<0 表示双向，中点为 0）
export const SLIDERS = [
  { group: '美颜', items: [
    { key: 'smooth',  name: '磨皮', min: 0, max: 1 },
    { key: 'whiten',  name: '美白', min: 0, max: 1 },
    { key: 'rosy',    name: '红润', min: 0, max: 1 },
    { key: 'sharpen', name: '清晰', min: 0, max: 1 }
  ]},
  { group: '美型', items: [
    { key: 'slimFace', name: '瘦脸', min: 0, max: 1 },
    { key: 'slimBody', name: '瘦身', min: 0, max: 1 }
  ]},
  { group: '调色', items: [
    { key: 'brightness',  name: '亮度', min: -1, max: 1 },
    { key: 'contrast',    name: '对比', min: -1, max: 1 },
    { key: 'saturation',  name: '饱和', min: -1, max: 1 },
    { key: 'temperature', name: '色温', min: -1, max: 1 },
    { key: 'vignette',    name: '暗角', min: 0,  max: 1 }
  ]}
];
