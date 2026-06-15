// ============================================================
// 一句话变一首歌：文案 → Song Manifest（服务端当"作曲导演"，前端 Web Audio 当"演唱者"）
// 复用 manifest.js 的情绪分析；本地规则引擎保证零成本、离线、永不失败；大模型可选增强。
// 设计与 manifest.js 完全对齐：buildSong = 规则引擎，buildSongEnhanced = 大模型导演 + 白名单校验。
// ============================================================
import { clamp, hashCode, seededRand, jparse } from './util.js';
import { analyzeText } from './manifest.js';
import { llmOrFallback } from './llm.js';

// ---- 乐理底座：音名 / 音阶 / 和弦进行 ----
// 调（主音 MIDI，落在适合"哼唱"的中音区）
const KEYS = [
  { name: 'C', root: 60 }, { name: 'D', root: 62 }, { name: 'E', root: 64 },
  { name: 'F', root: 65 }, { name: 'G', root: 67 }, { name: 'A', root: 69 }
];
// 音阶（相对主音的半音数）
const SCALES = {
  major: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
  pentatonic_major: [0, 2, 4, 7, 9],
  pentatonic_minor: [0, 3, 5, 7, 10]
};
// 和弦进行（音阶级数，1-based；不同情绪走不同的"色彩"）
const PROGRESSIONS = {
  major: [[1, 5, 6, 4], [1, 4, 5, 4], [6, 4, 1, 5]],
  minor: [[1, 6, 3, 7], [1, 4, 1, 5], [1, 7, 6, 7]],
  pentatonic_major: [[1, 5, 6, 4], [1, 4, 1, 5]],
  pentatonic_minor: [[1, 4, 1, 5], [1, 6, 1, 5]]
};
const INSTRUMENTS = ['music_box', 'soft_pluck', 'warm_pad', 'bell'];
const MODE_LIST = Object.keys(SCALES);

export const midiToFreq = (m) => 440 * Math.pow(2, (m - 69) / 12);

// 音阶级 → MIDI（支持跨八度的正负 degree）
function degreeToMidi(rootMidi, scale, degree) {
  const n = scale.length;
  const oct = Math.floor(degree / n);
  const idx = ((degree % n) + n) % n;
  return rootMidi + oct * 12 + scale[idx];
}
// 在某音阶级上叠三和弦（root / +2 / +4 音阶级）
function triad(rootMidi, scale, deg) {
  return [deg, deg + 2, deg + 4].map((d) => degreeToMidi(rootMidi, scale, d));
}
// 找最接近当前 degree 的"稳定收束音"（主音或当前和弦音）
function nearestStable(scale, degree, chordRootDeg) {
  const targets = [0, chordRootDeg, chordRootDeg + 2];
  const n = scale.length;
  let best = degree, bestD = 99;
  for (const tb of targets) {
    for (let oct = -1; oct <= 1; oct++) {
      const cand = tb + oct * n;
      const d = Math.abs(cand - degree);
      if (d < bestD) { bestD = d; best = cand; }
    }
  }
  return best;
}

// 情绪 → 调式（valence 正负定大小调，治愈/平静用五声更空灵）
function modeFor(emotion) {
  const { key, valence, arousal } = emotion;
  if (key === '治愈' || key === '平静') return valence >= 0 ? 'pentatonic_major' : 'pentatonic_minor';
  if (valence >= 0.35) return 'major';
  if (valence <= -0.2) return 'minor';
  return arousal > 0.5 ? 'major' : 'pentatonic_major';
}

// 文案 → 可演唱的"字"序列（标点变成换气/乐句边界）
function tokenize(text) {
  const tokens = [];
  for (const ch of String(text || '').trim()) {
    if (/\s/.test(ch)) continue;
    if (/[，。、,.!?！？;；:：~…—\-·]/.test(ch)) {
      if (tokens.length) tokens[tokens.length - 1].brk = true;
      continue;
    }
    tokens.push({ ch, brk: false });
  }
  return tokens;
}

function makeTitle(text, emotion) {
  const clean = String(text).replace(/[，。、,.!?！？;；:：~…—\s]+/g, ' ').trim();
  const first = (clean.split(' ')[0] || clean).slice(0, 8);
  return first || `${emotion.key}小调`;
}

/**
 * 规则引擎作曲：纯本地、零成本、可复现（同一文案恒定同一首）。
 * @param {object} override 可由大模型导演覆盖：{mode,bpm,progression,motif,instrument,title}
 * @returns {object} Song Manifest
 */
export function buildSong(text, { seed, override = {} } = {}) {
  const a = analyzeText(text);
  const emotion = a.emotion;
  const sd = (seed ?? hashCode('song:' + String(text))) >>> 0;
  const rnd = seededRand(sd);

  const mode = SCALES[override.mode] ? override.mode : modeFor(emotion);
  const scale = SCALES[mode];
  const keyPick = KEYS[Math.floor(rnd() * KEYS.length)];
  const rootMidi = keyPick.root;
  const bpm = clamp(Math.round(override.bpm || (62 + emotion.arousal * 70)), 50, 150);
  const beatsPerBar = 4;

  const progPool = PROGRESSIONS[mode];
  let progression = Array.isArray(override.progression)
    ? override.progression.map(Number).filter((d) => Number.isInteger(d) && d >= 1 && d <= scale.length).slice(0, 8)
    : [];
  if (!progression.length) progression = progPool[Math.floor(rnd() * progPool.length)];

  const instrument = INSTRUMENTS.includes(override.instrument) ? override.instrument
    : emotion.key === '难过' || emotion.key === '孤独' ? 'music_box'
      : emotion.arousal > 0.7 ? 'soft_pluck'
        : emotion.key === '治愈' || emotion.key === '平静' ? 'warm_pad'
          : 'bell';

  // 歌词单元（截断到一段，避免歌太长）
  let tokens = tokenize(text);
  if (!tokens.length) tokens = [{ ch: '啦', brk: false }];
  const MAX = 40;
  if (tokens.length > MAX) { tokens = tokens.slice(0, MAX); tokens[MAX - 1].brk = true; }

  // 旋律轮廓（可被大模型 motif 覆盖；否则随机走子）
  const motif = Array.isArray(override.motif) && override.motif.length
    ? override.motif.map((n) => clamp(Math.round(n), -5, 5))
    : null;

  const fast = emotion.arousal > 0.6;
  const rhythmPool = fast ? [0.5, 0.5, 0.5, 1, 1] : [1, 1, 1, 1.5, 2, 0.5];
  const center = mode.startsWith('pentatonic') ? 2 : 3; // 旋律重心音阶级

  const melody = [];
  let degree = 0;
  let t = 0;
  for (let i = 0; i < tokens.length; i++) {
    const chordRootDeg = progression[Math.floor(t / beatsPerBar) % progression.length] - 1;
    const beatInBar = t % beatsPerBar;
    const strong = beatInBar === 0 || beatInBar === 2; // 强拍

    // 旋律走子：多为级进，偶尔跳进
    let step;
    if (motif) step = motif[i % motif.length];
    else {
      const r = rnd();
      step = r < 0.5 ? (rnd() < 0.5 ? 1 : -1)
        : r < 0.78 ? (rnd() < 0.5 ? 2 : -2)
          : r < 0.9 ? 0 : (rnd() < 0.5 ? 3 : -3);
    }
    degree += step;
    if (degree > center + 5) degree -= 4;   // 向重心回拉，防跑飞
    if (degree < center - 5) degree += 4;

    // 强拍吸附到和弦音，弱拍保留经过音
    if (strong) {
      const chordTones = [chordRootDeg, chordRootDeg + 2, chordRootDeg + 4];
      let best = degree, bestD = 99;
      for (const ctBase of chordTones) {
        for (let oct = -1; oct <= 1; oct++) {
          const cand = ctBase + oct * scale.length;
          const d = Math.abs(cand - degree);
          if (d < bestD) { bestD = d; best = cand; }
        }
      }
      degree = best;
    }

    const token = tokens[i];
    const last = i === tokens.length - 1;
    let dur = rhythmPool[Math.floor(rnd() * rhythmPool.length)];

    if (token.brk || last) {
      // 乐句收束：落稳定音并拉长，句间留换气
      const resolveDeg = strong ? degree : nearestStable(scale, degree, chordRootDeg);
      dur = Math.max(dur, fast ? 1 : 1.5);
      melody.push({ midi: degreeToMidi(rootMidi, scale, resolveDeg), t: +t.toFixed(3), dur: +dur.toFixed(3), lyric: token.ch });
      degree = resolveDeg;
      t += dur + (last ? 0 : 0.5);
      continue;
    }
    melody.push({ midi: degreeToMidi(rootMidi, scale, degree), t: +t.toFixed(3), dur: +dur.toFixed(3), lyric: token.ch });
    t += dur;
  }

  const totalBeats = Math.max(t, beatsPerBar);
  const secPerBeat = 60 / bpm;

  // 和弦伴奏：每小节一个和弦，低八度铺底
  const chords = [];
  const bars = Math.ceil(totalBeats / beatsPerBar);
  for (let b = 0; b < bars; b++) {
    chords.push({ t: b * beatsPerBar, dur: beatsPerBar, midi: triad(rootMidi - 12, scale, progression[b % progression.length] - 1) });
  }

  return {
    v: 1,
    title: (override.title && String(override.title).slice(0, 12)) || makeTitle(text, emotion),
    mode,
    keyName: keyPick.name,
    rootMidi,
    bpm,
    beatsPerBar,
    emotion: { key: emotion.key, valence: emotion.valence, arousal: emotion.arousal },
    instrument,
    progression,
    melody,
    chords,
    durationSec: +(totalBeats * secPerBeat).toFixed(2),
    lyric: String(text).trim(),
    meta: { generated_by: override._by || 'rule', ai_label: 'AI 生成旋律 · 仅供体验' }
  };
}

// ---- 大模型"作曲导演"：输出受白名单约束的作曲 JSON，校验后驱动规则引擎 ----
function sanitizeSongPatch(p) {
  const out = {};
  if (!p || typeof p !== 'object') return out;
  if (typeof p.title === 'string') out.title = p.title.slice(0, 12);
  if (SCALES[p.mode]) out.mode = p.mode;
  if (Number(p.bpm) >= 50 && Number(p.bpm) <= 150) out.bpm = Math.round(Number(p.bpm));
  if (Array.isArray(p.progression)) {
    const prog = p.progression.map(Number).filter((d) => Number.isInteger(d) && d >= 1 && d <= 7).slice(0, 8);
    if (prog.length) out.progression = prog;
  }
  if (INSTRUMENTS.includes(p.instrument)) out.instrument = p.instrument;
  if (Array.isArray(p.motif)) {
    const motif = p.motif.map(Number).filter(Number.isFinite).map((n) => clamp(Math.round(n), -5, 5)).slice(0, 8);
    if (motif.length) out.motif = motif;
  }
  return out;
}

export async function buildSongEnhanced(text, { seed, userId, premium = false } = {}) {
  const base = buildSong(text, { seed });
  const system = '你是"句灵"的作曲导演。根据用户文案，决定这首小歌的基调，只能输出 JSON，字段：' +
    'title(不超过10字的歌名), ' +
    `mode(${MODE_LIST.join('/')}), bpm(50-150整数), ` +
    'progression(和弦进行，2-8个 1到7 的整数), ' +
    'instrument(music_box/soft_pluck/warm_pad/bell), ' +
    'motif(8个以内 -5到5 的整数，描述主旋律的起伏轮廓)。不要输出其他内容。';
  const r = await llmOrFallback({
    feature: premium ? 'song_premium' : 'song',
    userId,
    tier: premium ? 'premium' : 'default',
    system,
    prompt: `文案：「${String(text).slice(0, 120)}」\n当前情绪判定：${base.emotion.key}。请给出作曲 JSON。`,
    json: true,
    maxTokens: 300,
    temperature: 0.7,
    fallbackFn: () => null
  });
  if (r.byLLM) {
    const patch = sanitizeSongPatch(jparse(r.text, null));
    const song = buildSong(text, { seed, override: { ...patch, _by: premium ? 'llm_premium' : 'llm' } });
    song.meta.ai_label = '内容由 AI 作曲 · 仅供体验';
    return song;
  }
  return base;
}
