import { GET, POST, DEL, bad, notFound, denied } from '../lib/httpx.js';
import { q, tx } from '../lib/db.js';
import { now, jparse, sanitizeText } from '../lib/util.js';
import { gateContent, logModeration } from '../lib/moderation.js';
import { buildCard } from '../lib/manifest.js';
import { onNewUserPost, ensureTodayTopic } from '../warmup/bot.js';
import { publicUser } from './auth.js';
import { QUOTA, REPORT_REASONS } from '../lib/catalog.js';
import { useQuota } from '../lib/llm.js';

// ---- 帖子视图 ----
export function postView(row, viewer) {
  if (!row) return null;
  const author = q.get('SELECT * FROM users WHERE id = ?', row.user_id);
  return {
    id: row.id,
    content: row.content,
    card: jparse(row.card, {}),
    has_manifest: !!row.manifest,
    status: row.status,
    is_ai: !!row.is_ai,
    ai_label: row.ai_label || null,
    topic_id: row.topic_id,
    like_count: row.like_count,
    ai_like_count: row.ai_like_count,
    comment_count: row.comment_count,
    collect_count: row.collect_count,
    share_count: row.share_count,
    play_count: row.play_count,
    created_at: row.created_at,
    author: publicUser(author),
    viewer: viewer ? {
      liked: !!q.get('SELECT 1 x FROM likes WHERE user_id = ? AND post_id = ?', viewer.id, row.id),
      collected: !!q.get('SELECT 1 x FROM collects WHERE user_id = ? AND post_id = ?', viewer.id, row.id),
      following_author: !!q.get('SELECT 1 x FROM follows WHERE follower_id = ? AND followee_id = ?', viewer.id, row.user_id),
      is_author: viewer.id === row.user_id
    } : null
  };
}

function blockedIds(viewer) {
  if (!viewer) return new Set();
  const rows = q.all(
    'SELECT blocked_id id FROM blocks WHERE user_id = ? UNION SELECT user_id id FROM blocks WHERE blocked_id = ?',
    viewer.id, viewer.id
  );
  return new Set(rows.map((r) => r.id));
}

const hotScoreOf = (p) => 3 * p.like_count + 4 * p.comment_count + 3 * p.collect_count + 2 * p.share_count + 0.2 * p.play_count;
const decayed = (p) => hotScoreOf(p) / Math.pow((now() - p.created_at) / 3600_000 + 2, 1.4);

export function bumpHot(postId) {
  const p = q.get('SELECT * FROM posts WHERE id = ?', postId);
  if (p) q.run('UPDATE posts SET hot_score = ? WHERE id = ?', hotScoreOf(p), postId);
}

// ---- 信息流：rec 推荐 / new 最新 / follow 关注 / hot 热门榜 ----
GET('/api/posts', async (ctx) => {
  const tab = ctx.query.get('tab') || 'rec';
  const limit = Math.min(20, Number(ctx.query.get('limit')) || 10);
  const before = Number(ctx.query.get('before')) || 0;   // 游标：上一页最后一条 id
  const viewer = ctx.user;
  const blocked = blockedIds(viewer);
  const hideAI = viewer ? !!jparse(viewer.settings, {}).hide_ai_posts : false;

  let rows;
  if (tab === 'follow') {
    if (!viewer) return { items: [], next: null, need_login: true };
    rows = q.all(
      `SELECT p.* FROM posts p JOIN follows f ON f.followee_id = p.user_id
       WHERE f.follower_id = ? AND p.status = 'active' AND (? = 0 OR p.id < ?)
       ORDER BY p.id DESC LIMIT ?`, viewer.id, before, before, limit + 1
    );
  } else if (tab === 'new') {
    rows = q.all(
      `SELECT * FROM posts WHERE status = 'active' AND (? = 0 OR id < ?) ORDER BY id DESC LIMIT ?`,
      before, before, limit + 1
    );
  } else {
    // rec/hot：取近 7 天活跃帖在内存按"热度/时间衰减"排序（MVP 规模足够；规模化后移到离线任务）
    const since = now() - 7 * 86400_000;
    const pool = q.all(`SELECT * FROM posts WHERE status = 'active' AND created_at > ? ORDER BY id DESC LIMIT 300`, since);
    const sorted = pool.sort((a, b) => (tab === 'hot' ? hotScoreOf(b) - hotScoreOf(a) : decayed(b) - decayed(a)));
    const offset = Number(ctx.query.get('offset')) || 0;
    rows = sorted.slice(offset, offset + limit + 1);
    const filtered = rows.filter((p) => !blocked.has(p.user_id) && !(hideAI && p.is_ai));
    return {
      items: filtered.slice(0, limit).map((p) => postView(p, viewer)),
      next_offset: rows.length > limit ? offset + limit : null
    };
  }
  const filtered = rows.filter((p) => !blocked.has(p.user_id) && !(hideAI && p.is_ai)).slice(0, limit);
  return {
    items: filtered.map((p) => postView(p, viewer)),
    next: rows.length > limit && filtered.length ? filtered[filtered.length - 1].id : null
  };
});

// ---- 发布 ----
POST('/api/posts', async (ctx) => {
  const content = sanitizeText(ctx.body.content, 300);
  if (!content || content.length < 2) throw bad('写点什么吧，哪怕只有几个字');
  if (!useQuota(ctx.user.id, 'post', QUOTA.POST_PER_DAY)) throw bad('今天发得有点多啦，明天再来～');
  const dup = q.get('SELECT id FROM posts WHERE user_id = ? AND content = ? AND created_at > ?', ctx.user.id, content, now() - 600_000);
  if (dup) throw bad('刚刚才发过一样的内容哦');

  const gate = gateContent(content);
  if (!gate.allowed) {
    logModeration('system', 'block', 'post_attempt', ctx.user.id, `敏感词:${gate.hits.join(',')}`);
    throw bad(gate.notice);
  }
  const topicId = ctx.body.topic_id ? Number(ctx.body.topic_id) : null;
  const card = buildCard(content, String(ctx.user.id));
  const r = q.run(
    `INSERT INTO posts (user_id, content, topic_id, card, status, created_at) VALUES (?,?,?,?,?,?)`,
    ctx.user.id, content, topicId, JSON.stringify(card), gate.status, now()
  );
  const post = q.get('SELECT * FROM posts WHERE id = ?', Number(r.lastInsertRowid));
  if (gate.status === 'pending') {
    logModeration('system', 'review', 'post', post.id, `敏感词:${gate.hits.join(',')}${gate.care ? ' (自伤关怀)' : ''}`);
  } else {
    onNewUserPost(post, jparse(ctx.user.settings, {}));   // AI 暖场延迟评论
  }
  return { post: postView(post, ctx.user), notice: gate.notice, care: gate.care || false };
}, { auth: true });

GET('/api/posts/:id', async (ctx) => {
  const post = q.get('SELECT * FROM posts WHERE id = ?', Number(ctx.params.id));
  if (!post || post.status === 'removed' || post.status === 'rejected') throw notFound();
  if (post.status === 'pending' && (!ctx.user || (ctx.user.id !== post.user_id && ctx.user.role !== 'admin'))) throw notFound();
  return postView(post, ctx.user);
});

DEL('/api/posts/:id', async (ctx) => {
  const post = q.get('SELECT * FROM posts WHERE id = ?', Number(ctx.params.id));
  if (!post) throw notFound();
  if (post.user_id !== ctx.user.id && ctx.user.role !== 'admin') throw denied();
  q.run("UPDATE posts SET status = 'removed', remove_reason = ? WHERE id = ?", post.user_id === ctx.user.id ? '作者删除' : '管理员删除', post.id);
  logModeration(post.user_id === ctx.user.id ? `user:${ctx.user.id}` : `admin:${ctx.user.id}`, 'remove', 'post', post.id, '');
  return { done: true };
}, { auth: true });

// ---- 互动 ----
function toggle(table, countCol, ctx, on) {
  const postId = Number(ctx.params.id);
  const post = q.get("SELECT * FROM posts WHERE id = ? AND status = 'active'", postId);
  if (!post) throw notFound();
  return tx(() => {
    const exists = q.get(`SELECT 1 x FROM ${table} WHERE user_id = ? AND post_id = ?`, ctx.user.id, postId);
    if (on && !exists) {
      q.run(`INSERT INTO ${table} (user_id, post_id, created_at) VALUES (?,?,?)`, ctx.user.id, postId, now());
      q.run(`UPDATE posts SET ${countCol} = ${countCol} + 1 WHERE id = ?`, postId);
    } else if (!on && exists) {
      q.run(`DELETE FROM ${table} WHERE user_id = ? AND post_id = ?`, ctx.user.id, postId);
      q.run(`UPDATE posts SET ${countCol} = MAX(0, ${countCol} - 1) WHERE id = ?`, postId);
    }
    bumpHot(postId);
    const row = q.get('SELECT like_count, collect_count FROM posts WHERE id = ?', postId);
    return { like_count: row.like_count, collect_count: row.collect_count, active: on };
  });
}
POST('/api/posts/:id/like', async (ctx) => toggle('likes', 'like_count', ctx, true), { auth: true });
DEL('/api/posts/:id/like', async (ctx) => toggle('likes', 'like_count', ctx, false), { auth: true });
POST('/api/posts/:id/collect', async (ctx) => toggle('collects', 'collect_count', ctx, true), { auth: true });
DEL('/api/posts/:id/collect', async (ctx) => toggle('collects', 'collect_count', ctx, false), { auth: true });

POST('/api/posts/:id/share', async (ctx) => {
  const post = q.get("SELECT * FROM posts WHERE id = ? AND status = 'active'", Number(ctx.params.id));
  if (!post) throw notFound();
  q.run('UPDATE posts SET share_count = share_count + 1 WHERE id = ?', post.id);
  bumpHot(post.id);
  return {
    share_text: `「${post.content.slice(0, 50)}」—— 来句灵，让这句话活过来`,
    share_url: `/#/post/${post.id}`,
    share_count: post.share_count + 1
  };
}, { auth: true });

POST('/api/posts/:id/play', async (ctx) => {
  q.run("UPDATE posts SET play_count = play_count + 1 WHERE id = ? AND status = 'active'", Number(ctx.params.id));
  return { done: true };
}, { auth: true });

// ---- 评论 ----
function commentView(c, viewer) {
  const author = q.get('SELECT * FROM users WHERE id = ?', c.user_id);
  const replyTo = c.reply_to_user ? q.get('SELECT nickname FROM users WHERE id = ?', c.reply_to_user) : null;
  return {
    id: c.id, post_id: c.post_id, parent_id: c.parent_id,
    content: c.content, is_ai: !!c.is_ai, ai_label: c.is_ai ? 'AI 生成' : null,
    created_at: c.created_at, author: publicUser(author),
    reply_to: replyTo?.nickname || null,
    is_mine: viewer ? viewer.id === c.user_id : false
  };
}

GET('/api/posts/:id/comments', async (ctx) => {
  const postId = Number(ctx.params.id);
  const blocked = blockedIds(ctx.user);
  const rows = q.all("SELECT * FROM comments WHERE post_id = ? AND status = 'active' ORDER BY id ASC LIMIT 500", postId)
    .filter((c) => !blocked.has(c.user_id));
  const roots = [];
  const byId = new Map();
  for (const c of rows) {
    const v = { ...commentView(c, ctx.user), replies: [] };
    byId.set(c.id, v);
    if (c.parent_id && byId.has(c.parent_id)) byId.get(c.parent_id).replies.push(v);
    else roots.push(v);
  }
  return { items: roots };
});

POST('/api/posts/:id/comments', async (ctx) => {
  const postId = Number(ctx.params.id);
  const post = q.get("SELECT * FROM posts WHERE id = ? AND status = 'active'", postId);
  if (!post) throw notFound();
  if (!useQuota(ctx.user.id, 'comment', QUOTA.COMMENT_PER_DAY)) throw bad('今天评论有点多啦，休息一下～');
  const content = sanitizeText(ctx.body.content, 200);
  if (!content) throw bad('评论不能为空');
  const gate = gateContent(content);
  if (!gate.allowed || gate.status === 'pending') {
    logModeration('system', gate.allowed ? 'review' : 'block', 'comment_attempt', ctx.user.id, content.slice(0, 50));
    throw bad(gate.notice || '这条评论不太合适哦');
  }
  let parentId = ctx.body.parent_id ? Number(ctx.body.parent_id) : null;
  let replyTo = ctx.body.reply_to_user ? Number(ctx.body.reply_to_user) : null;
  if (parentId) {
    const parent = q.get("SELECT * FROM comments WHERE id = ? AND post_id = ? AND status='active'", parentId, postId);
    if (!parent) throw bad('回复的评论不存在');
    if (parent.parent_id) { replyTo = replyTo || parent.user_id; parentId = parent.parent_id; } // 楼中楼拍平到两层
  }
  const r = q.run(
    "INSERT INTO comments (post_id, user_id, parent_id, reply_to_user, content, status, created_at) VALUES (?,?,?,?,?,'active',?)",
    postId, ctx.user.id, parentId, replyTo, content, now()
  );
  q.run('UPDATE posts SET comment_count = comment_count + 1 WHERE id = ?', postId);
  bumpHot(postId);
  const c = q.get('SELECT * FROM comments WHERE id = ?', Number(r.lastInsertRowid));
  return { comment: { ...commentView(c, ctx.user), replies: [] } };
}, { auth: true });

DEL('/api/comments/:id', async (ctx) => {
  const c = q.get('SELECT * FROM comments WHERE id = ?', Number(ctx.params.id));
  if (!c || c.status !== 'active') throw notFound();
  const post = q.get('SELECT user_id FROM posts WHERE id = ?', c.post_id);
  const allowed = c.user_id === ctx.user.id || post?.user_id === ctx.user.id || ctx.user.role === 'admin';
  if (!allowed) throw denied();
  q.run("UPDATE comments SET status = 'removed' WHERE id = ?", c.id);
  q.run('UPDATE posts SET comment_count = MAX(0, comment_count - 1) WHERE id = ?', c.post_id);
  return { done: true };
}, { auth: true });

// ---- 举报 ----
GET('/api/report-reasons', async () => ({ reasons: REPORT_REASONS }));
POST('/api/reports', async (ctx) => {
  const { target_type, target_id, reason } = ctx.body;
  if (!['post', 'comment', 'user', 'room_message'].includes(target_type)) throw bad('举报类型无效');
  if (!target_id) throw bad('缺少举报对象');
  if (!REPORT_REASONS.includes(reason)) throw bad('请选择举报原因');
  const dup = q.get('SELECT id FROM reports WHERE reporter_id = ? AND target_type = ? AND target_id = ? AND status = ?',
    ctx.user.id, target_type, String(target_id), 'open');
  if (dup) return { done: true, message: '我们已收到你的举报，正在处理中' };
  q.run(
    'INSERT INTO reports (reporter_id, target_type, target_id, reason, detail, created_at) VALUES (?,?,?,?,?,?)',
    ctx.user.id, target_type, String(target_id), reason, sanitizeText(ctx.body.detail, 200), now()
  );
  return { done: true, message: '已收到举报，审核小队出动中。感谢你守护句灵 💜' };
}, { auth: true });

// ---- 今日话题 ----
GET('/api/ai/topic', async () => {
  const topic = await ensureTodayTopic();
  return { topic: { ...topic, ai_label: 'AI 生成话题' } };
});
