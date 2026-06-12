import { GET, POST, DEL, bad, notFound } from '../lib/httpx.js';
import { q, tx } from '../lib/db.js';
import { now } from '../lib/util.js';
import { publicUser } from './auth.js';
import { postView } from './posts.js';
import { notify, unreadCount } from '../lib/notify.js';
import { openSSE } from '../lib/httpx.js';
import { subscribe } from '../lib/hub.js';

GET('/api/users/:id', async (ctx) => {
  const u = q.get('SELECT * FROM users WHERE id = ?', Number(ctx.params.id));
  if (!u) throw notFound('用户不存在');
  const postCount = q.get("SELECT COUNT(*) c FROM posts WHERE user_id = ? AND status = 'active'", u.id)?.c || 0;
  const likeSum = q.get("SELECT COALESCE(SUM(like_count),0) c FROM posts WHERE user_id = ? AND status = 'active'", u.id)?.c || 0;
  return {
    user: publicUser(u),
    stats: { posts: postCount, likes_received: likeSum },
    viewer: ctx.user ? {
      following: !!q.get('SELECT 1 x FROM follows WHERE follower_id = ? AND followee_id = ?', ctx.user.id, u.id),
      blocked: !!q.get('SELECT 1 x FROM blocks WHERE user_id = ? AND blocked_id = ?', ctx.user.id, u.id),
      is_me: ctx.user.id === u.id
    } : null
  };
});

GET('/api/users/:id/posts', async (ctx) => {
  const uid = Number(ctx.params.id);
  const before = Number(ctx.query.get('before')) || 0;
  const isOwner = ctx.user && (ctx.user.id === uid || ctx.user.role === 'admin');
  const rows = q.all(
    `SELECT * FROM posts WHERE user_id = ? AND (status = 'active' OR (? = 1 AND status IN ('pending','rejected')))
     AND (? = 0 OR id < ?) ORDER BY id DESC LIMIT 11`,
    uid, isOwner ? 1 : 0, before, before
  );
  return {
    items: rows.slice(0, 10).map((p) => postView(p, ctx.user)),
    next: rows.length > 10 ? rows[9].id : null
  };
});

GET('/api/me/collects', async (ctx) => {
  const before = Number(ctx.query.get('before')) || 0;
  const rows = q.all(
    `SELECT p.*, c.created_at collected_at FROM collects c JOIN posts p ON p.id = c.post_id
     WHERE c.user_id = ? AND p.status = 'active' AND (? = 0 OR p.id < ?) ORDER BY c.created_at DESC LIMIT 11`,
    ctx.user.id, before, before
  );
  return { items: rows.slice(0, 10).map((p) => postView(p, ctx.user)), next: rows.length > 10 ? rows[9].id : null };
}, { auth: true });

POST('/api/users/:id/follow', async (ctx) => {
  const target = Number(ctx.params.id);
  if (target === ctx.user.id) throw bad('不能关注自己哦');
  const u = q.get("SELECT id FROM users WHERE id = ? AND status != 'deleted'", target);
  if (!u) throw notFound('用户不存在');
  return tx(() => {
    if (!q.get('SELECT 1 x FROM follows WHERE follower_id = ? AND followee_id = ?', ctx.user.id, target)) {
      q.run('INSERT INTO follows (follower_id, followee_id, created_at) VALUES (?,?,?)', ctx.user.id, target, now());
      q.run('UPDATE users SET following_count = following_count + 1 WHERE id = ?', ctx.user.id);
      q.run('UPDATE users SET follower_count = follower_count + 1 WHERE id = ?', target);
      notify(target, 'follow', { actorId: ctx.user.id });
    }
    return { following: true };
  });
}, { auth: true });

DEL('/api/users/:id/follow', async (ctx) => {
  const target = Number(ctx.params.id);
  return tx(() => {
    const r = q.run('DELETE FROM follows WHERE follower_id = ? AND followee_id = ?', ctx.user.id, target);
    if (r.changes > 0) {
      q.run('UPDATE users SET following_count = MAX(0, following_count - 1) WHERE id = ?', ctx.user.id);
      q.run('UPDATE users SET follower_count = MAX(0, follower_count - 1) WHERE id = ?', target);
    }
    return { following: false };
  });
}, { auth: true });

POST('/api/users/:id/block', async (ctx) => {
  const target = Number(ctx.params.id);
  if (target === ctx.user.id) throw bad('不能拉黑自己');
  if (!q.get('SELECT 1 x FROM blocks WHERE user_id = ? AND blocked_id = ?', ctx.user.id, target)) {
    q.run('INSERT INTO blocks (user_id, blocked_id, created_at) VALUES (?,?,?)', ctx.user.id, target, now());
  }
  q.run('DELETE FROM follows WHERE follower_id = ? AND followee_id = ?', ctx.user.id, target);
  return { blocked: true, message: '已拉黑，你将不再看到 TA 的内容' };
}, { auth: true });

DEL('/api/users/:id/block', async (ctx) => {
  q.run('DELETE FROM blocks WHERE user_id = ? AND blocked_id = ?', ctx.user.id, Number(ctx.params.id));
  return { blocked: false };
}, { auth: true });

GET('/api/me/blocks', async (ctx) => {
  const rows = q.all(
    'SELECT u.* FROM blocks b JOIN users u ON u.id = b.blocked_id WHERE b.user_id = ? ORDER BY b.created_at DESC LIMIT 100',
    ctx.user.id
  );
  return { items: rows.map((u) => publicUser(u)) };
}, { auth: true });

// ---- 通知中心 ----
GET('/api/notifications', async (ctx) => {
  const rows = q.all('SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 50', ctx.user.id);
  return {
    items: rows.map((n) => ({
      ...n,
      actor: n.actor_id ? publicUser(q.get('SELECT * FROM users WHERE id = ?', n.actor_id)) : null
    })),
    unread: unreadCount(ctx.user.id)
  };
}, { auth: true });

POST('/api/notifications/read', async (ctx) => {
  q.run('UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0', ctx.user.id);
  return { done: true };
}, { auth: true });

GET('/api/me/unread', async (ctx) => ({ unread: unreadCount(ctx.user.id) }), { auth: true });

// 个人实时通道（小铃铛即时 +1）
GET('/api/inbox/events', async (ctx) => {
  const client = openSSE(ctx.req, ctx.res);
  subscribe('inbox', client, ctx.user.id);
}, { auth: true });
