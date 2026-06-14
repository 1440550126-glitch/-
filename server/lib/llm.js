import { q } from './db.js';
import { now, dayCN, estimateTokens } from './util.js';

// ===== 提供商配置（OpenAI 兼容 Chat Completions；密钥只存在于服务端环境变量） =====
const PROVIDER = process.env.LLM_PROVIDER || 'none';
const BASE_URL = (process.env.LLM_BASE_URL || '').replace(/\/+$/, '');
const API_KEY = process.env.LLM_API_KEY || '';

const MODELS = {
  default: process.env.LLM_MODEL_DEFAULT || 'doubao-seed-1-6-flash',
  premium: process.env.LLM_MODEL_PREMIUM || 'doubao-seed-1-6'
};
// 单价：元/千token → 微元/token
const yuanPerK = (v, dft) => Math.round((Number(v) > 0 ? Number(v) : dft) * 1_000_000 / 1000);
const PRICES = {
  default: { in: yuanPerK(process.env.LLM_PRICE_DEFAULT_IN, 0.00015), out: yuanPerK(process.env.LLM_PRICE_DEFAULT_OUT, 0.0015) },
  premium: { in: yuanPerK(process.env.LLM_PRICE_PREMIUM_IN, 0.0008), out: yuanPerK(process.env.LLM_PRICE_PREMIUM_OUT, 0.008) }
};

export const llmEnabled = () => PROVIDER !== 'none' && !!BASE_URL && !!API_KEY;
export const llmProvider = () => PROVIDER;

export function logUsage({ userId = 0, feature, provider = 'local', model = 'rule-engine', promptTokens = 0, completionTokens = 0, ok = 1, fallback = 0, latency = 0, tier = 'default' }) {
  const price = PRICES[tier] || PRICES.default;
  const cost = provider === 'local' ? 0 : promptTokens * price.in + completionTokens * price.out;
  q.run(
    `INSERT INTO ai_usage_logs (user_id, feature, provider, model, prompt_tokens, completion_tokens, cost_micro, ok, fallback, latency_ms, created_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
    userId || 0, feature, provider, model, promptTokens, completionTokens, Math.round(cost), ok, fallback, latency, now()
  );
  return cost;
}

export function todayCostMicro(featurePrefix = '') {
  const start = new Date(dayCN() + 'T00:00:00+08:00').getTime();
  const row = featurePrefix
    ? q.get('SELECT COALESCE(SUM(cost_micro),0) c FROM ai_usage_logs WHERE created_at >= ? AND feature LIKE ?', start, featurePrefix + '%')
    : q.get('SELECT COALESCE(SUM(cost_micro),0) c FROM ai_usage_logs WHERE created_at >= ?', start);
  return row?.c || 0;
}

/**
 * 调用大模型（OpenAI 兼容）。失败/未配置时抛错，调用方必须有本地兜底。
 * @returns {Promise<{text:string, promptTokens:number, completionTokens:number}>}
 */
export async function chatLLM({ tier = 'default', system = '', prompt, json = false, maxTokens = 800, temperature = 0.8, timeoutMs = 12_000 }) {
  if (!llmEnabled()) throw new Error('llm-disabled');
  const model = MODELS[tier] || MODELS.default;
  const messages = [];
  if (system) messages.push({ role: 'system', content: system });
  messages.push({ role: 'user', content: prompt });

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(`${BASE_URL}/chat/completions`, {
      method: 'POST',
      signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${API_KEY}` },
      body: JSON.stringify({
        model, messages, max_tokens: maxTokens, temperature,
        ...(json ? { response_format: { type: 'json_object' } } : {})
      })
    });
    if (!resp.ok) throw new Error(`llm-http-${resp.status}`);
    const data = await resp.json();
    const text = data?.choices?.[0]?.message?.content || '';
    if (!text) throw new Error('llm-empty');
    return {
      text,
      model,
      promptTokens: data?.usage?.prompt_tokens ?? estimateTokens(system + prompt),
      completionTokens: data?.usage?.completion_tokens ?? estimateTokens(text)
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 带成本记录与兜底的便捷封装。
 * @param {Function} fallbackFn 本地兜底生成（必须提供，保证无 Key/断网也可用）
 */
export async function llmOrFallback({ feature, userId = 0, tier = 'default', system, prompt, json = false, maxTokens, temperature, fallbackFn, budgetMicro = 0, budgetPrefix = '' }) {
  if (llmEnabled() && (!budgetMicro || todayCostMicro(budgetPrefix || feature) < budgetMicro)) {
    const t0 = now();
    try {
      const r = await chatLLM({ tier, system, prompt, json, maxTokens, temperature });
      logUsage({ userId, feature, provider: PROVIDER, model: r.model, promptTokens: r.promptTokens, completionTokens: r.completionTokens, ok: 1, latency: now() - t0, tier });
      return { text: r.text, byLLM: true };
    } catch (e) {
      logUsage({ userId, feature, provider: PROVIDER, model: MODELS[tier], ok: 0, fallback: 1, latency: now() - t0, tier });
      console.warn('[llm] fallback:', feature, e.message);
    }
  } else {
    logUsage({ userId, feature, provider: 'local', fallback: llmEnabled() ? 1 : 0 });
  }
  return { text: null, byLLM: false, fallback: fallbackFn ? fallbackFn() : null };
}

// ===== 每日配额（按东八区自然日） =====
export function quotaUsed(userId, kind) {
  return q.get('SELECT used FROM quota_usage WHERE user_id = ? AND day = ? AND kind = ?', userId, dayCN(), kind)?.used || 0;
}
/** 尝试占用一次配额；超限返回 false */
export function useQuota(userId, kind, limit) {
  if (quotaUsed(userId, kind) >= limit) return false;
  q.run(
    `INSERT INTO quota_usage (user_id, day, kind, used) VALUES (?,?,?,1)
     ON CONFLICT(user_id, day, kind) DO UPDATE SET used = used + 1`,
    userId, dayCN(), kind
  );
  return true;
}
