// 灵阵 · 多智能体编排引擎（平台核心）
// 一次运行：① 队长拆解任务并分派 → ② 成员各自带工具 ReAct 产出（共享黑板记忆）→ ③ 总编整合交付。
// 三种策略：orchestrate(编排) / sequential(流水线) / route(路由) / debate(论战)。
// 铁律：每个大模型调用都有确定性本地兜底——无 Key / 断网 / 超预算时全程走规则引擎，真实调用工具、产出结构化成果。
import { q, getSetting } from '../lib/db.js';
import { now, clamp, jparse } from '../lib/util.js';
import { publish } from '../lib/hub.js';
import { chatLLM, logUsage, llmEnabled, llmProvider, todayCostMicro } from '../lib/llm.js';
import { getTool, toolsSpec } from './tools.js';
import { terms } from './knowledge.js';
import { AGENT_QUOTA, STRATEGIES } from './catalog.js';

// ---- 运行控制（停止）----
const STOPPED = new Set();
export const stopRun = (id) => STOPPED.add(Number(id));
const isStopped = (id) => STOPPED.has(Number(id));

// ---- 预算闸门：团队功能每日成本封顶后强制走本地引擎 ----
function withinBudget() {
  const budget = Number(getSetting('agent_budget_micro', AGENT_QUOTA.DEFAULT_BUDGET_MICRO));
  if (!budget || budget <= 0) return true;
  return todayCostMicro('agent_') < budget;
}

// ---- 大模型调用 + 精确记账 + 本地兜底标记 ----
async function llmStep({ userId, feature, tier = 'default', system, prompt, json = false, maxTokens = 700, temperature = 0.6, fallback }) {
  if (llmEnabled() && withinBudget()) {
    const t0 = now();
    try {
      const r = await chatLLM({ tier, system, prompt, json, maxTokens, temperature });
      const cost = logUsage({ userId, feature, provider: llmProvider(), model: r.model, promptTokens: r.promptTokens, completionTokens: r.completionTokens, ok: 1, latency: now() - t0, tier });
      return { text: r.text, tokens: r.promptTokens + r.completionTokens, cost, byLLM: true };
    } catch (e) {
      logUsage({ userId, feature, provider: llmProvider(), model: '-', ok: 0, fallback: 1, latency: now() - t0, tier });
      console.warn('[agent] llm fallback:', feature, e.message);
    }
  } else {
    logUsage({ userId, feature, provider: 'local', fallback: llmEnabled() ? 1 : 0 });
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
  try { out = await tool.run(args || {}, { kbIds, userId: run.user_id }); }
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
  let final = null, usedLLM = false, tok = 0, cost = 0;

  if (llmEnabled() && toolIds.length) {
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
      if (!action) { final = r.text || null; break; }
      if (action.action === 'tool' && toolIds.includes(action.tool)) {
        await runToolStep(run, agent, action.tool, action.args || {}, kbIds, observations);
        continue;
      }
      final = action.output ?? action.final ?? action.result ?? (typeof action === 'string' ? action : null);
      break;
    }
  } else if (llmEnabled()) {
    // 有大模型但该成员无工具：一次性产出
    const r = await llmStep({
      userId: run.user_id, feature: 'agent_act', tier: agent.tier,
      system: agentSystemPrompt(agent, []),
      prompt: `子任务：${item.step}\n目标：${item.objective}\n用户原始任务：${run.task}\n` + (memo ? `\n队友产出：\n${memo}\n` : '') + '\n请给出你的产出。',
      maxTokens: 800, temperature: agent.temperature ?? 0.6, fallback: () => null
    });
    tok += r.tokens; cost += r.cost; usedLLM = r.byLLM; final = r.byLLM ? r.text : null;
  }

  if (final == null || !String(final).trim()) {
    final = await localProduce(run, agent, item, memo, toolIds, kbIds, observations);
  }
  finishStep(run.id, step, { output: String(final).trim(), status: 'done', by_llm: usedLLM ? 1 : 0, tokens: tok, cost });
  blackboard.push({ agentId: agent.id, agentName: agent.name, step: item.step, output: String(final).trim() });
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
      depends_on: Array.isArray(it.depends_on) ? it.depends_on.map(Number).filter((x) => x >= 1) : []
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

async function planTasks(run, team, members, kbIds) {
  // sequential 直接确定性编排，省 token
  if (team.strategy === 'sequential') return { plan: fallbackPlan(run, team, members), byLLM: false, summary: '按既定工序串联流水线' };

  const roster = members.map((m) => `#${m.id} ${m.name}（${m.role || '通用'}）`).join('\n');
  const sys = `你是 AI 团队「${team.name}」的编排官(队长)。团队使命：${team.goal || '按用户任务交付高质量成果'}。${team.manager_note || ''}\n` +
    `团队成员：\n${roster}\n该团队${kbIds.length ? '挂载了知识库，成员可检索' : '未挂载知识库'}。` +
    (team.strategy === 'route' ? '\n采用「路由」模式：只挑选最合适的一名成员独立承接整个任务。'
      : team.strategy === 'debate' ? '\n采用「论战」模式：让每位成员各自就任务给出独立观点，稍后由你综合。'
        : '\n采用「编排协作」模式：把任务拆给最合适的成员，必要时标注依赖。');
  const prompt = `用户任务：${run.task}\n` +
    `只输出 JSON：{"plan":[{"step":"子任务标题","assignee":成员编号数字,"objective":"交给该成员的具体目标","depends_on":[前置子任务序号(从1开始)]}],"summary":"一句话拆解思路"}` +
    `\n子任务数量${team.strategy === 'route' ? '恰好 1 个' : `2~${members.length + 1} 个`}。`;
  const r = await llmStep({ userId: run.user_id, feature: 'agent_plan', tier: 'default', system: sys, prompt, json: true, maxTokens: 700, temperature: 0.4, fallback: () => null });
  let plan = null, summary = '';
  if (r.byLLM) { const parsed = parseJSON(r.text); plan = validatePlan(parsed, members); summary = parsed?.summary || ''; }
  if (!plan) plan = fallbackPlan(run, team, members);
  return { plan, byLLM: r.byLLM, summary, tokens: r.tokens, cost: r.cost };
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
// 整合阶段
// ============================================================
function localSynthesize(run, team, blackboard) {
  const stratName = STRATEGIES[team.strategy]?.name || team.strategy;
  const lead = blackboard.length
    ? `团队已从 ${blackboard.length} 个角度完成「${run.task}」，以下是整合后的成果与下一步建议。`
    : `团队就「${run.task}」完成了处理。`;
  const sections = blackboard.map((b) => `### ${b.agentName} · ${b.step}\n${b.output}`).join('\n\n');
  const roles = blackboard.map((b) => b.agentName).join('、');
  return `# 「${run.task}」· 团队交付\n> 由 ${team.name}（${stratName}）的 ${blackboard.length} 位成员协作完成：${roles}\n\n` +
    `**一句话结论**：${lead}\n\n## 各部分产出\n${sections}\n\n## 下一步建议\n` +
    `- 选取上面最关键的 1~2 个结论先行落地，快速验证；\n- 把仍标注「待确认」的点补齐资料或数据后复跑；\n- 如需更高质量，配置大模型 Key 后重跑本团队即可获得更深入的产出。`;
}

async function synthesize(run, team, members, blackboard) {
  const sys = `你是团队「${team.name}」的总编。把成员们的产出整合成给用户的最终交付物：结构清晰、可直接使用的中文 Markdown；开头给一句话结论，中间分要点，最后给「下一步建议」。只给成果，不要复述过程。`;
  const parts = blackboard.map((b) => `## ${b.agentName} · ${b.step}\n${b.output}`).join('\n\n');
  const prompt = `用户任务：${run.task}\n团队策略：${STRATEGIES[team.strategy]?.name || team.strategy}\n各成员产出：\n${parts}\n\n请整合成最终交付物。`;
  const step = newStep(run.id, { phase: 'synthesize', agent_id: 0, agent_name: '总编 · 整合官', agent_avatar: '🧩', title: '整合各成员产出，生成最终交付物', input: run.task, status: 'running' });
  const r = await llmStep({ userId: run.user_id, feature: 'agent_synth', tier: 'default', system: sys, prompt, maxTokens: 1200, temperature: 0.6, fallback: () => null });
  const result = (r.byLLM && r.text?.trim()) ? r.text.trim() : localSynthesize(run, team, blackboard);
  finishStep(run.id, step, { output: result, status: 'done', by_llm: r.byLLM ? 1 : 0, tokens: r.tokens, cost: r.cost });
  return { result, byLLM: r.byLLM };
}

// ============================================================
// 运行总控
// ============================================================
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

    // ① 计划
    const planStep = newStep(run.id, { phase: 'plan', title: '编排官拆解任务、分派成员', input: run.task, status: 'running' });
    const { plan, byLLM: planByLLM, summary, tokens: pt = 0, cost: pc = 0 } = await planTasks(run, team, members, kbIds);
    const planView = plan.map((p, i) => {
      const m = members.find((x) => x.id === p.agentId);
      return `${i + 1}. ${p.step} → ${m ? m.avatar + ' ' + m.name : '成员'}：${p.objective}${p.depends_on?.length ? `（依赖 ${p.depends_on.join(',')}）` : ''}`;
    }).join('\n');
    finishStep(run.id, planStep, { output: (summary ? summary + '\n\n' : '') + planView, status: 'done', by_llm: planByLLM ? 1 : 0, tokens: pt, cost: pc });
    q.run('UPDATE agent_runs SET plan = ?, by_llm = MAX(by_llm, ?) WHERE id = ?', JSON.stringify(plan), planByLLM ? 1 : 0, run.id);

    if (isStopped(run.id)) return finalizeStopped(run.id);

    // ② 执行（按依赖拓扑序，共享黑板）
    const blackboard = [];
    for (const idx of topoOrder(plan)) {
      if (isStopped(run.id)) return finalizeStopped(run.id);
      const item = plan[idx];
      const agent = members.find((m) => m.id === item.agentId) || members[0];
      await runSubtask(run, team, agent, item, blackboard, kbIds);
    }

    if (isStopped(run.id)) return finalizeStopped(run.id);

    // ③ 整合
    const { result, byLLM: synBy } = await synthesize(run, team, members, blackboard);

    const fresh = q.get('SELECT by_llm FROM agent_runs WHERE id = ?', run.id);
    q.run("UPDATE agent_runs SET status = 'done', result = ?, by_llm = MAX(?, ?), ended_at = ? WHERE id = ?",
      result, fresh?.by_llm || 0, synBy ? 1 : 0, now(), run.id);
    q.run('UPDATE teams SET run_count = run_count + 1 WHERE id = ?', team.id);
    emit(run.id, 'done', q.get('SELECT * FROM agent_runs WHERE id = ?', run.id));
  } catch (e) {
    console.error('[agent] run failed', runId, e);
    q.run("UPDATE agent_runs SET status = 'failed', error = ?, ended_at = ? WHERE id = ?", String(e.message || e).slice(0, 200), now(), runId);
    emit(runId, 'error', { error: String(e.message || e).slice(0, 200) });
  } finally {
    STOPPED.delete(Number(runId));
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
