// ============================================================
// 句灵 · 文字变动画引擎 v3「未来已来」
// ------------------------------------------------------------
// 3D 流体粒子文字：成千上万颗发光粒子在 curl-noise 流体场中
// 以透视景深汇聚成你写下的句子，再「活」着呼吸、流动、表达情绪。
//
// 设计原则（针对旧版「线条简笔画」的彻底重做）：
//   · 不再有任何 stroke 描边的火柴人 / 云 / 伞 —— 一切皆为光与粒子
//   · 加性辉光（lighter 混合 + 预渲染辉光精灵）做出全息 bloom 质感
//   · 透视投影 + 缓慢摄像机偏航 → 真 3D 体积感与视差
//   · curl 噪声流体场 → 有机、非线性、像液体一样的运动
//   · 情绪不是标签，而是「运动签名」：文字怎么动，就在表达什么情绪
// ============================================================
import { SoundScape } from './sound.js';

const TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, p) => a + (b - a) * p;
const smooth = (t) => t * t * (3 - 2 * t);

// ---- 非线性缓动（汇聚的灵魂） ----
const easeOutCubic = (p) => 1 - Math.pow(1 - p, 3);
const easeOutExpo = (p) => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p));
const easeInOutSine = (p) => 0.5 - 0.5 * Math.cos(Math.PI * p);
const easeOutBack = (p) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const easeOutElastic = (p) => (p === 0 || p === 1 ? p : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * (TAU / 3)) + 1);
const EASE = { cubic: easeOutCubic, expo: easeOutExpo, sine: easeInOutSine, back: easeOutBack, elastic: easeOutElastic };

// ---- 2D 平滑噪声 + curl（无散度流体场） ----
function hash2(x, y, s) { const n = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return n - Math.floor(n); }
function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = smooth(xf), v = smooth(yf);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return lerp(lerp(a, b, u), lerp(c, d, u), v);
}
function curl(x, y, s) {
  const e = 0.2;
  const dy = (vnoise(x, y + e, s) - vnoise(x, y - e, s)) / (2 * e);
  const dx = (vnoise(x + e, y, s) - vnoise(x - e, y, s)) / (2 * e);
  return [dy, -dx]; // 旋度 → 漩涡流动
}

// ---- 情绪画像：valence/arousal + 运动签名 ----
// conv 汇聚缓动 · grav 重力(正=下坠) · swirl 流体湍流 · breath 呼吸幅度
// warm 色温(暖↔冷) · out 散场方式 · beat 心跳脉冲 · sparse 稀疏度
const EMO = {
  热血: { val: 0.70, aro: 0.95, grav: -0.10, swirl: 1.7, conv: 'back', breath: 0.10, warm: 0.85, out: 'burst' },
  心动: { val: 0.85, aro: 0.62, grav: -0.02, swirl: 0.9, conv: 'elastic', breath: 0.16, warm: 0.70, out: 'rise', beat: true },
  搞笑: { val: 0.60, aro: 0.78, grav: 0.00, swirl: 1.9, conv: 'back', breath: 0.13, warm: 0.55, out: 'scatter' },
  治愈: { val: 0.55, aro: 0.32, grav: -0.05, swirl: 0.7, conv: 'expo', breath: 0.09, warm: 0.45, out: 'rise' },
  平静: { val: 0.20, aro: 0.16, grav: 0.00, swirl: 0.4, conv: 'sine', breath: 0.06, warm: 0.10, out: 'fade' },
  思念: { val: -0.10, aro: 0.32, grav: 0.02, swirl: 0.8, conv: 'expo', breath: 0.07, warm: -0.05, out: 'driftX' },
  孤独: { val: -0.45, aro: 0.26, grav: 0.05, swirl: 0.5, conv: 'sine', breath: 0.05, warm: -0.30, out: 'fall', sparse: 0.72 },
  难过: { val: -0.75, aro: 0.46, grav: 0.16, swirl: 0.6, conv: 'expo', breath: 0.05, warm: -0.55, out: 'fall' }
};
const EMO_DEFAULT = EMO.治愈;

// ---- 颜色工具 ----
function hex2rgb(h) {
  const m = /^#?([0-9a-f]{6})$/i.exec(h || '');
  if (!m) return [157, 140, 255];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
const WARM = [255, 196, 130], COOL = [120, 170, 255];
function temperated(rgb, warm) {
  const t = clamp(warm, -1, 1);
  const tgt = t >= 0 ? WARM : COOL;
  const k = Math.abs(t) * 0.4;
  return [lerp(rgb[0], tgt[0], k), lerp(rgb[1], tgt[1], k), lerp(rgb[2], tgt[2], k)];
}

// ---- 预渲染辉光精灵：软核 + 内嵌白热核心（一次 drawImage 即全息光点） ----
function glowSprite(rgb, R, coreWhite) {
  const s = Math.ceil(R * 2);
  const cv = document.createElement('canvas'); cv.width = s; cv.height = s;
  const g = cv.getContext('2d');
  const [r, gg, b] = rgb;
  const grd = g.createRadialGradient(R, R, 0, R, R, R);
  grd.addColorStop(0, `rgba(${r | 0},${gg | 0},${b | 0},0.9)`);
  grd.addColorStop(0.3, `rgba(${r | 0},${gg | 0},${b | 0},0.42)`);
  grd.addColorStop(0.65, `rgba(${r | 0},${gg | 0},${b | 0},0.12)`);
  grd.addColorStop(1, `rgba(${r | 0},${gg | 0},${b | 0},0)`);
  g.fillStyle = grd; g.fillRect(0, 0, s, s);
  if (coreWhite) {
    const cg = g.createRadialGradient(R, R, 0, R, R, R * 0.42);
    cg.addColorStop(0, `rgba(255,255,255,${coreWhite})`);
    cg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = cg; g.fillRect(0, 0, s, s);
  }
  return cv;
}

// ---- 文字 → 3D 粒子（目标点采样 + 流体起点 + 错峰延迟） ----
function sampleText(text, W, H, rnd, thickness) {
  const off = document.createElement('canvas');
  const c = off.getContext('2d');
  const maxW = Math.min(W * 0.84, 480);   // 行宽上限：宽屏不至于拉太开
  let size = text.length <= 10 ? 46 : text.length <= 24 ? 34 : text.length <= 60 ? 25 : 19;
  size = Math.min(size, Math.floor(W / 8.5));
  const font = `700 ${size}px "PingFang SC", "Noto Sans SC", system-ui, sans-serif`;
  c.font = font;
  const lines = []; let line = '';
  for (const ch of text) {
    if (ch === '\n' || c.measureText(line + ch).width > maxW) { lines.push(line); line = ch === '\n' ? '' : ch; }
    else line += ch;
  }
  if (line) lines.push(line);
  const lh = size * 1.5;
  off.width = W; off.height = Math.ceil(lines.length * lh + size);
  c.font = font; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = '#fff';
  lines.forEach((ln, i) => c.fillText(ln, W / 2, size * 0.78 + i * lh));

  const img = c.getImageData(0, 0, off.width, off.height).data;
  const raw = [];
  const step = text.length > 60 ? 4 : 3;
  for (let y = 0; y < off.height; y += step) {
    for (let x = 0; x < W; x += step) {
      if (img[(y * W + x) * 4 + 3] > 110) raw.push([x, y]);
    }
  }
  const cx = W / 2, cyText = off.height / 2;
  const offsetY = H * 0.40 - cyText;       // 文字块在屏幕上的位置（略高于中线）
  const cap = 1150;
  const keep = raw.length > cap ? cap / raw.length : 1;
  const maxDim = Math.hypot(W, H);
  const pts = [];
  for (let i = 0; i < raw.length; i++) {
    if (Math.random() > keep) continue;
    const [px, py] = raw[i];
    const tx = px, ty = py + offsetY;
    const tz = (rnd() - 0.5) * thickness;          // 字体本身的厚度 → 体积
    // 流体起点：环绕中心的一圈「光尘风暴」
    const ang = rnd() * TAU, rad = (0.55 + rnd() * 0.9) * maxDim * 0.5;
    const radial = Math.hypot(tx - cx, ty - (H * 0.4)); // 离字心的距离 → 错峰
    pts.push({
      tx, ty, tz,
      x: cx + Math.cos(ang) * rad, y: H * 0.4 + Math.sin(ang) * rad * 0.72, z: (rnd() - 0.5) * thickness * 9,
      delay: clamp(radial / (W * 0.6), 0, 1) * 0.45 + rnd() * 0.32,
      seed: rnd() * 1000, fseed: rnd() * 10 + 1,
      hot: rnd() < 0.22                              // 少量白热粒子 → 层次
    });
  }
  return { pts, size, top: H * 0.4 - cyText, bottom: H * 0.4 + cyText };
}

// ---- 心形粒子（心动 / 心碎，替代旧版描边爱心） ----
function sampleHeart(rnd, n, R) {
  const arr = [];
  for (let i = 0; i < n; i++) {
    const tt = (i / n) * TAU;
    const k = 0.5 + rnd() * 0.5;                     // 内部填充
    const hx = 16 * Math.pow(Math.sin(tt), 3);
    const hy = -(13 * Math.cos(tt) - 5 * Math.cos(2 * tt) - 2 * Math.cos(3 * tt) - Math.cos(4 * tt));
    arr.push({ bx: hx / 16 * R * k, by: hy / 16 * R * k, half: hx >= 0 ? 1 : -1, ph: rnd() * TAU, sp: 0.6 + rnd() * 0.8 });
  }
  return arr;
}

// ---- 环境粒子（雨/雪/花瓣/星/萤/火星/气泡/风），全部加性发光 ----
function spawnAmbient(kind, density, W, H, rnd) {
  const base = { windline: 9, raindrop: 60, snowflake: 46, petal: 22, star: 70, spark: 34, firefly: 20, bubble: 20, shard: 0 };
  const n = Math.round((base[kind] ?? 16) * clamp(density, 0.1, 1) * 1.5);
  const arr = [];
  for (let i = 0; i < n; i++) {
    arr.push({ kind, x: rnd() * W, y: rnd() * H, v: 0.5 + rnd() * 0.9, ph: rnd() * TAU, sz: 0.6 + rnd() * 1.5, depth: 0.4 + rnd() * 0.6 });
  }
  return arr;
}

// ============================================================
// 主引擎
// ============================================================
export function playManifest(canvas, manifest, opts = {}) {
  const c = canvas.getContext('2d');
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const reduce = matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  let W = 0, H = 0;
  function resize() {
    W = canvas.clientWidth || canvas.width; H = canvas.clientHeight || canvas.height;
    canvas.width = Math.max(2, W * dpr); canvas.height = Math.max(2, H * dpr);
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  const onResize = () => { resize(); rebuild(); };
  addEventListener('resize', onResize);

  const m = manifest || {};
  const submit = !!opts.submitMode;                 // 发帖提交动效：短、不循环、最后 fly-out
  const loopOn = !submit && m.behavior?.loop !== false;

  // 调色板 + 情绪
  const pal = m.palette || { bg: ['#10101e', '#1b1c30'], ink: '#e9e6f7', accent: '#9d8cff', glow: '#7c6cff' };
  const profile = EMO[m.emotion?.key] || EMO_DEFAULT;
  const arousal = m.emotion?.arousal ?? profile.aro;
  const valence = m.emotion?.valence ?? profile.val;
  const intensity = m.emotion?.intensity ?? clamp(0.45 + arousal * 0.4, 0.3, 1);
  const breathAmp = (m.behavior?.breath ? clamp(m.behavior.breath, 0.3, 1.4) : 1) * profile.breath;

  // 色温调制后的粒子颜色
  const glowRGB = temperated(hex2rgb(pal.glow || pal.accent), profile.warm);
  const accentRGB = temperated(hex2rgb(pal.accent || pal.glow), profile.warm * 0.7);
  const bgRGB = [hex2rgb(pal.bg?.[0] || '#10101e'), hex2rgb(pal.bg?.[1] || '#1b1c30')];

  // 预渲染精灵（随调色板烘焙一次）
  let SP = {};
  function bakeSprites() {
    SP = {
      text: glowSprite(glowRGB, 24, 0.85),
      hot: glowSprite([255, 255, 255], 20, 0.0),
      accent: glowSprite(accentRGB, 22, 0.3),
      white: glowSprite([255, 255, 255], 18, 0.0),
      pink: glowSprite([255, 150, 196], 20, 0.35),
      warm: glowSprite([255, 196, 130], 20, 0.4),
      cool: glowSprite([150, 200, 255], 20, 0.2)
    };
  }
  bakeSprites();

  // 随机源（可复现）
  let rndS = ((m.seed || 12345) >>> 0) || 1;
  const rnd = () => ((rndS = (rndS * 1103515245 + 12345) >>> 0) / 4294967296);

  // 构建场景对象
  let text = null, ambient = [], heart = null, orbs = [], flows = [];
  const thickness = 26 * (m.text?.thickness || 1);
  function rebuild() {
    rndS = ((m.seed || 12345) >>> 0) || 1;
    text = sampleText(opts.text || m.text_content || '句灵', W, H, rnd, thickness);
    ambient = [];
    const densMul = profile.sparse || 1;
    for (const p of m.particles || []) ambient.push(...spawnAmbient(p.kind, (p.density ?? 0.4) * densMul, W, H, rnd));
    if (opts.fxPayload?.trail) ambient.push(...spawnAmbient(opts.fxPayload.trail, 0.4 * densMul, W, H, rnd));
    if (!ambient.length) ambient.push(...spawnAmbient(valence < -0.2 ? 'firefly' : 'star', 0.3, W, H, rnd));
    if (ambient.length > 420) ambient.length = 420;                  // 性能护栏

    // 心 / 心碎
    heart = null;
    const hasHeart = (m.actors || []).some((a) => a.type === 'heart' || a.type === 'brokenheart');
    if (hasHeart || ['心动'].includes(m.emotion?.key)) {
      const broken = (m.actors || []).some((a) => a.type === 'brokenheart') || m.emotion?.key === '难过';
      heart = { pts: sampleHeart(rnd, 120, 30), broken, x: W * 0.5, y: text.top - 34 };
    }
    // 月 / 日 → 发光体
    orbs = [];
    for (const a of m.actors || []) {
      if (a.type === 'moon') orbs.push({ kind: 'moon', x: a.x * W, y: a.y * H, r: 20 });
      else if (a.type === 'sun') orbs.push({ kind: 'sun', x: a.x * W, y: a.y * H, r: 17 });
    }
    // 文字溢出的光流
    flows = (m.flows || []).map((f) => ({ strength: f.strength || 0.5, ph: rnd() * TAU }));
  }
  rebuild();

  // 声音
  let sound = null, ambientStarted = false;
  try { sound = new SoundScape(); sound.setVolume(m.soundscape?.volume ?? 0.5); } catch { /* 静音模式 */ }

  // 时间轴
  const timeline = [...(m.timeline || [])].sort((a, b) => a.t - b.t);
  const fired = new Set();
  const st = { beatAt: -1, crackAt: -1, glowAt: -1 };
  function fire(ev) {
    if (ev.action === 'beat') st.beatAt = T;
    else if (ev.action === 'crack') st.crackAt = T;
    else if (ev.action === 'glow') st.glowAt = T;
    else if (ev.action === 'wake' && sound && !ambientStarted && m.soundscape?.ambient && m.soundscape.ambient !== 'none') {
      ambientStarted = true; sound.ambient(m.soundscape.ambient, m.soundscape.volume ?? 0.5);
    }
    if (ev.sound && sound) sound.oneshot(ev.sound, m.soundscape?.volume ?? 0.5);
  }

  // 编排时间（随唤醒度伸缩；submit 模式更紧凑）
  const spd = reduce ? 2.2 : (0.85 + arousal * 0.5);
  const T_STORM = (submit ? 0.7 : 1.0) / spd;            // 流体风暴聚拢
  const CONV = (submit ? 1.1 : 1.35) / spd;              // 单粒子汇聚时长
  const T_DONE = T_STORM + 0.77 + CONV;                  // 全部成形（含最大延迟）
  const HOLD = submit ? 1.2 : 999;                        // submit 模式停留后散场
  const OUT = 1.25;                                       // fly-out 时长
  const convEase = EASE[profile.conv] || easeOutExpo;

  let T = 0, start = performance.now(), raf = 0, stopped = false, doneCb = false;

  // 摄像机偏航（轻微，制造 3D 体积/视差，不伤可读性）
  function project(x, y, z, yaw, cx) {
    const dx = x - cx;
    const rx = dx * Math.cos(yaw) - z * Math.sin(yaw);
    const rz = dx * Math.sin(yaw) + z * Math.cos(yaw);
    const focal = 540;
    const scale = focal / (focal + rz);
    return [cx + rx * scale, y, scale];
  }

  function drawAmbient(t, wake, yaw, cx) {
    c.globalCompositeOperation = 'lighter';
    const para = Math.sin(yaw) * 26;
    for (const p of ambient) {
      let x, y, sp = SP.white, sx = 1, sy = 1, R = 4, al = 0.5 * p.depth * wake;
      const drift = para * p.depth;
      if (p.kind === 'raindrop') {
        y = (p.y + t * 360 * p.v) % (H + 40) - 20; x = (p.x + t * 22) % W + drift;
        sp = SP.cool; sx = 0.5; sy = 4.2; R = 5 * p.sz; al *= 0.7;
      } else if (p.kind === 'windline') {
        y = (p.y + Math.sin(t * 0.6 + p.ph) * 22) % H; x = (p.x + t * 70 * p.v) % (W + 160) - 80 + drift;
        sp = SP.accent; sx = 6; sy = 0.5; R = 7 * p.sz; al *= 0.55;
      } else if (p.kind === 'snowflake') {
        y = (p.y + t * 34 * p.v) % (H + 20); x = p.x + Math.sin(t * 0.8 + p.ph) * 26 + drift;
        sp = SP.white; R = 3.4 * p.sz;
      } else if (p.kind === 'petal') {
        y = (p.y + t * 42 * p.v) % (H + 24); x = p.x + Math.sin(t * 0.75 + p.ph) * 40 + drift;
        sp = SP.pink; sx = 1.6; sy = 1; R = 5 * p.sz; al *= 0.85;
      } else if (p.kind === 'spark') {
        y = (p.y - t * 66 * p.v + H) % H; x = p.x + Math.sin(t * 2 + p.ph) * 12 + drift;
        sp = SP.warm; R = 3.4 * p.sz; al *= 0.5 + 0.5 * Math.sin(t * 3 + p.ph) ** 2;
      } else if (p.kind === 'firefly') {
        x = p.x + Math.sin(t * 0.5 + p.ph) * 46 + drift; y = p.y * 0.9 + Math.cos(t * 0.4 + p.ph * 2) * 34;
        sp = SP.warm; R = 4 * p.sz; al *= 0.3 + 0.7 * Math.sin(t * 1.6 + p.ph) ** 2;
      } else if (p.kind === 'bubble') {
        y = (p.y - t * 30 * p.v + H) % H; x = p.x + Math.sin(t + p.ph) * 10 + drift;
        sp = SP.cool; R = 6 * p.sz; al *= 0.4;
      } else { // star
        x = p.x + drift * 0.5; y = p.y * 0.78;
        sp = SP.text; R = 3 * p.sz; al *= 0.4 + 0.6 * Math.sin(t * (1 + p.v) + p.ph) ** 2;
      }
      c.globalAlpha = clamp(al, 0, 1);
      c.drawImage(sp, x - R * sx, y - R * sy, R * 2 * sx, R * 2 * sy);
    }
  }

  function drawHeart(t) {
    if (!heart) return;
    const beat = st.beatAt >= 0 ? clamp((T - st.beatAt) / 0.5, 0, 1) : 1;
    const pulse = 1 + (1 - beat) * 0.28 + Math.sin(t * 4 + 0) * 0.03 * (profile.beat ? 1 : 0.4);
    const crackP = heart.broken && st.crackAt >= 0 ? clamp((T - st.crackAt) / 1.0, 0, 1) : 0;
    c.globalCompositeOperation = 'lighter';
    for (const p of heart.pts) {
      const sep = crackP * p.half * 16;
      const fall = crackP * crackP * 26;
      const x = heart.x + p.bx * pulse + sep;
      const y = heart.y + p.by * pulse + fall;
      const tw = 0.55 + 0.45 * Math.sin(t * 3 + p.ph);
      c.globalAlpha = clamp((heart.broken ? 0.7 : 0.85) * tw * (1 - crackP * 0.4), 0, 1);
      const R = 5 * p.sp;
      c.drawImage(SP.pink, x - R, y - R, R * 2, R * 2);
    }
  }

  function drawOrbs(t, wake) {
    c.globalCompositeOperation = 'lighter';
    for (const o of orbs) {
      const sp = o.kind === 'sun' ? SP.warm : SP.cool;
      const pulse = 1 + Math.sin(t * 0.8) * 0.05;
      const R = o.r * 2.6 * pulse;
      c.globalAlpha = 0.5 * wake;
      c.drawImage(sp, o.x - R, o.y - R, R * 2, R * 2);
      c.globalAlpha = 0.9 * wake;
      const r2 = o.r * pulse;
      c.drawImage(SP.white, o.x - r2, o.y - r2, r2 * 2, r2 * 2);
    }
  }

  function frame(nowTs) {
    if (stopped) return;
    raf = requestAnimationFrame(frame);
    T = (nowTs - start) / 1000;
    for (const ev of timeline) if (T >= ev.t && !fired.has(ev)) { fired.add(ev); fire(ev); }

    const cx = W / 2;
    const fseedBase = ((m.seed || 1) % 7) + 1;
    const yaw = reduce ? 0 : Math.sin(T * 0.32) * 0.085 * (0.6 + arousal * 0.6);

    // ---- 背景：竖向渐变 + 中心能量辉光 ----
    c.globalCompositeOperation = 'source-over';
    const bg = c.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, `rgb(${bgRGB[0].join(',')})`);
    bg.addColorStop(1, `rgb(${bgRGB[1].join(',')})`);
    c.fillStyle = bg; c.fillRect(0, 0, W, H);

    const wake = clamp(T / (T_STORM + 0.4), 0, 1);
    const coreGlow = 0.12 + 0.06 * Math.sin(T * 1.4) + (st.glowAt >= 0 ? 0.12 : 0);
    const rg = c.createRadialGradient(cx, H * 0.4, 8, cx, H * 0.4, H * 0.6);
    rg.addColorStop(0, `rgba(${glowRGB.map((v) => v | 0).join(',')},${coreGlow * wake})`);
    rg.addColorStop(1, 'transparent');
    c.fillStyle = rg; c.fillRect(0, 0, W, H);

    // ---- 环境粒子（最远景） ----
    drawAmbient(T, wake, yaw, cx);

    // ---- 月/日发光体 ----
    drawOrbs(T, wake);

    // ---- 心形粒子 ----
    drawHeart(T);

    // ---- 文字粒子（主角）：流体场汇聚 + 加性辉光 ----
    c.globalCompositeOperation = 'lighter';
    const aliveT = Math.max(0, T - T_DONE);
    // submit 散场进度
    const outP = submit ? clamp((T - (T_DONE + HOLD)) / OUT, 0, 1) : 0;
    if (outP >= 1 && !doneCb) { doneCb = true; opts.onDone?.(); }
    const breathe = 1 + Math.sin(T * (1.2 + arousal) ) * breathAmp * (aliveT > 0 ? 1 : 0.3);
    // 循环模式下的「呼吸释放波」：让成形的文字微微吐纳，像活着
    const releaseWave = loopOn ? 0.10 * (0.5 + 0.5 * Math.sin(aliveT * 0.55)) : 0;

    for (const p of text.pts) {
      // 流体起点持续被 curl 场推动（汇聚前的「光尘风暴」）
      const [fx, fy] = curl(p.x * 0.006 + T * 0.12 * profile.swirl, p.y * 0.006 - T * 0.08, fseedBase);
      p.x += fx * 26 * profile.swirl * (1 - wake * 0.3);
      p.y += fy * 26 * profile.swirl * (1 - wake * 0.3) + profile.grav * 8;
      p.x += (cx - p.x) * 0.012; p.y += (H * 0.4 - p.y) * 0.012;  // 向字心缓拉

      // 汇聚缓动（错峰 + 非线性）
      const localT = T - T_STORM - p.delay;
      let e = localT <= 0 ? 0 : convEase(clamp(localT / CONV, 0, 1));
      e = clamp(e, 0, 1);

      // 活着之后的呼吸释放 + 微抖
      const jitterAmp = (0.6 + arousal * 0.8) * (e) * (aliveT > 0 ? 1 : 0.4);
      const jx = (vnoise(T * 0.6 + p.seed, p.seed, 3) - 0.5) * 2.4 * jitterAmp;
      const jy = (vnoise(T * 0.55 + p.seed + 40, p.seed, 5) - 0.5) * 2.4 * jitterAmp;
      const rel = releaseWave * vnoise(p.seed, aliveT * 0.3, 9);

      // 目标（带呼吸缩放，绕字心）
      const tgx = cx + (p.tx - cx) * breathe;
      const tgy = H * 0.4 + (p.ty - H * 0.4) * breathe;

      let X = lerp(p.x, tgx, e * (1 - rel)) + jx * e;
      let Y = lerp(p.y, tgy, e * (1 - rel)) + jy * e;
      let Z = lerp(p.z, p.tz, e);
      let alpha = clamp((wake * 0.5 + e * 0.5), 0, 1) * 0.92;

      // fly-out 散场（提交动效收尾：文字化作光飞向世界）
      if (outP > 0) {
        const o = easeOutCubic(outP);
        if (profile.out === 'fall' || profile.out === 'driftX') { Y += o * (H * 0.5) * (profile.out === 'fall' ? 1 : 0.2); X += o * (profile.out === 'driftX' ? W * 0.4 : 0); }
        else { const a2 = p.seed * 0.0063 * TAU; X += Math.cos(a2) * o * W * 0.5; Y += Math.sin(a2) * o * H * 0.5 - o * H * 0.18; }
        Z += o * 240;
        alpha *= 1 - o;
      }

      const [sx, sy, sc] = project(X, Y, Z, yaw, cx);
      const depthA = clamp(0.45 + sc * 0.55, 0.2, 1.2);
      const R = (p.hot ? 3.0 : 4.2) * sc * (0.85 + intensity * 0.4);
      c.globalAlpha = clamp(alpha * depthA, 0, 1);
      c.drawImage(p.hot ? SP.hot : SP.text, sx - R, sy - R, R * 2, R * 2);
    }

    // ---- 文字溢出的光流（替代旧版灰色风线） ----
    if (flows.length && aliveT > 0) {
      for (let fi = 0; fi < flows.length; fi++) {
        const f = flows[fi];
        for (let i = 0; i < 4; i++) {
          const pp = ((T * (0.16 + i * 0.05) + f.ph + i * 0.25) % 1);
          const y0 = H * 0.4 + (i - 1.5) * 22;
          const x = lerp(cx, W * 1.02, pp);
          const R = 9 * Math.sin(pp * Math.PI);
          c.globalAlpha = Math.sin(pp * Math.PI) * 0.4 * f.strength;
          c.drawImage(SP.text, x - R, y0 - R * 0.5, R * 2, R);
        }
      }
    }

    // ---- 暗角 ----
    c.globalCompositeOperation = 'source-over';
    const vg = c.createRadialGradient(cx, H / 2, H * 0.34, cx, H / 2, H * 0.86);
    vg.addColorStop(0, 'transparent'); vg.addColorStop(1, 'rgba(5,4,12,0.55)');
    c.fillStyle = vg; c.fillRect(0, 0, W, H);
    c.globalAlpha = 1;
  }
  raf = requestAnimationFrame(frame);

  return {
    toggleMute: () => sound?.toggleMute(),
    stop() {
      if (stopped) return;
      stopped = true;
      cancelAnimationFrame(raf);
      removeEventListener('resize', onResize);
      sound?.stop();
    }
  };
}
