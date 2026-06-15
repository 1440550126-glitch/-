// dolby-store · 可选的偏好持久化助手（与引擎解耦）
// 把用户的杜比设置存到 localStorage，并能一键套用到引擎实例。
// 引擎本身不依赖它；不需要持久化的项目可以完全忽略本文件。
//
//   import { DolbyAudio } from './dolby-audio.js';
//   import { loadPrefs, savePrefs, applyPrefs, snapshot } from './dolby-store.js';
//   const dolby = new DolbyAudio();
//   applyPrefs(dolby, loadPrefs());                 // 启动时恢复
//   // ...用户调整后：
//   savePrefs(snapshot(dolby));                     // 持久化当前状态

export const DEFAULT_PREFS = {
  enabled: true, preset: 'standard', intensity: 0.85,
  spatialMode: 'speakers', multiband: false, loudnessMatch: false
};
const KEY = 'dolby:prefs';

export function loadPrefs(key = KEY) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '{}');
    const p = { ...DEFAULT_PREFS, ...raw };
    p.intensity = Math.min(1, Math.max(0, +p.intensity || 0));
    if (p.spatialMode !== 'headphones') p.spatialMode = 'speakers';
    return p;
  } catch { return { ...DEFAULT_PREFS }; }
}

export function savePrefs(prefs, key = KEY) {
  try { localStorage.setItem(key, JSON.stringify({ ...DEFAULT_PREFS, ...prefs })); return true; }
  catch { return false; }     // 隐私模式/无 localStorage 时静默失败
}

/** 读取引擎当前状态为可持久化的 prefs 对象 */
export function snapshot(dolby) {
  return {
    enabled: dolby.enabled, preset: dolby.presetId, intensity: dolby.intensity,
    spatialMode: dolby.spatialMode, multiband: dolby.multiband, loudnessMatch: dolby.loudnessMatch
  };
}

/** 把 prefs 套用到引擎实例 */
export function applyPrefs(dolby, prefs = loadPrefs(), { instant = true } = {}) {
  dolby.setPreset(prefs.preset, instant);
  dolby.setSpatialMode(prefs.spatialMode, instant);
  dolby.setMultiband(!!prefs.multiband, instant);
  dolby.setIntensity(prefs.intensity, instant);
  dolby.setLoudnessMatch(!!prefs.loudnessMatch);
  dolby.setEnabled(prefs.enabled !== false, instant);
  return dolby;
}

/** 包一层引擎：任意 set* 调用后自动持久化（节流写入） */
export function autosave(dolby, key = KEY, delay = 400) {
  let timer = null;
  const flush = () => { timer = null; savePrefs(snapshot(dolby), key); };
  const schedule = () => { if (timer) clearTimeout(timer); timer = setTimeout(flush, delay); };
  for (const m of ['setPreset', 'setIntensity', 'setEnabled', 'setSpatialMode', 'setMultiband', 'setLoudnessMatch', 'enable', 'bypass']) {
    const orig = dolby[m].bind(dolby);
    dolby[m] = (...a) => { const r = orig(...a); schedule(); return r; };
  }
  return dolby;
}

// ---- 预设导入/导出（分享 / 备份 / 跨设备迁移） ----
const validPreset = (p) => p && typeof p.id === 'string' && p.p && typeof p.p === 'object';

/** 单个预设 → JSON 文本 */
export function exportPreset(preset, pretty = true) { return JSON.stringify(preset, null, pretty ? 2 : 0); }
/** JSON 文本/对象 → 预设（校验结构） */
export function importPreset(json) {
  const p = typeof json === 'string' ? JSON.parse(json) : json;
  if (!validPreset(p)) throw new Error('无效预设：需要 { id, p }');
  return p;
}
/** 多个预设 → JSON 文本 */
export function exportPresets(presets, pretty = true) { return JSON.stringify(presets, null, pretty ? 2 : 0); }
/** JSON 文本/数组 → 预设数组（逐个校验） */
export function importPresets(json) {
  const arr = typeof json === 'string' ? JSON.parse(json) : json;
  if (!Array.isArray(arr)) throw new Error('应为预设数组');
  return arr.map(importPreset);
}
