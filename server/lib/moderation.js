import { q, getSetting } from './db.js';
import { now, jparse } from './util.js';

// 敏感词缓存（30s 失效；后台增删词后很快生效）
let cache = null;
let cacheAt = 0;
function words() {
  if (!cache || now() - cacheAt > 30_000) {
    cache = q.all('SELECT word, category FROM sensitive_words');
    cacheAt = now();
  }
  return cache;
}
export function invalidateWordCache() { cache = null; }

export const CARE_MESSAGE =
  '我们注意到这段文字里可能藏着一些难过。你并不孤单——可以联系信任的朋友、家人，' +
  '或拨打全国心理援助热线 12356（24 小时）。句灵会一直在这里陪你。';

/**
 * 文本审核
 * @returns {{verdict:'ok'|'block'|'review'|'selfharm', hits:string[], message?:string}}
 * - block    直接拦截（赌博/色情/诈骗等硬违规）
 * - review   可发布但进入人工审核（status=pending，不进入公共流）
 * - selfharm 自伤风险：进入人工审核 + 返回关怀提示，绝不娱乐化
 */
export function moderate(text) {
  const t = String(text || '');
  const hits = { block: [], review: [], selfharm: [] };
  for (const { word, category } of words()) {
    if (word && t.includes(word)) hits[category]?.push(word);
  }
  if (hits.block.length) return { verdict: 'block', hits: hits.block };
  if (hits.selfharm.length) return { verdict: 'selfharm', hits: hits.selfharm, message: CARE_MESSAGE };
  if (hits.review.length) return { verdict: 'review', hits: hits.review };
  return { verdict: 'ok', hits: [] };
}

export function logModeration(actor, action, targetType, targetId, detail = '') {
  q.run(
    'INSERT INTO moderation_logs (actor, action, target_type, target_id, detail, created_at) VALUES (?,?,?,?,?,?)',
    String(actor), action, targetType, String(targetId), detail, now()
  );
}

/**
 * 发布类内容统一入口：返回内容应有的状态与给用户的提示
 */
/**
 * 大模型机审（异步，不阻塞发布）：敏感词过滤之上的第二道防线。
 * 后台开关 ai_moderation（默认关）；仅在配置了大模型时生效；
 * 每日预算封顶（复用 warmup 预算口径的 1 倍），失败静默放行（人审兜底）。
 */
export async function aiModeratePost(post) {
  if (!getSetting('ai_moderation', false)) return;
  const { llmEnabled, llmOrFallback } = await import('./llm.js');
  if (!llmEnabled()) return;
  try {
    const r = await llmOrFallback({
      feature: 'moderation', userId: post.user_id, tier: 'default',
      system: '你是中文社交平台的内容安全审核员。判断用户内容是否违规（色情低俗/赌博诈骗/暴力血腥/违法/引导私下交易/攻击辱骂/未成年人不适内容）。' +
        '只输出 JSON：{"verdict":"pass"|"review"|"block","reason":"15字内原因"}。情绪表达（难过/emo）不算违规；拿不准选 review。',
      prompt: `内容：「${String(post.content).slice(0, 300)}」`,
      json: true, maxTokens: 60, temperature: 0,
      budgetMicro: 2_000_000, budgetPrefix: 'moderation',
      fallbackFn: () => null
    });
    if (!r.byLLM) return;
    const v = jparse(r.text, null);
    if (!v || v.verdict === 'pass') return;
    const status = v.verdict === 'block' ? 'removed' : 'pending';
    q.run('UPDATE posts SET status = ?, remove_reason = ? WHERE id = ? AND status = ?', status, `AI 机审：${v.reason || ''}`, post.id, 'active');
    logModeration('ai', v.verdict === 'block' ? 'remove' : 'review', 'post', post.id, `AI机审 ${v.verdict}：${v.reason || ''}`);
    const { notify } = await import('./notify.js');
    notify(post.user_id, 'system', {
      postId: post.id,
      content: v.verdict === 'block' ? '你的内容经审核未通过，已被移除。如有疑问可申诉。' : '你的内容已进入人工复核，通过后将正常展示。'
    });
  } catch (e) {
    console.warn('[ai-moderation]', e.message);
  }
}

export function gateContent(text) {
  const r = moderate(text);
  if (r.verdict === 'block') {
    return { allowed: false, status: null, notice: '内容包含违规信息，发布失败。如有疑问可联系客服申诉。', hits: r.hits };
  }
  if (r.verdict === 'selfharm') {
    return { allowed: true, status: 'pending', notice: CARE_MESSAGE, hits: r.hits, care: true };
  }
  if (r.verdict === 'review') {
    return { allowed: true, status: 'pending', notice: '内容已提交，将在人工审核通过后展示给大家～', hits: r.hits };
  }
  return { allowed: true, status: 'active', notice: null, hits: [] };
}
