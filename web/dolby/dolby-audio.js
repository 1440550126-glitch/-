// ============================================================
// dolby-audio · 杜比风格沉浸音效引擎（独立 / 零依赖 / 纯 Web Audio）
// ------------------------------------------------------------
// 一个与框架无关的母带处理器，可挂在任意音频源后端：
//   <audio>/<video> 元素、AudioBufferSource、麦克风、或任意 AudioNode。
// 处理链：
//   低频增强（低架 + 次谐波激励器）→ 中频清晰 + 高频空气感 → 人声/对白增强（中置）
//   → 立体声声场展宽（M/S，保留并增强原立体声，单声道安全）
//   → 缓慢声场"呼吸"（LFO 调制 Side）→ 空间混响（合成立体声 IR）
//   → 声场渲染：扬声器立体声 / 耳机 HRTF 双耳虚拟环绕
//   → 动态：单段 或 三段多频带压缩 → 软削波限制 → 响度对齐（A/B 等响）
//   → 干湿混合（强度可调 / 一键旁通）
//
//   import { DolbyAudio } from './dolby-audio.js';
//   const dolby = new DolbyAudio({ preset: 'cinema' });
//   dolby.attachMedia(document.querySelector('audio'));
//   await dolby.resume(); dolby.setSpatialMode('headphones');
// ============================================================
import { makeKWeighting, lufsFromMeanSquare, gainForLufs, IntegratedLoudness } from './dolby-loudness.js';
import { buildBinauralIR } from './dolby-hrir.js';

// width：Side 增益倍数（1=原立体声宽度）；vocal：人声中置提升 dB
export const DOLBY_PRESETS = [
  { id: 'standard', label: '标准增强', desc: '均衡的沉浸感，日常聆听', p: {
    preGain: 1.0, bass: { freq: 110, gain: 5 }, bassDrive: { amount: 0.18, mix: 0.32 },
    mid: { freq: 2600, gain: 2.0, q: 0.9 }, air: { freq: 9000, gain: 3.5 }, vocal: 1.5,
    width: 1.3, motion: { rate: 0.08, depth: 0.06 }, reverb: { mix: 0.16, seconds: 1.8, decay: 2.6 },
    comp: { threshold: -20, ratio: 3, knee: 24, attack: 0.012, release: 0.22 }, outGain: 1.1 } },
  { id: 'cinema', label: '影院环绕', desc: '大空间环绕 · 重低音 · 戏剧动态', p: {
    preGain: 1.0, bass: { freq: 95, gain: 7.5 }, bassDrive: { amount: 0.28, mix: 0.45 },
    mid: { freq: 2200, gain: 1.4, q: 0.8 }, air: { freq: 11000, gain: 4.5 }, vocal: 1.0,
    width: 1.65, motion: { rate: 0.06, depth: 0.14 }, reverb: { mix: 0.30, seconds: 3.0, decay: 3.4 },
    comp: { threshold: -24, ratio: 4, knee: 26, attack: 0.008, release: 0.26 }, outGain: 1.16 } },
  { id: 'music', label: '音乐厅', desc: '低音扎实 · 高音通透 · 适合旋律', p: {
    preGain: 1.0, bass: { freq: 120, gain: 6 }, bassDrive: { amount: 0.22, mix: 0.38 },
    mid: { freq: 3000, gain: 2.6, q: 1.0 }, air: { freq: 12000, gain: 5 }, vocal: 2.0,
    width: 1.45, motion: { rate: 0.1, depth: 0.08 }, reverb: { mix: 0.18, seconds: 1.6, decay: 2.2 },
    comp: { threshold: -18, ratio: 3.5, knee: 20, attack: 0.006, release: 0.18 }, outGain: 1.13 } },
  { id: 'night', label: '夜深人静', desc: '压缩动态 · 收敛低音 · 不扰人', p: {
    preGain: 0.95, bass: { freq: 90, gain: 2 }, bassDrive: { amount: 0.06, mix: 0.18 },
    mid: { freq: 2400, gain: 1.6, q: 0.9 }, air: { freq: 8000, gain: 2.5 }, vocal: 2.5,
    width: 1.12, motion: { rate: 0.08, depth: 0.03 }, reverb: { mix: 0.12, seconds: 1.2, decay: 1.8 },
    comp: { threshold: -34, ratio: 6, knee: 30, attack: 0.004, release: 0.32 }, outGain: 1.0 } },
  { id: 'vocal', label: '人声清晰', desc: '突出中高频 · 干净近场 · 适合旁白/播客', p: {
    preGain: 1.0, bass: { freq: 100, gain: 1.5 }, bassDrive: { amount: 0.04, mix: 0.12 },
    mid: { freq: 3200, gain: 4, q: 1.1 }, air: { freq: 10000, gain: 4 }, vocal: 5.0,
    width: 1.0, motion: { rate: 0, depth: 0 }, reverb: { mix: 0.07, seconds: 1.0, decay: 1.6 },
    comp: { threshold: -22, ratio: 3, knee: 22, attack: 0.01, release: 0.2 }, outGain: 1.08 } }
];
export const presetById = (id) => DOLBY_PRESETS.find((x) => x.id === id) || DOLBY_PRESETS[0];

// 图形均衡频段中心频率（Hz）
export const EQ_BANDS = [60, 150, 400, 1000, 2500, 6000, 12000];
/** 注册/覆盖一个自定义预设（按 id 去重），返回该预设 */
export function registerPreset(preset) {
  if (!preset || !preset.id || !preset.p) throw new Error('preset 需要 { id, p }');
  const i = DOLBY_PRESETS.findIndex((x) => x.id === preset.id);
  if (i >= 0) DOLBY_PRESETS[i] = preset; else DOLBY_PRESETS.push(preset);
  return preset;
}

const dbToAmp = (db) => Math.pow(10, db / 20);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

/** 生成对数分布的频率刻度（Hz），用于画频响曲线 */
export function logFreqScale(n = 200, min = 20, max = 20000) {
  const f = new Float32Array(n), lmin = Math.log10(min), lmax = Math.log10(max);
  for (let i = 0; i < n; i++) f[i] = Math.pow(10, lmin + (lmax - lmin) * (i / (n - 1)));
  return f;
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
   * @param {AudioContext} [options.context]      复用已有 AudioContext（不传则自建）
   * @param {string|object} [options.preset='standard'] 预设 id 或完整预设对象
   * @param {number}  [options.intensity=0.85]    干湿比 0..1
   * @param {boolean} [options.enabled=true]      启用（关=直通原声）
   * @param {boolean} [options.autoConnect=true]  自动连接到 destination
   * @param {boolean} [options.analyser=false]    挂频谱 AnalyserNode（getAnalyser）
   * @param {'speakers'|'headphones'} [options.spatialMode='speakers']
   * @param {boolean} [options.multiband=false]   三段多频带压缩（默认单段）
   * @param {boolean} [options.loudnessMatch=false] 响度对齐（处理后≈原声响度，A/B 公平）
   */
  constructor(options = {}) {
    const Ctor = typeof window !== 'undefined' ? (window.AudioContext || window.webkitAudioContext) : null;
    if (!options.context && !Ctor) throw new Error('Web Audio API 不可用：请传入 options.context');
    this.context = options.context || new Ctor();
    this._ownsContext = !options.context;
    this._sources = new Map();

    const ctx = this.context;
    const Gain = () => ctx.createGain(), Filt = () => ctx.createBiquadFilter();
    const LR = (type, freq) => { const f = Filt(); f.type = type; f.frequency.value = freq; f.Q.value = Math.SQRT1_2; return f; };
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
    // 多声道源（5.1/7.1 等）按标准 ITU 下混到立体声后再处理
    this.input.channelCount = 2; this.input.channelCountMode = 'explicit'; this.input.channelInterpretation = 'speakers';
    this.low = Filt(); this.low.type = 'lowshelf';
    this.midEq = Filt(); this.midEq.type = 'peaking';
    this.high = Filt(); this.high.type = 'highshelf';
    this.tone = Gain();
    this.bassLP = Filt(); this.bassLP.type = 'lowpass'; this.bassLP.frequency.value = 130;
    this.bassSat = ctx.createWaveShaper();
    this.bassGain = Gain(); this.bassGain.gain.value = 0;
    // 用户图形均衡（多段 peaking 串联，默认全 0dB）
    this.eqBands = EQ_BANDS.map((f) => { const b = Filt(); b.type = 'peaking'; b.frequency.value = f; b.Q.value = 1.0; b.gain.value = 0; return b; });
    this.eqOut = Gain();
    this._eqGains = new Array(EQ_BANDS.length).fill(0);
    // M/S 声场展宽
    this.splitter = ctx.createChannelSplitter(2);
    this.merger = ctx.createChannelMerger(2);
    this.midL = Gain(); this.midR = Gain(); this.midBus = Gain();
    this.sideL = Gain(); this.sideR = Gain(); this.sideBus = Gain();
    this.sideW = Gain(); this.sidePlus = Gain(); this.sideMinus = Gain();
    this.midL.gain.value = 0.5; this.midR.gain.value = 0.5;
    this.sideL.gain.value = 0.5; this.sideR.gain.value = -0.5;
    this.sidePlus.gain.value = 1; this.sideMinus.gain.value = -1;
    // 人声/对白增强（提升中置带通）
    this.vocalBP = Filt(); this.vocalBP.type = 'peaking'; this.vocalBP.frequency.value = 2500; this.vocalBP.Q.value = 1.0;
    this.vocalGain = Gain(); this.vocalGain.gain.value = 0;
    // 声场呼吸
    this.motionLfo = ctx.createOscillator(); this.motionLfo.type = 'sine';
    this.motionDepth = Gain(); this.motionDepth.gain.value = 0;
    this.motionLfo.connect(this.motionDepth); this.motionDepth.connect(this.sideW.gain);
    // 混响
    this.convolver = ctx.createConvolver();
    this.reverbGain = Gain(); this.reverbGain.gain.value = 0;
    // 渲染：扬声器 / 耳机
    this.stereoBus = Gain(); this.stereoTap = Gain();
    this.bSplit = ctx.createChannelSplitter(2); this.bRevSplit = ctx.createChannelSplitter(2);
    this.panFL = vSpeaker(-30); this.panFR = vSpeaker(30);
    this.panRL = vSpeaker(-110); this.panRR = vSpeaker(110);
    this.binauralBus = Gain(); this.binauralTap = Gain();
    // 个性化 HRTF：自定义 HRIR 卷积双耳（设了 HRIR 且耳机模式时取代内置 HRTF）
    this.hrirConv = ctx.createConvolver(); this.hrirTap = Gain(); this.hrirTap.gain.value = 0; this._hasHRIR = false;
    const preComp = Gain(); this._preComp = preComp;
    // 动态：单段
    this.comp = ctx.createDynamicsCompressor(); this.compTap = Gain();
    // 动态：三段多频带（lo<250<mid<3500<hi，LR4 分频）
    this.loA = LR('lowpass', 250); this.loB = LR('lowpass', 250);
    this.miHP = LR('highpass', 250); this.miLP = LR('lowpass', 3500);
    this.hiA = LR('highpass', 3500); this.hiB = LR('highpass', 3500);
    this.compLow = ctx.createDynamicsCompressor(); this.compMid = ctx.createDynamicsCompressor(); this.compHigh = ctx.createDynamicsCompressor();
    this.bandSum = Gain(); this.mbTap = Gain(); this.mbTap.gain.value = 0;
    // 限制 → 补偿 → 响度对齐 → 湿声
    this.limiterIn = Gain();
    this.limiter = ctx.createWaveShaper(); this.limiter.curve = shaperCurve(2.2); this.limiter.oversample = '4x';
    this.makeup = Gain(); this.matchGain = Gain(); this.matchGain.gain.value = 1;
    // 耳机交叉馈送（crossfeed）：对侧声道延迟+低通后少量混入，缓解耳机过宽、改善头外定位
    this.cfIn = Gain(); this.cfSplit = ctx.createChannelSplitter(2); this.cfMerge = ctx.createChannelMerger(2);
    this.cfDL = Gain(); this.cfDR = Gain();
    this.cfLd = ctx.createDelay(0.01); this.cfLlp = Filt(); this.cfLlp.type = 'lowpass'; this.cfLlp.frequency.value = 700; this.cfLg = Gain(); this.cfLg.gain.value = 0;
    this.cfRd = ctx.createDelay(0.01); this.cfRlp = Filt(); this.cfRlp.type = 'lowpass'; this.cfRlp.frequency.value = 700; this.cfRg = Gain(); this.cfRg.gain.value = 0;
    this.cfLd.delayTime.value = 0.0003; this.cfRd.delayTime.value = 0.0003; this._crossfeed = 0;
    this.dry = Gain(); this.wet = Gain();
    // 电平表（输出）+ 响度对齐用的干/湿表 + K 加权响度表
    this._meter = ctx.createAnalyser(); this._meter.fftSize = 256;
    this._dryMeter = ctx.createAnalyser(); this._dryMeter.fftSize = 256;
    this._wetMeter = ctx.createAnalyser(); this._wetMeter.fftSize = 256;
    this._kw = makeKWeighting(ctx); this._kwMeter = ctx.createAnalyser(); this._kwMeter.fftSize = 2048;
    this._lufs = -Infinity; this._lastMs = 0; this._normTarget = null;
    this._integ = new IntegratedLoudness(); this._integMeasuring = false;

    // —— 连线 ——
    this.input.connect(this.pre);
    this.pre.connect(this.low); this.low.connect(this.midEq); this.midEq.connect(this.high); this.high.connect(this.tone);
    this.pre.connect(this.bassLP); this.bassLP.connect(this.bassSat); this.bassSat.connect(this.bassGain); this.bassGain.connect(this.tone);
    // 用户图形均衡：tone → eq[0] → … → eq[n-1] → eqOut（其后所有处理基于 eqOut）
    let _eqPrev = this.tone;
    for (const b of this.eqBands) { _eqPrev.connect(b); _eqPrev = b; }
    _eqPrev.connect(this.eqOut);
    // M/S
    this.eqOut.connect(this.splitter);
    this.splitter.connect(this.midL, 0); this.splitter.connect(this.midR, 1);
    this.midL.connect(this.midBus); this.midR.connect(this.midBus);
    this.splitter.connect(this.sideL, 0); this.splitter.connect(this.sideR, 1);
    this.sideL.connect(this.sideBus); this.sideR.connect(this.sideBus);
    this.sideBus.connect(this.sideW);
    this.midBus.connect(this.merger, 0, 0); this.midBus.connect(this.merger, 0, 1);
    this.sideW.connect(this.sidePlus); this.sidePlus.connect(this.merger, 0, 0);
    this.sideW.connect(this.sideMinus); this.sideMinus.connect(this.merger, 0, 1);
    // 人声增强：中置带通 → 增益 → 回注左右
    this.midBus.connect(this.vocalBP); this.vocalBP.connect(this.vocalGain);
    this.vocalGain.connect(this.merger, 0, 0); this.vocalGain.connect(this.merger, 0, 1);
    // 混响
    this.eqOut.connect(this.convolver); this.convolver.connect(this.reverbGain);
    // 扬声器路
    this.merger.connect(this.stereoBus); this.reverbGain.connect(this.stereoBus);
    this.stereoBus.connect(this.stereoTap); this.stereoTap.connect(preComp);
    // 耳机路
    this.merger.connect(this.bSplit);
    this.bSplit.connect(this.panFL, 0); this.bSplit.connect(this.panFR, 1);
    this.reverbGain.connect(this.bRevSplit);
    this.bRevSplit.connect(this.panRL, 0); this.bRevSplit.connect(this.panRR, 1);
    for (const sp of [this.panFL, this.panFR, this.panRL, this.panRR]) sp.connect(this.binauralBus);
    this.binauralBus.connect(this.binauralTap); this.binauralTap.connect(preComp);
    // 个性化 HRIR 卷积路（取加宽立体声）
    this.merger.connect(this.hrirConv); this.hrirConv.connect(this.hrirTap); this.hrirTap.connect(preComp);
    // 动态：单段路
    preComp.connect(this.comp); this.comp.connect(this.compTap); this.compTap.connect(this.limiterIn);
    // 动态：多频带路
    preComp.connect(this.loA); this.loA.connect(this.loB); this.loB.connect(this.compLow); this.compLow.connect(this.bandSum);
    preComp.connect(this.miHP); this.miHP.connect(this.miLP); this.miLP.connect(this.compMid); this.compMid.connect(this.bandSum);
    preComp.connect(this.hiA); this.hiA.connect(this.hiB); this.hiB.connect(this.compHigh); this.compHigh.connect(this.bandSum);
    this.bandSum.connect(this.mbTap); this.mbTap.connect(this.limiterIn);
    // 限制 → 补偿 → 交叉馈送 → 响度对齐 → 湿声；干声直通
    this.limiterIn.connect(this.limiter); this.limiter.connect(this.makeup);
    this.makeup.connect(this.cfIn);
    this.cfIn.connect(this.cfSplit);
    this.cfSplit.connect(this.cfDL, 0); this.cfDL.connect(this.cfMerge, 0, 0);
    this.cfSplit.connect(this.cfDR, 1); this.cfDR.connect(this.cfMerge, 0, 1);
    this.cfSplit.connect(this.cfLd, 0); this.cfLd.connect(this.cfLlp); this.cfLlp.connect(this.cfLg); this.cfLg.connect(this.cfMerge, 0, 1);   // 左→右
    this.cfSplit.connect(this.cfRd, 1); this.cfRd.connect(this.cfRlp); this.cfRlp.connect(this.cfRg); this.cfRg.connect(this.cfMerge, 0, 0);   // 右→左
    this.cfDL.gain.value = 1; this.cfDR.gain.value = 1;
    this.cfMerge.connect(this.matchGain); this.matchGain.connect(this.wet); this.wet.connect(this.output);
    this.input.connect(this.dry); this.dry.connect(this.output);
    // 表
    this.output.connect(this._meter);
    this.input.connect(this._dryMeter);
    this.makeup.connect(this._wetMeter);
    this.makeup.connect(this._kw.input); this._kw.output.connect(this._kwMeter);   // K 加权响度测量

    try { this.motionLfo.start(); } catch { /* 已启动 */ }

    if (options.analyser) {
      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 2048; this.analyser.smoothingTimeConstant = 0.82;
      this.output.connect(this.analyser);
    }
    if (options.autoConnect !== false) this.output.connect(ctx.destination);

    this._intensity = options.intensity != null ? clamp(options.intensity, 0, 1) : 0.85;
    this._enabled = options.enabled !== false;
    this._matchVal = 1;
    this.setPreset(options.preset || 'standard', true);
    this.setSpatialMode(options.spatialMode || 'speakers', true);
    this.setMultiband(!!options.multiband, true);
    this._applyMix(true);
    if (options.crossfeed) this.setCrossfeed(options.crossfeed);
    if (options.loudnessMatch) this.setLoudnessMatch(true);
    if (options.loudnessNorm != null) this.setLoudnessNorm(options.loudnessNorm);
    if (options.worklet) this._initWorklet();
    if (options.limiterWorklet) this._initLimiterWorklet();
  }

  // 用 AudioWorklet 前瞻限幅器替换软削波（实验性，主信号路径）；失败保持 WaveShaper
  _initLimiterWorklet() {
    const ctx = this.context;
    if (this._limiterWorklet || !ctx.audioWorklet || typeof AudioWorkletNode === 'undefined') return;
    let url; try { url = new URL('./dolby-limiter-worklet.js', import.meta.url); } catch { return; }
    ctx.audioWorklet.addModule(url).then(() => {
      this._limNode = new AudioWorkletNode(ctx, 'dolby-limiter', { outputChannelCount: [2], processorOptions: { lookahead: 64 } });
      this._limNode.port.onmessage = (e) => { this._limGr = e.data; };
      this.limiterIn.disconnect();
      this.limiterIn.connect(this._limNode); this._limNode.connect(this.makeup);
      try { this.limiter.disconnect(); } catch { /* ok */ }
      this._limiterWorklet = true;
    }).catch(() => { /* 回退软削波 */ });
  }
  get limiterWorklet() { return !!this._limiterWorklet; }
  /** 调限幅器参数（真机调参用）：{ threshold 0.1..1, attack, release }；仅 limiterWorklet 生效 */
  setLimiterParams(p = {}) {
    if (!this._limNode || !this._limNode.parameters) return this;
    const t = this.context.currentTime;
    const set = (name, v) => { if (typeof v === 'number') { const pr = this._limNode.parameters.get(name); if (pr) pr.setTargetAtTime(v, t, 0.02); } };
    set('threshold', p.threshold); set('attack', p.attack); set('release', p.release);
    return this;
  }
  /** 限幅器增益衰减（dB，≤0；需 limiterWorklet 开启） */
  getLimiterReduction() { return this._limGr != null ? 20 * Math.log10(this._limGr || 1e-6) : 0; }

  // 用 AudioWorklet 在音频线程做响度测量（脱离主线程）；失败/不支持则保持分析器测量
  _initWorklet() {
    const ctx = this.context;
    if (this._worklet || !ctx.audioWorklet || typeof AudioWorkletNode === 'undefined') return;
    let url;
    try { url = new URL('./dolby-loudness-worklet.js', import.meta.url); } catch { return; }
    ctx.audioWorklet.addModule(url).then(() => {
      this._workletNode = new AudioWorkletNode(ctx, 'dolby-loudness');
      this._workletSink = ctx.createGain(); this._workletSink.gain.value = 0;   // 静默汇入，确保节点被驱动
      this._kw.output.connect(this._workletNode); this._workletNode.connect(this._workletSink); this._workletSink.connect(this.output);
      this._workletNode.port.onmessage = (e) => { this._wmMs = e.data; if (this._integMeasuring) this._integ.addBlock(e.data); };  // 真 400ms 块喂积分
      this._worklet = true;
    }).catch(() => { /* 回退到分析器测量 */ });
  }
  get worklet() { return !!this._worklet; }

  // ---- 源接入 ----
  attachMedia(el) {
    let src = this._sources.get(el);
    if (!src) { src = this.context.createMediaElementSource(el); this._sources.set(el, src); }
    src.connect(this.input); return src;
  }
  attachSource(node) { node.connect(this.input); this._sources.set(node, node); return node; }
  detach(elOrNode) { const src = this._sources.get(elOrNode) || elOrNode; try { src.disconnect(this.input); } catch { /* ok */ } }
  connect(dest) { this.output.connect(dest || this.context.destination); return this; }
  resume() { return this.context.state === 'suspended' ? this.context.resume() : Promise.resolve(); }

  // ---- 预设 ----
  setPreset(idOrPreset, instant = false) {
    const ctx = this.context, t = ctx.currentTime, tc = instant ? 0.001 : 0.08;
    let p;
    if (typeof idOrPreset === 'string') { const pr = presetById(idOrPreset); p = pr.p; this._presetId = pr.id; }
    else if (idOrPreset && idOrPreset.p) { p = idOrPreset.p; this._presetId = idOrPreset.id || 'custom'; }
    else { p = idOrPreset; this._presetId = 'custom'; }
    this._p = structuredClone(p);           // 拷贝，避免微调时污染共享预设对象
    const set = (param, v) => param.setTargetAtTime(v, t, tc);
    set(this.pre.gain, p.preGain);
    this.low.frequency.setTargetAtTime(p.bass.freq, t, tc); set(this.low.gain, p.bass.gain);
    this.midEq.frequency.setTargetAtTime(p.mid.freq, t, tc); this.midEq.Q.setTargetAtTime(p.mid.q, t, tc); set(this.midEq.gain, p.mid.gain);
    this.high.frequency.setTargetAtTime(p.air.freq, t, tc); set(this.high.gain, p.air.gain);
    this.bassSat.curve = shaperCurve(1 + p.bassDrive.amount * 8); set(this.bassGain.gain, p.bassDrive.mix);
    set(this.vocalGain.gain, Math.max(0, dbToAmp(p.vocal || 0) - 1));
    set(this.sideW.gain, p.width);
    this.motionLfo.frequency.setTargetAtTime(p.motion.rate || 0.0001, t, tc);
    set(this.motionDepth.gain, p.motion.depth * p.width);
    this.convolver.buffer = createImpulseResponse(ctx, p.reverb.seconds, p.reverb.decay);
    set(this.reverbGain.gain, p.reverb.mix);
    this._applyComp(this.comp, p.comp, 0);
    this._applyComp(this.compLow, p.comp, -3);   // 低频压得更稳
    this._applyComp(this.compMid, p.comp, 0);
    this._applyComp(this.compHigh, p.comp, 3);   // 高频更轻
    set(this.makeup.gain, p.outGain);
    this.setEQ(Array.isArray(p.eq) ? p.eq : new Array(this.eqBands.length).fill(0), instant);
    return this;
  }
  _applyComp(node, c, dThresh) {
    const t = this.context.currentTime, tc = 0.05;
    node.threshold.setTargetAtTime(c.threshold + dThresh, t, tc);
    node.ratio.setTargetAtTime(c.ratio, t, tc);
    node.knee.setTargetAtTime(c.knee, t, tc);
    node.attack.setTargetAtTime(c.attack, t, tc);
    node.release.setTargetAtTime(c.release, t, tc);
  }

  /** 声场渲染：'speakers' / 'headphones'（内置 HRTF 或自定义 HRIR 双耳） */
  setSpatialMode(mode, instant = false) {
    this._spatialMode = mode === 'headphones' ? 'headphones' : 'speakers';
    this._applyRender(instant);
    return this;
  }
  _applyRender(instant = false) {
    const t = this.context.currentTime, tc = instant ? 0.001 : 0.1;
    const hp = this._spatialMode === 'headphones', useHrir = hp && this._hasHRIR;
    this.stereoTap.gain.setTargetAtTime(hp ? 0 : 1, t, tc);
    this.binauralTap.gain.setTargetAtTime(hp && !useHrir ? 1 : 0, t, tc);
    this.hrirTap.gain.setTargetAtTime(useHrir ? 1 : 0, t, tc);
  }
  /** 上传个性化 HRTF：用自定义双耳脉冲响应(HRIR/BRIR，AudioBuffer)做卷积双耳；耳机模式下生效 */
  setHRIR(buffer) { try { this.hrirConv.buffer = buffer; this._hasHRIR = !!buffer; } catch { this._hasHRIR = false; } this._applyRender(); return this; }
  clearHRIR() { try { this.hrirConv.buffer = null; } catch { /* ok */ } this._hasHRIR = false; this._applyRender(); return this; }
  /** 由 HRIR 数据集（见 dolby-hrir.js 格式）渲染并应用个性化双耳 */
  loadHRIRSet(set) { return this.setHRIR(buildBinauralIR(this.context, set)); }
  get hasHRIR() { return !!this._hasHRIR; }

  /** 多频带压缩开关（三段 / 单段），等功率交叉淡化 */
  setMultiband(on, instant = false) {
    this._multiband = !!on;
    const t = this.context.currentTime, tc = instant ? 0.001 : 0.1, m = this._multiband ? 1 : 0;
    this.mbTap.gain.setTargetAtTime(Math.sin(m * Math.PI / 2), t, tc);
    this.compTap.gain.setTargetAtTime(Math.cos(m * Math.PI / 2), t, tc);
    return this;
  }

  /** 耳机交叉馈送强度 0..1（0=关）：改善耳机头外定位、收敛过宽声场 */
  setCrossfeed(amount) {
    this._crossfeed = clamp(amount || 0, 0, 1);
    const g = this._crossfeed * 0.5, t = this.context.currentTime;
    this.cfLg.gain.setTargetAtTime(g, t, 0.05); this.cfRg.gain.setTargetAtTime(g, t, 0.05);
    return this;
  }
  get crossfeed() { return this._crossfeed; }

  /** 响度对齐：让处理后的响度≈原声，A/B 切换公平 */
  setLoudnessMatch(on) {
    this._loudnessMatch = !!on;
    if (!this._loudnessMatch && this._normTarget == null) { this._matchVal = 1; this.matchGain.gain.setTargetAtTime(1, this.context.currentTime, 0.2); }
    this._ensureLoop();
    return this;
  }
  /** 响度归一化（向 Dolby Volume 看齐）：把输出拉到目标 LUFS（如 -14）；传 null 关闭 */
  setLoudnessNorm(targetLufs) {
    this._normTarget = (typeof targetLufs === 'number') ? targetLufs : null;
    if (this._normTarget == null && !this._loudnessMatch) { this._matchVal = 1; this.matchGain.gain.setTargetAtTime(1, this.context.currentTime, 0.2); }
    this._ensureLoop();
    return this;
  }
  get loudnessNorm() { return this._normTarget; }
  /** 当前估计的响度（LUFS 近似，K 加权瞬时；非认证 BS.1770 积分值） */
  getLoudness() { return this._measureLufs(); }
  /** 开/关积分响度测量回路（供 getIntegratedLoudness 累积） */
  measureLoudness(on = true) { this._integMeasuring = !!on; this._ensureLoop(); return this; }
  /** 门控积分响度（LUFS，BS.1770/R128 风格）；需测量回路在跑（归一/对齐/measureLoudness 任一开启） */
  getIntegratedLoudness() { return this._integ.integrated(); }
  resetLoudness() { this._integ.reset(); return this; }

  _ensureLoop() {
    const need = this._loudnessMatch || this._normTarget != null || this._integMeasuring;
    if (need && !this._matchTimer) { if (typeof setInterval === 'function') this._matchTimer = setInterval(() => this._updateMatch(), 250); }
    else if (!need && this._matchTimer) { clearInterval(this._matchTimer); this._matchTimer = null; }
  }
  _rms(an) {
    const buf = this._mbuf || (this._mbuf = new Float32Array(an.fftSize));
    if (an.getFloatTimeDomainData) an.getFloatTimeDomainData(buf);
    let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
    return Math.sqrt(s / buf.length);
  }
  _measureLufs() {
    let ms;
    if (this._wmMs != null) ms = this._wmMs;                  // Worklet 测量优先
    else {
      const an = this._kwMeter, buf = this._kbuf || (this._kbuf = new Float32Array(an.fftSize));
      if (an.getFloatTimeDomainData) an.getFloatTimeDomainData(buf);
      let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      ms = s / buf.length;
    }
    this._lastMs = ms; this._lufs = lufsFromMeanSquare(ms);
    return this._lufs;
  }
  _updateMatch() {
    const lufs = this._measureLufs();
    if (this._integMeasuring && !this._worklet) this._integ.addBlock(this._lastMs);   // 无 worklet 时由此累积（近似块）
    if (this._normTarget != null) {                        // 归一化到目标 LUFS
      if (!isFinite(lufs) || lufs < -70) return;           // 静音不调
      const target = gainForLufs(lufs, this._normTarget);
      this._matchVal += (target - this._matchVal) * 0.2;
      this.matchGain.gain.setTargetAtTime(clamp(this._matchVal, 0.25, 4), this.context.currentTime, 0.25);
    } else if (this._loudnessMatch) {                      // 干/湿等响（A/B 公平）
      const dry = this._rms(this._dryMeter), wet = this._rms(this._wetMeter);
      if (dry < 1e-4 || wet < 1e-4) return;
      const target = clamp(dry / wet, 0.25, 4);
      this._matchVal += (target - this._matchVal) * 0.3;
      this.matchGain.gain.setTargetAtTime(this._matchVal, this.context.currentTime, 0.2);
    }
  }

  setIntensity(v, instant = false) { this._intensity = clamp(v, 0, 1); this._applyMix(instant); return this; }
  setEnabled(on, instant = false) { this._enabled = !!on; this._applyMix(instant); return this; }
  enable(on) { return this.setEnabled(on); }
  bypass(on) { return this.setEnabled(!on); }

  // 单项微调（同时记入当前参数快照，供 snapshotPreset 保存）
  setWidth(mult) { this.sideW.gain.setTargetAtTime(mult, this.context.currentTime, 0.05); if (this._p) this._p.width = mult; return this; }
  setBass(dB) { this.low.gain.setTargetAtTime(dB, this.context.currentTime, 0.05); if (this._p) this._p.bass.gain = dB; return this; }
  setAir(dB) { this.high.gain.setTargetAtTime(dB, this.context.currentTime, 0.05); if (this._p) this._p.air.gain = dB; return this; }
  setReverb(mix) { this.reverbGain.gain.setTargetAtTime(mix, this.context.currentTime, 0.05); if (this._p) this._p.reverb.mix = mix; return this; }
  setVocal(dB) { this.vocalGain.gain.setTargetAtTime(Math.max(0, dbToAmp(dB) - 1), this.context.currentTime, 0.05); if (this._p) this._p.vocal = dB; return this; }

  // 图形均衡（用户可拖拽调节的多段 peaking）
  setEQBand(i, dB, instant = false) {
    const b = this.eqBands[i]; if (!b) return this;
    b.gain.setTargetAtTime(dB, this.context.currentTime, instant ? 0.001 : 0.05);
    this._eqGains[i] = dB; return this;
  }
  setEQ(gains, instant = false) { (gains || []).forEach((g, i) => this.setEQBand(i, g, instant)); return this; }
  getEQ() { return this.eqBands.map((b, i) => ({ freq: EQ_BANDS[i], gain: this._eqGains[i] })); }
  resetEQ(instant = false) { return this.setEQ(new Array(this.eqBands.length).fill(0), instant); }

  /** 把当前全部设置打包成预设对象（含图形均衡），可交给 registerPreset 保存 */
  snapshotPreset(id, label, desc = '') {
    const p = structuredClone(this._p); p.eq = this._eqGains.slice();
    return { id, label: label || id, desc, p };
  }

  _applyMix(instant = false) {
    const t = this.context.currentTime, tc = instant ? 0.001 : 0.12, wet = this._enabled ? this._intensity : 0;
    this.wet.gain.setTargetAtTime(Math.sin(wet * Math.PI / 2), t, tc);
    this.dry.gain.setTargetAtTime(Math.cos(wet * Math.PI / 2), t, tc);
  }

  getAnalyser() { return this.analyser || null; }

  /**
   * 当前均衡（低架·中频·高架串联）的频响曲线，反映实时 bass/mid/air 设置。
   * @param {Float32Array|number[]} [freqs] 频率点（Hz），默认对数 20–20kHz 200 点
   * @returns {{ freqs: Float32Array, magDb: Float32Array }} 各频点的增益（dB）
   */
  getFrequencyResponse(freqs) {
    const f = freqs ? (freqs instanceof Float32Array ? freqs : Float32Array.from(freqs)) : logFreqScale();
    const n = f.length, mag = new Float32Array(n), ph = new Float32Array(n), total = new Float32Array(n).fill(1);
    for (const filt of [this.low, this.midEq, this.high, ...this.eqBands]) {
      filt.getFrequencyResponse(f, mag, ph);
      for (let i = 0; i < n; i++) total[i] *= mag[i];
    }
    const magDb = new Float32Array(n);
    for (let i = 0; i < n; i++) magDb[i] = 20 * Math.log10(total[i] || 1e-6);
    return { freqs: f, magDb };
  }

  getLevel() {
    if (!this._meterBuf) this._meterBuf = new Float32Array(this._meter.fftSize);
    const buf = this._meterBuf;
    if (this._meter.getFloatTimeDomainData) this._meter.getFloatTimeDomainData(buf);
    let sum = 0, peak = 0;
    for (let i = 0; i < buf.length; i++) { const v = buf[i]; sum += v * v; if (Math.abs(v) > peak) peak = Math.abs(v); }
    const rms = Math.sqrt(sum / buf.length);
    return { rms, peak, db: 20 * Math.log10(rms || 1e-6), clip: peak >= 0.99 };
  }

  get enabled() { return this._enabled; }
  get intensity() { return this._intensity; }
  get presetId() { return this._presetId; }
  get spatialMode() { return this._spatialMode; }
  get multiband() { return this._multiband; }
  get loudnessMatch() { return !!this._loudnessMatch; }
  get state() { return { enabled: this._enabled, preset: this._presetId, intensity: this._intensity, spatialMode: this._spatialMode, multiband: this._multiband, loudnessMatch: !!this._loudnessMatch, loudnessNorm: this._normTarget, crossfeed: this._crossfeed, supported: true }; }

  dispose({ closeContext = false } = {}) {
    try { this.motionLfo.stop(); } catch { /* ok */ }
    if (this._matchTimer) { clearInterval(this._matchTimer); this._matchTimer = null; }
    const nodes = [this.input, this.output, this.pre, this.low, this.midEq, this.high, this.tone,
      this.bassLP, this.bassSat, this.bassGain, ...this.eqBands, this.eqOut, this.splitter, this.merger, this.midL, this.midR,
      this.midBus, this.sideL, this.sideR, this.sideBus, this.sideW, this.sidePlus, this.sideMinus,
      this.vocalBP, this.vocalGain, this.motionLfo, this.motionDepth, this.convolver, this.reverbGain,
      this.stereoBus, this.stereoTap, this.bSplit, this.bRevSplit, this.panFL, this.panFR, this.panRL,
      this.panRR, this.binauralBus, this.binauralTap, this.hrirConv, this.hrirTap, this._preComp, this.comp, this.compTap,
      this.loA, this.loB, this.miHP, this.miLP, this.hiA, this.hiB, this.compLow, this.compMid,
      this.compHigh, this.bandSum, this.mbTap, this.limiterIn, this.limiter, this.makeup, this.matchGain,
      this.cfIn, this.cfSplit, this.cfMerge, this.cfDL, this.cfDR, this.cfLd, this.cfLlp, this.cfLg,
      this.cfRd, this.cfRlp, this.cfRg, this._kw.input, this._kw.output, this._kwMeter, this._workletNode, this._workletSink, this._limNode,
      this.dry, this.wet, this._meter, this._dryMeter, this._wetMeter, this.analyser];
    for (const n of nodes) { try { n && n.disconnect(); } catch { /* ok */ } }
    this._sources.clear();
    if (closeContext && this._ownsContext) { try { this.context.close(); } catch { /* ok */ } }
  }
}

export function createDolby(options) { return new DolbyAudio(options); }
export default DolbyAudio;
