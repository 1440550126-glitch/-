// ============================================================
// dolby-visualizer · 音频湍流可视化（独立 / 零依赖 / Canvas2D）
// ------------------------------------------------------------
// 读取引擎的频谱，把声音化成一团跟随节奏流动、随频谱变色的"湍流"：
//   · 低频/能量 → 流场强度与粒子速度（越炸越翻涌）
//   · 频谱高低比 + 时间 → 色相漂移（变色）
//   · 节拍 → 爆发式冲击环 + 亮度闪动（视觉冲击）
// 加色（lighter）叠加 + 半透明拖尾，形成流体/极光质感。
//
//   import { DolbyVisualizer } from './dolby-visualizer.js';
//   const viz = new DolbyVisualizer(canvas, { dolby });   // dolby 需 analyser:true
//   viz.start();                  // 或 new DolbyVisualizer(canvas, { analyser })
//   viz.setBaseHue(coverHue);     // 配合封面取色换肤
// ============================================================

const DPR = () => Math.min(globalThis.devicePixelRatio || 1, 2);

export function resolveAnalyser(o) {
  if (o.analyser) return o.analyser;
  if (o.dolby) {
    const a = o.dolby.getAnalyser();
    if (a) return a;
    const an = o.dolby.context.createAnalyser(); o.dolby.output.connect(an); return an;
  }
  if (o.node && o.context) { const an = o.context.createAnalyser(); o.node.connect(an); return an; }
  throw new Error('可视化需要 analyser / dolby / {node,context} 之一');
}

// 频谱分析 + 节拍检测 + BPM 估计（Canvas 与 WebGL 渲染器共用）
export class AudioReactor {
  constructor(analyser) { this.analyser = analyser; this.data = new Uint8Array(analyser.frequencyBinCount); this._bassEMA = 0; this._intervals = []; this._lastBeat = 0; }
  read(now = (globalThis.performance && globalThis.performance.now ? globalThis.performance.now() : Date.now())) {
    const d = this.data; this.analyser.getByteFrequencyData(d);
    const n = d.length;
    const band = (a, b) => { let s = 0; for (let i = a; i < b; i++) s += d[i]; return (b > a) ? s / ((b - a) * 255) : 0; };
    const bass = band(0, Math.max(1, n * 0.08 | 0));
    const mid = band(n * 0.08 | 0, n * 0.4 | 0);
    const treble = band(n * 0.4 | 0, n);
    const energy = (bass * 1.4 + mid + treble * 0.7) / 3.1;
    const beat = bass > this._bassEMA * 1.35 && bass > 0.22;
    this._bassEMA = this._bassEMA * 0.92 + bass * 0.08;
    if (beat) {
      if (this._lastBeat) { const dt = now - this._lastBeat; if (dt > 250 && dt < 2000) { this._intervals.push(dt); if (this._intervals.length > 8) this._intervals.shift(); } }
      this._lastBeat = now;
    }
    let bpm = 0;
    if (this._intervals.length) { const s = [...this._intervals].sort((a, b) => a - b); bpm = Math.round(60000 / s[s.length >> 1]); }
    return { bass, mid, treble, energy, beat, bpm };
  }
}

export class DolbyVisualizer {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {object} options  analyser | dolby（需 analyser:true）| {node, context}
   *   baseHue=270 基础色相 / hueRange=80 频谱影响幅度 / particles=90 / background=[10,8,18]
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = resolveAnalyser(options);
    this.analyser.fftSize = options.fftSize || 1024;
    this.reactor = new AudioReactor(this.analyser);
    this.baseHue = options.baseHue ?? 270;
    this.hueRange = options.hueRange ?? 80;
    this.particleCount = options.particles ?? 90;
    this.bg = options.background ?? [10, 8, 18];
    this.particles = []; this.rings = []; this._cover = null;
    this._t = 0; this._raf = 0; this._running = false; this._hue = this.baseHue; this._pulse = 0;
    this._onResize = () => this.resize();
    if (typeof addEventListener === 'function') addEventListener('resize', this._onResize);
    this.resize();
    this._initParticles();
  }

  resize() {
    const dpr = DPR();
    this.w = this.canvas.clientWidth || this.canvas.width || 320;
    this.h = this.canvas.clientHeight || this.canvas.height || 200;
    this.canvas.width = this.w * dpr; this.canvas.height = this.h * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  _initParticles() {
    this.particles = [];
    for (let i = 0; i < this.particleCount; i++) this.particles.push({ x: Math.random() * this.w, y: Math.random() * this.h, hueOff: Math.random() * 40 - 20 });
  }
  setBaseHue(h) { this.baseHue = ((h % 360) + 360) % 360; return this; }
  setParticles(n) { this.particleCount = Math.max(1, n | 0); this._initParticles(); return this; }
  /** 设置封面图（Image/Canvas）作为暗淡背景层；接口与 WebGL 版一致 */
  setCover(img) { this._cover = img || null; return this; }
  clearCover() { this._cover = null; return this; }

  start() {
    if (this._running) return this;
    this._running = true;
    if (typeof requestAnimationFrame === 'function') {
      const loop = () => { if (!this._running) return; this._raf = requestAnimationFrame(loop); this._frame(); };
      this._raf = requestAnimationFrame(loop);
    }
    return this;
  }
  stop() { this._running = false; if (this._raf && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this._raf); return this; }
  get running() { return this._running; }

  /** 取一帧的频谱特征：低/中/高频能量、总能量、是否节拍 */
  analyze() { return this.reactor.read(); }

  get last() { return this._last || { bass: 0, mid: 0, treble: 0, energy: 0, beat: false, bpm: 0 }; }
  _frame() {
    const f = this._last = this.analyze();
    const { bass, mid, treble, energy, beat } = f;
    this._pulse = Math.max(this._pulse * 0.9, beat ? 1 : 0);
    const ctx = this.ctx, w = this.w, h = this.h, t = (this._t += 0.016), pulse = this._pulse;
    ctx.globalCompositeOperation = 'source-over';
    if (this._cover) { try { ctx.globalAlpha = 0.5; ctx.drawImage(this._cover, 0, 0, w, h); ctx.globalAlpha = 1; } catch { /* ok */ } }
    // 半透明拖尾（同时把封面压暗）
    ctx.fillStyle = `rgba(${this.bg[0]},${this.bg[1]},${this.bg[2]},0.18)`;
    ctx.fillRect(0, 0, w, h);
    // 色相随频谱倾斜 + 缓慢漂移，节拍时多偏一点
    const tilt = treble - bass;
    this._hue += ((this.baseHue + tilt * this.hueRange + t * 6 + (beat ? 18 : 0)) - this._hue) * 0.05;
    if (beat) this.rings.push({ x: w / 2, y: h / 2, r: 4, a: 0.6 });
    // 镜头脉冲：以中心随节拍缩放整幅
    ctx.save();
    ctx.translate(w / 2, h / 2); const z = 1 + pulse * 0.06; ctx.scale(z, z); ctx.translate(-w / 2, -h / 2);
    ctx.globalCompositeOperation = 'lighter';
    // 湍流粒子（流场平流 + 拖尾辉光）
    const turb = 0.6 + bass * 2.4, speed = 0.5 + energy * 3.5;
    const light = Math.min(80, 45 + energy * 40 + (beat ? 15 : 0)), size = 1.5 + bass * 6 + (beat ? 2 : 0);
    ctx.shadowBlur = 6 + bass * 22;
    for (const p of this.particles) {
      const ang = (Math.sin(p.x * 0.003 + t * 0.3) + Math.sin(p.y * 0.0034 - t * 0.25) + Math.sin((p.x + p.y) * 0.002 + t * 0.2)) * Math.PI * turb;
      p.x += Math.cos(ang) * speed; p.y += Math.sin(ang) * speed;
      if (p.x < 0) p.x += w; else if (p.x > w) p.x -= w;
      if (p.y < 0) p.y += h; else if (p.y > h) p.y -= h;
      const hue = (this._hue + p.hueOff) % 360;
      ctx.shadowColor = `hsl(${hue},90%,60%)`;
      ctx.fillStyle = `hsla(${hue}, 90%, ${light}%, 0.5)`;
      ctx.beginPath(); ctx.arc(p.x, p.y, size, 0, Math.PI * 2); ctx.fill();
    }
    ctx.shadowBlur = 0;
    this._drawBars(ctx, w, h, energy);            // 频段光柱
    // 节拍冲击环
    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i]; r.r += 6 + energy * 8; r.a *= 0.92;
      if (r.a < 0.03) { this.rings.splice(i, 1); continue; }
      ctx.strokeStyle = `hsla(${this._hue % 360},90%,65%,${r.a})`; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
    ctx.globalCompositeOperation = 'source-over';
  }

  // 径向频段光柱：从中心向外按频谱画一圈光柱
  _drawBars(ctx, w, h, energy) {
    const d = this.reactor.data, n = d.length, N = 64, cx = w / 2, cy = h / 2;
    const r0 = Math.min(w, h) * 0.18, len = Math.min(w, h) * 0.16;
    ctx.lineWidth = Math.max(2, (w / N) * 0.4);
    for (let k = 0; k < N; k++) {
      const mag = d[(k * n / N) | 0] / 255;
      if (mag < 0.04) continue;
      const ang = (k / N) * Math.PI * 2 - Math.PI / 2, c = Math.cos(ang), s = Math.sin(ang);
      const r1 = r0 + mag * len * (1.4 + energy);
      ctx.strokeStyle = `hsla(${(this._hue + (k / N) * 300) % 360}, 90%, ${50 + mag * 30}%, ${0.4 + mag * 0.5})`;  // 分色：低→高频跨色
      ctx.beginPath(); ctx.moveTo(cx + c * r0, cy + s * r0); ctx.lineTo(cx + c * r1, cy + s * r1); ctx.stroke();
    }
  }

  dispose() { this.stop(); if (typeof removeEventListener === 'function') removeEventListener('resize', this._onResize); }
}

/** 从已加载的图片取平均主色（封面取色换肤用）：返回 { r, g, b, hue } */
export function coverColor(img) {
  if (typeof document === 'undefined') throw new Error('coverColor 需要浏览器环境');
  const s = 16, c = document.createElement('canvas'); c.width = s; c.height = s;
  const cx = c.getContext('2d'); cx.drawImage(img, 0, 0, s, s);
  const d = cx.getImageData(0, 0, s, s).data;
  let r = 0, g = 0, b = 0, n = 0;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; n++; }
  r = (r / n) | 0; g = (g / n) | 0; b = (b / n) | 0;
  return { r, g, b, hue: rgbToHue(r, g, b) };
}
function rgbToHue(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let hbase = 0;
  if (d) { if (mx === r) hbase = ((g - b) / d) % 6; else if (mx === g) hbase = (b - r) / d + 2; else hbase = (r - g) / d + 4; hbase *= 60; if (hbase < 0) hbase += 360; }
  return hbase;
}

export function createVisualizer(canvas, options) { return new DolbyVisualizer(canvas, options); }
export default DolbyVisualizer;
