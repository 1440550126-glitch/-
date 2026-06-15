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

function resolveAnalyser(o) {
  if (o.analyser) return o.analyser;
  if (o.dolby) {
    const a = o.dolby.getAnalyser();
    if (a) return a;
    const an = o.dolby.context.createAnalyser(); o.dolby.output.connect(an); return an;
  }
  if (o.node && o.context) { const an = o.context.createAnalyser(); o.node.connect(an); return an; }
  throw new Error('DolbyVisualizer 需要 analyser / dolby / {node,context} 之一');
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
    this.data = new Uint8Array(this.analyser.frequencyBinCount);
    this.baseHue = options.baseHue ?? 270;
    this.hueRange = options.hueRange ?? 80;
    this.particleCount = options.particles ?? 90;
    this.bg = options.background ?? [10, 8, 18];
    this.particles = []; this.rings = [];
    this._bassEMA = 0; this._t = 0; this._raf = 0; this._running = false; this._hue = this.baseHue;
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
  analyze() {
    const d = this.data; this.analyser.getByteFrequencyData(d);
    const n = d.length;
    const band = (a, b) => { let s = 0; for (let i = a; i < b; i++) s += d[i]; return (b > a) ? s / ((b - a) * 255) : 0; };
    const bass = band(0, Math.max(1, n * 0.08 | 0));
    const mid = band(n * 0.08 | 0, n * 0.4 | 0);
    const treble = band(n * 0.4 | 0, n);
    const energy = (bass * 1.4 + mid + treble * 0.7) / 3.1;
    const beat = bass > this._bassEMA * 1.35 && bass > 0.22;   // 与运行均值比较
    this._bassEMA = this._bassEMA * 0.92 + bass * 0.08;
    return { bass, mid, treble, energy, beat };
  }

  _frame() {
    const { bass, mid, treble, energy, beat } = this.analyze();
    const ctx = this.ctx, w = this.w, h = this.h, t = (this._t += 0.016);
    // 半透明拖尾
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = `rgba(${this.bg[0]},${this.bg[1]},${this.bg[2]},0.16)`;
    ctx.fillRect(0, 0, w, h);
    // 色相随频谱倾斜 + 缓慢漂移，节拍时多偏一点
    const tilt = treble - bass;
    const targetHue = this.baseHue + tilt * this.hueRange + t * 6 + (beat ? 18 : 0);
    this._hue += (targetHue - this._hue) * 0.05;
    if (beat) this.rings.push({ x: w / 2 + (Math.random() - 0.5) * w * 0.3, y: h / 2 + (Math.random() - 0.5) * h * 0.3, r: 4, a: 0.7 });
    // 湍流粒子（流场平流，强度随低频/能量）
    ctx.globalCompositeOperation = 'lighter';
    const turb = 0.6 + bass * 2.4, speed = 0.5 + energy * 3.5;
    const light = Math.min(80, 45 + energy * 40 + (beat ? 15 : 0)), size = 1.5 + bass * 6 + (beat ? 2 : 0);
    for (const p of this.particles) {
      const ang = (Math.sin(p.x * 0.003 + t * 0.3) + Math.sin(p.y * 0.0034 - t * 0.25) + Math.sin((p.x + p.y) * 0.002 + t * 0.2)) * Math.PI * turb;
      p.x += Math.cos(ang) * speed; p.y += Math.sin(ang) * speed;
      if (p.x < 0) p.x += w; else if (p.x > w) p.x -= w;
      if (p.y < 0) p.y += h; else if (p.y > h) p.y -= h;
      ctx.fillStyle = `hsla(${(this._hue + p.hueOff) % 360}, 90%, ${light}%, 0.5)`;
      ctx.beginPath(); ctx.arc(p.x, p.y, size, 0, Math.PI * 2); ctx.fill();
    }
    // 节拍冲击环
    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i]; r.r += 6 + energy * 8; r.a *= 0.92;
      if (r.a < 0.03) { this.rings.splice(i, 1); continue; }
      ctx.strokeStyle = `hsla(${this._hue % 360},90%,65%,${r.a})`; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
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
