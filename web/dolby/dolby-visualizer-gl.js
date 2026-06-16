// ============================================================
// dolby-visualizer-gl · 音频湍流可视化（WebGL fbm 流体 shader）
// ------------------------------------------------------------
// 用域扭曲 fbm 噪声渲染一团流体星云，由音频驱动：
//   低频/能量 → 流场翻涌强度与流速；频谱高低比 → 色相；节拍 → 亮度爆闪。
// 不支持 WebGL 或着色器编译失败时，createVisualizer() 自动回退到 Canvas2D 版。
//
//   import { createVisualizer } from './dolby-visualizer-gl.js';
//   const viz = createVisualizer(canvas, { dolby });   // GL 优先，失败回退
//   viz.start(); viz.setBaseHue(coverHue);
// ============================================================
import { AudioReactor, resolveAnalyser, DolbyVisualizer, VIZ_PRESETS, VIZ_QUALITY, vizPresetById } from './dolby-visualizer.js';

const FRAG = `
precision mediump float;
uniform vec2 u_res;
uniform float u_t, u_bass, u_mid, u_treble, u_energy, u_beat, u_hue;
uniform sampler2D u_spec;
uniform sampler2D u_cover;
uniform float u_coverMix;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){ float v=0.0,a=0.5; for(int i=0;i<5;i++){ v+=a*noise(p); p=p*2.03+vec2(1.7,9.2); a*=0.55; } return v; }
vec3 hsv2rgb(vec3 c){
  vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz)*6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = (uv - 0.5) * vec2(u_res.x/u_res.y, 1.0) * 2.2;
  p *= 1.0 - u_beat*0.10;                             // 节拍镜头脉冲（zoom）
  float rot = u_t*0.03 + u_mid*0.25;                  // 缓慢镜头旋转
  p = mat2(cos(rot), -sin(rot), sin(rot), cos(rot)) * p;
  float t = u_t * (0.05 + u_energy * 0.18);           // 能量越高流得越快
  float warp = 2.0 + u_bass*4.0 + u_beat*2.5;         // 低频/节拍 → 翻涌更剧
  vec2 q = vec2(fbm(p + t), fbm(p + vec2(5.2,1.3) - t*0.8));
  vec2 r = vec2(fbm(p + warp*q + t*0.5), fbm(p + (warp*0.9)*q - t*0.4));
  float f = fbm(p + (2.4 + u_beat*2.0)*r);
  float hue = u_hue + (u_treble - u_bass)*0.12 + f*0.16;
  float sat = 0.72 + u_energy*0.28;
  float val = 0.10 + smoothstep(0.2,0.95,f)*(0.45 + u_energy*0.65) + u_beat*0.28;
  vec3 col = hsv2rgb(vec3(fract(hue), sat, clamp(val, 0.0, 1.0)));
  col += smoothstep(0.82,1.0,f) * (0.18 + u_beat*0.45);   // 高光/爆闪
  // 封面随流场扭曲混入（"融化"在流体里）
  vec2 cuv = uv + (r - 0.5) * 0.22;
  vec3 cov = texture2D(u_cover, cuv).rgb;
  col = mix(col, col*0.35 + cov*0.95, u_coverMix * 0.6);
  // 径向频段光柱（按角度采样频谱，半径随幅度外扩）
  vec2 dd = uv - 0.5;
  float ang = atan(dd.y, dd.x) / 6.2831853 + 0.5;
  float mag = texture2D(u_spec, vec2(ang, 0.5)).r;
  float ring = smoothstep(0.013, 0.0, abs(length(dd) - (0.30 + mag*0.16)));
  col += ring * hsv2rgb(vec3(fract(u_hue + ang*0.85), 0.85, 1.0)) * (0.6 + u_energy);   // 分色：按角度(频段)跨色
  col *= 1.0 - 0.5*pow(length(uv-0.5), 2.4);          // 暗角
  gl_FragColor = vec4(col, 1.0);
}`;

function compile(gl, type, src) {
  const sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh); gl.deleteShader(sh);
    throw new Error('shader 编译失败: ' + log);
  }
  return sh;
}
function hsvToRgb(h, s, v) {           // h 0..1 → [r,g,b] 0..1
  const i = Math.floor(h * 6), f = h * 6 - i, p = v * (1 - s), q = v * (1 - f * s), w = v * (1 - (1 - f) * s), m = ((i % 6) + 6) % 6;
  return [[v, q, p, p, w, v][m], [w, v, v, q, p, p][m], [p, p, w, v, v, q][m]];
}

export class DolbyVisualizerGL {
  constructor(canvas, options = {}) {
    const gl = canvas.getContext('webgl', { antialias: false, depth: false, alpha: false }) ||
               canvas.getContext('experimental-webgl');
    if (!gl) throw new Error('WebGL 不可用');
    // 先确认着色器可用，再去解析 analyser（避免失败回退时留下半成品连接）
    const vs = compile(gl, gl.VERTEX_SHADER, 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}');
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    const prog = gl.createProgram(); gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('program 链接失败');
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'a'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    this.gl = gl; this.canvas = canvas; this.prog = prog; this.quadBuf = buf; this.aLoc = loc;
    this.u = {}; for (const n of ['u_res', 'u_t', 'u_bass', 'u_mid', 'u_treble', 'u_energy', 'u_beat', 'u_hue', 'u_spec', 'u_cover', 'u_coverMix']) this.u[n] = gl.getUniformLocation(prog, n);
    // 频谱纹理（频段光柱用）：N×1 LUMINANCE，每帧上传
    this._specN = 128; this._spec = new Uint8Array(this._specN);
    this.specTex = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this.specTex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, this._specN, 1, 0, gl.LUMINANCE, gl.UNSIGNED_BYTE, this._spec);
    gl.uniform1i(this.u.u_spec, 0);
    // 封面纹理（背景混合用）：默认 1×1 占位，setCover 上传后才显现
    this._coverMix = 0; this._coverMixTarget = 0;
    this.coverTex = gl.createTexture();
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, this.coverTex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
    gl.uniform1i(this.u.u_cover, 1);
    gl.uniform1f(this.u.u_coverMix, 0);
    gl.activeTexture(gl.TEXTURE0);

    // 粒子层（叠加在流体之上，gl.POINTS 加色发光）；编译失败则跳过，不影响流体
    this._pointsOk = false;
    try {
      const pvs = compile(gl, gl.VERTEX_SHADER, 'attribute vec2 a_pos;uniform float u_size;void main(){gl_Position=vec4(a_pos,0.,1.);gl_PointSize=u_size;}');
      const pfs = compile(gl, gl.FRAGMENT_SHADER, 'precision mediump float;uniform vec3 u_col;void main(){vec2 d=gl_PointCoord-0.5;float a=smoothstep(0.5,0.0,length(d));gl_FragColor=vec4(u_col*a,a);}');
      const pp = gl.createProgram(); gl.attachShader(pp, pvs); gl.attachShader(pp, pfs); gl.linkProgram(pp);
      if (!gl.getProgramParameter(pp, gl.LINK_STATUS)) throw new Error('points link');
      this.pProg = pp; this.paLoc = gl.getAttribLocation(pp, 'a_pos');
      this.uPSize = gl.getUniformLocation(pp, 'u_size'); this.uPCol = gl.getUniformLocation(pp, 'u_col');
      this._pn = options.points ?? 80; this._pts = new Float32Array(this._pn * 2);
      for (let i = 0; i < this._pn; i++) { this._pts[2 * i] = Math.random() * 2 - 1; this._pts[2 * i + 1] = Math.random() * 2 - 1; }
      this.pBuf = gl.createBuffer();
      this._pointsOk = true;
    } catch { this._pointsOk = false; }

    this.analyser = resolveAnalyser(options);
    this.analyser.fftSize = options.fftSize || 1024;
    this.reactor = new AudioReactor(this.analyser);
    this.baseHue = options.baseHue ?? 270;
    this.hueRange = options.hueRange ?? 80;
    this.scale = options.scale ?? Math.min(globalThis.devicePixelRatio || 1, 1.5);
    this._hue = this.baseHue / 360; this._pulse = 0; this._t0 = (globalThis.performance?.now?.() ?? 0); this._raf = 0; this._running = false;
    this._minDt = 0; this._lastTs = 0;
    this._onResize = () => this.resize();
    if (typeof addEventListener === 'function') addEventListener('resize', this._onResize);
    this.resize();
    if (options.vizPreset) this.setVizPreset(options.vizPreset);
    if (options.quality) this.setQuality(options.quality);
  }

  get renderer() { return 'webgl'; }
  resize() {
    const w = Math.max(2, Math.floor((this.canvas.clientWidth || 320) * this.scale));
    const h = Math.max(2, Math.floor((this.canvas.clientHeight || 200) * this.scale));
    this.canvas.width = w; this.canvas.height = h; this.gl.viewport(0, 0, w, h);
  }
  setBaseHue(h) { this.baseHue = ((h % 360) + 360) % 360; return this; }
  setParticles() { return this; }                 // GL 无粒子概念，留空以统一接口
  /** 把封面图（Image/Canvas，需 CORS 干净）作为背景纹理混入流体 */
  setCover(img) {
    const gl = this.gl;
    try {
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, this.coverTex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.activeTexture(gl.TEXTURE0);
      this._coverMixTarget = 1;
    } catch { this._coverMixTarget = 0; }   // 跨域污染等 → 不混入
    return this;
  }
  clearCover() { this._coverMixTarget = 0; return this; }
  /** 视觉预设（配色风格） */
  setVizPreset(id) { const p = vizPresetById(id); this.baseHue = p.baseHue; this.hueRange = p.hueRange; this._vizPreset = p.id; return this; }
  /** 性能档位 'low' | 'mid' | 'high'（渲染分辨率 + 粒子数 + 帧率） */
  setQuality(q) {
    const m = VIZ_QUALITY[q] || VIZ_QUALITY.mid; this._quality = (q in VIZ_QUALITY) ? q : 'mid';
    this._minDt = 1000 / m.fps;
    this.scale = m.scale ?? Math.min(globalThis.devicePixelRatio || 1, 1.5);
    this.resize();
    if (this._pointsOk) { this._pn = m.points; this._pts = new Float32Array(this._pn * 2); for (let i = 0; i < this._pn; i++) { this._pts[2 * i] = Math.random() * 2 - 1; this._pts[2 * i + 1] = Math.random() * 2 - 1; } }
    return this;
  }
  get vizPreset() { return this._vizPreset; }
  get quality() { return this._quality; }
  analyze() { return this.reactor.read(); }

  start() {
    if (this._running) return this;
    this._running = true;
    if (typeof requestAnimationFrame === 'function') {
      const loop = (ts) => { if (!this._running) return; this._raf = requestAnimationFrame(loop); if (this._minDt && ts - this._lastTs < this._minDt) return; this._lastTs = ts; this._frame(); };
      this._raf = requestAnimationFrame(loop);
    }
    return this;
  }
  stop() { this._running = false; if (this._raf && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this._raf); return this; }
  get running() { return this._running; }
  get last() { return this._last || { bass: 0, mid: 0, treble: 0, energy: 0, beat: false, bpm: 0 }; }

  _frame() {
    const f = this._last = this.reactor.read();
    const { bass, mid, treble, energy, beat } = f;
    this._pulse = Math.max(this._pulse * 0.9, beat ? 1 : 0);
    const targetHue = (this.baseHue + (treble - bass) * this.hueRange) / 360;
    this._hue += (targetHue - this._hue) * 0.05;
    const gl = this.gl, u = this.u, now = (globalThis.performance?.now?.() ?? Date.now());
    // 流体程序 + 全屏三角形（粒子层会切换程序/缓冲，每帧复位）
    gl.useProgram(this.prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.enableVertexAttribArray(this.aLoc); gl.vertexAttribPointer(this.aLoc, 2, gl.FLOAT, false, 0, 0);
    // 频谱降采样 → 上传纹理（频段光柱）
    const src = this.reactor.data, sn = src.length, N = this._specN, spec = this._spec;
    for (let k = 0; k < N; k++) spec[k] = src[(k * sn / N) | 0];
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this.specTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, N, 1, 0, gl.LUMINANCE, gl.UNSIGNED_BYTE, spec);
    gl.uniform1i(u.u_spec, 0);
    // 封面混合渐入/渐出
    this._coverMix += (this._coverMixTarget - this._coverMix) * 0.06;
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, this.coverTex); gl.uniform1i(u.u_cover, 1);
    gl.uniform1f(u.u_coverMix, this._coverMix);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform2f(u.u_res, this.canvas.width, this.canvas.height);
    gl.uniform1f(u.u_t, (now - this._t0) / 1000);
    gl.uniform1f(u.u_bass, bass); gl.uniform1f(u.u_mid, mid); gl.uniform1f(u.u_treble, treble);
    gl.uniform1f(u.u_energy, energy); gl.uniform1f(u.u_beat, this._pulse); gl.uniform1f(u.u_hue, this._hue);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    // 粒子层（流场平流 + 加色发光，节拍时变亮变大）
    if (this._pointsOk) {
      const pts = this._pts, pn = this._pn, tt = (now - this._t0) / 1000, spd = 0.0015 + energy * 0.012, turb = 0.6 + bass * 2.0;
      for (let i = 0; i < pn; i++) {
        let x = pts[2 * i], y = pts[2 * i + 1];
        const ang = (Math.sin(x * 3 + tt * 0.3) + Math.sin(y * 3.2 - tt * 0.25) + Math.sin((x + y) * 2 + tt * 0.2)) * turb;
        x += Math.cos(ang) * spd; y += Math.sin(ang) * spd;
        if (x < -1) x += 2; else if (x > 1) x -= 2;
        if (y < -1) y += 2; else if (y > 1) y -= 2;
        pts[2 * i] = x; pts[2 * i + 1] = y;
      }
      gl.useProgram(this.pProg);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pBuf);
      gl.bufferData(gl.ARRAY_BUFFER, pts, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(this.paLoc); gl.vertexAttribPointer(this.paLoc, 2, gl.FLOAT, false, 0, 0);
      gl.uniform1f(this.uPSize, (3 + energy * 10 + this._pulse * 8) * this.scale);
      const c = hsvToRgb(this._hue, 0.7, 1.0), k = 0.4 + this._pulse * 0.6;
      gl.uniform3f(this.uPCol, c[0] * k, c[1] * k, c[2] * k);
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.drawArrays(gl.POINTS, 0, pn);
      gl.disable(gl.BLEND);
    }
  }

  dispose() { this.stop(); try { this.gl.deleteTexture(this.specTex); this.gl.deleteTexture(this.coverTex); if (this.pProg) this.gl.deleteProgram(this.pProg); if (this.pBuf) this.gl.deleteBuffer(this.pBuf); } catch { /* ok */ } if (typeof removeEventListener === 'function') removeEventListener('resize', this._onResize); }
}

/** 优先 WebGL，失败（无 WebGL / 编译失败）自动回退到 Canvas2D。renderer:'webgl'|'canvas' 可强制 */
export function createVisualizer(canvas, options = {}) {
  if (options.renderer !== 'canvas') {
    try { return new DolbyVisualizerGL(canvas, options); }
    catch (e) { if (options.renderer === 'webgl') throw e; /* 否则回退 */ }
  }
  return new DolbyVisualizer(canvas, options);
}

export default DolbyVisualizerGL;
