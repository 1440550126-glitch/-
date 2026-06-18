// dolby:demo —— 离线"看/听效果"脚本（无需浏览器）
// 用引擎真实的预设数值 + 真实响度/HRIR 模块，对一段立体声测试信号做与引擎一致的处理
// （低/中/高架 EQ + M/S 展宽 + 软削波 + 响度匹配），打印硬指标并写出 dry/dolby 对比 WAV。
// 注：这是离线"镜像"预览（忠实复刻参数），真引擎在浏览器里跑（demo.html / player.html）。
// 用法：node web/dolby/tools/render-demo.mjs [输出目录]    （默认系统临时目录）
import { DOLBY_PRESETS } from '../dolby-audio.js';
import { lufsFromMeanSquare, IntegratedLoudness } from '../dolby-loudness.js';
import { buildBinauralIR } from '../dolby-hrir.js';
import { writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const FS = 44100, DUR = 6, N = FS * DUR;
const OUT = process.argv[2] || os.tmpdir();
const PRESET = process.env.DOLBY_PRESET || 'music';
const P = (DOLBY_PRESETS.find((p) => p.id === PRESET) || DOLBY_PRESETS[0]).p;

const SQRT2 = Math.SQRT2;
const lowshelf = (f, dB) => { const A = 10 ** (dB / 40), w = 2 * Math.PI * f / FS, c = Math.cos(w), al = Math.sin(w) / 2 * SQRT2, b = 2 * Math.sqrt(A) * al; return { b0: A * ((A + 1) - (A - 1) * c + b), b1: 2 * A * ((A - 1) - (A + 1) * c), b2: A * ((A + 1) - (A - 1) * c - b), a0: (A + 1) + (A - 1) * c + b, a1: -2 * ((A - 1) + (A + 1) * c), a2: (A + 1) + (A - 1) * c - b }; };
const highshelf = (f, dB) => { const A = 10 ** (dB / 40), w = 2 * Math.PI * f / FS, c = Math.cos(w), al = Math.sin(w) / 2 * SQRT2, b = 2 * Math.sqrt(A) * al; return { b0: A * ((A + 1) + (A - 1) * c + b), b1: -2 * A * ((A - 1) + (A + 1) * c), b2: A * ((A + 1) + (A - 1) * c - b), a0: (A + 1) - (A - 1) * c + b, a1: 2 * ((A - 1) - (A + 1) * c), a2: (A + 1) - (A - 1) * c - b }; };
const peaking = (f, Q, dB) => { const A = 10 ** (dB / 40), w = 2 * Math.PI * f / FS, c = Math.cos(w), al = Math.sin(w) / (2 * Q); return { b0: 1 + al * A, b1: -2 * c, b2: 1 - al * A, a0: 1 + al / A, a1: -2 * c, a2: 1 - al / A }; };
function run(co, x) { const y = new Float32Array(x.length); let x1 = 0, x2 = 0, y1 = 0, y2 = 0; const b0 = co.b0 / co.a0, b1 = co.b1 / co.a0, b2 = co.b2 / co.a0, a1 = co.a1 / co.a0, a2 = co.a2 / co.a0; for (let i = 0; i < x.length; i++) { const xn = x[i], yn = b0 * xn + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = xn; y2 = y1; y1 = yn; y[i] = yn; } return y; }
function mag(co, f) { const w = 2 * Math.PI * f / FS, cw = Math.cos(w), c2 = Math.cos(2 * w), sw = Math.sin(w), s2 = Math.sin(2 * w); const nr = co.b0 + co.b1 * cw + co.b2 * c2, ni = -(co.b1 * sw + co.b2 * s2), dr = co.a0 + co.a1 * cw + co.a2 * c2, di = -(co.a1 * sw + co.a2 * s2); return Math.hypot(nr, ni) / Math.hypot(dr, di); }
const rms = (a) => Math.sqrt(a.reduce((s, v) => s + v * v, 0) / a.length);

// 测试信号：Am–F–C–G，pad 分声像 + 低音
const L = new Float32Array(N), R = new Float32Array(N);
const CH = [[220, 261.63, 329.63, 110], [174.61, 220, 261.63, 87.31], [261.63, 329.63, 392, 130.81], [196, 246.94, 293.66, 98]];
for (let b = 0; b < 8; b++) {
  const c = CH[b % 4], t0 = b * 0.75;
  for (let k = 0; k < c.length - 1; k++) { const f = c[k], pan = (k - 1) * 0.4, s0 = (t0 * FS) | 0, n = (0.75 * FS) | 0; for (let i = 0; i < n; i++) { const t = i / FS, env = Math.min(1, t / 0.05) * Math.max(0, (0.75 - t) / 0.2), v = Math.sin(2 * Math.PI * f * t) * 0.09 * env, idx = s0 + i; if (idx < N) { L[idx] += v * (1 - Math.max(0, pan)); R[idx] += v * (1 + Math.min(0, pan)); } } }
  const bf = c[3], s0 = (t0 * FS) | 0, n = (0.75 * FS) | 0; for (let i = 0; i < n; i++) { const t = i / FS, env = Math.max(0, (0.75 - t) / 0.4), v = Math.sin(2 * Math.PI * bf * t) * 0.28 * env, idx = s0 + i; if (idx < N) { L[idx] += v; R[idx] += v; } }
}

const lo = lowshelf(P.bass.freq, P.bass.gain), mid = peaking(P.mid.freq, P.mid.q, P.mid.gain), hi = highshelf(P.air.freq, P.air.gain);
let pL = run(hi, run(mid, run(lo, L))), pR = run(hi, run(mid, run(lo, R)));
const w = P.width, dL = new Float32Array(N), dR = new Float32Array(N);
for (let i = 0; i < N; i++) { const M = (pL[i] + pR[i]) / 2, S = (pL[i] - pR[i]) / 2; dL[i] = M + w * S; dR[i] = M - w * S; }
const k = 2.2, sc = (x) => Math.tanh(k * x) / Math.tanh(k);
for (let i = 0; i < N; i++) { dL[i] = sc(dL[i] * P.outGain); dR[i] = sc(dR[i] * P.outGain); }
const msDry = (rms(L) ** 2 + rms(R) ** 2) / 2, msDolby = (rms(dL) ** 2 + rms(dR) ** 2) / 2;
const mGain = Math.min(4, Math.max(0.25, Math.sqrt(msDry / msDolby)));
for (let i = 0; i < N; i++) { dL[i] *= mGain; dR[i] *= mGain; }

const sideDry = rms(L.map((v, i) => (v - R[i]) / 2)), sideDolby = rms(dL.map((v, i) => (v - dR[i]) / 2));
console.log(`\n================  杜比效果离线验证（${PRESET} 预设）  ================`);
console.log('EQ 频响曲线（低/中/高架串联，dB）：');
for (const f of [60, 150, 400, 1000, 2500, 6000, 12000]) { const db = 20 * Math.log10(mag(lo, f) * mag(mid, f) * mag(hi, f)); console.log(`  ${String(f).padStart(6)} Hz : ${db >= 0 ? '+' : ''}${db.toFixed(1)} dB`); }
console.log(`\n声场展宽（Side RMS）：dry ${sideDry.toFixed(4)} → dolby ${sideDolby.toFixed(4)}  (×${(sideDolby / sideDry).toFixed(2)}，width=${w})`);
console.log(`响度(LUFS 估计)：dry ${lufsFromMeanSquare(msDry).toFixed(1)} · dolby(未匹配) ${lufsFromMeanSquare(msDolby).toFixed(1)} · 匹配增益 ×${mGain.toFixed(2)} → 与 dry 对齐(A/B 公平)`);
const il = new IntegratedLoudness(), hop = (FS * 0.1) | 0;
for (let s = 0; s + hop <= N; s += hop) { let sum = 0; for (let i = s; i < s + hop; i++) sum += dL[i] * dL[i] + dR[i] * dR[i]; il.addBlock(sum / (hop * 2)); }
console.log(`门控积分 LUFS（dolby，${il.count} 块）：${il.integrated().toFixed(1)}`);
const hset = { sampleRate: FS, dirs: [{ az: -30, el: 0 }, { az: 30, el: 0 }], ir: [[Float32Array.of(1, 0.3), Float32Array.of(0.4, 0.1)], [Float32Array.of(0.4, 0.1), Float32Array.of(1, 0.3)]] };
const fakeCtx = { sampleRate: FS, createBuffer: (c, l) => { const a = Array.from({ length: c }, () => new Float32Array(l)); return { numberOfChannels: c, length: l, getChannelData: (i) => a[i] }; } };
console.log(`个性化 HRTF：buildBinauralIR → ${buildBinauralIR(fakeCtx, hset).numberOfChannels} 声道真立体声 IR`);

function wav(file, l, r) {
  let pk = 1e-6; for (let i = 0; i < N; i++) pk = Math.max(pk, Math.abs(l[i]), Math.abs(r[i]));
  const g = pk > 0.99 ? 0.99 / pk : 1, ab = new ArrayBuffer(44 + N * 4), dv = new DataView(ab), str = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); dv.setUint32(4, 36 + N * 4, true); str(8, 'WAVE'); str(12, 'fmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
  dv.setUint32(24, FS, true); dv.setUint32(28, FS * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, N * 4, true);
  let o = 44; for (let i = 0; i < N; i++) { dv.setInt16(o, Math.max(-1, Math.min(1, l[i] * g)) * 32767, true); o += 2; dv.setInt16(o, Math.max(-1, Math.min(1, r[i] * g)) * 32767, true); o += 2; }
  writeFileSync(file, Buffer.from(ab));
}
const dry = path.join(OUT, 'dolby-dry.wav'), dolby = path.join(OUT, 'dolby-processed.wav');
wav(dry, L, R); wav(dolby, dL, dR);
console.log(`\n已写出对比 WAV：\n  ${dry}\n  ${dolby}`);
console.log('====================================================================\n');
