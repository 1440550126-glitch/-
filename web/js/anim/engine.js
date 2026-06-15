// ============================================================
// 文字变动画引擎：Animation Manifest 播放器
// 非线性：状态机（入场→苏醒→呼吸循环）+ 行为函数 + 情绪参数调制
//        + 噪声微动 + 物理粒子 + 时间轴声音事件
// ============================================================
import { SoundScape } from './sound.js';

// 平滑值噪声（行为微动用）
function makeNoise(seed = 1) {
  const hash = (n) => {
    const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
    return s - Math.floor(s);
  };
  return (x) => {
    const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
    return hash(i) * (1 - u) + hash(i + 1) * u;
  };
}
const TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, p) => a + (b - a) * p;

// ---- 文字 → 粒子目标点采样 ----
function sampleText(text, W, H) {
  const off = document.createElement('canvas');
  const c = off.getContext('2d');
  const maxW = W * 0.82;
  let size = text.length <= 10 ? 42 : text.length <= 24 ? 32 : text.length <= 60 ? 24 : 18;
  size = Math.min(size, Math.floor(W / 9));
  c.font = `600 ${size}px "PingFang SC", system-ui, sans-serif`;
  // 逐字换行
  const lines = [];
  let line = '';
  for (const ch of text) {
    if (ch === '\n' || c.measureText(line + ch).width > maxW) { lines.push(line); line = ch === '\n' ? '' : ch; }
    else line += ch;
  }
  if (line) lines.push(line);
  const lh = size * 1.55;
  off.width = W; off.height = Math.ceil(lines.length * lh + size);
  c.font = `600 ${size}px "PingFang SC", system-ui, sans-serif`;
  c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillStyle = '#fff';
  lines.forEach((ln, i) => c.fillText(ln, W / 2, size * 0.8 + i * lh));

  const img = c.getImageData(0, 0, off.width, off.height).data;
  const pts = [];
  const step = text.length > 50 ? 4 : 3;
  for (let y = 0; y < off.height; y += step) {
    for (let x = 0; x < W; x += step) {
      if (img[(y * W + x) * 4 + 3] > 120) pts.push({ x, y });
    }
  }
  const blockH = off.height;
  const offsetY = H * 0.30 - blockH / 2;
  // 控制粒子总量
  const cap = 1500;
  const keep = pts.length > cap ? cap / pts.length : 1;
  return pts.filter(() => Math.random() < keep).map((p, i) => ({
    tx: p.x, ty: p.y + offsetY,
    x: W / 2 + (Math.random() - 0.5) * W * 1.3,
    y: H * 0.3 + (Math.random() - 0.5) * H * 0.9,
    delay: Math.random() * 0.55, seed: i * 0.37
  }));
}

// ---- 粒子系统 ----
function spawnParticles(kind, density, W, H, rnd) {
  const counts = { windline: 7, raindrop: 46, snowflake: 36, petal: 16, star: 42, spark: 22, shard: 0, firefly: 14, bubble: 14 };
  const n = Math.round((counts[kind] ?? 14) * clamp(density, 0.1, 1) * 1.6);
  const arr = [];
  for (let i = 0; i < n; i++) {
    arr.push({
      kind,
      x: rnd() * W, y: rnd() * H,
      v: 0.5 + rnd() * 0.9, ph: rnd() * TAU, sz: 0.6 + rnd() * 1.4, a: 0.3 + rnd() * 0.5
    });
  }
  return arr;
}

function drawParticle(c, p, t, W, H, pal, em) {
  const speed = 0.6 + em.arousal * 0.9;
  c.save();
  if (p.kind === 'windline') {
    const y = (p.y + Math.sin(t * 0.7 + p.ph) * 18) % H;
    const x = (p.x + t * 60 * speed * p.v) % (W + 140) - 70;
    const g = c.createLinearGradient(x - 50, y, x + 50, y);
    g.addColorStop(0, 'transparent'); g.addColorStop(0.5, pal.accent + '88'); g.addColorStop(1, 'transparent');
    c.strokeStyle = g; c.lineWidth = 1.1;
    c.beginPath();
    c.moveTo(x - 50, y);
    c.quadraticCurveTo(x, y - 9 * p.sz, x + 50, y + Math.sin(p.ph) * 6);
    c.stroke();
  } else if (p.kind === 'raindrop') {
    const y = (p.y + t * 320 * p.v * speed) % (H + 30);
    const x = (p.x + t * 28) % W;
    c.strokeStyle = pal.accent + '66'; c.lineWidth = 1;
    c.beginPath(); c.moveTo(x, y); c.lineTo(x - 2.5, y + 11 * p.sz); c.stroke();
  } else if (p.kind === 'snowflake') {
    const y = (p.y + t * 36 * p.v) % (H + 16);
    const x = p.x + Math.sin(t * 0.9 + p.ph) * 26;
    c.fillStyle = '#ffffffcc';
    c.beginPath(); c.arc(x, y, 1.5 * p.sz, 0, TAU); c.fill();
  } else if (p.kind === 'petal') {
    const y = (p.y + t * 46 * p.v) % (H + 22);
    const x = p.x + Math.sin(t * 0.8 + p.ph) * 38;
    c.translate(x, y);
    c.rotate(Math.sin(t * 1.4 + p.ph) * 0.9);
    c.fillStyle = '#ffb3cdcc';
    c.beginPath(); c.ellipse(0, 0, 4.2 * p.sz, 2.6 * p.sz, 0, 0, TAU); c.fill();
  } else if (p.kind === 'star') {
    const tw = 0.45 + 0.55 * Math.sin(t * (1.1 + p.v) + p.ph) ** 2;
    c.fillStyle = pal.glow;
    c.globalAlpha = p.a * tw;
    c.beginPath(); c.arc(p.x, p.y * 0.72, 1.25 * p.sz, 0, TAU); c.fill();
  } else if (p.kind === 'spark') {
    const y = (p.y - t * 60 * p.v + H) % H;
    const x = p.x + Math.sin(t * 2 + p.ph) * 10;
    c.fillStyle = '#ffb46acc';
    c.beginPath(); c.arc(x, y, 1.3 * p.sz, 0, TAU); c.fill();
  } else if (p.kind === 'firefly') {
    const x = p.x + Math.sin(t * 0.5 + p.ph) * 42;
    const y = p.y * 0.85 + Math.cos(t * 0.4 + p.ph * 2) * 30;
    const tw = 0.3 + 0.7 * Math.sin(t * 1.6 + p.ph) ** 2;
    c.globalAlpha = tw * 0.85;
    c.shadowColor = '#ffe28a'; c.shadowBlur = 9;
    c.fillStyle = '#fff3c4';
    c.beginPath(); c.arc(x, y, 1.7 * p.sz, 0, TAU); c.fill();
  } else if (p.kind === 'bubble') {
    const y = (p.y - t * 34 * p.v + H) % H;
    c.strokeStyle = pal.accent + '55'; c.lineWidth = 1;
    c.beginPath(); c.arc(p.x + Math.sin(t + p.ph) * 8, y, 3.2 * p.sz, 0, TAU); c.stroke();
  }
  c.restore();
}

// ---- 火柴人/角色绘制 ----
function drawFigure(c, a, t, W, H, pal, em, noise, moving) {
  const X = a.x * W + (a._dx || 0), Y = a.y * H;
  const s = 34 * (a.scale || 1);
  const jit = em.jitter * 1.6;
  const breathe = Math.sin(t * em.breath * 1.9) * 0.05;
  const n1 = noise(t * 0.7 + a._i * 9) - 0.5;
  c.save();
  c.translate(X + n1 * jit, Y + Math.sin(t * em.breath * 2.1) * 1.6);
  c.strokeStyle = pal.ink; c.lineWidth = 2.4; c.lineCap = 'round';
  c.shadowColor = pal.glow; c.shadowBlur = 7;

  const beh = a.behavior;
  let legA = 0, armA = 0.32, lean = 0, headDy = 0, bob = 0;
  if (beh === 'walk' || beh === 'run') {
    const f = beh === 'run' ? 7.5 : 4;
    const amp = beh === 'run' ? 0.85 : 0.5;
    legA = Math.sin(t * f) * amp;
    armA = Math.sin(t * f + Math.PI) * amp * 0.8;
    lean = beh === 'run' ? 0.24 : 0.07;
    bob = Math.abs(Math.sin(t * f)) * (beh === 'run' ? 3.4 : 1.6);
    if (moving) a._dx = ((a._dx || 0) + (beh === 'run' ? 1.6 : 0.65)) % (W * 0.55);
  } else if (beh === 'wait') {
    lean = n1 * 0.05;
    headDy = Math.sin(t * 0.5) * 1.2;
    legA = 0.06;
  } else if (beh === 'look_up') {
    lean = -0.12; headDy = -3.5;
  } else if (beh === 'bounce') {
    bob = Math.abs(Math.sin(t * 4.2)) * 8;
  } else if (beh === 'sleep') {
    lean = 0.5;
  }
  c.rotate(lean);
  c.translate(0, -bob);

  const headR = s * 0.22;
  const neckY = -s * 0.95, hipY = -s * 0.35;
  // 头
  c.beginPath(); c.arc(0, neckY - headR + headDy, headR * (1 + breathe * 0.5), 0, TAU); c.stroke();
  // 身体
  c.beginPath(); c.moveTo(0, neckY + headDy * 0.4); c.lineTo(0, hipY); c.stroke();
  // 手臂
  c.beginPath();
  c.moveTo(0, neckY + s * 0.12);
  c.lineTo(Math.sin(armA) * s * 0.3, neckY + s * 0.42);
  c.moveTo(0, neckY + s * 0.12);
  c.lineTo(-Math.sin(armA) * s * 0.3, neckY + s * 0.42);
  c.stroke();
  // 腿
  c.beginPath();
  c.moveTo(0, hipY); c.lineTo(Math.sin(legA) * s * 0.3, 0);
  c.moveTo(0, hipY); c.lineTo(-Math.sin(legA) * s * 0.3, 0);
  c.stroke();
  if (beh === 'sleep') {
    c.font = '11px sans-serif'; c.fillStyle = pal.accent;
    const zy = Math.sin(t * 1.5) * 4;
    c.fillText('z', headR + 6, neckY - headR - 4 - zy);
    c.fillText('Z', headR + 14, neckY - headR - 12 - zy);
  }
  c.restore();
}

function drawFigure2(c, a, t, W, H, pal, em) {
  // 两个互相依靠的小人（拥抱）
  const X = a.x * W, Y = a.y * H, s = 32;
  const hug = 0.5 + Math.sin(t * em.breath * 1.6) * 0.04;
  c.save();
  c.translate(X, Y);
  c.strokeStyle = pal.ink; c.lineWidth = 2.4; c.lineCap = 'round';
  c.shadowColor = pal.glow; c.shadowBlur = 8;
  for (const dir of [-1, 1]) {
    c.save();
    c.translate(dir * s * 0.34, 0);
    c.rotate(-dir * 0.22 * hug * 1.6);
    c.beginPath(); c.arc(0, -s * 1.15, s * 0.2, 0, TAU); c.stroke();
    c.beginPath(); c.moveTo(0, -s * 0.95); c.lineTo(0, -s * 0.3); c.stroke();
    c.beginPath();
    c.moveTo(0, -s * 0.78); c.quadraticCurveTo(-dir * s * 0.42, -s * 0.7, -dir * s * 0.4, -s * 0.52);
    c.stroke();
    c.beginPath();
    c.moveTo(0, -s * 0.3); c.lineTo(dir * s * 0.16, 0);
    c.moveTo(0, -s * 0.3); c.lineTo(-dir * s * 0.1, 0);
    c.stroke();
    c.restore();
  }
  c.restore();
}

function drawActor(c, a, t, W, H, pal, em, noise, state) {
  const enterP = clamp((state.t - (a._enterAt ?? 0)) / 0.8, 0, 1);
  if (enterP <= 0) return;
  c.save();
  c.globalAlpha = enterP;
  const floatY = Math.sin(t * 0.8 + (a._i || 0) * 2) * 4;

  if (a.type === 'figure') drawFigure(c, a, t, W, H, pal, em, noise, state.moving);
  else if (a.type === 'figure2') drawFigure2(c, a, t, W, H, pal, em);
  else if (a.type === 'heart' || a.type === 'brokenheart') {
    const X = a.x * W, Y = a.y * H + floatY;
    const beatP = state.beatAt >= 0 ? clamp((state.t - state.beatAt) / 0.5, 0, 1) : 1;
    const pulse = 1 + (1 - beatP) * 0.3 + Math.sin(t * em.breath * 2.4) * 0.035;
    const s = 17 * (a.scale || 1) * pulse;
    const crackP = state.crackAt >= 0 ? clamp((state.t - state.crackAt) / 0.8, 0, 1) : 0;
    const trembleX = state.crackAt < 0 && a.type === 'brokenheart' ? (noise(t * 6) - 0.5) * 3 : 0;
    c.translate(X + trembleX, Y);
    c.strokeStyle = a.type === 'brokenheart' ? pal.ink : '#ff8fb3';
    c.shadowColor = a.type === 'brokenheart' ? pal.glow : '#ff8fb3';
    c.shadowBlur = 11;
    c.lineWidth = 2.3; c.lineCap = 'round';
    for (const half of a.type === 'brokenheart' && crackP > 0 ? [-1, 1] : [0]) {
      c.save();
      if (half) {
        c.translate(half * crackP * 9, crackP * 7 * Math.abs(half));
        c.rotate(half * crackP * 0.22);
      }
      c.beginPath();
      c.moveTo(0, s * 0.32);
      c.bezierCurveTo(-s, -s * 0.42, -s * 0.48, -s * 1.05, 0, -s * 0.36);
      c.bezierCurveTo(s * 0.48, -s * 1.05, s, -s * 0.42, 0, s * 0.32);
      c.stroke();
      c.restore();
    }
    if (a.type === 'brokenheart') {
      // 裂缝
      c.beginPath();
      c.moveTo(0, -s * 0.42);
      c.lineTo(-s * 0.12, -s * 0.1); c.lineTo(s * 0.1, s * 0.02); c.lineTo(-s * 0.06, s * 0.3);
      c.stroke();
    }
  } else if (a.type === 'moon') {
    const X = a.x * W, Y = a.y * H + floatY;
    c.translate(X, Y);
    c.fillStyle = '#ffeec2';
    c.shadowColor = '#ffe9a8'; c.shadowBlur = 22;
    c.beginPath(); c.arc(0, 0, 17, 0, TAU); c.fill();
    c.globalCompositeOperation = 'destination-out';
    c.beginPath(); c.arc(7, -5, 14, 0, TAU); c.fill();
  } else if (a.type === 'sun') {
    const X = a.x * W, Y = a.y * H;
    c.translate(X, Y); c.rotate(t * 0.18);
    c.strokeStyle = '#ffc46b'; c.fillStyle = '#ffd98e';
    c.shadowColor = '#ffd98e'; c.shadowBlur = 18; c.lineWidth = 2;
    c.beginPath(); c.arc(0, 0, 13, 0, TAU); c.fill();
    for (let i = 0; i < 8; i++) {
      c.rotate(TAU / 8);
      c.beginPath(); c.moveTo(19, 0); c.lineTo(25, 0); c.stroke();
    }
  } else if (a.type === 'cloud') {
    const X = a.x * W + Math.sin(t * 0.25 + (a._i || 0)) * 16, Y = a.y * H + floatY;
    c.translate(X, Y);
    c.strokeStyle = pal.ink; c.lineWidth = 2; c.shadowColor = pal.glow; c.shadowBlur = 6;
    c.beginPath();
    c.arc(-13, 0, 9, Math.PI * 0.4, Math.PI * 1.5);
    c.arc(0, -7, 11, Math.PI * 0.85, Math.PI * 1.96);
    c.arc(14, 0, 9, Math.PI * 1.3, Math.PI * 0.6);
    c.closePath(); c.stroke();
  } else if (a.type === 'cat') {
    const X = a.x * W, Y = a.y * H;
    c.translate(X, Y);
    c.strokeStyle = pal.ink; c.lineWidth = 2.2; c.lineCap = 'round';
    c.shadowColor = pal.glow; c.shadowBlur = 6;
    const purr = state.purrAt >= 0 && state.t - state.purrAt < 1.6;
    const earW = purr ? Math.sin(t * 18) * 1.6 : 0;
    // 身体（卧姿曲线）
    c.beginPath(); c.moveTo(-16, 0); c.quadraticCurveTo(-18, -13, -4, -13); c.lineTo(8, -13); c.quadraticCurveTo(17, -13, 16, 0); c.stroke();
    // 头 + 耳朵
    c.beginPath(); c.arc(12, -17, 7.5, 0, TAU); c.stroke();
    c.beginPath();
    c.moveTo(7, -22); c.lineTo(6 + earW, -29); c.lineTo(11, -24);
    c.moveTo(16, -23); c.lineTo(18 + earW, -30); c.lineTo(19, -23);
    c.stroke();
    // 尾巴摇摆
    const tw = Math.sin(t * (purr ? 4 : 1.6)) * 9;
    c.beginPath(); c.moveTo(-16, -2); c.quadraticCurveTo(-26, -8, -24 + tw * 0.3, -18 - tw * 0.4); c.stroke();
  } else if (a.type === 'umbrella') {
    const X = a.x * W, Y = a.y * H + floatY * 0.4;
    c.translate(X, Y);
    c.strokeStyle = pal.accent; c.lineWidth = 2.2; c.lineCap = 'round';
    c.shadowColor = pal.glow; c.shadowBlur = 8;
    c.beginPath(); c.arc(0, 0, 22, Math.PI, 0); c.stroke();
    c.beginPath();
    for (let i = 0; i <= 4; i++) {
      const x = -22 + i * 11;
      c.moveTo(x, 0); c.quadraticCurveTo(x + 5.5, 4, x + 11, 0);
    }
    c.stroke();
    c.beginPath(); c.moveTo(0, -22); c.lineTo(0, 26); c.quadraticCurveTo(0, 32, 6, 31); c.stroke();
  }
  c.restore();
}

// ---- 主引擎 ----
export function playManifest(canvas, manifest, opts = {}) {
  const c = canvas.getContext('2d');
  const dpr = Math.min(devicePixelRatio || 1, 2);
  let W = 0, H = 0;
  function resize() {
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  const onResize = () => resize();
  addEventListener('resize', onResize);

  const m = manifest;
  const pal = m.palette || { bg: ['#1c1d2e', '#272a44'], ink: '#e8e6f7', accent: '#9d8cff', glow: '#7c6cff' };
  const em = { arousal: m.emotion?.arousal ?? 0.4, valence: m.emotion?.valence ?? 0.3, breath: m.behavior?.breath ?? 0.7, jitter: m.behavior?.jitter ?? 0.25 };
  const eager = m.behavior?.speedCurve === 'eager';
  const noise = makeNoise(m.seed || 1);
  let rndS = (m.seed || 12345) >>> 0;
  const rnd = () => ((rndS = (rndS * 1103515245 + 12345) >>> 0) / 4294967296);

  const textPts = sampleText(opts.text || m.text_content || '', Math.min(W, 520), H);
  const particles = [];
  for (const p of m.particles || []) particles.push(...spawnParticles(p.kind, p.density, W, H, rnd));
  if (opts.fxPayload?.trail) particles.push(...spawnParticles(opts.fxPayload.trail, 0.4, W, H, rnd));
  const shards = [];

  const actors = (m.actors || []).map((a, i) => ({ ...a, _i: i, _enterAt: 99 }));
  const timeline = [...(m.timeline || [])].sort((x, y) => x.t - y.t);
  const fired = new Set();
  const state = { t: 0, assembleAt: -1, glowAt: -1, wakeAt: -1, beatAt: -1, crackAt: -1, purrAt: -1, moving: false };

  // 声音（用户手势后创建）
  let sound = null;
  let ambientStarted = false;
  try { sound = new SoundScape(); sound.setVolume(m.soundscape?.volume ?? 0.5); } catch { /* 无声模式 */ }

  function fire(ev) {
    if (ev.action === 'glow') state.glowAt = state.t;
    else if (ev.action === 'assemble') state.assembleAt = state.t;
    else if (ev.action === 'wake') {
      state.wakeAt = state.t;
      if (sound && !ambientStarted && m.soundscape?.ambient && m.soundscape.ambient !== 'none') {
        ambientStarted = true;
        sound.ambient(m.soundscape.ambient, m.soundscape.volume ?? 0.5);
      }
    } else if (ev.action === 'enter') {
      const a = actors.find((x) => x.id === ev.target);
      if (a) a._enterAt = state.t;
    } else if (ev.action === 'beat') state.beatAt = state.t;
    else if (ev.action === 'crack') {
      state.crackAt = state.t;
      const ha = actors.find((x) => x.type === 'brokenheart');
      if (ha) {
        for (let i = 0; i < 14; i++) {
          shards.push({ x: ha.x * W, y: ha.y * H, vx: (rnd() - 0.5) * 90, vy: -rnd() * 70 - 10, rot: rnd() * TAU, vr: (rnd() - 0.5) * 6, born: state.t });
        }
      }
    } else if (ev.action === 'move') state.moving = true;
    else if (ev.action === 'purr') state.purrAt = state.t;
    if (ev.sound && sound) sound.oneshot(ev.sound, m.soundscape?.volume ?? 0.5);
  }

  const dur = m.duration || 9;
  const loopFrom = m.behavior?.loopFrom ?? 3.2;
  let start = performance.now();
  let raf = 0, stopped = false;

  function frame(nowTs) {
    if (stopped) return;
    raf = requestAnimationFrame(frame);
    let t = (nowTs - start) / 1000;
    if (m.behavior?.loop !== false && t > dur) {
      // 循环回呼吸点：一次性事件不再触发
      start = nowTs - loopFrom * 1000;
      t = loopFrom;
    }
    state.t = t;
    for (const ev of timeline) {
      if (t >= ev.t && !fired.has(ev)) { fired.add(ev); fire(ev); }
    }

    // 背景
    const g = c.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, pal.bg[0]); g.addColorStop(1, pal.bg[1]);
    c.fillStyle = g;
    c.fillRect(0, 0, W, H);
    const wake = state.wakeAt >= 0 ? clamp((t - state.wakeAt) / 1.0, 0, 1) : 0;

    // 城市剪影
    if (m.scene?.skyline && wake > 0) {
      c.save();
      c.globalAlpha = wake * 0.25;
      c.fillStyle = pal.ink;
      let x = 0; let i = 0;
      while (x < W) {
        const bw = 24 + ((m.seed + i * 37) % 40);
        const bh = 36 + ((m.seed + i * 53) % 70);
        c.fillRect(x, H * 0.82 - bh, bw, bh);
        x += bw + 7; i++;
      }
      c.restore();
    }

    // 地面 / 海面
    if (wake > 0 && m.scene?.ground !== 'none') {
      c.save();
      c.globalAlpha = wake * 0.8;
      c.strokeStyle = pal.ink + 'aa'; c.lineWidth = 1.6; c.lineCap = 'round';
      c.beginPath();
      const gy = H * 0.82;
      if (m.scene.ground === 'sea') {
        for (let x = 0; x <= W; x += 7) {
          const y = gy + Math.sin(x * 0.035 + t * 1.7) * 4 + Math.sin(x * 0.013 - t * 0.8) * 3;
          x === 0 ? c.moveTo(x, y) : c.lineTo(x, y);
        }
      } else {
        for (let x = 0; x <= W; x += 11) {
          const y = gy + (noise(x * 0.02 + 5) - 0.5) * 5;
          x === 0 ? c.moveTo(x, y) : c.lineTo(x, y);
        }
      }
      c.stroke();
      c.restore();
    }

    // 粒子
    if (wake > 0) {
      c.save();
      c.globalAlpha = wake;
      for (const p of particles) drawParticle(c, p, t, W, H, pal, em);
      c.restore();
    }

    // 心碎碎片
    for (let i = shards.length - 1; i >= 0; i--) {
      const s = shards[i];
      const age = t - s.born;
      if (age > 2.4 || age < 0) { shards.splice(i, 1); continue; }
      s.x += s.vx * 0.016; s.y += s.vy * 0.016; s.vy += 60 * 0.016; s.rot += s.vr * 0.016;
      c.save();
      c.globalAlpha = clamp(1 - age / 2.4, 0, 1);
      c.translate(s.x, s.y); c.rotate(s.rot);
      c.strokeStyle = '#ff8fb3';
      c.beginPath(); c.moveTo(0, -3.5); c.lineTo(3, 2.5); c.lineTo(-3, 2.5); c.closePath(); c.stroke();
      c.restore();
    }

    // 文字流出的"风线"
    if ((m.flows || []).length && wake > 0.4) {
      c.save();
      for (const f of m.flows) {
        for (let i = 0; i < 3; i++) {
          const p = ((t * (0.22 + i * 0.07) + i * 0.33) % 1);
          const y0 = H * 0.30 + (i - 1) * 26;
          const x = lerp(W * 0.5, W * 1.05, p);
          c.globalAlpha = Math.sin(p * Math.PI) * 0.5 * (f.strength || 0.6);
          c.strokeStyle = pal.glow; c.lineWidth = 1.2;
          c.beginPath();
          c.moveTo(x - 44, y0);
          c.quadraticCurveTo(x - 14, y0 - 10 - i * 4, x + 22, y0 + Math.sin(t + i) * 7);
          c.stroke();
        }
      }
      c.restore();
    }

    // 角色
    for (const a of actors) drawActor(c, a, t, W, H, pal, em, noise, state);

    // 文字粒子
    if (state.assembleAt >= 0) {
      const ap = clamp((t - state.assembleAt) / 1.5, 0, 1);
      c.save();
      const glowPulse = state.glowAt >= 0 ? 0.6 + 0.4 * Math.sin(t * 2.2) : 0.5;
      c.shadowColor = pal.glow;
      c.fillStyle = pal.ink;
      for (const p of textPts) {
        const pp = clamp((ap * 1.55 - p.delay) / 1.0, 0, 1);
        if (pp <= 0) continue;
        const e = eager ? 1 - Math.pow(1 - pp, 2.6) : 1 - Math.pow(1 - pp, 3.6);
        // 汇聚后保留呼吸微动（活着的感觉）
        const jx = (noise(t * 0.9 + p.seed) - 0.5) * 1.7 * (0.5 + em.jitter);
        const jy = (noise(t * 0.8 + p.seed + 50) - 0.5) * 1.7 * (0.5 + em.jitter);
        const x = lerp(p.x, p.tx, e) + jx * e;
        const y = lerp(p.y, p.ty, e) + jy * e;
        c.globalAlpha = e * 0.95;
        c.shadowBlur = 5 * glowPulse * e;
        c.fillRect(x, y, 1.55, 1.55);
      }
      c.restore();
    } else if (state.glowAt >= 0) {
      // 汇聚前的预热光晕
      const gp = clamp((t - state.glowAt) / 0.7, 0, 1);
      const rg = c.createRadialGradient(W / 2, H * 0.3, 6, W / 2, H * 0.3, 130);
      rg.addColorStop(0, pal.glow + Math.round(gp * 60).toString(16).padStart(2, '0'));
      rg.addColorStop(1, 'transparent');
      c.fillStyle = rg;
      c.fillRect(0, 0, W, H);
    }

    // 暗角
    const vg = c.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 0.85);
    vg.addColorStop(0, 'transparent'); vg.addColorStop(1, 'rgba(8,6,16,0.4)');
    c.fillStyle = vg;
    c.fillRect(0, 0, W, H);
  }
  raf = requestAnimationFrame(frame);

  return {
    toggleMute: () => sound?.toggleMute(),
    // 杜比沉浸音效控制（透传给声音引擎）
    setDolby: (on) => sound?.setDolby(on),
    setDolbyPreset: (id) => sound?.setDolbyPreset(id),
    setDolbyIntensity: (v) => sound?.setDolbyIntensity(v),
    dolbyState: () => sound?.dolbyState,
    stop() {
      stopped = true;
      cancelAnimationFrame(raf);
      removeEventListener('resize', onResize);
      sound?.stop();
    }
  };
}
