import { GET, POST, bad, notFound, denied } from '../lib/httpx.js';
import { q, tx } from '../lib/db.js';
import { jparse, now } from '../lib/util.js';
import { isMember } from '../lib/auth.js';
import { buildCard, buildManifest, buildManifestEnhanced, ANIM_STYLES } from '../lib/manifest.js';
import { useQuota, quotaUsed, logUsage } from '../lib/llm.js';
import { QUOTA } from '../lib/catalog.js';

// 发布前实时预览卡（纯本地规则，零成本）
POST('/api/ai/preview', async (ctx) => {
  const content = String(ctx.body.content || '').slice(0, 300);
  if (!content.trim()) throw bad('先写点什么');
  return { card: buildCard(content, String(ctx.user.id)) };
}, { auth: true });

// 可用动画风格 + 我的额度状态
GET('/api/ai/styles', async (ctx) => {
  const member = isMember(ctx.user);
  const used = quotaUsed(ctx.user.id, 'anim');
  const limit = member ? QUOTA.MEMBER_ANIM_PER_DAY : QUOTA.FREE_ANIM_PER_DAY;
  return {
    styles: ANIM_STYLES.map((s) => ({
      ...s,
      credit_cost: s.tier === 'premium' ? (member ? QUOTA.MEMBER_PREMIUM_COST : QUOTA.PREMIUM_CREDIT_COST) : 0,
      available: s.tier === 'free' || (s.tier === 'member' && member) || s.tier === 'premium'
    })),
    quota: { used, limit, left: Math.max(0, limit - used) },
    member,
    credits: ctx.user.credits
  };
}, { auth: true });

/**
 * 生成"文字变动画" Manifest —— 核心卖点
 * 免费用户：清墨风格 每日 3 次体验
 * 会员：全部基础风格 每日 100 次（防刷上限）
 * 高级风格：消耗高级额度（会员 8 折），由高级模型担任导演
 */
POST('/api/posts/:id/manifest', async (ctx) => {
  const post = q.get("SELECT * FROM posts WHERE id = ? AND status = 'active'", Number(ctx.params.id));
  if (!post) throw notFound();
  const styleId = String(ctx.body.style || 'ink');
  const style = ANIM_STYLES.find((s) => s.id === styleId);
  if (!style) throw bad('动画风格不存在');

  const member = isMember(ctx.user);
  const user = ctx.user;

  if (style.tier === 'member' && !member) {
    throw denied('这是会员专属风格，开通 9.9 元/月会员即可解锁全部基础风格～', { need_member: true });
  }

  if (style.tier === 'premium') {
    const cost = member ? QUOTA.MEMBER_PREMIUM_COST : QUOTA.PREMIUM_CREDIT_COST;
    if (user.credits < cost) {
      throw denied(`高级风格需要 ${cost} 点星尘额度（当前 ${user.credits} 点）`, { need_credits: true, cost, balance: user.credits });
    }
    const manifest = await buildManifestEnhanced(post.content, { style: styleId, userId: user.id, premium: true });
    tx(() => {
      q.run('UPDATE users SET credits = credits - ? WHERE id = ?', cost, user.id);
      q.run('INSERT INTO credit_logs (user_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)',
        user.id, -cost, `高级动画风格 · ${style.name}`, `post:${post.id}`, now());
    });
    const balance = q.get('SELECT credits FROM users WHERE id = ?', user.id).credits;
    return { manifest, charged: cost, credits: balance };
  }

  // 免费 / 会员基础风格：每日配额
  const limit = member ? QUOTA.MEMBER_ANIM_PER_DAY : QUOTA.FREE_ANIM_PER_DAY;
  if (!useQuota(user.id, 'anim', limit)) {
    throw denied(
      member ? '今日动画次数已达上限，明天再来～' : `每天可免费体验 ${QUOTA.FREE_ANIM_PER_DAY} 次文字变动画，开通会员解锁更多次数和风格～`,
      { need_member: !member, quota_exceeded: true }
    );
  }

  // 默认清墨风格缓存到帖子上；会员风格用规则引擎+可选 LLM 增强
  let manifest;
  if (styleId === 'ink' && post.manifest) {
    manifest = jparse(post.manifest, null);
  }
  if (!manifest) {
    manifest = member
      ? await buildManifestEnhanced(post.content, { style: styleId, userId: user.id, premium: false })
      : buildManifest(post.content, { style: styleId });
    if (!member) logUsage({ userId: user.id, feature: 'manifest', provider: 'local' });
    if (styleId === 'ink') q.run('UPDATE posts SET manifest = ? WHERE id = ?', JSON.stringify(manifest), post.id);
  }
  const left = Math.max(0, limit - quotaUsed(user.id, 'anim'));
  return { manifest, quota_left: left, member };
}, { auth: true });
