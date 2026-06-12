import { GET, POST, PATCH, bad, rateLimit } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { hashPassword, verifyPassword, signToken, isMember } from '../lib/auth.js';
import { now, sanitizeText, uid, jparse } from '../lib/util.js';
import { gateContent } from '../lib/moderation.js';
import { AVATARS } from '../lib/catalog.js';
import { unreadCount } from '../lib/notify.js';

export function publicUser(u, viewer = null) {
  if (!u) return null;
  const deleted = u.status === 'deleted';
  return {
    id: u.id,
    nickname: deleted ? '已注销用户' : u.nickname,
    avatar: deleted ? 'blob_10' : u.avatar,
    bio: deleted ? '' : u.bio,
    is_ai: !!u.is_ai,
    ai_label: u.is_ai ? 'AI 暖场官 · AI 生成内容' : null,
    is_member: isMember(u),
    equipped: jparse(u.equipped, {}),
    follower_count: u.follower_count,
    following_count: u.following_count,
    created_at: u.created_at
  };
}

export function meView(u) {
  return {
    ...publicUser(u),
    username: u.username,
    role: u.role,
    member_until: u.member_until,
    credits: u.credits,
    settings: jparse(u.settings, {}),
    unread_notifications: unreadCount(u.id),
    is_guest: !u.username && !!u.device_id
  };
}

function issue(u) {
  q.run('UPDATE users SET last_seen = ? WHERE id = ?', now(), u.id);
  return { token: signToken(u.id), user: meView(u) };
}

function checkNickname(nickname) {
  const nick = sanitizeText(nickname, 12);
  if (!nick || nick.length < 2) throw bad('昵称需要 2-12 个字');
  if (/小句灵|句灵官方|句灵主持|句灵灵感|管理员|admin/i.test(nick)) throw bad('这个昵称是保留昵称哦');
  const gate = gateContent(nick);
  if (!gate.allowed || gate.status === 'pending') throw bad('昵称包含不合适的内容');
  return nick;
}

POST('/api/auth/register', async (ctx) => {
  if (!rateLimit(`reg:${ctx.ip}`, 5, 3600_000)) throw bad('注册太频繁，请稍后再试');
  const username = String(ctx.body.username || '').trim().toLowerCase();
  const password = String(ctx.body.password || '');
  if (!/^[a-z0-9_]{3,20}$/.test(username)) throw bad('用户名需为 3-20 位字母/数字/下划线');
  if (password.length < 6) throw bad('密码至少 6 位');
  if (q.get('SELECT id FROM users WHERE username = ?', username)) throw bad('用户名已被占用');
  const nick = checkNickname(ctx.body.nickname || username);
  const avatar = AVATARS.some((a) => a.id === ctx.body.avatar) ? ctx.body.avatar : AVATARS[Math.floor(Math.random() * AVATARS.length)].id;
  const r = q.run(
    'INSERT INTO users (username, pass_hash, nickname, avatar, created_at, last_seen) VALUES (?,?,?,?,?,?)',
    username, hashPassword(password), nick, avatar, now(), now()
  );
  return issue(q.get('SELECT * FROM users WHERE id = ?', Number(r.lastInsertRowid)));
});

POST('/api/auth/login', async (ctx) => {
  if (!rateLimit(`login:${ctx.ip}`, 10, 600_000)) throw bad('尝试次数过多，请稍后再试');
  const username = String(ctx.body.username || '').trim().toLowerCase();
  const u = q.get('SELECT * FROM users WHERE username = ?', username);
  if (!u || !verifyPassword(String(ctx.body.password || ''), u.pass_hash)) throw bad('用户名或密码不对哦');
  if (u.status === 'deleted') throw bad('该账号已注销');
  return issue(u);
});

// 游客一键进入（设备号绑定，可后续升级为正式账号）
POST('/api/auth/guest', async (ctx) => {
  if (!rateLimit(`guest:${ctx.ip}`, 20, 3600_000)) throw bad('操作太频繁');
  let deviceId = String(ctx.body.device_id || '').slice(0, 64);
  if (!deviceId) deviceId = uid('dev_', 24);
  let u = q.get('SELECT * FROM users WHERE device_id = ?', deviceId);
  if (!u) {
    const av = AVATARS[Math.floor(Math.random() * AVATARS.length)];
    const r = q.run(
      'INSERT INTO users (device_id, nickname, avatar, created_at, last_seen) VALUES (?,?,?,?,?)',
      deviceId, `${av.name}${String(Math.floor(Math.random() * 9000) + 1000)}`, av.id, now(), now()
    );
    u = q.get('SELECT * FROM users WHERE id = ?', Number(r.lastInsertRowid));
  }
  if (u.status === 'deleted') throw bad('该账号已注销');
  const out = issue(u);
  return { ...out, device_id: deviceId };
});

GET('/api/me', async (ctx) => meView(ctx.user), { auth: true });

PATCH('/api/me', async (ctx) => {
  const u = ctx.user;
  const fields = {};
  if (ctx.body.nickname !== undefined) fields.nickname = checkNickname(ctx.body.nickname);
  if (ctx.body.bio !== undefined) {
    const bio = sanitizeText(ctx.body.bio, 60);
    const gate = gateContent(bio);
    if (!gate.allowed) throw bad('简介包含不合适的内容');
    fields.bio = bio;
  }
  if (ctx.body.avatar !== undefined) {
    if (!AVATARS.some((a) => a.id === ctx.body.avatar)) throw bad('头像不存在');
    fields.avatar = ctx.body.avatar;
  }
  if (ctx.body.settings !== undefined && typeof ctx.body.settings === 'object') {
    const cur = jparse(u.settings, {});
    const allowed = ['no_ai_warmup', 'hide_ai_posts', 'teen_mode', 'reduce_motion'];
    for (const k of allowed) if (k in ctx.body.settings) cur[k] = !!ctx.body.settings[k];
    fields.settings = JSON.stringify(cur);
  }
  const keys = Object.keys(fields);
  if (keys.length) {
    q.run(`UPDATE users SET ${keys.map((k) => `${k} = ?`).join(', ')} WHERE id = ?`, ...keys.map((k) => fields[k]), u.id);
  }
  return meView(q.get('SELECT * FROM users WHERE id = ?', u.id));
}, { auth: true });

// 注销账号：匿名化处理（保留内容骨架但不可识别个人）
POST('/api/me/deactivate', async (ctx) => {
  if (String(ctx.body.confirm) !== '确认注销') throw bad('请输入「确认注销」以完成操作');
  q.run(
    `UPDATE users SET status='deleted', username=NULL, pass_hash=NULL, device_id=NULL,
     nickname='已注销用户', bio='', settings='{}' WHERE id = ?`, ctx.user.id
  );
  return { done: true, message: '账号已注销。感谢你来过句灵，江湖再见。' };
}, { auth: true });
