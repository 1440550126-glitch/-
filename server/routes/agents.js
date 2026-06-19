// 灵阵 · AI 团队：REST + SSE 路由
import { GET, POST, PUT, PATCH, DEL, bad, notFound, denied, openSSE } from '../lib/httpx.js';
import { q, getSetting, setSetting } from '../lib/db.js';
import { now, jparse, sanitizeText, clamp, dayCN, uid } from '../lib/util.js';
import { isMember } from '../lib/auth.js';
import { subscribe } from '../lib/hub.js';
import { toolList, getTool } from '../agents/tools.js';
import { searchKnowledge, addDoc } from '../agents/knowledge.js';
import { STRATEGIES, STRATEGY_LIST, AGENT_QUOTA } from '../agents/catalog.js';
import { startTeamRun, runTeamSync, stopRun, resolveTask, startBatch } from '../agents/engine.js';
import { computeNext, fireTrigger, MIN_INTERVAL_MIN, MAX_TRIGGERS } from '../agents/scheduler.js';
import { assertSafeHop } from '../agents/safefetch.js';
import { useQuota, quotaUsed, todayCostMicro, resolveLLM, invalidateUserLLM, chatLLM, userHasLLM } from '../lib/llm.js';
import { LLM_PROVIDERS, findProvider } from '../lib/llm-providers.js';
import { seal } from '../lib/secretbox.js';

// ---------- 访问控制小工具 ----------
const agentRow = (id) => q.get('SELECT * FROM agents WHERE id = ?', Number(id));
const teamRow = (id) => q.get('SELECT * FROM teams WHERE id = ?', Number(id));
const kbRow = (id) => q.get('SELECT * FROM knowledge_bases WHERE id = ?', Number(id));
const canUse = (row, uid) => row && (row.owner_id === uid || row.is_template || row.published);
const canEdit = (row, uid) => row && row.owner_id === uid && !row.is_template;

const viewAgent = (a, uid) => a && ({
  id: a.id, name: a.name, avatar: a.avatar, role: a.role, persona: a.persona,
  tier: a.tier, tools: jparse(a.tools, []), temperature: a.temperature,
  is_template: !!a.is_template, mine: a.owner_id === uid, updated_at: a.updated_at
});
const memberPreview = (ids) => (jparse(ids, []) || []).map((id) => {
  const a = agentRow(id); return a ? { id: a.id, name: a.name, avatar: a.avatar, role: a.role } : null;
}).filter(Boolean);
const kbPreview = (ids) => (jparse(ids, []) || []).map((id) => {
  const k = kbRow(id); return k ? { id: k.id, name: k.name, chunk_count: k.chunk_count } : null;
}).filter(Boolean);
const viewTeam = (t, uid) => t && ({
  id: t.id, name: t.name, avatar: t.avatar, goal: t.goal, strategy: t.strategy,
  manager_note: t.manager_note, max_rounds: t.max_rounds, run_count: t.run_count,
  is_template: !!t.is_template, published: !!t.published, has_api: !!t.api_key, has_webhook: !!t.webhook_url, mine: t.owner_id === uid, updated_at: t.updated_at,
  members: memberPreview(t.member_ids), knowledge: kbPreview(t.knowledge_ids),
  knowledge_ids: jparse(t.knowledge_ids, [])
});

const sanitizeTools = (arr) => [...new Set((Array.isArray(arr) ? arr : []).map(String))].filter(getTool);
const sanitizeEmoji = (s, dft) => sanitizeText(s, 8) || dft;

// ============================================================
// 元信息：工具清单 / 策略 / 我的额度
// ============================================================
GET('/api/agents/meta', async (ctx) => {
  const member = isMember(ctx.user);
  const byok = userHasLLM(ctx.user.id);
  const limit = dailyRunLimit(ctx.user);
  const used = quotaUsed(ctx.user.id, 'agent_run');
  return {
    tools: toolList(),
    strategies: STRATEGY_LIST,
    quota: { used, limit, left: Math.max(0, limit - used) },
    limits: { max_members: AGENT_QUOTA.MAX_MEMBERS, max_rounds: AGENT_QUOTA.MAX_TOOL_ROUNDS },
    member, byok
  };
}, { auth: true });

// 个人用量看板（注册在 /api/agents/:id 之前）
GET('/api/agents/usage', async (ctx) => {
  const start = new Date(dayCN() + 'T00:00:00+08:00').getTime();
  const uidv = ctx.user.id;
  const runs = q.get(
    `SELECT COUNT(*) total,
       COALESCE(SUM(CASE WHEN status='done'   THEN 1 ELSE 0 END),0) done,
       COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),0) failed,
       COALESCE(SUM(CASE WHEN started_at >= ? THEN 1 ELSE 0 END),0) today
     FROM agent_runs WHERE user_id = ?`, start, uidv
  );
  const member = isMember(ctx.user);
  const byok = userHasLLM(uidv);
  return {
    member, byok, runs,
    quota: {
      run: { used: quotaUsed(uidv, 'agent_run'), limit: dailyRunLimit(ctx.user) },
      api: { used: quotaUsed(uidv, 'agent_api'), limit: 50 }
    },
    cost: {
      today_micro: q.get("SELECT COALESCE(SUM(cost_micro),0) c FROM ai_usage_logs WHERE user_id = ? AND feature LIKE 'agent_%' AND created_at >= ?", uidv, start).c,
      total_micro: q.get("SELECT COALESCE(SUM(cost_micro),0) c FROM ai_usage_logs WHERE user_id = ? AND feature LIKE 'agent_%'", uidv).c
    },
    assets: {
      teams: q.get('SELECT COUNT(*) c FROM teams WHERE owner_id = ?', uidv).c,
      agents: q.get('SELECT COUNT(*) c FROM agents WHERE owner_id = ?', uidv).c,
      kbs: q.get('SELECT COUNT(*) c FROM knowledge_bases WHERE owner_id = ?', uidv).c
    }
  };
}, { auth: true });

// 每日运行上限：非会员=体验额度；会员自带 Key(BYOK)=不限量；会员用平台 Key=80
const UNLIMITED = 1_000_000;
function dailyRunLimit(user) {
  if (!isMember(user)) return AGENT_QUOTA.FREE_RUNS_PER_DAY;
  return userHasLLM(user.id) ? UNLIMITED : AGENT_QUOTA.MEMBER_RUNS_PER_DAY;
}

// ============================================================
// 自带大模型 Key（BYOK）：推荐清单 + 个人配置 + 连通性测试
// ============================================================
GET('/api/me/llm', async (ctx) => {
  const row = q.get('SELECT provider, base_url, model_default, model_premium, updated_at FROM user_llm WHERE user_id = ?', ctx.user.id);
  return { providers: LLM_PROVIDERS, config: row ? { ...row, has_key: true } : null };
}, { auth: true });

PUT('/api/me/llm', async (ctx) => {
  const b = ctx.body || {};
  const provider = findProvider(b.provider) ? b.provider : 'custom';
  const base_url = sanitizeText(b.base_url, 200);
  const existing = q.get('SELECT api_key FROM user_llm WHERE user_id = ?', ctx.user.id);
  const rawKey = sanitizeText(b.api_key, 256);
  const api_key = rawKey ? seal(rawKey) : (existing?.api_key || '');   // 新 Key 加密落库；不重填则沿用旧的（已加密）
  const model_default = sanitizeText(b.model_default, 80);
  const model_premium = sanitizeText(b.model_premium, 80) || model_default;
  if (!/^https?:\/\/.+/.test(base_url)) throw bad('请填写有效的接口地址（base_url，需以 http(s):// 开头）');
  if (!api_key) throw bad('请填写 API Key');
  if (!model_default) throw bad('请填写默认模型名');
  q.run(
    `INSERT INTO user_llm (user_id, provider, base_url, api_key, model_default, model_premium, updated_at)
     VALUES (?,?,?,?,?,?,?)
     ON CONFLICT(user_id) DO UPDATE SET provider=excluded.provider, base_url=excluded.base_url, api_key=excluded.api_key,
       model_default=excluded.model_default, model_premium=excluded.model_premium, updated_at=excluded.updated_at`,
    ctx.user.id, provider, base_url.replace(/\/+$/, ''), api_key, model_default, model_premium, now()
  );
  invalidateUserLLM(ctx.user.id);
  return { saved: true, provider, has_key: true };
}, { auth: true });

DEL('/api/me/llm', async (ctx) => {
  q.run('DELETE FROM user_llm WHERE user_id = ?', ctx.user.id);
  invalidateUserLLM(ctx.user.id);
  return { deleted: true };
}, { auth: true });

POST('/api/me/llm/test', async (ctx) => {
  const cfg = resolveLLM(ctx.user.id);
  if (!cfg.byok) throw bad('请先保存你的模型 Key 再测试');
  try {
    const r = await chatLLM({ tier: 'default', system: '只回复一个字。', prompt: '请回复：好', maxTokens: 8, temperature: 0, cfg, timeoutMs: 15000 });
    return { ok: true, model: r.model, sample: (r.text || '').trim().slice(0, 40) };
  } catch (e) {
    const m = String(e.message || e);
    throw bad('连接失败：' + (m.includes('llm-http-401') ? 'Key 无效(401)，确认是 API Key 而非 AccessKey' : m.includes('llm-http-404') ? '模型名不对(404)，核对控制台模型 ID' : m.includes('llm-http-429') ? '限流/余额不足(429)' : m.replace('llm-http-', 'HTTP ')));
  }
}, { auth: true });

// ============================================================
// 智能体（成员）CRUD
// ============================================================
GET('/api/agents', async (ctx) => ({
  mine: q.all('SELECT * FROM agents WHERE owner_id = ? ORDER BY updated_at DESC', ctx.user.id).map((a) => viewAgent(a, ctx.user.id)),
  templates: q.all('SELECT * FROM agents WHERE is_template = 1 AND owner_id = 0 ORDER BY id').map((a) => viewAgent(a, ctx.user.id))
}), { auth: true });

GET('/api/agents/:id', async (ctx) => {
  const a = agentRow(ctx.params.id);
  if (!canUse(a, ctx.user.id)) throw notFound();
  return { agent: viewAgent(a, ctx.user.id) };
}, { auth: true });

POST('/api/agents', async (ctx) => {
  const b = ctx.body || {};
  const name = sanitizeText(b.name, 24);
  if (!name) throw bad('给这个智能体起个名字');
  const ts = now();
  const r = q.run(
    `INSERT INTO agents (owner_id, name, avatar, role, persona, tier, tools, temperature, is_template, enabled, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,0,1,?,?)`,
    ctx.user.id, name, sanitizeEmoji(b.avatar, '🤖'), sanitizeText(b.role, 60), sanitizeText(b.persona, 1200),
    b.tier === 'premium' ? 'premium' : 'default', JSON.stringify(sanitizeTools(b.tools)),
    clamp(b.temperature ?? 0.7, 0, 1.5), ts, ts
  );
  return { agent: viewAgent(agentRow(Number(r.lastInsertRowid)), ctx.user.id) };
}, { auth: true });

PATCH('/api/agents/:id', async (ctx) => {
  const a = agentRow(ctx.params.id);
  if (!a) throw notFound();
  if (!canEdit(a, ctx.user.id)) throw denied('内置模板不可编辑，可「复制为我的」后再改');
  const b = ctx.body || {};
  q.run(
    `UPDATE agents SET name = ?, avatar = ?, role = ?, persona = ?, tier = ?, tools = ?, temperature = ?, updated_at = ? WHERE id = ?`,
    sanitizeText(b.name, 24) || a.name, sanitizeEmoji(b.avatar, a.avatar), sanitizeText(b.role, 60),
    sanitizeText(b.persona, 1200), b.tier === 'premium' ? 'premium' : 'default',
    JSON.stringify(b.tools !== undefined ? sanitizeTools(b.tools) : jparse(a.tools, [])),
    clamp(b.temperature ?? a.temperature, 0, 1.5), now(), a.id
  );
  return { agent: viewAgent(agentRow(a.id), ctx.user.id) };
}, { auth: true });

POST('/api/agents/:id/clone', async (ctx) => {
  const a = agentRow(ctx.params.id);
  if (!canUse(a, ctx.user.id)) throw notFound();
  const ts = now();
  const r = q.run(
    `INSERT INTO agents (owner_id, name, avatar, role, persona, tier, tools, temperature, is_template, enabled, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,0,1,?,?)`,
    ctx.user.id, (a.name + ' 副本').slice(0, 24), a.avatar, a.role, a.persona, a.tier, a.tools, a.temperature, ts, ts
  );
  return { agent: viewAgent(agentRow(Number(r.lastInsertRowid)), ctx.user.id) };
}, { auth: true });

DEL('/api/agents/:id', async (ctx) => {
  const a = agentRow(ctx.params.id);
  if (!a) throw notFound();
  if (!canEdit(a, ctx.user.id)) throw denied('不能删除内置模板');
  q.run('DELETE FROM agents WHERE id = ?', a.id);
  return { deleted: true };
}, { auth: true });

// ============================================================
// 团队 CRUD
// ============================================================
GET('/api/teams', async (ctx) => ({
  mine: q.all('SELECT * FROM teams WHERE owner_id = ? ORDER BY updated_at DESC', ctx.user.id).map((t) => viewTeam(t, ctx.user.id)),
  templates: q.all('SELECT * FROM teams WHERE is_template = 1 AND owner_id = 0 ORDER BY id').map((t) => viewTeam(t, ctx.user.id))
}), { auth: true });

// 团队广场：他人发布的团队（注意必须注册在 /api/teams/:id 之前）
GET('/api/teams/gallery', async (ctx) => ({
  items: q.all(
    `SELECT t.*, u.nickname owner_name FROM teams t LEFT JOIN users u ON u.id = t.owner_id
     WHERE t.published = 1 AND t.owner_id != 0 ORDER BY t.run_count DESC, t.updated_at DESC LIMIT 30`
  ).map((t) => ({ ...viewTeam(t, ctx.user.id), owner_name: t.owner_name || '匿名创作者' }))
}), { auth: true });

GET('/api/teams/:id', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!canUse(t, ctx.user.id)) throw notFound();
  const members = (jparse(t.member_ids, []) || []).map((id) => viewAgent(agentRow(id), ctx.user.id)).filter(Boolean);
  const team = viewTeam(t, ctx.user.id);
  if (t.owner_id === ctx.user.id) team.webhook_url = t.webhook_url || '';
  return { team, members };
}, { auth: true });

function validateMembers(ids, uid) {
  const out = [];
  for (const id of (Array.isArray(ids) ? ids : [])) {
    const a = agentRow(id);
    if (canUse(a, uid) && !out.includes(a.id)) out.push(a.id);
  }
  if (out.length > AGENT_QUOTA.MAX_MEMBERS) throw bad(`一个团队最多 ${AGENT_QUOTA.MAX_MEMBERS} 名成员`);
  return out;
}
function validateKbs(ids, uid) {
  return (Array.isArray(ids) ? ids : []).map(Number).filter((id) => canUse(kbRow(id), uid));
}

POST('/api/teams', async (ctx) => {
  const b = ctx.body || {};
  const name = sanitizeText(b.name, 24);
  if (!name) throw bad('给团队起个名字');
  const strategy = STRATEGIES[b.strategy] ? b.strategy : 'orchestrate';
  const members = validateMembers(b.member_ids, ctx.user.id);
  const ts = now();
  const r = q.run(
    `INSERT INTO teams (owner_id, name, avatar, goal, strategy, manager_note, member_ids, knowledge_ids, max_rounds, is_template, published, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,?,0,0,?,?)`,
    ctx.user.id, name, sanitizeEmoji(b.avatar, '🛰'), sanitizeText(b.goal, 300), strategy, sanitizeText(b.manager_note, 400),
    JSON.stringify(members), JSON.stringify(validateKbs(b.knowledge_ids, ctx.user.id)),
    clamp(b.max_rounds ?? 3, 1, AGENT_QUOTA.MAX_TOOL_ROUNDS), ts, ts
  );
  return { team: viewTeam(teamRow(Number(r.lastInsertRowid)), ctx.user.id) };
}, { auth: true });

PATCH('/api/teams/:id', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('内置模板不可编辑，可「用此模板」复制后再改');
  const b = ctx.body || {};
  q.run(
    `UPDATE teams SET name = ?, avatar = ?, goal = ?, strategy = ?, manager_note = ?, member_ids = ?, knowledge_ids = ?, max_rounds = ?, updated_at = ? WHERE id = ?`,
    sanitizeText(b.name, 24) || t.name, sanitizeEmoji(b.avatar, t.avatar), sanitizeText(b.goal, 300),
    STRATEGIES[b.strategy] ? b.strategy : t.strategy, sanitizeText(b.manager_note, 400),
    JSON.stringify(b.member_ids !== undefined ? validateMembers(b.member_ids, ctx.user.id) : jparse(t.member_ids, [])),
    JSON.stringify(b.knowledge_ids !== undefined ? validateKbs(b.knowledge_ids, ctx.user.id) : jparse(t.knowledge_ids, [])),
    clamp(b.max_rounds ?? t.max_rounds, 1, AGENT_QUOTA.MAX_TOOL_ROUNDS), now(), t.id
  );
  return { team: viewTeam(teamRow(t.id), ctx.user.id) };
}, { auth: true });

POST('/api/teams/:id/clone', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!canUse(t, ctx.user.id)) throw notFound();
  const ts = now();
  const r = q.run(
    `INSERT INTO teams (owner_id, name, avatar, goal, strategy, manager_note, member_ids, knowledge_ids, max_rounds, is_template, published, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,?,0,0,?,?)`,
    ctx.user.id, (t.name + (t.is_template ? '' : ' 副本')).slice(0, 24), t.avatar, t.goal, t.strategy, t.manager_note,
    t.member_ids, t.knowledge_ids, t.max_rounds, ts, ts
  );
  return { team: viewTeam(teamRow(Number(r.lastInsertRowid)), ctx.user.id) };
}, { auth: true });

DEL('/api/teams/:id', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('不能删除内置模板');
  q.run('DELETE FROM teams WHERE id = ?', t.id);
  return { deleted: true };
}, { auth: true });

// 发布 / 取消发布到团队广场
POST('/api/teams/:id/publish', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('只能发布自己的团队');
  const pub = ctx.body?.published ? 1 : 0;
  if (pub && !(jparse(t.member_ids, []) || []).length) throw bad('空团队不能发布');
  q.run('UPDATE teams SET published = ?, updated_at = ? WHERE id = ?', pub, now(), t.id);
  return { team: viewTeam(teamRow(t.id), ctx.user.id), published: !!pub };
}, { auth: true });

// 对外 API：生成 / 吊销调用密钥（密钥只在生成时返回一次）
POST('/api/teams/:id/api-key', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('只能为自己的团队开启 API');
  if (!(jparse(t.member_ids, []) || []).length) throw bad('空团队不能开启 API');
  const key = 'lk_' + uid('', 28);
  q.run('UPDATE teams SET api_key = ?, updated_at = ? WHERE id = ?', key, now(), t.id);
  return { api_key: key, endpoint: '/api/public/run' };
}, { auth: true });

DEL('/api/teams/:id/api-key', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('无权操作');
  q.run('UPDATE teams SET api_key = NULL, updated_at = ? WHERE id = ?', now(), t.id);
  return { revoked: true };
}, { auth: true });

// 团队记忆（变量）：跨运行持久状态，成员可用 memory 工具读写，用户可在此查看/编辑
GET('/api/teams/:id/memory', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!canUse(t, ctx.user.id)) throw notFound();
  return { items: q.all('SELECT key, value, updated_at FROM team_memory WHERE team_id = ? ORDER BY key', t.id), editable: t.owner_id === ctx.user.id };
}, { auth: true });

PUT('/api/teams/:id/memory', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('只能编辑自己团队的记忆');
  const key = sanitizeText(ctx.body?.key, 60);
  if (!key) throw bad('记忆需要一个键名');
  const value = sanitizeText(ctx.body?.value, 500);
  const exists = q.get('SELECT 1 FROM team_memory WHERE team_id = ? AND key = ?', t.id, key);
  if (!exists && q.get('SELECT COUNT(*) c FROM team_memory WHERE team_id = ?', t.id).c >= 50) throw bad('团队记忆已满（最多 50 条）');
  q.run('INSERT INTO team_memory (team_id, key, value, updated_at) VALUES (?,?,?,?) ON CONFLICT(team_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at', t.id, key, value, now());
  return { key, value };
}, { auth: true });

DEL('/api/teams/:id/memory/:key', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('无权操作');
  q.run('DELETE FROM team_memory WHERE team_id = ? AND key = ?', t.id, ctx.params.key);
  return { deleted: true };
}, { auth: true });

// 出站 Webhook：运行完成后把结果 POST 给这个地址（设置时即做 SSRF 校验）
PUT('/api/teams/:id/webhook', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('只能配置自己团队的 Webhook');
  const raw = sanitizeText(ctx.body?.url, 300);
  if (!raw) throw bad('填一个回调地址');
  let u; try { u = new URL(raw); } catch { throw bad('无效的网址'); }
  const blocked = await assertSafeHop(u);
  if (blocked) throw bad('该地址不可用：' + blocked);
  q.run('UPDATE teams SET webhook_url = ?, updated_at = ? WHERE id = ?', u.href, now(), t.id);
  return { webhook_url: u.href };
}, { auth: true });

DEL('/api/teams/:id/webhook', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!t) throw notFound();
  if (!canEdit(t, ctx.user.id)) throw denied('无权操作');
  q.run('UPDATE teams SET webhook_url = NULL, updated_at = ? WHERE id = ?', now(), t.id);
  return { removed: true };
}, { auth: true });

// ============================================================
// 运行任务
// ============================================================
POST('/api/teams/:id/run', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!canUse(t, ctx.user.id)) throw notFound();
  const raw = sanitizeText(ctx.body?.task, 1000);
  if (!raw) throw bad('先描述一下要这支团队做什么');
  const task = resolveTask(raw, ctx.body?.vars || {}, t.id);   // {{变量}} 用入参 / 团队记忆填充
  const members = (jparse(t.member_ids, []) || []).map(agentRow).filter((a) => a && a.enabled);
  if (!members.length) throw bad('这个团队还没有成员，先去添加成员吧');

  const limit = dailyRunLimit(ctx.user);
  if (!useQuota(ctx.user.id, 'agent_run', limit)) {
    throw denied(
      isMember(ctx.user) ? '今天平台额度到上限了～在「模型设置」填上你自己的大模型 Key，即可用自己的模型不限量跑' : `每天可免费体验 ${AGENT_QUOTA.FREE_RUNS_PER_DAY} 次，开通会员并自带大模型 Key 即可不限量`,
      { need_member: !isMember(ctx.user), quota_exceeded: true, byok_hint: true }
    );
  }
  const runId = startTeamRun(t, task, ctx.user.id, 'manual');   // 异步执行，步骤通过 SSE 实时直播
  return { run_id: runId };
}, { auth: true });

// 批量运行：一个任务模板套用多条输入（最多 10 条），逐条顺序执行
POST('/api/teams/:id/batch', async (ctx) => {
  const t = teamRow(ctx.params.id);
  if (!canUse(t, ctx.user.id)) throw notFound();
  const task = sanitizeText(ctx.body?.task, 1000);
  if (!task) throw bad('先写好任务模板（用 {{input}} 代表每条输入）');
  let items = (Array.isArray(ctx.body?.items) ? ctx.body.items : [])
    .slice(0, 10).map((x) => typeof x === 'string' ? sanitizeText(x, 500) : x).filter((x) => x && (typeof x !== 'string' || x.length));
  if (!items.length) throw bad('至少给一条输入');
  if (!(jparse(t.member_ids, []) || []).map(agentRow).some((a) => a && a.enabled)) throw bad('这个团队还没有成员');
  const limit = dailyRunLimit(ctx.user);
  const left = Math.max(0, limit - quotaUsed(ctx.user.id, 'agent_run'));
  if (items.length > left) throw denied(`批量需要 ${items.length} 次运行额度，今天只剩 ${left} 次`, { need_member: !isMember(ctx.user), quota_exceeded: true });
  for (let i = 0; i < items.length; i++) useQuota(ctx.user.id, 'agent_run', limit);
  const { batchId, runIds } = startBatch(t, task, items, ctx.user.id);
  return { batch_id: batchId, run_ids: runIds, count: runIds.length };
}, { auth: true });

GET('/api/runs', async (ctx) => ({
  items: q.all('SELECT id, team_id, team_name, strategy, task, status, by_llm, step_count, started_at, ended_at FROM agent_runs WHERE user_id = ? ORDER BY started_at DESC LIMIT 30', ctx.user.id)
}), { auth: true });

GET('/api/runs/:id', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run || run.user_id !== ctx.user.id) throw notFound();
  return { run: { ...run, plan: jparse(run.plan, null) }, steps: q.all('SELECT * FROM run_steps WHERE run_id = ? ORDER BY idx', run.id) };
}, { auth: true });

// 生成 / 取消 公开分享链接（只读作战室，免登录可看，用于传播获客）
POST('/api/runs/:id/share', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run || run.user_id !== ctx.user.id) throw notFound();
  if (run.status === 'running') throw bad('等这次运行结束再分享吧');
  let sid = run.share_id;
  if (!sid) { sid = uid('s_', 12); q.run('UPDATE agent_runs SET share_id = ? WHERE id = ?', sid, run.id); }
  return { share_id: sid };
}, { auth: true });

DEL('/api/runs/:id/share', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run || run.user_id !== ctx.user.id) throw notFound();
  q.run('UPDATE agent_runs SET share_id = NULL WHERE id = ?', run.id);
  return { unshared: true };
}, { auth: true });

// 公开只读读取（免登录）：仅暴露协作过程与交付，不含用户身份
GET('/api/public/share/:shareId', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE share_id = ?', String(ctx.params.shareId));
  if (!run) throw notFound('分享不存在或已取消');
  return {
    run: { team_name: run.team_name, strategy: run.strategy, task: run.task, status: run.status, result: run.result, by_llm: run.by_llm, step_count: run.step_count, started_at: run.started_at },
    steps: q.all('SELECT idx, phase, agent_name, agent_avatar, title, output, tool, tool_result, status FROM run_steps WHERE run_id = ? ORDER BY idx', run.id)
  };
});

// 批量运行结果（轮询用）
GET('/api/runs/batch/:batchId', async (ctx) => {
  const items = q.all('SELECT id, task, status, result, step_count, by_llm, started_at, ended_at FROM agent_runs WHERE batch_id = ? AND user_id = ? ORDER BY id', ctx.params.batchId, ctx.user.id);
  if (!items.length) throw notFound();
  return { batch_id: ctx.params.batchId, items, done: items.every((r) => r.status !== 'running') };
}, { auth: true });

POST('/api/runs/:id/stop', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run || run.user_id !== ctx.user.id) throw notFound();
  if (run.status === 'running') stopRun(run.id);
  return { stopping: true };
}, { auth: true });

// 作战室实时事件流：先回放已产生的步骤，再订阅后续；终态补发 done/error
GET('/api/runs/:id/events', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run || run.user_id !== ctx.user.id) throw notFound();
  const client = openSSE(ctx.req, ctx.res);
  const terminal = (r) => r.status === 'failed' ? ['error', { error: r.error || '运行失败' }] : ['done', r];

  for (const s of q.all('SELECT * FROM run_steps WHERE run_id = ? ORDER BY idx', run.id)) client.send('step', s);
  if (run.status !== 'running') { const [ev, data] = terminal(run); client.send(ev, data); client.close(); return; }

  subscribe(`run:${run.id}`, client, ctx.user.id);
  // 回放与订阅之间若已结束，立即补发终态
  const fresh = q.get('SELECT * FROM agent_runs WHERE id = ?', run.id);
  if (fresh.status !== 'running') { const [ev, data] = terminal(fresh); client.send(ev, data); }
}, { auth: true });

// ============================================================
// 定时触发器：让团队按计划自动执行任务
// ============================================================
const triggerView = (t) => ({
  id: t.id, team_id: t.team_id, team_name: q.get('SELECT name FROM teams WHERE id = ?', t.team_id)?.name || '(团队已删除)',
  name: t.name, task: t.task, schedule_kind: t.schedule_kind, interval_min: t.interval_min,
  at_hour: t.at_hour, at_minute: t.at_minute, enabled: !!t.enabled,
  next_run_at: t.next_run_at, last_run_at: t.last_run_at, last_run_id: t.last_run_id, run_count: t.run_count
});
const triggerRow = (id) => q.get('SELECT * FROM agent_triggers WHERE id = ?', Number(id));

function readTrigger(b, base = {}) {
  const kind = b.schedule_kind === 'daily' ? 'daily' : (b.schedule_kind === 'interval' ? 'interval' : base.schedule_kind || 'interval');
  return {
    name: sanitizeText(b.name ?? base.name, 30),
    task: sanitizeText(b.task ?? base.task, 500),
    schedule_kind: kind,
    interval_min: Math.max(MIN_INTERVAL_MIN, Math.round(Number(b.interval_min ?? base.interval_min) || 60)),
    at_hour: clamp(b.at_hour ?? base.at_hour ?? 9, 0, 23),
    at_minute: clamp(b.at_minute ?? base.at_minute ?? 0, 0, 59)
  };
}

GET('/api/triggers', async (ctx) => ({
  items: q.all('SELECT * FROM agent_triggers WHERE owner_id = ? ORDER BY updated_at DESC', ctx.user.id).map(triggerView),
  limits: { min_interval_min: MIN_INTERVAL_MIN, max_triggers: MAX_TRIGGERS }
}), { auth: true });

POST('/api/triggers', async (ctx) => {
  const b = ctx.body || {};
  const team = teamRow(b.team_id);
  if (!canUse(team, ctx.user.id)) throw bad('团队不存在或无权使用');
  if (!(jparse(team.member_ids, []) || []).length) throw bad('空团队不能设定时任务');
  const f = readTrigger(b);
  if (!f.task) throw bad('设定要自动执行的任务');
  if (!f.name) f.name = team.name + ' · 定时任务';
  if (q.get('SELECT COUNT(*) c FROM agent_triggers WHERE owner_id = ? AND enabled = 1', ctx.user.id).c >= MAX_TRIGGERS) {
    throw bad(`最多同时启用 ${MAX_TRIGGERS} 个定时任务，先停用一些吧`);
  }
  const ts = now();
  const r = q.run(
    `INSERT INTO agent_triggers (owner_id, team_id, name, task, schedule_kind, interval_min, at_hour, at_minute, enabled, next_run_at, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,1,?,?,?)`,
    ctx.user.id, team.id, f.name, f.task, f.schedule_kind, f.interval_min, f.at_hour, f.at_minute, computeNext(f), ts, ts
  );
  return { trigger: triggerView(triggerRow(Number(r.lastInsertRowid))) };
}, { auth: true });

PATCH('/api/triggers/:id', async (ctx) => {
  const t = triggerRow(ctx.params.id);
  if (!t || t.owner_id !== ctx.user.id) throw notFound();
  const b = ctx.body || {};
  const f = readTrigger(b, t);
  const enabling = b.enabled !== undefined ? (b.enabled ? 1 : 0) : t.enabled;
  if (enabling && !t.enabled && q.get('SELECT COUNT(*) c FROM agent_triggers WHERE owner_id = ? AND enabled = 1 AND id != ?', ctx.user.id, t.id).c >= MAX_TRIGGERS) {
    throw bad(`最多同时启用 ${MAX_TRIGGERS} 个定时任务`);
  }
  q.run(
    `UPDATE agent_triggers SET name = ?, task = ?, schedule_kind = ?, interval_min = ?, at_hour = ?, at_minute = ?, enabled = ?, next_run_at = ?, updated_at = ? WHERE id = ?`,
    f.name || t.name, f.task || t.task, f.schedule_kind, f.interval_min, f.at_hour, f.at_minute, enabling, computeNext(f), now(), t.id
  );
  return { trigger: triggerView(triggerRow(t.id)) };
}, { auth: true });

DEL('/api/triggers/:id', async (ctx) => {
  const t = triggerRow(ctx.params.id);
  if (!t || t.owner_id !== ctx.user.id) throw notFound();
  q.run('DELETE FROM agent_triggers WHERE id = ?', t.id);
  return { deleted: true };
}, { auth: true });

POST('/api/triggers/:id/run-now', async (ctx) => {
  const t = triggerRow(ctx.params.id);
  if (!t || t.owner_id !== ctx.user.id) throw notFound();
  const limit = dailyRunLimit(ctx.user);
  if (!useQuota(ctx.user.id, 'agent_run', limit)) throw denied('今天的运行次数到上限了', { need_member: !isMember(ctx.user), quota_exceeded: true });
  const runId = fireTrigger(t, { advance: false });   // 立即跑一次，不打乱原定计划
  if (!runId) throw bad('团队已不可用，触发器已自动停用');
  return { run_id: runId };
}, { auth: true });

// ============================================================
// 对外 API：用团队密钥同步调用（可被任意外部系统 / Webhook 调用，无需登录）
// ============================================================
const API_DAILY_LIMIT = 50;
POST('/api/public/run', async (ctx) => {
  const key = String(ctx.body?.key || '').trim();
  const task = sanitizeText(ctx.body?.task, 1000);
  if (!key) throw bad('缺少 API key');
  if (!task) throw bad('缺少 task');
  const team = q.get('SELECT * FROM teams WHERE api_key = ?', key);
  if (!team) throw denied('无效的 API key');
  const members = (jparse(team.member_ids, []) || []).map(agentRow).filter((a) => a && a.enabled);
  if (!members.length) throw bad('该团队当前没有可用成员');
  if (!useQuota(team.owner_id, 'agent_api', API_DAILY_LIMIT)) throw denied('该团队今日 API 调用已达上限，请明天再试');
  const run = await runTeamSync(team, task, team.owner_id, 'api');     // 跑完返回结果
  return { run_id: run.id, status: run.status, result: run.result, by_llm: !!run.by_llm, step_count: run.step_count };
});

// ============================================================
// 智能体草稿箱（站内动作 draft_post 的产物）
// ============================================================
const draftView = (d) => ({ id: d.id, text: d.text, card: jparse(d.card, {}), run_id: d.run_id, created_at: d.created_at });
GET('/api/agent-drafts', async (ctx) => ({
  items: q.all("SELECT * FROM agent_post_drafts WHERE owner_id = ? AND status = 'draft' ORDER BY created_at DESC LIMIT 50", ctx.user.id).map(draftView)
}), { auth: true });

DEL('/api/agent-drafts/:id', async (ctx) => {
  const d = q.get('SELECT * FROM agent_post_drafts WHERE id = ?', Number(ctx.params.id));
  if (!d || d.owner_id !== ctx.user.id) throw notFound();
  q.run('DELETE FROM agent_post_drafts WHERE id = ?', d.id);
  return { deleted: true };
}, { auth: true });

// ============================================================
// 知识库
// ============================================================
GET('/api/kb', async (ctx) => ({
  mine: q.all('SELECT * FROM knowledge_bases WHERE owner_id = ? ORDER BY updated_at DESC', ctx.user.id),
  templates: q.all('SELECT * FROM knowledge_bases WHERE is_template = 1 AND owner_id = 0 ORDER BY id')
    .map((k) => ({ ...k, mine: false }))
}), { auth: true });

POST('/api/kb', async (ctx) => {
  const name = sanitizeText(ctx.body?.name, 30);
  if (!name) throw bad('给知识库起个名字');
  const ts = now();
  const r = q.run('INSERT INTO knowledge_bases (owner_id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)',
    ctx.user.id, name, sanitizeText(ctx.body?.description, 200), ts, ts);
  return { kb: kbRow(Number(r.lastInsertRowid)) };
}, { auth: true });

GET('/api/kb/:id', async (ctx) => {
  const kb = kbRow(ctx.params.id);
  if (!canUse(kb, ctx.user.id)) throw notFound();
  const sources = q.all('SELECT source, COUNT(*) chunks FROM knowledge_chunks WHERE kb_id = ? GROUP BY source', kb.id);
  const sample = q.all('SELECT id, source, idx, text FROM knowledge_chunks WHERE kb_id = ? ORDER BY idx LIMIT 8', kb.id);
  return { kb: { ...kb, mine: kb.owner_id === ctx.user.id }, sources, sample };
}, { auth: true });

POST('/api/kb/:id/docs', async (ctx) => {
  const kb = kbRow(ctx.params.id);
  if (!kb) throw notFound();
  if (!canEdit(kb, ctx.user.id)) throw denied('内置示例知识库不可修改');
  const text = sanitizeText(ctx.body?.text, 50_000);
  if (!text) throw bad('粘贴一些文本内容');
  const res = addDoc(kb.id, sanitizeText(ctx.body?.source, 60) || '文档', text);
  return { added: res.added, kb: kbRow(kb.id) };
}, { auth: true });

POST('/api/kb/:id/search', async (ctx) => {
  const kb = kbRow(ctx.params.id);
  if (!canUse(kb, ctx.user.id)) throw notFound();
  const query = sanitizeText(ctx.body?.query, 200);
  if (!query) throw bad('输入要检索的内容');
  return { hits: searchKnowledge([kb.id], query, 5) };
}, { auth: true });

DEL('/api/kb/:id', async (ctx) => {
  const kb = kbRow(ctx.params.id);
  if (!kb) throw notFound();
  if (!canEdit(kb, ctx.user.id)) throw denied('不能删除内置知识库');
  q.run('DELETE FROM knowledge_chunks WHERE kb_id = ?', kb.id);
  q.run('DELETE FROM knowledge_bases WHERE id = ?', kb.id);
  return { deleted: true };
}, { auth: true });

// ============================================================
// 后台：灵阵运行监控与管控
// ============================================================
GET('/api/admin/agents/overview', async () => {
  const start = new Date(dayCN() + 'T00:00:00+08:00').getTime();
  const tot = q.get(
    `SELECT COUNT(*) total,
       COALESCE(SUM(CASE WHEN status='running' THEN 1 ELSE 0 END),0) running,
       COALESCE(SUM(CASE WHEN status='done'    THEN 1 ELSE 0 END),0) done,
       COALESCE(SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END),0) failed,
       COALESCE(SUM(CASE WHEN by_llm=1 THEN 1 ELSE 0 END),0) by_llm
     FROM agent_runs`
  );
  return {
    totals: {
      teams: q.get('SELECT COUNT(*) c FROM teams WHERE owner_id != 0').c,
      agents: q.get('SELECT COUNT(*) c FROM agents WHERE owner_id != 0').c,
      kbs: q.get('SELECT COUNT(*) c FROM knowledge_bases WHERE owner_id != 0').c,
      published: q.get('SELECT COUNT(*) c FROM teams WHERE published = 1 AND owner_id != 0').c,
      api_teams: q.get('SELECT COUNT(*) c FROM teams WHERE api_key IS NOT NULL').c,
      triggers: q.get('SELECT COUNT(*) c FROM agent_triggers').c,
      triggers_enabled: q.get('SELECT COUNT(*) c FROM agent_triggers WHERE enabled = 1').c,
      drafts: q.get("SELECT COUNT(*) c FROM agent_post_drafts WHERE status = 'draft'").c,
      memory: q.get('SELECT COUNT(*) c FROM team_memory').c
    },
    runs: { ...tot, today: q.get('SELECT COUNT(*) c FROM agent_runs WHERE started_at >= ?', start).c },
    cost_today_micro: todayCostMicro('agent_'),
    budget_micro: Number(getSetting('agent_budget_micro', AGENT_QUOTA.DEFAULT_BUDGET_MICRO)),
    quota: { free: AGENT_QUOTA.FREE_RUNS_PER_DAY, member: AGENT_QUOTA.MEMBER_RUNS_PER_DAY },
    recent: q.all(
      `SELECT r.id, r.team_name, r.strategy, r.status, r.step_count, r.token_total, r.cost_micro, r.by_llm, r.source, r.started_at, u.nickname owner_name
       FROM agent_runs r LEFT JOIN users u ON u.id = r.user_id ORDER BY r.started_at DESC LIMIT 30`
    )
  };
}, { admin: true });

GET('/api/admin/agents/runs/:id', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run) throw notFound();
  return { run: { ...run, plan: jparse(run.plan, null) }, steps: q.all('SELECT * FROM run_steps WHERE run_id = ? ORDER BY idx', run.id) };
}, { admin: true });

POST('/api/admin/agents/runs/:id/stop', async (ctx) => {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', Number(ctx.params.id));
  if (!run) throw notFound();
  if (run.status === 'running') stopRun(run.id);
  return { stopping: true };
}, { admin: true });

PUT('/api/admin/agents/config', async (ctx) => {
  const v = Math.max(0, Math.round(Number(ctx.body?.budget_micro) || 0));
  setSetting('agent_budget_micro', v);
  return { budget_micro: v };
}, { admin: true });
