// ============================================================
// 句灵 · 个性化推荐「越来越懂你」
// ------------------------------------------------------------
// 思路（内容召回 + 行为画像，透明可解释，MVP 规模无需 ML 基建）：
//   1. buildTasteProfile：从点赞/收藏/评论/关注构建兴趣画像（情绪/作者/话题，
//      按交互强度加权 + 时间衰减；收藏>评论>点赞），并纳入「不感兴趣」负反馈。
//   2. scoreAndRank（纯函数，可单测）：亲和度 × 个性化强度 + 质量 + 新鲜 + 探索，
//      再做多样性贪心去重；个性化强度随互动增长 → 越用越懂你。
//   3. 冷启动（新用户无画像）：自动回退到「质量 + 新鲜」，保证「引新」体验不塌。
//   4. 每条给出可解释的 rec_reason，让「懂你」被用户感知到，建立信任。
// ============================================================
import { clamp, jparse, seededRand } from './util.js';

const W = { collect: 3.0, comment: 2.5, like: 2.0, follow: 4.0 };

// 时间衰减：近 3 周内权重高，越久越弱（软衰减，不归零）
const recency = (ageMs) => 1 / (1 + Math.max(0, ageMs) / (21 * 86400_000));

// 帖子质量（与 feed 热度口径一致），饱和到 0..1
function qualityNorm(p) {
  const hot = 3 * p.like_count + 4 * p.comment_count + 3 * p.collect_count + 2 * p.share_count + 0.2 * p.play_count;
  return hot / (hot + 12);
}

/**
 * 构建用户兴趣画像（读库）。signal 越多，个性化越强。
 * @returns {{emotions:Object, authors:Object, topics:Object, total:number,
 *            dismissedPosts:Set<number>, dismissedAuthors:Map<number,number>}}
 */
export async function buildTasteProfile(userId, nowTs = Date.now()) {
  const { q } = await import('./db.js');   // 动态导入：scoreAndRank 可脱离数据库单测
  const emotions = new Map(), authors = new Map(), topics = new Map();
  let total = 0;
  const add = (map, key, w) => { if (key == null || key === '') return; map.set(key, (map.get(key) || 0) + w); };

  const ingest = (rows, w) => {
    for (const r of rows) {
      const post = q.get('SELECT user_id, card, topic_id FROM posts WHERE id = ?', r.post_id);
      if (!post) continue;
      const ww = w * recency(nowTs - r.created_at);
      add(emotions, jparse(post.card, {}).emotion, ww);
      add(authors, post.user_id, ww);
      add(topics, post.topic_id, ww);
      total += ww;
    }
  };
  ingest(q.all('SELECT post_id, created_at FROM collects WHERE user_id = ? ORDER BY created_at DESC LIMIT 200', userId), W.collect);
  ingest(q.all('SELECT post_id, created_at FROM likes WHERE user_id = ? ORDER BY created_at DESC LIMIT 300', userId), W.like);
  ingest(q.all("SELECT post_id, MAX(created_at) created_at FROM comments WHERE user_id = ? AND status='active' GROUP BY post_id ORDER BY created_at DESC LIMIT 200", userId), W.comment);

  // 关注 = 强作者亲和
  for (const f of q.all('SELECT followee_id, created_at FROM follows WHERE follower_id = ? LIMIT 300', userId)) {
    const ww = W.follow * recency(nowTs - f.created_at);
    add(authors, f.followee_id, ww); total += ww;
  }

  // 负反馈：不感兴趣 → 排除该帖 + 记下作者用于降权
  const dismissedPosts = new Set();
  const dismissedAuthors = new Map();
  for (const d of q.all("SELECT post_id FROM post_feedback WHERE user_id = ? AND kind = 'dismiss' ORDER BY created_at DESC LIMIT 300", userId)) {
    dismissedPosts.add(d.post_id);
    const post = q.get('SELECT user_id FROM posts WHERE id = ?', d.post_id);
    if (post) dismissedAuthors.set(post.user_id, (dismissedAuthors.get(post.user_id) || 0) + 1);
  }

  const norm = (map) => {
    let s = 0; for (const v of map.values()) s += v;
    const o = {}; if (s > 0) for (const [k, v] of map) o[k] = v / s;
    return o;
  };
  return { emotions: norm(emotions), authors: norm(authors), topics: norm(topics), total, dismissedPosts, dismissedAuthors };
}

/**
 * 纯函数：对候选帖个性化打分 + 多样性重排。不读库，便于单测。
 * @param pool 候选帖行数组（含 card/计数/created_at 等字段）
 */
export function scoreAndRank(pool, profile, opts = {}) {
  const {
    viewerId = 0, seen = new Set(), daySeed = 0, nowTs = Date.now(), hideOwn = true
  } = opts;
  const emptyProfile = { emotions: {}, authors: {}, topics: {}, total: 0, dismissedPosts: new Set(), dismissedAuthors: new Map() };
  const prof = profile || emptyProfile;
  // 个性化强度：随累计互动增长（越用越懂你），冷启动 ≈ 0 → 走热度
  const s = clamp(prof.total / (prof.total + 8), 0, 0.82);

  const scored = [];
  for (const p of pool) {
    if (prof.dismissedPosts?.has?.(p.id)) continue;          // 不感兴趣：直接剔除
    const emo = jparse(p.card, {}).emotion || '';
    const emoA = prof.emotions[emo] || 0;
    const authA = prof.authors[p.user_id] || 0;
    const topA = p.topic_id ? (prof.topics[p.topic_id] || 0) : 0;
    const affinity = 0.5 * emoA + 0.35 * authA + 0.15 * topA;          // 0..~1

    const fresh = recency((nowTs - p.created_at) * 8);                  // 以小时计更敏感
    const popularity = 0.6 * qualityNorm(p) + 0.4 * fresh;
    const explore = seededRand(p.id + daySeed)() * 0.10;               // 当日内稳定的探索扰动

    let score = s * affinity + (1 - s) * popularity + 0.08 * fresh + explore;
    if (hideOwn && p.user_id === viewerId) score -= 1;                  // 不给用户推自己的帖
    if (seen.has(p.id)) score -= 0.35;                                  // 已赞/已藏 → 降权
    if (prof.dismissedAuthors?.get?.(p.user_id)) score -= 0.25;         // 反感作者 → 降权

    scored.push({ post: p, emo, score, parts: { emoA, authA, topA, fresh, popularity, s } });
  }
  scored.sort((a, b) => b.score - a.score);

  // 多样性贪心：避免同作者/同情绪扎堆
  const out = [];
  const authorCnt = new Map(), emoCnt = new Map();
  const rest = scored;
  while (rest.length) {
    let bi = 0, best = -Infinity;
    for (let i = 0; i < rest.length; i++) {
      const it = rest[i];
      const adj = it.score - (authorCnt.get(it.post.user_id) || 0) * 0.15 - (emoCnt.get(it.emo) || 0) * 0.06;
      if (adj > best) { best = adj; bi = i; }
    }
    const [c] = rest.splice(bi, 1);
    authorCnt.set(c.post.user_id, (authorCnt.get(c.post.user_id) || 0) + 1);
    emoCnt.set(c.emo, (emoCnt.get(c.emo) || 0) + 1);
    out.push({ post: c.post, reason: reasonFor(c.parts, c.emo) });
  }
  return out;
}

// 可解释推荐理由（个性化命中优先，冷启动落到热度/新鲜）
function reasonFor(parts, emo) {
  const { emoA, authA, topA, fresh, popularity, s } = parts;
  if (s > 0.12) {
    if (authA > 0 && authA >= emoA && authA >= topA) return '你常看的人更新了';
    if (emoA > 0 && emoA >= topA) return `你常被「${emo || '这种情绪'}」打动`;
    if (topA > 0) return '你感兴趣的话题';
  }
  if (fresh > 0.55) return '新鲜出炉';
  if (popularity > 0.5) return '正在被热聊';
  return '大家都在看';
}
