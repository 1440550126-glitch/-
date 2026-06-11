import { GET, POST, PUT, bad, notFound } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { now, dayCN, micro2yuan, fen2yuan } from '../lib/util.js';
import { logModeration, invalidateWordCache } from '../lib/moderation.js';
import { warmupConfig, setWarmupConfig, warmupAccountList, warmupPost, ensureTodayTopic } from '../warmup/bot.js';
import { llmEnabled, todayCostMicro } from '../lib/llm.js';
import { publicUser } from './auth.js';
import { postView } from './posts.js';

const A = { admin: true, auth: true };
const dayStartMs = (day = dayCN()) => new Date(day + 'T00:00:00+08:00').getTime();

// ---- 总览 ----
GET('/api/admin/stats', async () => {
  const ds = dayStartMs();
  const g = (sql, ...a) => q.get(sql, ...a)?.c || 0;
  return {
    users: {
      total: g("SELECT COUNT(*) c FROM users WHERE is_ai = 0 AND status != 'deleted'"),
      today_new: g('SELECT COUNT(*) c FROM users WHERE is_ai = 0 AND created_at >= ?', ds),
      today_active: g('SELECT COUNT(*) c FROM users WHERE is_ai = 0 AND last_seen >= ?', ds),
      members: g('SELECT COUNT(*) c FROM users WHERE member_until > ?', now()),
      banned: g("SELECT COUNT(*) c FROM users WHERE status = 'banned'")
    },
    content: {
      posts: g("SELECT COUNT(*) c FROM posts WHERE status = 'active'"),
      today_posts: g('SELECT COUNT(*) c FROM posts WHERE created_at >= ?', ds),
      pending: g("SELECT COUNT(*) c FROM posts WHERE status = 'pending'"),
      comments: g("SELECT COUNT(*) c FROM comments WHERE status = 'active'"),
      open_reports: g("SELECT COUNT(*) c FROM reports WHERE status = 'open'")
    },
    revenue: {
      total_yuan: fen2yuan(g("SELECT COALESCE(SUM(amount_fen),0) c FROM orders WHERE status = 'paid'")),
      today_yuan: fen2yuan(g("SELECT COALESCE(SUM(amount_fen),0) c FROM orders WHERE status = 'paid' AND paid_at >= ?", ds)),
      paid_orders: g("SELECT COUNT(*) c FROM orders WHERE status = 'paid'")
    },
    ai: {
      llm_enabled: llmEnabled(),
      today_cost_yuan: micro2yuan(todayCostMicro()),
      total_cost_yuan: micro2yuan(g('SELECT COALESCE(SUM(cost_micro),0) c FROM ai_usage_logs')),
      today_calls: g('SELECT COUNT(*) c FROM ai_usage_logs WHERE created_at >= ?', ds),
      today_fallbacks: g('SELECT COUNT(*) c FROM ai_usage_logs WHERE created_at >= ? AND fallback = 1', ds)
    },
    warmup: {
      enabled: warmupConfig().enabled,
      today_actions: g('SELECT COUNT(*) c FROM warmup_logs WHERE created_at >= ?', ds)
    },
    games: {
      total: g('SELECT COUNT(*) c FROM game_rooms'),
      today: g('SELECT COUNT(*) c FROM game_rooms WHERE created_at >= ?', ds)
    }
  };
}, A);

// ---- 用户管理 ----
GET('/api/admin/users', async (ctx) => {
  const kw = `%${ctx.query.get('q') || ''}%`;
  const rows = q.all(
    `SELECT * FROM users WHERE (nickname LIKE ? OR username LIKE ? OR CAST(id AS TEXT) = ?)
     ORDER BY id DESC LIMIT 100`, kw, kw, ctx.query.get('q') || ''
  );
  return {
    items: rows.map((u) => ({
      ...publicUser(u), username: u.username, status: u.status, role: u.role,
      banned_until: u.banned_until, banned_reason: u.banned_reason,
      member_until: u.member_until, credits: u.credits, last_seen: u.last_seen
    }))
  };
}, A);

POST('/api/admin/users/:id/ban', async (ctx) => {
  const id = Number(ctx.params.id);
  const u = q.get('SELECT * FROM users WHERE id = ?', id);
  if (!u) throw notFound('用户不存在');
  if (u.role === 'admin') throw bad('不能封禁管理员');
  const days = Math.min(3650, Math.max(1, Number(ctx.body.days) || 7));
  const reason = String(ctx.body.reason || '违反社区规范').slice(0, 100);
  q.run("UPDATE users SET status = 'banned', banned_until = ?, banned_reason = ? WHERE id = ?", now() + days * 86400_000, reason, id);
  logModeration(`admin:${ctx.user.id}`, 'ban', 'user', id, `${days}天：${reason}`);
  return { done: true };
}, A);

POST('/api/admin/users/:id/unban', async (ctx) => {
  q.run("UPDATE users SET status = 'active', banned_until = NULL, banned_reason = NULL WHERE id = ?", Number(ctx.params.id));
  logModeration(`admin:${ctx.user.id}`, 'unban', 'user', ctx.params.id, '');
  return { done: true };
}, A);

// ---- 内容管理 ----
GET('/api/admin/posts', async (ctx) => {
  const status = ctx.query.get('status') || 'all';
  const rows = status === 'all'
    ? q.all('SELECT * FROM posts ORDER BY id DESC LIMIT 100')
    : q.all('SELECT * FROM posts WHERE status = ? ORDER BY id DESC LIMIT 100', status);
  return { items: rows.map((p) => ({ ...postView(p, null), status: p.status, remove_reason: p.remove_reason })) };
}, A);

POST('/api/admin/posts/:id/action', async (ctx) => {
  const id = Number(ctx.params.id);
  const post = q.get('SELECT * FROM posts WHERE id = ?', id);
  if (!post) throw notFound();
  const action = ctx.body.action;
  const reason = String(ctx.body.reason || '').slice(0, 100);
  const map = {
    approve: ['active', '人工审核通过'],
    reject: ['rejected', reason || '审核未通过'],
    remove: ['removed', reason || '违规下架'],
    restore: ['active', '恢复展示']
  };
  if (!map[action]) throw bad('操作无效');
  q.run('UPDATE posts SET status = ?, remove_reason = ? WHERE id = ?', map[action][0], map[action][1], id);
  logModeration(`admin:${ctx.user.id}`, action, 'post', id, map[action][1]);
  return { done: true };
}, A);

GET('/api/admin/comments', async (ctx) => {
  const rows = q.all('SELECT c.*, u.nickname FROM comments c JOIN users u ON u.id = c.user_id ORDER BY c.id DESC LIMIT 100');
  return { items: rows };
}, A);

POST('/api/admin/comments/:id/remove', async (ctx) => {
  const c = q.get('SELECT * FROM comments WHERE id = ?', Number(ctx.params.id));
  if (!c) throw notFound();
  if (c.status === 'active') {
    q.run("UPDATE comments SET status = 'removed' WHERE id = ?", c.id);
    q.run('UPDATE posts SET comment_count = MAX(0, comment_count - 1) WHERE id = ?', c.post_id);
  }
  logModeration(`admin:${ctx.user.id}`, 'remove', 'comment', c.id, '');
  return { done: true };
}, A);

// ---- 举报处理 ----
GET('/api/admin/reports', async (ctx) => {
  const status = ctx.query.get('status') || 'open';
  const rows = q.all('SELECT * FROM reports WHERE (? = ? OR status = ?) ORDER BY id DESC LIMIT 100', status, 'all', status);
  return {
    items: rows.map((r) => {
      let snapshot = null;
      if (r.target_type === 'post') snapshot = q.get('SELECT content, status FROM posts WHERE id = ?', Number(r.target_id));
      if (r.target_type === 'comment') snapshot = q.get('SELECT content, status FROM comments WHERE id = ?', Number(r.target_id));
      if (r.target_type === 'room_message') snapshot = q.get('SELECT content FROM room_messages WHERE id = ?', Number(r.target_id));
      if (r.target_type === 'user') snapshot = q.get('SELECT nickname content, status FROM users WHERE id = ?', Number(r.target_id));
      return { ...r, snapshot };
    })
  };
}, A);

POST('/api/admin/reports/:id/handle', async (ctx) => {
  const r = q.get('SELECT * FROM reports WHERE id = ?', Number(ctx.params.id));
  if (!r) throw notFound();
  const action = ctx.body.action === 'dismiss' ? 'dismissed' : 'resolved';
  q.run('UPDATE reports SET status = ?, handled_by = ?, handle_note = ?, handled_at = ? WHERE id = ?',
    action, ctx.user.id, String(ctx.body.note || '').slice(0, 200), now(), r.id);
  logModeration(`admin:${ctx.user.id}`, `report_${action}`, r.target_type, r.target_id, ctx.body.note || '');
  return { done: true };
}, A);

// ---- AI 暖场配置 ----
GET('/api/admin/warmup', async () => ({
  config: warmupConfig(),
  accounts: warmupAccountList(),
  recent: q.all(`SELECT w.*, u.nickname FROM warmup_logs w LEFT JOIN users u ON u.id = w.account_id ORDER BY w.id DESC LIMIT 50`)
}), A);

PUT('/api/admin/warmup', async (ctx) => {
  const cfg = setWarmupConfig(ctx.body || {});
  logModeration(`admin:${ctx.user.id}`, 'warmup_config', 'settings', 'warmup', JSON.stringify(cfg));
  return { config: cfg };
}, A);

POST('/api/admin/warmup/trigger', async (ctx) => {
  if (ctx.body.action === 'topic') {
    const topic = await ensureTodayTopic(true);
    return { topic };
  }
  const postId = await warmupPost(ctx.body.persona || null);
  return { post_id: postId, message: postId ? '已发布一条暖场内容' : '生成被跳过（重复内容）' };
}, A);

// ---- 皮肤管理 ----
GET('/api/admin/skins', async () => ({ items: q.all('SELECT * FROM skins ORDER BY sort, id') }), A);
POST('/api/admin/skins/:id/update', async (ctx) => {
  const s = q.get('SELECT * FROM skins WHERE id = ?', ctx.params.id);
  if (!s) throw notFound();
  const enabled = ctx.body.enabled === undefined ? s.enabled : (ctx.body.enabled ? 1 : 0);
  const price = ctx.body.price_fen === undefined ? s.price_fen : Math.max(0, Math.min(50000, Number(ctx.body.price_fen) | 0));
  q.run('UPDATE skins SET enabled = ?, price_fen = ? WHERE id = ?', enabled, price, s.id);
  return { done: true };
}, A);

// ---- 订单 ----
GET('/api/admin/orders', async () => {
  const rows = q.all('SELECT o.*, u.nickname FROM orders o JOIN users u ON u.id = o.user_id ORDER BY o.created_at DESC LIMIT 100');
  return { items: rows };
}, A);

// ---- AI 成本 ----
GET('/api/admin/ai-usage', async (ctx) => {
  const days = Math.min(30, Number(ctx.query.get('days')) || 7);
  const daily = [];
  for (let i = 0; i < days; i++) {
    const day = dayCN(now() - i * 86400_000);
    const start = dayStartMs(day);
    const end = start + 86400_000;
    const row = q.get(
      `SELECT COUNT(*) calls, COALESCE(SUM(cost_micro),0) cost, COALESCE(SUM(prompt_tokens),0) ptok,
       COALESCE(SUM(completion_tokens),0) ctok, SUM(fallback) fallbacks
       FROM ai_usage_logs WHERE created_at >= ? AND created_at < ?`, start, end
    );
    daily.push({ day, calls: row.calls, cost_yuan: micro2yuan(row.cost || 0), prompt_tokens: row.ptok, completion_tokens: row.ctok, fallbacks: row.fallbacks || 0 });
  }
  const byFeature = q.all(
    `SELECT feature, COUNT(*) calls, COALESCE(SUM(cost_micro),0) cost FROM ai_usage_logs
     WHERE created_at >= ? GROUP BY feature ORDER BY cost DESC`, now() - days * 86400_000
  ).map((r) => ({ feature: r.feature, calls: r.calls, cost_yuan: micro2yuan(r.cost) }));
  const recent = q.all('SELECT * FROM ai_usage_logs ORDER BY id DESC LIMIT 50');
  return { daily, by_feature: byFeature, recent, llm_enabled: llmEnabled() };
}, A);

// ---- 敏感词 ----
GET('/api/admin/sensitive-words', async () => ({ items: q.all('SELECT * FROM sensitive_words ORDER BY category, word') }), A);
POST('/api/admin/sensitive-words', async (ctx) => {
  const word = String(ctx.body.word || '').trim();
  const category = ['block', 'review', 'selfharm'].includes(ctx.body.category) ? ctx.body.category : 'block';
  if (!word || word.length > 20) throw bad('词语无效');
  q.run('INSERT OR REPLACE INTO sensitive_words (word, category, created_at) VALUES (?,?,?)', word, category, now());
  invalidateWordCache();
  return { done: true };
}, A);
POST('/api/admin/sensitive-words/delete', async (ctx) => {
  q.run('DELETE FROM sensitive_words WHERE word = ?', String(ctx.body.word || ''));
  invalidateWordCache();
  return { done: true };
}, A);

// ---- 审核日志 ----
GET('/api/admin/moderation-logs', async () => ({ items: q.all('SELECT * FROM moderation_logs ORDER BY id DESC LIMIT 100') }), A);
