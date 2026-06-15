// ============================================================
// 杜比风格沉浸音效引擎（Dolby-like immersive master）
// 纯 Web Audio 实时处理，零音频资源依赖：
//   低频增强（低架 + 次谐波激励器）→ 中频清晰 + 高频空气感
//   → 虚拟环绕展宽（Lauridsen 伪立体声，单声道下可完美回落不抵消）
//   → 空间混响（实时合成立体声脉冲响应）→ 动态压缩（响度/胶水）
//   → 软削波限制（防过载）→ 干湿混合（强度可调 / 一键旁通）
// 作为母带处理器挂在声音总线后：source → master →〔Dolby〕→ destination
// ============================================================

// 预设：每一档对应一种听感性格（参数即"调音"）
export const DOLBY_PRESETS = [
  {
    id: 'standard', label: '标准增强', desc: '均衡的沉浸感，日常聆听',
    p: {
      preGain: 1.0,
      bass: { freq: 110, gain: 5 }, bassDrive: { amount: 0.18, mix: 0.35 },
      mid: { freq: 2600, gain: 2.0, q: 0.9 }, air: { freq: 9000, gain: 3.5 },
      width: 0.55, haasMs: 12, surroundDepth: 2.0, surroundRate: 0.09,
      reverb: { mix: 0.16, seconds: 1.8, decay: 2.6 },
      comp: { threshold: -20, ratio: 3, knee: 24, attack: 0.012, release: 0.22 },
      outGain: 1.12
    }
  },
  {
    id: 'cinema', label: '影院环绕', desc: '大空间环绕 · 重低音 · 戏剧动态',
    p: {
      preGain: 1.0,
      bass: { freq: 95, gain: 7.5 }, bassDrive: { amount: 0.28, mix: 0.5 },
      mid: { freq: 2200, gain: 1.4, q: 0.8 }, air: { freq: 11000, gain: 4.5 },
      width: 0.85, haasMs: 18, surroundDepth: 4.5, surroundRate: 0.07,
      reverb: { mix: 0.30, seconds: 3.0, decay: 3.4 },
      comp: { threshold: -24, ratio: 4, knee: 26, attack: 0.008, release: 0.26 },
      outGain: 1.18
    }
  },
  {
    id: 'music', label: '音乐厅', desc: '低音扎实 · 高音通透 · 适合旋律',
    p: {
      preGain: 1.0,
      bass: { freq: 120, gain: 6 }, bassDrive: { amount: 0.22, mix: 0.4 },
      mid: { freq: 3000, gain: 2.6, q: 1.0 }, air: { freq: 12000, gain: 5 },
      width: 0.7, haasMs: 14, surroundDepth: 2.6, surroundRate: 0.1,
      reverb: { mix: 0.18, seconds: 1.6, decay: 2.2 },
      comp: { threshold: -18, ratio: 3.5, knee: 20, attack: 0.006, release: 0.18 },
      outGain: 1.15
    }
  },
  {
    id: 'night', label: '夜深人静', desc: '压缩动态 · 收敛低音 · 不扰人',
    p: {
      preGain: 0.95,
      bass: { freq: 90, gain: 2 }, bassDrive: { amount: 0.06, mix: 0.2 },
      mid: { freq: 2400, gain: 1.6, q: 0.9 }, air: { freq: 8000, gain: 2.5 },
      width: 0.4, haasMs: 10, surroundDepth: 1.2, surroundRate: 0.08,
      reverb: { mix: 0.12, seconds: 1.2, decay: 1.8 },
      comp: { threshold: -34, ratio: 6, knee: 30, attack: 0.004, release: 0.32 },
      outGain: 1.0
    }
  },
  {
    id: 'vocal', label: '人声清晰', desc: '突出中高频 · 干净近场 · 适合旁白',
    p: {
      preGain: 1.0,
      bass: { freq: 100, gain: 1.5 }, bassDrive: { amount: 0.04, mix: 0.15 },
      mid: { freq: 3200, gain: 4, q: 1.1 }, air: { freq: 10000, gain: 4 },
      width: 0.3, haasMs: 8, surroundDepth: 0.8, surroundRate: 0.1,
      reverb: { mix: 0.08, seconds: 1.0, decay: 1.6 },
      comp: { threshold: -22, ratio: 3, knee: 22, attack: 0.01, release: 0.2 },
      outGain: 1.1
    }
  }
];

export const DEFAULT_DOLBY = { on: true, preset: 'standard', intensity: 0.85 };
const PREF_KEY = 'jl_dolby';

export function loadDolbyPref() {
  try {
    const raw = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
    const pref = { ...DEFAULT_DOLBY, ...raw };
    if (!DOLBY_PRESETS.some((x) => x.id === pref.preset)) pref.preset = DEFAULT_DOLBY.preset;
    pref.intensity = Math.min(1, Math.max(0, +pref.intensity || 0));
    return pref;
  } catch { return { ...DEFAULT_DOLBY }; }
}
export function saveDolbyPref(pref) {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(pref)); } catch { /* 隐私模式忽略 */ }
}
export const presetById = (id) => DOLBY_PRESETS.find((x) => x.id === id) || DOLBY_PRESETS[0];

// 软饱和/限制曲线（tanh 形），k 越大越"硬"
function shaperCurve(k, n = 2048) {
  const c = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * 2 - 1;
    c[i] = Math.tanh(k * x) / Math.tanh(k);
  }
  return c;
}

// 合成立体声混响脉冲响应：预延迟 + 早期反射 + 指数衰减噪声，左右轻微解相关
const irCache = new Map();
function makeIR(ctx, seconds, decay) {
  const key = `${seconds}|${decay}|${ctx.sampleRate}`;
  if (irCache.has(key)) return irCache.get(key);
  const rate = ctx.sampleRate;
  const len = Math.max(1, Math.floor(seconds * rate));
  const buf = ctx.createBuffer(2, len, rate);
  const pre = Math.floor(rate * 0.02);                       // 20ms 预延迟
  const refl = [0.03, 0.047, 0.069, 0.093];                  // 早期反射时刻（秒）
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    const seed = ch ? 1.7 : 1.0;
    for (let i = pre; i < len; i++) {
      const t = (i - pre) / len;
      d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay) * seed * 0.6;
    }
    for (const r of refl) {                                   // 叠加早期反射
      const idx = pre + Math.floor(r * rate * (ch ? 1.06 : 1));
      if (idx < len) d[idx] += (ch ? -1 : 1) * 0.5 * Math.pow(0.6, refl.indexOf(r));
    }
  }
  irCache.set(key, buf);
  return buf;
}

export class DolbyProcessor {
  constructor(ctx) {
    this.ctx = ctx;
    const N = (f) => ctx[f].bind(ctx);
    const Gain = N('createGain'), Filt = N('createBiquadFilter'), Delay = N('createDelay');

    // —— 节点 ——
    this.input = Gain();                 // 总线入口（外部连这里）
    this.output = Gain();                // 连 destination
    this.pre = Gain();

    // 音色：低架 → 中频峰 → 高架（串联）
    this.low = Filt(); this.low.type = 'lowshelf';
    this.midEq = Filt(); this.midEq.type = 'peaking';
    this.high = Filt(); this.high.type = 'highshelf';
    this.tone = Gain();

    // 次谐波低频激励（并联）：低通 → 饱和 → 增益
    this.bassLP = Filt(); this.bassLP.type = 'lowpass'; this.bassLP.frequency.value = 130;
    this.bassSat = ctx.createWaveShaper();
    this.bassGain = Gain(); this.bassGain.gain.value = 0;

    // 虚拟环绕展宽（Lauridsen 伪立体声，单声道完美回落）
    this.splitDelay = Delay(0.05);
    this.posW = Gain(); this.negW = Gain(); this.negW.gain.value = 0; this.posW.gain.value = 0;
    this.merger = ctx.createChannelMerger(2);
    this.directL = Gain(); this.directR = Gain();
    // 环绕缓慢移动的 LFO（调制延迟时间，营造"声场在动"的包围感）
    this.lfo = ctx.createOscillator();
    this.lfoGain = Gain(); this.lfoGain.gain.value = 0;
    this.lfo.connect(this.lfoGain); this.lfoGain.connect(this.splitDelay.delayTime);

    // 空间混响（并联湿声）
    this.convolver = ctx.createConvolver();
    this.reverbGain = Gain(); this.reverbGain.gain.value = 0;

    // 动态 + 限制
    this.comp = ctx.createDynamicsCompressor();
    this.limiter = ctx.createWaveShaper(); this.limiter.curve = shaperCurve(2.2); this.limiter.oversample = '4x';
    this.makeup = Gain();

    // 干湿混合（强度 / 旁通）
    this.dry = Gain(); this.wet = Gain();

    // —— 连线 ——
    this.input.connect(this.pre);
    // 音色串联
    this.pre.connect(this.low); this.low.connect(this.midEq); this.midEq.connect(this.high); this.high.connect(this.tone);
    // 低频激励并联汇入 tone
    this.pre.connect(this.bassLP); this.bassLP.connect(this.bassSat); this.bassSat.connect(this.bassGain); this.bassGain.connect(this.tone);

    // 展宽：tone → 直达(L/R) + 延迟支路(±) → 立体声合并
    this.tone.connect(this.directL); this.directL.connect(this.merger, 0, 0);
    this.tone.connect(this.directR); this.directR.connect(this.merger, 0, 1);
    this.tone.connect(this.splitDelay);
    this.splitDelay.connect(this.posW); this.posW.connect(this.merger, 0, 0);   // 左 = 直达 + 延迟
    this.splitDelay.connect(this.negW); this.negW.connect(this.merger, 0, 1);   // 右 = 直达 − 延迟

    const preComp = Gain();
    this.merger.connect(preComp);
    // 混响并联（取 tone，立体声 IR）
    this.tone.connect(this.convolver); this.convolver.connect(this.reverbGain); this.reverbGain.connect(preComp);

    preComp.connect(this.comp); this.comp.connect(this.limiter); this.limiter.connect(this.makeup);
    this.makeup.connect(this.wet); this.wet.connect(this.output);
    this.input.connect(this.dry); this.dry.connect(this.output);

    try { this.lfo.start(); } catch { /* 已启动 */ }

    this._pref = loadDolbyPref();
    this.applyPreset(this._pref.preset, true);
    this.setIntensity(this._pref.intensity, true);
    this.setEnabled(this._pref.on, true);
  }

  connect(dest) { this.output.connect(dest); return this; }

  applyPreset(id, instant = false) {
    const ctx = this.ctx, t = ctx.currentTime, tc = instant ? 0.001 : 0.08;
    const p = presetById(id).p;
    this._presetParams = p;
    const set = (param, v) => param.setTargetAtTime(v, t, tc);

    set(this.pre.gain, p.preGain);
    this.low.frequency.setTargetAtTime(p.bass.freq, t, tc); set(this.low.gain, p.bass.gain);
    this.midEq.frequency.setTargetAtTime(p.mid.freq, t, tc); this.midEq.Q.setTargetAtTime(p.mid.q, t, tc); set(this.midEq.gain, p.mid.gain);
    this.high.frequency.setTargetAtTime(p.air.freq, t, tc); set(this.high.gain, p.air.gain);

    this.bassSat.curve = shaperCurve(1 + p.bassDrive.amount * 8);
    set(this.bassGain.gain, p.bassDrive.mix);

    // 展宽：directL/R 保持 1，±支路用 width 调制；单声道 L+R 时延迟支路互相抵消
    set(this.directL.gain, 1); set(this.directR.gain, 1);
    set(this.posW.gain, p.width); set(this.negW.gain, -p.width);
    this.splitDelay.delayTime.setTargetAtTime(p.haasMs / 1000, t, tc);
    this.lfo.frequency.setTargetAtTime(p.surroundRate, t, tc);
    set(this.lfoGain.gain, (p.surroundDepth / 1000));

    this.convolver.buffer = makeIR(ctx, p.reverb.seconds, p.reverb.decay);
    this._reverbMix = p.reverb.mix;
    set(this.reverbGain.gain, this._enabled ? p.reverb.mix : 0);

    this.comp.threshold.setTargetAtTime(p.comp.threshold, t, tc);
    this.comp.ratio.setTargetAtTime(p.comp.ratio, t, tc);
    this.comp.knee.setTargetAtTime(p.comp.knee, t, tc);
    this.comp.attack.setTargetAtTime(p.comp.attack, t, tc);
    this.comp.release.setTargetAtTime(p.comp.release, t, tc);
    set(this.makeup.gain, p.outGain);

    this._pref.preset = id; saveDolbyPref(this._pref);
  }

  // 强度：处理链的干湿比（0=原声，1=满处理）
  setIntensity(v, instant = false) {
    v = Math.min(1, Math.max(0, v));
    this._intensity = v;
    this._pref.intensity = v; saveDolbyPref(this._pref);
    this._applyMix(instant);
  }

  setEnabled(on, instant = false) {
    this._enabled = !!on;
    this._pref.on = this._enabled; saveDolbyPref(this._pref);
    this._applyMix(instant);
  }

  _applyMix(instant = false) {
    const t = this.ctx.currentTime, tc = instant ? 0.001 : 0.12;
    const wet = this._enabled ? this._intensity : 0;
    // 等功率交叉淡化，避免开关时音量跳变
    this.wet.gain.setTargetAtTime(Math.sin(wet * Math.PI / 2), t, tc);
    this.dry.gain.setTargetAtTime(Math.cos(wet * Math.PI / 2), t, tc);
  }

  get enabled() { return this._enabled; }
  get intensity() { return this._intensity; }
  get presetId() { return this._pref.preset; }

  dispose() {
    try { this.lfo.stop(); } catch { /* ok */ }
    for (const n of [this.input, this.output, this.pre, this.low, this.midEq, this.high, this.tone,
      this.bassLP, this.bassSat, this.bassGain, this.splitDelay, this.posW, this.negW, this.merger,
      this.directL, this.directR, this.lfo, this.lfoGain, this.convolver, this.reverbGain,
      this.comp, this.limiter, this.makeup, this.dry, this.wet]) {
      try { n.disconnect(); } catch { /* ok */ }
    }
  }
}
