import crypto from 'node:crypto';
import { q, getSetting, setSetting } from './db.js';
import { now } from './util.js';

let SECRET = process.env.APP_SECRET || '';
export function initSecret() {
  if (SECRET) return;
  let s = getSetting('app_secret');
  if (!s) {
    s = crypto.randomBytes(32).toString('hex');
    setSetting('app_secret', s);
  }
  SECRET = s;
}

export function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 32).toString('hex');
  return `${salt}:${hash}`;
}
export function verifyPassword(password, stored) {
  if (!stored) return false;
  const [salt, hash] = stored.split(':');
  if (!salt || !hash) return false;
  const test = crypto.scryptSync(password, salt, 32).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), Buffer.from(test, 'hex'));
}

const b64u = (buf) => Buffer.from(buf).toString('base64url');

export function signToken(userId, days = 30) {
  const payload = b64u(JSON.stringify({ u: userId, e: now() + days * 86400_000 }));
  const sig = crypto.createHmac('sha256', SECRET).update(payload).digest('base64url');
  return `${payload}.${sig}`;
}

export function verifyToken(token) {
  if (!token || typeof token !== 'string') return null;
  const [payload, sig] = token.split('.');
  if (!payload || !sig) return null;
  const expect = crypto.createHmac('sha256', SECRET).update(payload).digest('base64url');
  if (sig.length !== expect.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expect))) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString());
    if (!data.u || data.e < now()) return null;
    return data.u;
  } catch { return null; }
}

// 取当前请求用户；封禁到期自动解封
export function userFromToken(token) {
  const uid = verifyToken(token);
  if (!uid) return null;
  const user = q.get('SELECT * FROM users WHERE id = ?', uid);
  if (!user || user.status === 'deleted') return null;
  if (user.status === 'banned' && user.banned_until && user.banned_until < now()) {
    q.run("UPDATE users SET status = 'active', banned_until = NULL, banned_reason = NULL WHERE id = ?", uid);
    user.status = 'active';
  }
  return user;
}

export const isMember = (user) => !!user && user.member_until > now();
