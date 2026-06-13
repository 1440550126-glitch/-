// AI 治愈陪聊：1 对 1 倾听陪伴（句灵）。所有回复均标识 AI 生成；自伤风险走确定性关怀响应。
import { GET, POST, bad } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { now, sanitizeText } from '../lib/util.js';
import { moderate, logModeration } from '../lib/moderation.js';
import { useQuota, quotaUsed } from '../lib/llm.js';
import { QUOTA } from '../lib/catalog.js';
import { companionReply, localReply, CARE_REPLY, COMPANION_GREETING, HOTLINE } from '../lib/companion.js';

const DISCLAIMER =
  '句灵是 AI 陪伴，会用心倾听，但不能替代专业心理咨询。如果你正处于危机中，请联系信任的人，或拨打' + HOTLINE + '。';

function save(userId, role, content, care = 0) {
  const ts = now();
  const r = q.run(
    'INSERT INTO ai_chat_messages (user_id, role, content, care, created_at) VALUES (?,?,?,?,?)',
    userId, role, content, care ? 1 : 0, ts
  );
  return { id: Number(r.lastInsertRowid), role, content, care: !!care, created_at: ts };
}

// 历史 + 开场白 + 合规提示 + 今日剩余次数
GET('/api/ai/chat', async (ctx) => {
  const rows = q.all(
    'SELECT id, role, content, care, created_at FROM ai_chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 50',
    ctx.user.id
  ).reverse();
  const left = Math.max(0, QUOTA.AI_CHAT_PER_DAY - quotaUsed(ctx.user.id, 'ai_chat'));
  return {
    messages: rows.map((m) => ({ ...m, care: !!m.care })),
    greeting: COMPANION_GREETING,
    disclaimer: DISCLAIMER,
    hotline: HOTLINE,
    quota_left: left,
    ai_label: 'AI 生成'
  };
}, { auth: true });

// 发一句话 → 句灵回应
POST('/api/ai/chat', async (ctx) => {
  const content = sanitizeText(ctx.body.content, 500);
  if (!content || content.length < 1) throw bad('说点什么吧，我在听');
  if (!useQuota(ctx.user.id, 'ai_chat', QUOTA.AI_CHAT_PER_DAY)) {
    throw bad('今天聊了好多啦，让我们都歇一歇，明天再继续好吗？');
  }

  const mod = moderate(content);
  if (mod.verdict === 'block') {
    // 硬违规不入库，温和拒绝（不退还本次配额，避免被当作绕过手段）
    throw bad('这个话题我没办法陪你聊呢，换个想说的吧～');
  }

  const care = mod.verdict === 'selfharm';
  const userMsg = save(ctx.user.id, 'user', content, care);

  let reply, byLLM = false;
  if (care) {
    // 自伤关怀：确定性响应 + 记审核日志（人工跟进），绝不交给模型
    logModeration('system', 'review', 'ai_chat', ctx.user.id, '自伤关怀: ' + mod.hits.join(','));
    reply = CARE_REPLY;
  } else {
    // 取最近的非关怀历史作为上下文（不含刚存入的这条）
    const hist = q.all(
      'SELECT role, content FROM ai_chat_messages WHERE user_id = ? AND care = 0 ORDER BY id DESC LIMIT 9',
      ctx.user.id
    ).reverse().slice(0, -1);
    const res = await companionReply({ userId: ctx.user.id, content, history: hist });
    reply = res.reply; byLLM = res.byLLM;
  }
  if (!reply) reply = localReply(content);   // 双保险，绝不空回复
  const aiMsg = save(ctx.user.id, 'assistant', reply, care);

  return {
    user_message: userMsg,
    reply: aiMsg,
    by_llm: byLLM,
    care,
    ai_label: 'AI 生成',
    ...(care ? { hotline: HOTLINE } : {})
  };
}, { auth: true });

// 清空对话（重新开始）
POST('/api/ai/chat/clear', async (ctx) => {
  q.run('DELETE FROM ai_chat_messages WHERE user_id = ?', ctx.user.id);
  return { done: true };
}, { auth: true });
