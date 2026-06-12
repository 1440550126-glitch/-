import crypto from 'node:crypto';

export const now = () => Date.now();

// 北京时间的 YYYY-MM-DD（产品面向国内用户，配额/话题按东八区切天）
export function dayCN(ts = Date.now()) {
  return new Date(ts + 8 * 3600_000).toISOString().slice(0, 10);
}
export function hourCN(ts = Date.now()) {
  return new Date(ts + 8 * 3600_000).getUTCHours();
}

export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, Number(v) || 0));
export const pick = (arr, rnd = Math.random) => arr[Math.floor(rnd() * arr.length)];
export const randInt = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));
export const shuffle = (arr) => {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};

export const uid = (prefix = '', len = 10) =>
  prefix + crypto.randomBytes(len).toString('base64url').replace(/[-_]/g, 'a').slice(0, len);

export const roomCode = () => {
  // 6 位数字房间码，避开易混淆开头 0
  return String(randInt(100000, 999999));
};

export function jparse(str, fallback = null) {
  if (str == null) return fallback;
  if (typeof str === 'object') return str;
  try { return JSON.parse(str); } catch { return fallback; }
}

export const fen2yuan = (fen) => (fen / 100).toFixed(2);
export const micro2yuan = (micro) => (micro / 1_000_000).toFixed(4);

// 估算中文为主文本的 token 数（无 usage 返回时兜底统计成本用）
export const estimateTokens = (text) => Math.max(1, Math.ceil(String(text || '').length / 1.6));

export function sanitizeText(text, maxLen) {
  return String(text ?? '')
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
    .trim()
    .slice(0, maxLen);
}

// 简单的可种子化随机数（动画 Manifest 用，保证同一帖子动画形态可复现）
export function seededRand(seed) {
  let s = seed >>> 0 || 88675123;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
}

export function hashCode(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h;
}
