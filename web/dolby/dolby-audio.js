// ============================================================
// dolby-audio · 杜比风格沉浸音效引擎（独立 / 零依赖 / 纯 Web Audio）
// ------------------------------------------------------------
// 一个与框架无关的母带处理器，可挂在任意音频源后端：
//   <audio>/<video> 元素、AudioBufferSource、麦克风、或任意 AudioNode。
// 处理链：
//   低频增强（低架 + 次谐波激励器）→ 中频清晰 + 高频空气感
//   → 立体声声场展宽（M/S 处理，保留并增强原始立体声，单声道安全）
//   → 缓慢声场"呼吸"（LFO 调制 Side，营造环绕移动感）
//   → 空间混响（实时合成立体声脉冲响应）
//   → 声场渲染：扬声器立体声 / 耳机 HRTF 双耳虚拟环绕（虚拟前置+环绕音箱）
//   → 动态压缩（响度/胶水）→ 软削波限制（防过载）→ 干湿混合（强度可调 / 一键旁通）
//
// 用法：
//   import { DolbyAudio } from './dolby-audio.js';
//   const dolby = new DolbyAudio({ preset: 'cinema' });
//   dolby.attachMedia(document.querySelector('audio'));   // 接 <audio>
//   await dolby.resume();                                  // 用户手势后唤醒
//   dolby.setIntensity(0.9); dolby.setSpatialMode('headphones');
// ============================================================

// ---- 预设：每一档对应一种听感性格 ----
// width：Side（声道差）增益倍数，1=原始立体声宽度，>1 更宽，<1 更窄，0=单声道
export const DOLBY_PRESETS = [
  { id: 'standard', label: '标准增强', desc: '均衡的沉浸感，日常聆听', p: {
    preGain: 1.0, bass: { freq: 110, gain: 5 }, bassDrive: { amount: 0.18, mix: 0.32 },
    mid: { freq: 2600, gain: 2.0, q: 0.9 }, air: { freq: 9000, gain: 3.5 },
    width: 1.3, motion: { rate: 0.08, depth: 0.06 }, reverb: { mix: 0.16, seconds: 1.8, decay: 2.6 },
    comp: { threshold: -20, ratio: 3, knee: 24, attack: 0.012, release: 0.22 }, outGain: 1.1 } },
  { id: 'cinema', label: '影院环绕', desc: '大空间环绕 · 重低音 · 戏剧动态', p: {
    preGain: 1.0, bass: { freq: 95, gain: 7.5 }, bassDrive: { amount: 0.28, mix: 0.45 },
    mid: { freq: 2200, gain: 1.4, q: 0.8 }, air: { freq: 11000, gain: 4.5 },
    width: 1.65, motion: { rate: 0.06, depth: 0.14 }, reverb: { mix: 0.30, seconds: 3.0, decay: 3.4 },
    comp: { threshold: -24, ratio: 4, knee: 26, attack: 0.008, release: 0.26 }, outGain: 1.16 } },
  { id: 'music', label: '音乐厅', desc: '低音扎实 · 高音通透 · 适合旋律', p: {
    preGain: 1.0, bass: { freq: 120, gain: 6 }, bassDrive: { amount: 0.22, mix: 0.38 },
    mid: { freq: 3000, gain: 2.6, q: 1.0 }, air: { freq: 12000, gain: 5 },
    width: 1.45, motion: { rate: 0.1, depth: 0.08 }, reverb: { mix: 0.18, seconds: 1.6, decay: 2.2 },
    comp: { threshold: -18, ratio: 3.5, knee: 20, attack: 0.006, release: 0.18 }, outGain: 1.13 } },
  { id: 'night', label: '夜深人静', desc: '压缩动态 · 收敛低音 · 不扰人', p: {
    preGain: 0.95, bass: { freq: 90, gain: 2 }, bassDrive: { amount: 0.06, mix: 0.18 },
    mid: { freq: 2400, gain: 1.6, q: 0.9 }, air: { freq: 8000, gain: 2.5 },
    width: 1.12, motion: { rate: 0.08, depth: 0.03 }, reverb: { mix: 0.12, seconds: 1.2, decay: 1.8 },
    comp: { threshold: -34, ratio: 6, knee: 30, attack: 0.004, release: 0.32 }, outGain: 1.0 } },
  { id: 'vocal', label: '人声清晰', desc: '突出中高频 · 干净近场 · 适合旁白/播客', p: {
    preGain: 1.0, bass: { freq: 100, gain: 1.5 }, bassDrive: { amount: 0.04, mix: 0.12 },
    mid: { freq: 3200, gain: 4, q: 1.1 }, air: { freq: 10000, gain: 4 },
    width: 1.0, motion: { rate: 0, depth: 0 }, reverb: { mix: 0.07, seconds: 1.0, decay: 1.6 },
    comp: { threshold: -22, ratio: 3, knee: 22, attack: 0.01, release: 0.2 }, outGain: 1.08 } }
];
export const presetById = (id) => DOLBY_PRESETS.find((x) => x.id === id) || DOLBY_PRESETS[0];
/** 注册/覆盖一个自定义预设（按 id 去重），返回该预设 */
export function registerPreset(preset) {
  if (!preset || !preset.id || !preset.p) throw new Error('preset 需要 { id, p }');
  const i = DOLBY_PRESETS.findIndex((x) => x.id === preset.id);
  if (i >= 0) DOLBY_PRESETS[i] = preset; else DOLBY_PRESETS.push(preset);
  return preset;
}

// 软饱和/限制曲线（tanh 形）
function shaperCurve(k, n = 2048) {
  const c = new Float32Array(n);
  for (let i = 0; i < n; i++) { const x = (i / (n - 1)) * 2 - 1; c[i] = Math.tanh(k * x) / Math.tanh(k); }
  return c;
}

// 合成立体声混响脉冲响应：预延迟 + 早期反射 + 指数衰减噪声，左右解相关
const irCache = new WeakMap();
export function createImpulseResponse(ctx, seconds, decay) {
  let perCtx = irCache.get(ctx);
  if (!perCtx) { perCtx = new Map(); irCache.set(ctx, perCtx); }
  const key = `${seconds}|${decay}`;
  if (perCtx.has(key)) return perCtx.get(key);
  const rate = ctx.sampleRate, len = Math.max(1, Math.floor(seconds * rate));
  const buf = ctx.createBuffer(2, len, rate);
  const pre = Math.floor(rate * 0.02);
  const refl = [0.03, 0.047, 0.069, 0.093];
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch), seed = ch ? 1.7 : 1.0;
    for (let i = pre; i < len; i++) {
      const t = (i - pre) / len;
      d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay) * seed * 0.6;
    }
    refl.forEach((r, k) => {
      const idx = pre + Math.floor(r * rate * (ch ? 1.06 : 1));
      if (idx < len) d[idx] += (ch ? -1 : 1) * 0.5 * Math.pow(0.6, k);
    });
  }
  perCtx.set(key, buf);
  return buf;
}

export class DolbyAudio {
  /**
   * @param {object} [options]
   * @param {AudioContext} [options.context]      复用已有的 AudioContext（不传则自建）
   * @param {string}  [options.preset='standard'] 初始预设 id，或传完整预设对象
   * @param {number}  [options.intensity=0.85]    干湿比 0..1
   * @param {boolean} [options.enabled=true]      是否启用（关=直通原声）
   * @param {boolean} [options.autoConnect=true]  自动连接到 context.destination
   * @param {boolean} [options.analyser=false]    额外挂频谱 AnalyserNode（getAnalyser 取出）
   * @param {'speakers'|'headphones'} [options.spatialMode='speakers'] 声场渲染方式
   */
  constructor(options = {}) {
    const Ctor = typeof window !== 'undefined' ? (window.AudioContext || window.webkitAudioContext) : null;
    if (!options.context && !Ctor) throw new Error('Web Audio API 不可用：请传入 options.context');
    this.context = options.context || new Ctor();
    this._ownsContext = !options.context;
    this._sources = new Map();         // mediaEl/node -> 源节点（避免重复 createMediaElementSource）

    const ctx = this.context;
    const Gain = () => ctx.createGain(), Filt = () => ctx.createBiquadFilter();
    // HRTF 虚拟音箱：方位角(度) → 三维坐标（默认听者朝 -z）
    const vSpeaker = (azDeg) => {
      const p = ctx.createPanner();
      p.panningModel = 'HRTF'; p.distanceModel = 'inverse';
      const rad = azDeg * Math.PI / 180, x = Math.sin(rad), z = -Math.cos(rad);
      if (p.positionX) { p.positionX.value = x; p.positionY.value = 0; p.positionZ.value = z; }
      else if (p.setPosition) p.setPosition(x, 0, z);
      return p;
    };

    // —— 节点 ——
    this.input = Gain(); this.output = Gain(); this.pre = Gain();
    this.low = Filt(); this.low.type = 'lowshelf';
    this.midEq = Filt(); this.midEq.type = 'peaking';
    this.high = Filt(); this.high.type = 'highshelf';
    this.tone = Gain();
    // 低频次谐波激励（并联）
    this.bassLP = Filt(); this.bassLP.type = 'lowpass'; this.bassLP.frequency.value = 130;
    this.bassSat = ctx.createWaveShaper();
    this.bassGain = Gain(); this.bassGain.gain.value = 0;
    // M/S 声场展宽
    this.splitter = ctx.createChannelSplitter(2);
    this.merger = ctx.createChannelMerger(2);
    this.midL = Gain(); this.midR = Gain(); this.midBus = Gain();   // Mid = 0.5L + 0.5R
    this.sideL = Gain(); this.sideR = Gain(); this.sideBus = Gain(); // Side = 0.5L - 0.5R
    this.sideW = Gain();                                             // Side × width
    this.sidePlus = Gain(); this.sideMinus = Gain();                 // ±Side 重建左右
    this.midL.gain.value = 0.5; this.midR.gain.value = 0.5;
    this.sideL.gain.value = 0.5; this.sideR.gain.value = -0.5;
    this.sidePlus.gain.value = 1; this.sideMinus.gain.value = -1;
    // 声场缓慢"呼吸"（LFO 调制 Side 增益）
    this.motionLfo = ctx.createOscillator(); this.motionLfo.type = 'sine';
    this.motionDepth = Gain(); this.motionDepth.gain.value = 0;
    this.motionLfo.connect(this.motionDepth); this.motionDepth.connect(this.sideW.gain);
    // 空间混响
    this.convolver = ctx.createConvolver();
    this.reverbGain = Gain(); this.reverbGain.gain.value = 0;
    // 声场渲染：扬声器路 / 耳机 HRTF 路（交叉淡化）
    this.stereoBus = Gain(); this.stereoTap = Gain();
    this.bSplit = ctx.createChannelSplitter(2); this.bRevSplit = ctx.createChannelSplitter(2);
    this.panFL = vSpeaker(-30); this.panFR = vSpeaker(30);     // 虚拟前置音箱 ±30°
    this.panRL = vSpeaker(-110); this.panRR = vSpeaker(110);   // 虚拟环绕音箱 ±110°
    this.binauralBus = Gain(); this.binauralTap = Gain();
    // 动态 + 限制
    this.comp = ctx.createDynamicsCompressor();
    this.limiter = ctx.createWaveShaper(); this.limiter.curve = shaperCurve(2.2); this.limiter.oversample = '4x';
    this.makeup = Gain();
    // 干湿混合
    this.dry = Gain(); this.wet = Gain();
    const preComp = Gain(); this._preComp = preComp;
    // 输出电平表（时域，做 UI 电平条）
    this._meter = ctx.createAnalyser(); this._meter.fftSize = 256;

    // —— 连线 ——
    this.input.connect(this.pre);
    this.pre.connect(this.low); this.low.connect(this.midEq); this.midEq.connect(this.high); this.high.connect(this.tone);
    this.pre.connect(this.bassLP); this.bassLP.connect(this.bassSat); this.bassSat.connect(this.bassGain); this.bassGain.connect(this.tone);
    // M/S：tone → 分离 → 重建为加宽立体声（merger）
    this.tone.connect(this.splitter);
    this.splitter.connect(this.midL, 0); this.splitter.connect(this.midR, 1);
    this.midL.connect(this.midBus); this.midR.connect(this.midBus);
    this.splitter.connect(this.sideL, 0); this.splitter.connect(this.sideR, 1);
    this.sideL.connect(this.sideBus); this.sideR.connect(this.sideBus);
    this.sideBus.connect(this.sideW);
    this.midBus.connect(this.merger, 0, 0); this.midBus.connect(this.merger, 0, 1);
    this.sideW.connect(this.sidePlus); this.sidePlus.connect(this.merger, 0, 0);
    this.sideW.connect(this.sideMinus); this.sideMinus.connect(this.merger, 0, 1);
    // 混响：tone → 卷积 → reverbGain（被两种渲染共享）
    this.tone.connect(this.convolver); this.convolver.connect(this.reverbGain);
    // 扬声器路：加宽立体声 + 立体声混响
    this.merger.connect(this.stereoBus); this.reverbGain.connect(this.stereoBus);
    this.stereoBus.connect(this.stereoTap); this.stereoTap.connect(preComp);
    // 耳机路：HRTF 虚拟前置（取加宽立体声）+ 虚拟环绕（取混响）
    this.merger.connect(this.bSplit);
    this.bSplit.connect(this.panFL, 0); this.bSplit.connect(this.panFR, 1);
    this.reverbGain.connect(this.bRevSplit);
    this.bRevSplit.connect(this.panRL, 0); this.bRevSplit.connect(this.panRR, 1);
    for (const sp of [this.panFL, this.panFR, this.panRL, this.panRR]) sp.connect(this.binauralBus);
    this.binauralBus.connect(this.binauralTap); this.binauralTap.connect(preComp);
    // 动态 → 限制 → 补偿 → 湿声；输入 → 干声
    preComp.connect(this.comp); this.comp.connect(this.limiter); this.limiter.connect(this.makeup);
    this.makeup.connect(this.wet); this.wet.connect(this.output);
    this.input.connect(this.dry); this.dry.connect(this.output);
    this.output.connect(this._meter);

    try { this.motionLfo.start(); } catch { /* 已启动 */ }

    if (options.analyser) {
      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 2048; this.analyser.smoothingTimeConstant = 0.82;
      this.output.connect(this.analyser);
    }
    if (options.autoConnect !== false) this.output.connect(ctx.destination);

    this._intensity = options.intensity != null ? Math.min(1, Math.max(0, options.intensity)) : 0.85;
    this._enabled = options.enabled !== false;
    this.setPreset(options.preset || 'standard', true);
    this.setSpatialMode(options.spatialMode || 'speakers', true);
    this._applyMix(true);
  }

  // ---- 音频源接入 ----
  /** 接 <audio>/<video> 元素（同一元素只会建立一次源节点） */
  attachMedia(el) {
    let src = this._sources.get(el);
    if (!src) { src = this.context.createMediaElementSource(el); this._sources.set(el, src); }
    src.connect(this.input); return src;
  }
  /** 接任意 AudioNode（AudioBufferSource / Oscillator / 麦克风流等） */
  attachSource(node) { node.connect(this.input); this._sources.set(node, node); return node; }
  /** 断开某个已接入的源 */
  detach(elOrNode) {
    const src = this._sources.get(elOrNode) || elOrNode;
    try { src.disconnect(this.input); } catch { /* ok */ }
  }
  /** 把处理后的输出连到指定节点（默认 destination） */
  connect(dest) { this.output.connect(dest || this.context.destination); return this; }
  /** 在用户手势后唤醒 AudioContext（满足浏览器自动播放策略） */
  resume() { return this.context.state === 'suspended' ? this.context.resume() : Promise.resolve(); }

  // ---- 参数控制 ----
  setPreset(idOrPreset, instant = false) {
    const ctx = this.context, t = ctx.currentTime, tc = instant ? 0.001 : 0.08;
    let p;
    if (typeof idOrPreset === 'string') { const pr = presetById(idOrPreset); p = pr.p; this._presetId = pr.id; }
    else if (idOrPreset && idOrPreset.p) { p = idOrPreset.p; this._presetId = idOrPreset.id || 'custom'; }
    else { p = idOrPreset; this._presetId = 'custom'; }
    this._p = p;
    const set = (param, v) => param.setTargetAtTime(v, t, tc);
    set(this.pre.gain, p.preGain);
    this.low.frequency.setTargetAtTime(p.bass.freq, t, tc); set(this.low.gain, p.bass.gain);
    this.midEq.frequency.setTargetAtTime(p.mid.freq, t, tc); this.midEq.Q.setTargetAtTime(p.mid.q, t, tc); set(this.midEq.gain, p.mid.gain);
    this.high.frequency.setTargetAtTime(p.air.freq, t, tc); set(this.high.gain, p.air.gain);
    this.bassSat.curve = shaperCurve(1 + p.bassDrive.amount * 8); set(this.bassGain.gain, p.bassDrive.mix);
    set(this.sideW.gain, p.width);
    this.motionLfo.frequency.setTargetAtTime(p.motion.rate || 0.0001, t, tc);
    set(this.motionDepth.gain, p.motion.depth * p.width);
    this.convolver.buffer = createImpulseResponse(ctx, p.reverb.seconds, p.reverb.decay);
    set(this.reverbGain.gain, p.reverb.mix);
    this.comp.threshold.setTargetAtTime(p.comp.threshold, t, tc);
    this.comp.ratio.setTargetAtTime(p.comp.ratio, t, tc);
    this.comp.knee.setTargetAtTime(p.comp.knee, t, tc);
    this.comp.attack.setTargetAtTime(p.comp.attack, t, tc);
    this.comp.release.setTargetAtTime(p.comp.release, t, tc);
    set(this.makeup.gain, p.outGain);
    return this;
  }

  /** 声场渲染：'speakers'（外放立体声）/ 'headphones'（HRTF 双耳虚拟环绕） */
  setSpatialMode(mode, instant = false) {
    this._spatialMode = mode === 'headphones' ? 'headphones' : 'speakers';
    const t = this.context.currentTime, tc = instant ? 0.001 : 0.1;
    const hp = this._spatialMode === 'headphones' ? 1 : 0;
    this.binauralTap.gain.setTargetAtTime(hp, t, tc);
    this.stereoTap.gain.setTargetAtTime(1 - hp, t, tc);
    return this;
  }

  /** 整体强度（处理链干湿比，0=原声 1=满处理） */
  setIntensity(v, instant = false) { this._intensity = Math.min(1, Math.max(0, v)); this._applyMix(instant); return this; }
  setEnabled(on, instant = false) { this._enabled = !!on; this._applyMix(instant); return this; }
  enable(on) { return this.setEnabled(on); }
  bypass(on) { return this.setEnabled(!on); }

  // ---- 单项微调（覆盖当前预设值，做精细调音/滑杆） ----
  setWidth(mult) { this.sideW.gain.setTargetAtTime(mult, this.context.currentTime, 0.05); return this; }
  setBass(dB) { this.low.gain.setTargetAtTime(dB, this.context.currentTime, 0.05); return this; }
  setAir(dB) { this.high.gain.setTargetAtTime(dB, this.context.currentTime, 0.05); return this; }
  setReverb(mix) { this.reverbGain.gain.setTargetAtTime(mix, this.context.currentTime, 0.05); return this; }

  _applyMix(instant = false) {
    const t = this.context.currentTime, tc = instant ? 0.001 : 0.12;
    const wet = this._enabled ? this._intensity : 0;
    // 等功率交叉淡化，开关/调节强度时不爆音、不掉响度
    this.wet.gain.setTargetAtTime(Math.sin(wet * Math.PI / 2), t, tc);
    this.dry.gain.setTargetAtTime(Math.cos(wet * Math.PI / 2), t, tc);
  }

  getAnalyser() { return this.analyser || null; }
  /** 输出电平：{ rms, peak }（0..1）与 db（dBFS），用于电平表/动效 */
  getLevel() {
    if (!this._meterBuf) this._meterBuf = new Float32Array(this._meter.fftSize);
    const buf = this._meterBuf;
    if (this._meter.getFloatTimeDomainData) this._meter.getFloatTimeDomainData(buf);
    let sum = 0, peak = 0;
    for (let i = 0; i < buf.length; i++) { const v = buf[i]; sum += v * v; if (Math.abs(v) > peak) peak = Math.abs(v); }
    const rms = Math.sqrt(sum / buf.length);
    return { rms, peak, db: 20 * Math.log10(rms || 1e-6) };
  }

  get enabled() { return this._enabled; }
  get intensity() { return this._intensity; }
  get presetId() { return this._presetId; }
  get spatialMode() { return this._spatialMode; }
  get state() { return { enabled: this._enabled, preset: this._presetId, intensity: this._intensity, spatialMode: this._spatialMode, supported: true }; }

  /** 释放节点。closeContext=true 且 context 为自建时，关闭 AudioContext */
  dispose({ closeContext = false } = {}) {
    try { this.motionLfo.stop(); } catch { /* ok */ }
    const nodes = [this.input, this.output, this.pre, this.low, this.midEq, this.high, this.tone,
      this.bassLP, this.bassSat, this.bassGain, this.splitter, this.merger, this.midL, this.midR,
      this.midBus, this.sideL, this.sideR, this.sideBus, this.sideW, this.sidePlus, this.sideMinus,
      this.motionLfo, this.motionDepth, this.convolver, this.reverbGain, this.stereoBus, this.stereoTap,
      this.bSplit, this.bRevSplit, this.panFL, this.panFR, this.panRL, this.panRR, this.binauralBus,
      this.binauralTap, this.comp, this.limiter, this.makeup, this.dry, this.wet, this._preComp,
      this._meter, this.analyser];
    for (const n of nodes) { try { n && n.disconnect(); } catch { /* ok */ } }
    this._sources.clear();
    if (closeContext && this._ownsContext) { try { this.context.close(); } catch { /* ok */ } }
  }
}

export function createDolby(options) { return new DolbyAudio(options); }
export default DolbyAudio;
