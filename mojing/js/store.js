// 魔镜魔镜 · 修图参数状态（含本地持久化）
const KEY = 'mojing.params.v1';

export const DEFAULTS = {
  smooth: 0,        // 磨皮 0..1
  whiten: 0,        // 美白 0..1
  rosy: 0,          // 红润 0..1
  sharpen: 0,       // 锐化/清晰度 0..1
  brightness: 0,    // 亮度 -1..1
  contrast: 0,      // 对比度 -1..1
  saturation: 0,    // 饱和度 -1..1
  temperature: 0,   // 色温 -1..1
  vignette: 0,      // 暗角 0..1
  slimFace: 0,      // 瘦脸 0..1
  slimBody: 0,      // 瘦身 0..1
  filter: 'none',   // 滤镜 id
  filterStrength: 1 // 滤镜强度 0..1
};

export function createStore() {
  let state = { ...DEFAULTS };
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    state = { ...state, ...saved };
  } catch { /* ignore */ }

  const subs = new Set();
  let saveTimer = 0;

  function persist() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* 隐私模式忽略 */ }
    }, 250);
  }

  function emit() { subs.forEach((fn) => fn(state)); persist(); }

  return {
    get() { return state; },
    set(key, val) { state[key] = val; emit(); },
    patch(obj) { Object.assign(state, obj); emit(); },
    reset() { state = { ...DEFAULTS }; emit(); },
    subscribe(fn) { subs.add(fn); fn(state); return () => subs.delete(fn); }
  };
}
