// 生成播放器 Demo 用的小体积 WAV 片段（可复现，非不透明二进制）
// 运行：node web/dolby/tools/make-demo-tracks.mjs
import { writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RATE = 22050;
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'demo-assets');

function env(t, dur, a = 0.012, r = 0.18) {
  const up = Math.min(1, t / a);
  const down = Math.min(1, (dur - t) / r);
  return Math.max(0, up) * Math.max(0, down);
}
function osc(type, ph) {
  if (type === 'sine') return Math.sin(ph);
  if (type === 'triangle') return 2 / Math.PI * Math.asin(Math.sin(ph));
  // 软锯齿
  const x = (ph / (2 * Math.PI)) % 1;
  return (x * 2 - 1) * 0.7;
}

function render(progression, beatDur, beats) {
  const total = Math.floor(beatDur * beats * RATE);
  const buf = new Float32Array(total);
  const addVoice = (freq, startSec, durSec, amp, type) => {
    const s0 = Math.floor(startSec * RATE), n = Math.floor(durSec * RATE);
    for (let i = 0; i < n; i++) {
      const idx = s0 + i; if (idx >= total) break;
      const t = i / RATE;
      buf[idx] += osc(type, 2 * Math.PI * freq * t) * amp * env(t, durSec);
    }
  };
  for (let b = 0; b < beats; b++) {
    const ch = progression[b % progression.length], t0 = b * beatDur;
    for (const f of ch.notes) addVoice(f, t0, beatDur, 0.10, 'saw');   // 铺底
    addVoice(ch.bass, t0, beatDur, 0.28, 'sine');                      // 低音
    for (let k = 0; k < 4; k++) {                                      // 琶音
      addVoice(ch.notes[k % ch.notes.length] * 2, t0 + k * (beatDur / 4), beatDur / 4 * 0.9, 0.14, 'triangle');
    }
  }
  // 归一化 + 边缘淡入淡出
  let peak = 1e-6; for (let i = 0; i < total; i++) peak = Math.max(peak, Math.abs(buf[i]));
  const g = 0.9 / peak, fade = Math.floor(0.05 * RATE);
  for (let i = 0; i < total; i++) {
    let v = buf[i] * g;
    if (i < fade) v *= i / fade;
    if (i > total - fade) v *= (total - i) / fade;
    buf[i] = v;
  }
  return buf;
}

function writeWav(file, samples) {
  const n = samples.length, bytes = 44 + n * 2, ab = new ArrayBuffer(bytes), dv = new DataView(ab);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); dv.setUint32(4, 36 + n * 2, true); str(8, 'WAVE');
  str(12, 'fmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, RATE, true); dv.setUint32(28, RATE * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  str(36, 'data'); dv.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) dv.setInt16(44 + i * 2, Math.max(-1, Math.min(1, samples[i])) * 32767, true);
  writeFileSync(file, Buffer.from(ab));
  console.log(`  ✅ ${path.relative(process.cwd(), file)} (${(bytes / 1024).toFixed(0)} KB)`);
}

const Am = { notes: [220.0, 261.63, 329.63], bass: 110.0 }, F = { notes: [174.61, 220.0, 261.63], bass: 87.31 };
const C = { notes: [261.63, 329.63, 392.0], bass: 130.81 }, G = { notes: [196.0, 246.94, 293.66], bass: 98.0 };
const Dm = { notes: [293.66, 349.23, 440.0], bass: 146.83 }, Bb = { notes: [233.08, 293.66, 349.23], bass: 116.54 };

mkdirSync(OUT, { recursive: true });
console.log('生成 Demo 音轨：');
writeWav(path.join(OUT, 'track-1.wav'), render([Am, F, C, G], 1.2, 4));
writeWav(path.join(OUT, 'track-2.wav'), render([Dm, Bb, F, C], 1.0, 4));
console.log('完成。');
