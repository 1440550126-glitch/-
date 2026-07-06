// SoloCompany OS · 多智能体编排引擎（平台核心）
// 一次运行：① 队长拆解任务并分派 → ② 成员各自带工具 ReAct 产出（共享黑板记忆）→ ③ 总编整合交付。
// 三种策略：orchestrate(编排) / sequential(流水线) / route(路由) / debate(论战)。
// 铁律：每个大模型调用都有确定性本地兜底——无 Key / 断网 / 超预算时全程走规则引擎，真实调用工具、产出结构化成果。
import { q, getSetting } from '../lib/db.js';
import { now, clamp, jparse, uid } from '../lib/util.js';
import { publish } from '../lib/hub.js';
import { chatLLM, logUsage, resolveLLM, todayCostMicro } from '../lib/llm.js';
import { getTool, toolsSpec } from './tools.js';
import { terms } from './knowledge.js';
import { safeFetch } from './safefetch.js';
import { AGENT_QUOTA, STRATEGIES } from './catalog.js';

// ---- 运行控制（停止）----
const STOPPED = new Set();
export const stopRun = (id) => STOPPED.add(Number(id));
const isStopped = (id) => STOPPED.has(Number(id));

// ---- 预算闸门：平台 Key 每日成本封顶后强制走本地引擎；用户自带 Key(BYOK) 不受此限 ----
function withinBudget(byok) {
  if (byok) return true;
  const budget = Number(getSetting('agent_budget_micro', AGENT_QUOTA.DEFAULT_BUDGET_MICRO));
  if (!budget || budget <= 0) return true;
  return todayCostMicro('agent_') < budget;
}
// 某用户当前是否可用大模型（平台 Key 或自带 Key）
const llmOn = (userId) => resolveLLM(userId).enabled;

// ---- 大模型调用 + 精确记账 + 本地兜底标记 ----
async function llmStep({ userId, feature, tier = 'default', system, prompt, json = false, maxTokens = 700, temperature = 0.6, fallback }) {
  const cfg = resolveLLM(userId);   // 自带 Key 优先，否则平台 Key
  if (cfg.enabled && withinBudget(cfg.byok)) {
    const t0 = now();
    try {
      const r = await chatLLM({ tier, system, prompt, json, maxTokens, temperature, cfg });
      const cost = logUsage({ userId, feature, provider: cfg.provider, model: r.model, promptTokens: r.promptTokens, completionTokens: r.completionTokens, ok: 1, latency: now() - t0, tier });
      return { text: r.text, tokens: r.promptTokens + r.completionTokens, cost, byLLM: true };
    } catch (e) {
      logUsage({ userId, feature, provider: cfg.provider, model: '-', ok: 0, fallback: 1, latency: now() - t0, tier });
      console.warn('[agent] llm fallback:', feature, e.message);
    }
  } else {
    logUsage({ userId, feature, provider: 'local', fallback: cfg.enabled ? 1 : 0 });
  }
  return { text: fallback ? fallback() : '', tokens: 0, cost: 0, byLLM: false };
}

function parseJSON(text) {
  if (!text) return null;
  try { return JSON.parse(text); } catch { /* try to salvage */ }
  const m = String(text).match(/\{[\s\S]*\}|\[[\s\S]*\]/);
  if (m) { try { return JSON.parse(m[0]); } catch { /* noop */ } }
  return null;
}

// ---- 步骤记录 + SSE 直播 ----
function emit(runId, event, data) { publish(`run:${runId}`, event, data); }
const stepRow = (id) => q.get('SELECT * FROM run_steps WHERE id = ?', id);

function newStep(runId, f) {
  const idx = q.get('SELECT COALESCE(MAX(idx),-1)+1 n FROM run_steps WHERE run_id = ?', runId).n;
  const r = q.run(
    `INSERT INTO run_steps (run_id, idx, phase, agent_id, agent_name, agent_avatar, title, input, output, tool, tool_args, status, by_llm, tokens, cost_micro, created_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
    runId, idx, f.phase, f.agent_id || 0, f.agent_name || '编排官', f.agent_avatar || '🛰',
    f.title || '', f.input ?? null, f.output ?? null, f.tool ?? null, f.tool_args ?? null,
    f.status || 'running', 0, 0, 0, now()
  );
  q.run('UPDATE agent_runs SET step_count = step_count + 1 WHERE id = ?', runId);
  const row = stepRow(Number(r.lastInsertRowid));
  emit(runId, 'step', row);
  return row;
}

function finishStep(runId, step, f) {
  q.run(
    `UPDATE run_steps SET output = COALESCE(?, output), tool_result = COALESCE(?, tool_result),
       status = ?, by_llm = ?, tokens = ?, cost_micro = ?, ended_at = ? WHERE id = ?`,
    f.output ?? null, f.tool_result ?? null, f.status || 'done', f.by_llm ? 1 : 0,
    f.tokens || 0, Math.round(f.cost || 0), now(), step.id
  );
  if (f.tokens || f.cost) q.run('UPDATE agent_runs SET token_total = token_total + ?, cost_micro = cost_micro + ? WHERE id = ?', f.tokens || 0, Math.round(f.cost || 0), runId);
  emit(runId, 'step', stepRow(step.id));
}

// ---- 关键词与表达式抽取（本地兜底用）----
const FILLER = '的了和与把被请帮我你他她它们这那并就也都吗呢吧啊给让向从对一二三四五六七八九十个种条款帮想要需可以怎如何什么';
function topKeywords(text, n = 6) {
  const counts = new Map();
  for (const t of terms(text)) {
    if (t.length < 2 || [...t].some((c) => FILLER.includes(c))) continue; // 滤掉填充词，留有信息量的词
    counts.set(t, (counts.get(t) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([t]) => t);
}
function extractExpr(text) {
  const m = String(text).match(/-?\d[\d\s+\-*/%.()×÷]*[+\-*/%^]\s*\d[\d\s+\-*/%.()×÷]*/);
  return m ? m[0].trim() : null;
}

// ============================================================
// 工具步骤（ReAct 中的一次工具调用，确定性，无 token）
// ============================================================
async function runToolStep(run, agent, toolId, args, kbIds, observations) {
  const tool = getTool(toolId);
  if (!tool) return { ok: false, result: '工具不存在' };
  const step = newStep(run.id, {
    phase: 'tool', agent_id: agent.id, agent_name: agent.name, agent_avatar: agent.avatar,
    title: `调用工具 · ${tool.name}`, tool: toolId, tool_args: JSON.stringify(args), input: JSON.stringify(args)
  });
  let out;
  try { out = await tool.run(args || {}, { kbIds, userId: run.user_id, runId: run.id, teamId: run.team_id }); }
  catch (e) { out = { ok: false, result: '工具异常：' + e.message }; }
  finishStep(run.id, step, { tool_result: out.result || '', output: out.result || '', status: out.ok ? 'done' : 'failed' });
  observations.push(`【工具 ${tool.name}】入参 ${JSON.stringify(args)} → ${out.result || '(空)'}`);
  return out;
}

// ============================================================
// 单个成员执行一个子任务（ReAct 工具循环 + 本地兜底）
// ============================================================
function agentSystemPrompt(agent, toolIds) {
  let s = `你是 AI 团队成员「${agent.name}」。职能：${agent.role || '通用助理'}。\n${agent.persona || ''}`;
  if (toolIds.length) {
    s += `\n你可以使用以下工具：\n${toolsSpec(toolIds)}\n` +
      `每一步只输出一个 JSON：调用工具用 {"action":"tool","tool":"工具id","args":{...}}；` +
      `已能给出结论用 {"action":"final","output":"你的产出（条理清晰、直接可用）"}。不要输出 JSON 以外的内容。`;
  } else {
    s += `\n请直接输出你的产出（条理清晰、直接可用）。`;
  }
  return s;
}

async function runSubtask(run, team, agent, item, blackboard, kbIds) {
  const toolIds = (jparse(agent.tools, []) || []).filter(getTool);
  const step = newStep(run.id, {
    phase: 'act', agent_id: agent.id, agent_name: agent.name, agent_avatar: agent.avatar,
    title: item.step, input: item.objective, status: 'running'
  });
  const memo = blackboard.map((b) => `【${b.agentName} 的产出 · ${b.step}】\n${b.output}`).join('\n\n').slice(0, 1800);
  const observations = [];
  const maxRounds = clamp(team.max_rounds, 1, AGENT_QUOTA.MAX_TOOL_ROUNDS);
  let final = null, usedLLM = false, tok = 0, cost = 0, flagged = false;

  async function produce() {
    if (llmOn(run.user_id) && toolIds.length) {
      const sys = agentSystemPrompt(agent, toolIds);
      for (let round = 0; round < maxRounds && !isStopped(run.id); round++) {
        const prompt =
          `子任务：${item.step}\n目标：${item.objective}\n用户原始任务：${run.task}\n` +
          (memo ? `\n队友已完成的产出（可参考、衔接）：\n${memo}\n` : '') +
          (observations.length ? `\n你已经获得的工具结果：\n${observations.join('\n')}\n` : '') +
          `\n现在请决定下一步（输出单个 JSON）。`;
        const r = await llmStep({ userId: run.user_id, feature: 'agent_act', tier: agent.tier, system: sys, prompt, json: true, maxTokens: 700, temperature: agent.temperature ?? 0.6, fallback: () => null });
        tok += r.tokens; cost += r.cost; usedLLM = usedLLM || r.byLLM;
        const action = r.byLLM ? parseJSON(r.text) : null;
        if (!action) return r.text || null;
        if (action.action === 'tool' && toolIds.includes(action.tool)) { await runToolStep(run, agent, action.tool, action.args || {}, kbIds, observations); continue; }
        return action.output ?? action.final ?? action.result ?? (typeof action === 'string' ? action : null);
      }
      return null;
    } else if (llmOn(run.user_id)) {
      const r = await llmStep({
        userId: run.user_id, feature: 'agent_act', tier: agent.tier, system: agentSystemPrompt(agent, []),
        prompt: `子任务：${item.step}\n目标：${item.objective}\n用户原始任务：${run.task}\n` + (memo ? `\n队友产出：\n${memo}\n` : '') + '\n请给出你的产出。',
        maxTokens: 800, temperature: agent.temperature ?? 0.6, fallback: () => null
      });
      tok += r.tokens; cost += r.cost; usedLLM = usedLLM || r.byLLM;
      return r.byLLM ? r.text : null;
    }
    return null;
  }

  // 失败可重试 + 升级：执行异常时自动重试一次，仍失败则降级并标注「需人工介入」
  for (let attempt = 0; attempt < 2; attempt++) {
    try { final = await produce(); break; }
    catch (e) {
      console.warn('[agent] subtask error', agent.id, item.step, e.message);
      if (attempt === 1) { flagged = true; }
      else {
        const div = newStep(run.id, { phase: 'system', title: `${agent.name} 执行异常，自动重试`, status: 'running' });
        finishStep(run.id, div, { output: `↻ ${agent.name} 首次执行出错（${String(e.message).slice(0, 80)}），自动重试一次…`, status: 'done' });
      }
    }
  }

  if (final == null || !String(final).trim()) {
    if (flagged) final = `（⚠ ${agent.name} 本环节连续两次执行异常，已自动重试仍未完成，建议人工介入或稍后重跑。）`;
    else { try { final = await localProduce(run, agent, item, memo, toolIds, kbIds, observations); } catch { flagged = true; final = `（⚠ ${agent.name} 本环节执行异常，建议人工介入。）`; } }
  }

  const clean = String(final).trim();
  const sc = selfCheck(item, clean, flagged);
  finishStep(run.id, step, { output: clean + '\n\n' + sc.note, status: flagged ? 'failed' : 'done', by_llm: usedLLM ? 1 : 0, tokens: tok, cost });
  blackboard.push({ agentId: agent.id, agentName: agent.name, step: item.step, output: clean, flagged });
}

// 成员交活前自检：对照子任务目标，确认要点齐备、篇幅达标（减少返工）
function selfCheck(item, output, flagged) {
  if (flagged) return { ok: false, note: '🔍 自检：本环节执行异常，需人工复核。' };
  const o = String(output || '');
  const kws = topKeywords(`${item.objective || ''} ${item.step || ''}`, 4);
  const missing = kws.filter((k) => !o.includes(k));
  const okCover = kws.length === 0 || missing.length <= Math.ceil(kws.length / 2);
  const okLen = o.length >= 60;
  const ok = okCover && okLen;
  const note = ok
    ? '🔍 自检：已对照目标完成，要点齐备，可交接下游。'
    : `🔍 自检：${!okLen ? '产出偏短、' : ''}${!okCover ? '部分要点待补、' : ''}已尽力，建议下游与验收重点关注。`;
  return { ok, note };
}

// ---- 本地兜底产出：先按启发式真实调用一个工具，再组织角色视角的结构化结论 ----
const FLAVORS = [
  { test: /调研|研究|search|research|事实|资料|检索/i, angle: '信息与事实层面', lead: '先核查可得资料，再下判断' },
  { test: /分析|数据|analy|衡|计算|指标|财务/i, angle: '数据与逻辑层面', lead: '用数字说话，量化关键指标' },
  { test: /策划|创意|plan(?!ner-pm)|谋|点子|方案/i, angle: '创意与方案层面', lead: '在约束内找有新意又能落地的解法' },
  { test: /文案|写作|writer|笔|内容|稿/i, angle: '表达与成稿层面', lead: '把要点写成打动人的成稿' },
  { test: /产品|需求|pm|舵|优先级|路线/i, angle: '产品与优先级层面', lead: '把目标拆成可验收的任务并排序' },
  { test: /工程|技术|engineer|匠|实现|架构|开发/i, angle: '技术与可行性层面', lead: '评估可行性并给出务实做法' },
  { test: /质检|审阅|critic|镜|挑错|风险|review/i, angle: '审阅与风险层面', lead: '逐条找漏洞并给出改进' }
];
function flavorOf(agent) {
  const hay = `${agent.role} ${agent.name} ${(jparse(agent.tools, []) || []).join(' ')}`;
  return FLAVORS.find((f) => f.test.test(hay)) || { angle: '专业视角', lead: '结合职责给出最有价值的产出' };
}

async function localProduce(run, agent, item, memo, toolIds, kbIds, observations) {
  // 1) 还没有工具观察时，按启发式真实触发一个工具
  if (!observations.length && toolIds.length) {
    const hay = `${item.objective} ${run.task}`;
    if (toolIds.includes('knowledge_search') && kbIds.length) {
      await runToolStep(run, agent, 'knowledge_search', { query: topKeywords(run.task, 5).join(' ') || run.task.slice(0, 20) }, kbIds, observations);
    } else if (toolIds.includes('calculator') && extractExpr(hay)) {
      await runToolStep(run, agent, 'calculator', { expression: extractExpr(hay) }, kbIds, observations);
    } else if (toolIds.includes('datetime') && /时间|日期|今天|截止|deadline|多少天|工期/i.test(hay)) {
      await runToolStep(run, agent, 'datetime', {}, kbIds, observations);
    } else if (toolIds.includes('compose_card') || toolIds.includes('draft_post')) {
      let line = '';
      for (const s of (memo ? memo.split('\n') : [])) {
        const cleaned = s.replace(/^【.*?】\s*/, '').trim();   // 去掉 “【某成员】” 表头，取正文
        if (cleaned.length >= 6) { line = cleaned; break; }
      }
      const text = (line || run.task).slice(0, 40);
      await runToolStep(run, agent, toolIds.includes('compose_card') ? 'compose_card' : 'draft_post', { text }, kbIds, observations);
    } else if (toolIds.includes('daily_topic')) {
      await runToolStep(run, agent, 'daily_topic', { theme: topKeywords(run.task, 1)[0] || '' }, kbIds, observations);
    } else if (toolIds.includes('fortune')) {
      await runToolStep(run, agent, 'fortune', { who: topKeywords(run.task, 1)[0] || '' }, kbIds, observations);
    } else if (toolIds.includes('summarize')) {
      await runToolStep(run, agent, 'summarize', { text: memo || run.task }, kbIds, observations);
    } else if (toolIds.includes('extract')) {
      await runToolStep(run, agent, 'extract', { text: memo || run.task }, kbIds, observations);
    } else if (toolIds.includes('memory')) {
      await runToolStep(run, agent, 'memory', { op: 'list' }, kbIds, observations);
    } else if (toolIds.includes('text_stats') && memo) {
      await runToolStep(run, agent, 'text_stats', { text: memo.slice(0, 500) }, kbIds, observations);
    }
  }
  // 2) 组织角色视角的结构化结论（真实引用工具结果与上游产出）
  const f = flavorOf(agent);
  const kws = topKeywords(`${run.task} ${item.objective}`, 5);
  const lines = [];
  lines.push(`从${f.angle}切入（${f.lead}）。本环节目标：${item.step}。`);
  if (kws.length) lines.push(`围绕关键点：${kws.join('、')}。`);
  lines.push('要点：');
  lines.push(`1. 紧扣任务「${run.task.slice(0, 40)}${run.task.length > 40 ? '…' : ''}」，给出本角色最该负责的结论；`);
  lines.push(`2. ${memo ? '在队友已有产出基础上补充、衔接，不重复造轮子；' : '作为起点，为后续成员铺好可继续加工的半成品；'}`);
  lines.push(`3. 标注尚不确定、需要进一步确认的地方，避免臆造。`);
  if (observations.length) lines.push(`工具佐证：\n${observations.join('\n')}`);
  return `【${agent.name}】${lines.join('\n')}`;
}

// ============================================================
// 计划阶段
// ============================================================
function validatePlan(raw, members) {
  const arr = Array.isArray(raw) ? raw : raw?.plan;
  if (!Array.isArray(arr) || !arr.length) return null;
  const out = [];
  for (const it of arr.slice(0, members.length + 2)) {
    let agent = members.find((m) => m.id === Number(it.assignee));
    if (!agent && typeof it.assignee === 'string') agent = members.find((m) => m.name === it.assignee || it.assignee.includes(String(m.id)));
    if (!agent) agent = members[out.length % members.length];
    out.push({
      step: String(it.step || it.title || `子任务 ${out.length + 1}`).slice(0, 60),
      agentId: agent.id,
      objective: String(it.objective || it.goal || run_taskOf(it) || '').slice(0, 400) || `完成「${it.step || ''}」`,
      depends_on: Array.isArray(it.depends_on) ? it.depends_on.map(Number).filter((x) => x >= 1) : [],
      estimate_min: Number(it.estimate_min) > 0 ? clamp(Math.round(Number(it.estimate_min)), 1, 120) : undefined
    });
  }
  return out.length ? out : null;
}
const run_taskOf = (it) => it.task || it.desc || '';

function fallbackPlan(run, team, members) {
  if (team.strategy === 'route') {
    const best = pickBestMember(run.task, members);
    return [{ step: '独立承接', agentId: best.id, objective: run.task, depends_on: [] }];
  }
  if (team.strategy === 'debate') {
    return members.map((m) => ({ step: `${m.name} 的立场`, agentId: m.id, objective: `就「${run.task}」给出你的立场、理由与潜在风险（${m.role || ''} 视角）`, depends_on: [] }));
  }
  // orchestrate / sequential：每位成员一个子任务，sequential 串成链
  return members.map((m, i) => ({
    step: `${m.name} 负责的部分`,
    agentId: m.id,
    objective: `结合你的专长（${m.role || m.name}），完成你在本任务中负责的部分，给出该角色视角下最有价值的产出。`,
    depends_on: team.strategy === 'sequential' && i > 0 ? [i] : []
  }));
}

function pickBestMember(task, members) {
  const kws = new Set(terms(task));
  let best = members[0], bestScore = -1;
  for (const m of members) {
    const mt = terms(`${m.role} ${m.name} ${m.persona}`);
    let s = 0; for (const t of mt) if (kws.has(t)) s++;
    if (s > bestScore) { bestScore = s; best = m; }
  }
  return best;
}

// 为计划补齐 RACI 与工时：负责(R)=承接成员，复核(C)=质检类成员或总编，预计工时按目标体量估算
function enrichPlan(plan, members) {
  const reviewer = members.find((m) => /质检|审阅|审核|critic|镜|复核|检查|挑错/i.test(`${m.role} ${m.name}`));
  for (const p of plan) {
    if (!(Number(p.estimate_min) > 0)) p.estimate_min = clamp(Math.round(String(p.objective || '').length / 12) + 5, 5, 30);
    if (!p.reviewer) p.reviewer = (reviewer && reviewer.id !== p.agentId) ? reviewer.name : '总编 · 整合官';
  }
  return plan;
}

async function planTasks(run, team, members, kbIds) {
  // sequential 直接确定性编排，省 token
  if (team.strategy === 'sequential') return { plan: enrichPlan(fallbackPlan(run, team, members), members), acceptance: localAcceptance(run.task), byLLM: false, summary: '按既定工序串联流水线' };

  const roster = members.map((m) => `#${m.id} ${m.name}（${m.role || '通用'}）`).join('\n');
  const sys = `你是 AI 团队「${team.name}」的编排官(队长)。团队使命：${team.goal || '按用户任务交付高质量成果'}。${team.manager_note || ''}\n` +
    `团队成员：\n${roster}\n该团队${kbIds.length ? '挂载了知识库，成员可检索' : '未挂载知识库'}。` +
    (team.strategy === 'route' ? '\n采用「路由」模式：只挑选最合适的一名成员独立承接整个任务。'
      : team.strategy === 'debate' ? '\n采用「论战」模式：让每位成员各自就任务给出独立观点，稍后由你综合。'
        : '\n采用「编排协作」模式：把任务拆给最合适的成员，必要时标注依赖。');
  const prompt = `用户任务：${run.task}\n` +
    `先像专业项目经理一样定义本次交付的「验收标准(Definition of Done)」，再拆解任务。只输出 JSON：` +
    `{"plan":[{"step":"子任务标题","assignee":成员编号数字,"objective":"交给该成员的具体目标","estimate_min":预计工时分钟数,"depends_on":[前置子任务序号(从1开始)]}],` +
    `"acceptance":["可逐条核对的验收标准1","验收标准2","验收标准3"],"summary":"一句话拆解思路"}` +
    `\n子任务数量${team.strategy === 'route' ? '恰好 1 个' : `2~${members.length + 1} 个`}；acceptance 给 3~5 条具体、可检验的成果标准。`;
  const r = await llmStep({ userId: run.user_id, feature: 'agent_plan', tier: 'default', system: sys, prompt, json: true, maxTokens: 760, temperature: 0.4, fallback: () => null });
  let plan = null, summary = '', acceptance = null;
  if (r.byLLM) {
    const parsed = parseJSON(r.text);
    plan = validatePlan(parsed, members); summary = parsed?.summary || '';
    if (Array.isArray(parsed?.acceptance)) acceptance = parsed.acceptance.map((x) => String(x).slice(0, 120)).filter(Boolean).slice(0, 6);
  }
  if (!plan) plan = fallbackPlan(run, team, members);
  plan = enrichPlan(plan, members);
  if (!acceptance || !acceptance.length) acceptance = localAcceptance(run.task);
  return { plan, acceptance, byLLM: r.byLLM, summary, tokens: r.tokens, cost: r.cost };
}

// 拓扑排序（按 depends_on，1 基序号；异常时退回原序）
function topoOrder(plan) {
  const n = plan.length;
  const indeg = plan.map((p) => (p.depends_on || []).filter((d) => d >= 1 && d <= n).length);
  const order = [];
  const used = new Array(n).fill(false);
  for (let guard = 0; guard < n; guard++) {
    const i = indeg.findIndex((d, idx) => d === 0 && !used[idx]);
    if (i < 0) break;
    used[i] = true; order.push(i);
    for (let j = 0; j < n; j++) if (!used[j] && (plan[j].depends_on || []).includes(i + 1)) indeg[j]--;
  }
  for (let i = 0; i < n; i++) if (!used[i]) order.push(i); // 兜底：残余按原序
  return order;
}

// ============================================================
// 圆桌论战：成员逐轮看到他人观点后回应/反驳/修正
// ============================================================
async function runDebate(run, team, members, kbIds) {
  const rounds = clamp(team.max_rounds, 1, 3);
  const latest = new Map(); // memberId -> { agentName, output }
  const finalBB = () => [...latest.values()].map((v) => ({ agentName: v.agentName, step: '最终立场', output: v.output }));
  for (let r = 1; r <= rounds && !isStopped(run.id); r++) {
    if (rounds > 1) {
      const div = newStep(run.id, { phase: 'system', agent_name: '圆桌主持', agent_avatar: '⚖️', title: r === 1 ? '第 1 轮 · 各陈立场' : `第 ${r} 轮 · 互相回应`, status: 'running' });
      finishStep(run.id, div, { output: r === 1 ? '请各位先独立给出立场与理由。' : '请阅读他人最新观点后，明确同意 / 反驳 / 补充，并更新结论。', status: 'done' });
    }
    for (const member of members) {
      if (isStopped(run.id)) return finalBB();
      // 传给该成员的"黑板"= 其他成员的最新观点
      const others = [...latest.entries()].filter(([id]) => id !== member.id).map(([, v]) => ({ agentName: v.agentName, step: '观点', output: v.output }));
      const objective = r === 1
        ? `就「${run.task}」给出你的立场、核心理由，以及你看到的潜在风险（从你的${member.role || '专业'}视角）。`
        : `第 ${r} 轮：阅读其他成员的最新观点后，明确表示同意 / 反驳 / 补充，并据此更新你的结论。`;
      const item = { step: r === 1 ? `${member.name} 的立场` : `${member.name} · 第${r}轮回应`, objective };
      await runSubtask(run, team, member, item, others, kbIds);
      const produced = others[others.length - 1]; // runSubtask 把新产出追加到传入数组末尾
      if (produced) latest.set(member.id, { agentName: member.name, output: produced.output });
    }
  }
  return finalBB();
}

// ============================================================
// 整合阶段
// ============================================================
function localSynthesize(run, team, blackboard) {
  const stratName = STRATEGIES[team.strategy]?.name || team.strategy;
  const roles = blackboard.map((b) => b.agentName).join('、');
  const flagged = blackboard.filter((b) => b.flagged);
  const sections = blackboard.map((b) => `### ${b.agentName} · ${b.step}\n${b.output}`).join('\n\n');
  const summary = !blackboard.length
    ? `团队就「${run.task}」完成了处理。`
    : team.strategy === 'debate'
      ? `${blackboard.length} 位成员围绕「${run.task}」多轮交锋，下面汇总各方立场与可取之处。`
      : `${team.name} 的 ${blackboard.length} 位成员从不同角度协作完成「${run.task}」，已整合为可直接使用的成果。`;
  const risks = [];
  if (flagged.length) risks.push(`**${flagged.map((f) => f.agentName).join('、')}** 的环节执行异常、已重试仍未完成，建议人工复核或重跑该部分。`);
  risks.push('部分结论基于通用经验给出，落地前请结合你的实际数据 / 场景核验。');
  risks.push('如需更强的事实性与更深入的产出，配置大模型 Key 后重跑本团队即可。');
  return `# 「${run.task}」· 团队交付\n> 由 ${team.name}（${stratName}）的 ${blackboard.length} 位成员协作完成：${roles}\n\n` +
    `## 执行摘要（TL;DR）\n${summary}\n\n## 各部分产出\n${sections}\n\n` +
    `## 假设与风险\n${risks.map((x) => '- ' + x).join('\n')}\n\n## 下一步建议\n` +
    `- 选取最关键的 1~2 个结论先行落地、快速验证；\n- 把仍标注「待确认」的点补齐资料或数据后复跑；\n- 需要规模化时用「批量运行」对多条输入套用同一流程。`;
}

async function synthesize(run, team, members, blackboard) {
  const sys = team.strategy === 'debate'
    ? `你是圆桌论战的主持总编。综合各成员观点，输出中文 Markdown，结构固定为：## 执行摘要（TL;DR，一句话裁决）→ ## 共识 → ## 分歧 → ## 假设与风险 → ## 结论与建议。客观中立，不偏袒某一方。`
    : `你是团队「${team.name}」的总编。把成员们的产出整合成给用户的最终交付物，中文 Markdown，结构固定为：## 执行摘要（TL;DR，一段话讲清结论）→ ## 正文（分点 / 分模块呈现核心成果）→ ## 假设与风险（列出关键假设与待确认风险）→ ## 下一步建议。只给成果，不要复述过程。`;
  const parts = blackboard.map((b) => `## ${b.agentName} · ${b.step}\n${b.output}`).join('\n\n');
  const prompt = `用户任务：${run.task}\n团队策略：${STRATEGIES[team.strategy]?.name || team.strategy}\n各成员产出：\n${parts}\n\n请整合成最终交付物。`;
  const step = newStep(run.id, { phase: 'synthesize', agent_id: 0, agent_name: '总编 · 整合官', agent_avatar: '🧩', title: '整合各成员产出，生成最终交付物', input: run.task, status: 'running' });
  const r = await llmStep({ userId: run.user_id, feature: 'agent_synth', tier: 'default', system: sys, prompt, maxTokens: 1200, temperature: 0.6, fallback: () => null });
  const result = (r.byLLM && r.text?.trim()) ? r.text.trim() : localSynthesize(run, team, blackboard);
  finishStep(run.id, step, { output: result, status: 'done', by_llm: r.byLLM ? 1 : 0, tokens: r.tokens, cost: r.cost });
  return { result, byLLM: r.byLLM };
}

// ============================================================
// 验收闸门：任务完成前不停下——产出未达标就让团队继续改进并重新整合
// ============================================================
const MAX_REFINE = 2;   // 自动改进最多轮数（安全上限，避免无限循环 / 成本失控）

// 验收标准（Definition of Done）——无大模型时的专业基线
export function localAcceptance() {
  return [
    '完整、准确地回应任务的核心要求，不遗漏、不跑题',
    '内容充实、可直接交付使用（有具体内容，不空话、不敷衍）',
    '结构清晰，分点 / 分段呈现，重点突出',
    '给出明确结论与可执行的下一步建议'
  ];
}

// 本地逐条验收清单（对应 localAcceptance 的 4 个专业维度）；覆盖度按任务汉字字符匹配，更稳健
export function localChecklist(task, result) {
  const r = String(result || '');
  const cjk = [...new Set(String(task).replace(/[^一-鿿]/g, '').split(''))];
  const coverage = cjk.length ? cjk.filter((c) => r.includes(c)).length / cjk.length : (r.length > 40 ? 1 : 0);
  const missing = topKeywords(task, 6).filter((k) => !r.includes(k));
  const structured = /(\n\s*[-*\d]|\n#{1,3}\s)/.test(r);
  const concluded = /(建议|下一步|总结|结论|next)/i.test(r);
  const checks = [
    { criterion: '完整覆盖任务要点', pass: coverage >= 0.6, note: coverage >= 0.6 ? '已覆盖主要内容' : '偏离任务，待补：' + missing.slice(0, 4).join('、') },
    { criterion: '内容充实可用、不空话', pass: r.length >= 160, note: r.length >= 160 ? '篇幅充足' : '偏单薄，需更具体' },
    { criterion: '结构清晰、分点呈现', pass: structured, note: structured ? '' : '建议分点 / 分段' },
    { criterion: '给出结论与下一步建议', pass: concluded, note: concluded ? '' : '缺少结论 / 建议' }
  ];
  const passN = checks.filter((c) => c.pass).length;
  const pass = checks[0].pass && passN >= 3;   // 必须覆盖要点 + 至少 3/4 达标
  const gaps = checks.filter((c) => !c.pass).map((c) => `${c.criterion}${c.note ? `（${c.note}）` : ''}`);
  return { pass, score: Math.round((passN / checks.length) * 100), checks, gaps };
}

// 验收官逐条对照「验收标准」检查产出，输出清单式结论并直播到作战室
async function reviewResult(run, team, task, result, criteria, roundNo) {
  const step = newStep(run.id, { phase: 'review', agent_id: 0, agent_name: '验收官 · 质控', agent_avatar: '✅', title: `按验收标准逐条检查（第 ${roundNo} 次）`, input: task, status: 'running' });
  let verdict = null, byLLM = false, tok = 0, cost = 0;
  if (llmOn(run.user_id)) {
    const r = await llmStep({
      userId: run.user_id, feature: 'agent_review', tier: 'default',
      system: '你是严格的验收官(QA)。逐条对照给定「验收标准」检查产出。只输出 JSON：{"checks":[{"criterion":"标准原文","pass":true|false,"note":"达标说明或具体缺口"}],"pass":全部关键项达标则true,"score":0-100}。务必对每条标准都给出判断。',
      prompt: `用户任务：${task}\n\n验收标准（逐条核对）：\n${criteria.map((c, i) => `${i + 1}. ${c}`).join('\n')}\n\n待验收产出：\n${String(result).slice(0, 2400)}`,
      json: true, maxTokens: 540, temperature: 0.2, fallback: () => null
    });
    tok = r.tokens; cost = r.cost; byLLM = r.byLLM;
    const v = r.byLLM ? parseJSON(r.text) : null;
    if (v && Array.isArray(v.checks) && v.checks.length) {
      const checks = v.checks.slice(0, 8).map((c) => ({ criterion: String(c.criterion || '').slice(0, 100), pass: !!c.pass, note: String(c.note || '').slice(0, 80) }));
      const passN = checks.filter((c) => c.pass).length;
      verdict = { pass: typeof v.pass === 'boolean' ? v.pass : passN === checks.length, score: clamp(Number(v.score ?? Math.round((passN / checks.length) * 100)), 0, 100), checks, gaps: checks.filter((c) => !c.pass).map((c) => `${c.criterion}${c.note ? `（${c.note}）` : ''}`) };
    }
  }
  if (!verdict) verdict = localChecklist(task, result);
  const passN = verdict.checks.filter((c) => c.pass).length, total = verdict.checks.length;
  const head = verdict.pass
    ? `✅ 通过验收，可交付（${passN}/${total} 项达标 · 评分 ${verdict.score}）`
    : `⚠ 未通过验收（${passN}/${total} 项达标 · 评分 ${verdict.score}），团队继续改进`;
  const lines = verdict.checks.map((c) => `${c.pass ? '✅' : '❌'} ${c.criterion}${c.note ? ` —— ${c.note}` : ''}`).join('\n');
  finishStep(run.id, step, { output: `${head}\n\n${lines}`, status: 'done', by_llm: byLLM ? 1 : 0, tokens: tok, cost });
  return verdict;
}

// 一轮改进：先发一个分隔说明，再让全体成员针对验收意见各自改进（写回黑板）
async function refineRound(run, team, members, blackboard, gaps, kbIds, roundNo) {
  const div = newStep(run.id, { phase: 'system', title: `根据验收意见，团队进入第 ${roundNo} 轮改进`, input: gaps.join('；'), status: 'running' });
  finishStep(run.id, div, { output: `🔁 验收未通过，团队针对以下意见继续打磨：\n- ${gaps.join('\n- ')}`, status: 'done' });
  const note = gaps.join('；');
  for (const agent of members) {
    if (isStopped(run.id)) break;
    await runSubtask(run, team, agent, { step: `第 ${roundNo} 轮改进`, objective: `针对验收意见改进你负责的部分：${note}。补齐缺口、提升质量与可用性，只产出改进后的内容。` }, blackboard, kbIds);
  }
}

// ============================================================
// 运行总控
// ============================================================
// 创建一次运行并异步执行（路由派活 / 定时触发器共用）。source: manual | trigger
export function startTeamRun(team, task, userId, source = 'manual') {
  const r = q.run(
    `INSERT INTO agent_runs (team_id, user_id, team_name, strategy, task, status, source, started_at)
     VALUES (?,?,?,?,?, 'running', ?, ?)`,
    team.id, userId, team.name, team.strategy, task, source, now()
  );
  const runId = Number(r.lastInsertRowid);
  void executeRun(runId);
  return runId;
}

// 变量替换：把任务里的 {{key}} 替换为 vars[key]，其次取团队记忆，都没有则原样保留
export function resolveTask(rawTask, vars = {}, teamId) {
  const mem = {};
  if (teamId) for (const r of q.all('SELECT key, value FROM team_memory WHERE team_id = ?', teamId)) mem[r.key] = r.value;
  return String(rawTask || '').replace(/\{\{\s*([\w一-鿿.-]+)\s*\}\}/g, (m, k) => {
    if (vars[k] != null && String(vars[k]) !== '') return String(vars[k]);
    if (mem[k] != null) return String(mem[k]);
    return m;
  });
}

// 批量运行：对一组输入套用同一个任务模板，逐个建运行并顺序执行（避免一次性打满大模型）
export function startBatch(team, rawTask, items, userId) {
  const batchId = 'b_' + uid('', 12);
  const runIds = [];
  for (const item of items) {
    const vars = typeof item === 'string' ? { input: item } : (item && typeof item === 'object' ? item : {});
    let task = resolveTask(rawTask, vars, team.id);
    if (typeof item === 'string' && task === rawTask && !/\{\{/.test(rawTask)) task = item;  // 模板无占位符时，字符串项即任务
    const r = q.run(
      `INSERT INTO agent_runs (team_id, user_id, team_name, strategy, task, status, source, batch_id, started_at)
       VALUES (?,?,?,?,?, 'running', 'batch', ?, ?)`,
      team.id, userId, team.name, team.strategy, task.slice(0, 1000), batchId, now()
    );
    runIds.push(Number(r.lastInsertRowid));
  }
  (async () => { for (const id of runIds) { if (!isStopped(id)) await executeRun(id); } })();
  return { batchId, runIds };
}

// 出站 Webhook：运行结束后把结果 POST 给团队配置的回调地址（SSRF 防护，失败不影响主流程）
// 自动识别飞书/Lark 自定义机器人地址，按飞书消息格式发送；其余地址按通用 JSON 推送。
export function isFeishuHook(u) {
  try { const host = new URL(u).hostname.toLowerCase(); return /(^|\.)feishu\.cn$|(^|\.)larksuite\.com$/.test(host); }
  catch { return false; }
}
export function feishuMessage(run) {
  const ok = run.status === 'done';
  const head = ok ? '✅ 任务完成' : run.status === 'failed' ? '❌ 任务失败' : 'ℹ️ 任务结束';
  let text = `【SoloCompany OS · AI 团队】${head}\n团队：${run.team_name}\n任务：${run.task}`;
  if (ok && run.result) text += `\n\n交付：\n${String(run.result).slice(0, 900)}`;
  else if (run.error) text += `\n\n原因：${run.error}`;
  return { msg_type: 'text', content: { text } };   // 飞书机器人若设关键词安全策略，加「SoloCompany OS」即可放行
}
async function fireWebhook(url, run) {
  const body = isFeishuHook(url)
    ? feishuMessage(run)
    : { run_id: run.id, team_id: run.team_id, team_name: run.team_name, task: run.task, status: run.status, result: run.result, by_llm: !!run.by_llm, source: run.source, ended_at: run.ended_at };
  try {
    await safeFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'User-Agent': 'LingArray-Webhook/1.0' },
      body: JSON.stringify(body),
      timeoutMs: 6000, followRedirects: false
    });
  } catch (e) { console.warn('[webhook]', run.id, e.message); }
}

// 同步执行：跑完再返回完整 run（对外 API 调用用，调用方要拿到最终结果）
export async function runTeamSync(team, task, userId, source = 'api') {
  const r = q.run(
    `INSERT INTO agent_runs (team_id, user_id, team_name, strategy, task, status, source, started_at)
     VALUES (?,?,?,?,?, 'running', ?, ?)`,
    team.id, userId, team.name, team.strategy, task, source, now()
  );
  const runId = Number(r.lastInsertRowid);
  await executeRun(runId);                 // executeRun 自带 try/catch，必定完成
  return q.get('SELECT * FROM agent_runs WHERE id = ?', runId);
}

export async function executeRun(runId) {
  const run = q.get('SELECT * FROM agent_runs WHERE id = ?', runId);
  if (!run) return;
  try {
    const team = q.get('SELECT * FROM teams WHERE id = ?', run.team_id);
    if (!team) throw new Error('团队不存在');
    const memberIds = jparse(team.member_ids, []) || [];
    const members = memberIds.map((id) => q.get('SELECT * FROM agents WHERE id = ? AND enabled = 1', id)).filter(Boolean);
    if (!members.length) throw new Error('团队还没有可用成员，请先添加成员');
    const kbIds = (jparse(team.knowledge_ids, []) || []).map(Number).filter(Boolean);

    // ① 计划 + 验收标准（Definition of Done）
    const planStep = newStep(run.id, { phase: 'plan', title: '编排官拆解任务、定义验收标准、分派成员', input: run.task, status: 'running' });
    const { plan, acceptance, byLLM: planByLLM, summary, tokens: pt = 0, cost: pc = 0 } = await planTasks(run, team, members, kbIds);
    const planView = plan.map((p, i) => {
      const m = members.find((x) => x.id === p.agentId);
      return `${i + 1}. ${p.step}\n   · 负责(R) ${m ? m.avatar + ' ' + m.name : '成员'}　· 复核(C) ${p.reviewer}　· 预计 ${p.estimate_min} 分钟${p.depends_on?.length ? `　· 依赖 #${p.depends_on.join(',')}` : ''}\n   · 目标：${p.objective}`;
    }).join('\n');
    const totalMin = plan.reduce((s, p) => s + (Number(p.estimate_min) || 0), 0);
    const accView = acceptance.length ? '\n\n📋 验收标准（Definition of Done）：\n' + acceptance.map((c, i) => `${i + 1}. ${c}`).join('\n') : '';
    finishStep(run.id, planStep, { output: (summary ? summary + '\n\n' : '') + `【分派 · 预计总工时 ${totalMin} 分钟】\n` + planView + accView, status: 'done', by_llm: planByLLM ? 1 : 0, tokens: pt, cost: pc });
    q.run('UPDATE agent_runs SET plan = ?, by_llm = MAX(by_llm, ?) WHERE id = ?', JSON.stringify(plan), planByLLM ? 1 : 0, run.id);

    if (isStopped(run.id)) return finalizeStopped(run.id);

    // ② 执行：debate 走多轮互评，其余按依赖拓扑序共享黑板
    let blackboard;
    if (team.strategy === 'debate') {
      blackboard = await runDebate(run, team, members, kbIds);
    } else {
      blackboard = [];
      for (const idx of topoOrder(plan)) {
        if (isStopped(run.id)) return finalizeStopped(run.id);
        const item = plan[idx];
        const agent = members.find((m) => m.id === item.agentId) || members[0];
        await runSubtask(run, team, agent, item, blackboard, kbIds);
      }
    }

    if (isStopped(run.id)) return finalizeStopped(run.id);

    // ③ 整合 → ④ 验收：未通过则团队继续改进并重新整合，直到通过或达到安全上限
    let { result, byLLM: synAny } = await synthesize(run, team, members, blackboard);
    for (let round = 0; round <= MAX_REFINE; round++) {
      if (isStopped(run.id)) return finalizeStopped(run.id);
      const review = await reviewResult(run, team, run.task, result, acceptance, round + 1);
      if (review.pass || round === MAX_REFINE) break;
      await refineRound(run, team, members, blackboard, review.gaps, kbIds, round + 1);
      if (isStopped(run.id)) return finalizeStopped(run.id);
      const re = await synthesize(run, team, members, blackboard);
      result = re.result; synAny = synAny || re.byLLM;
    }

    const fresh = q.get('SELECT by_llm FROM agent_runs WHERE id = ?', run.id);
    q.run("UPDATE agent_runs SET status = 'done', result = ?, by_llm = MAX(?, ?), ended_at = ? WHERE id = ?",
      result, fresh?.by_llm || 0, synAny ? 1 : 0, now(), run.id);
    q.run('UPDATE teams SET run_count = run_count + 1 WHERE id = ?', team.id);
    emit(run.id, 'done', q.get('SELECT * FROM agent_runs WHERE id = ?', run.id));
  } catch (e) {
    console.error('[agent] run failed', runId, e);
    q.run("UPDATE agent_runs SET status = 'failed', error = ?, ended_at = ? WHERE id = ?", String(e.message || e).slice(0, 200), now(), runId);
    emit(runId, 'error', { error: String(e.message || e).slice(0, 200) });
  } finally {
    STOPPED.delete(Number(runId));
    try {
      const fr = q.get('SELECT * FROM agent_runs WHERE id = ?', runId);
      if (fr && fr.status !== 'running') {
        const tm = q.get('SELECT webhook_url FROM teams WHERE id = ?', fr.team_id);
        if (tm?.webhook_url) void fireWebhook(tm.webhook_url, fr);
      }
    } catch { /* webhook 失败不影响运行 */ }
  }
}

function finalizeStopped(runId) {
  const r = q.get('SELECT status FROM agent_runs WHERE id = ?', runId);
  if (r && r.status === 'running') {
    q.run("UPDATE agent_runs SET status = 'stopped', ended_at = ? WHERE id = ?", now(), runId);
  }
  emit(runId, 'done', q.get('SELECT * FROM agent_runs WHERE id = ?', runId));
  STOPPED.delete(Number(runId));
}
