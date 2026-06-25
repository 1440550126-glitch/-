// 对称加密小盒：用于把用户的大模型 API Key 加密落库（AES-256-GCM，零依赖 node:crypto）。
// 密钥由 APP_SECRET / 持久化的 app_secret 派生；历史明文可平滑兼容（open 原样返回）。
import crypto from 'node:crypto';
import { getSetting } from './db.js';

let _key = null;
function key() {
  if (_key) return _key;
  const secret = process.env.APP_SECRET || getSetting('app_secret') || 'jvling-dev-secret';
  _key = crypto.createHash('sha256').update('llm-key:' + secret).digest();   // 32 字节
  return _key;
}

const PREFIX = 'enc1:';

export function seal(plain) {
  if (plain == null || plain === '') return '';
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key(), iv);
  const ct = Buffer.concat([cipher.update(String(plain), 'utf8'), cipher.final()]);
  return PREFIX + Buffer.concat([iv, cipher.getAuthTag(), ct]).toString('base64');
}

export function open(blob) {
  if (!blob) return '';
  const s = String(blob);
  if (!s.startsWith(PREFIX)) return s;                 // 兼容历史明文
  try {
    const raw = Buffer.from(s.slice(PREFIX.length), 'base64');
    const d = crypto.createDecipheriv('aes-256-gcm', key(), raw.subarray(0, 12));
    d.setAuthTag(raw.subarray(12, 28));
    return Buffer.concat([d.update(raw.subarray(28)), d.final()]).toString('utf8');
  } catch { return ''; }                                // 密钥变化/损坏 → 视为不可用，用户重填
}

export const isSealed = (s) => typeof s === 'string' && s.startsWith(PREFIX);
