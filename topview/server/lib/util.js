// 爆款工厂 · 通用工具（零依赖）
import crypto from 'node:crypto';

export const now = () => Date.now();

export const uid = (prefix = '') =>
  prefix + crypto.randomBytes(9).toString('base64url').replace(/[-_]/g, 'a');

export const token32 = () => 'tvk_' + crypto.randomBytes(24).toString('base64url');

export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, Number(v) || 0));

export const pick = (arr, rnd = Math.random) => arr[Math.floor(rnd() * arr.length)];

export function jparse(str, fallback = null) {
  if (str == null || str === '') return fallback;
  if (typeof str === 'object') return str;
  try { return JSON.parse(str); } catch { return fallback; }
}

/** 字符串哈希 → 稳定伪随机（本地生成器按提示词出确定性的画面） */
export function hashCode(str) {
  let h = 2166136261;
  for (let i = 0; i < String(str).length; i++) {
    h ^= String(str).charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
export function seededRandom(seed) {
  let s = seed >>> 0 || 88675123;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
}

export const estimateTokens = (text = '') => Math.ceil([...String(text)].length * 0.8);

export const escapeXML = (s = '') => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

export const micro2yuan = (micro) => (Number(micro || 0) / 1_000_000).toFixed(4).replace(/0+$/, '').replace(/\.$/, '') || '0';

/** 画幅 → 像素（本地 SVG 与各家 size 参数共用）。电商广告默认竖屏 9:16。 */
export function ratioSize(ratio = '9:16', base = 1280) {
  const map = {
    '16:9': [1280, 720], '9:16': [720, 1280], '1:1': [1024, 1024],
    '4:3': [1152, 864], '3:4': [864, 1152], '4:5': [1024, 1280]
  };
  const [w, h] = map[ratio] || map['9:16'];
  const k = base / 1280;
  return { w: Math.round(w * k), h: Math.round(h * k) };
}

/** 秒数 → SRT 时间戳 00:00:00,000 */
export function srtTime(sec) {
  const ms = Math.max(0, Math.round(sec * 1000));
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const f = ms % 1000;
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(h)}:${p(m)}:${p(s)},${p(f, 3)}`;
}
