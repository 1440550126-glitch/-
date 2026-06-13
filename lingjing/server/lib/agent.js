// 灵境AI · 创作 Agent v2：意图分析 → 思考规划 → 智能调度 → 执行
// 方舟可用：两阶段（先分析意图出计划，再函数调用循环执行）；未配置：本地意图引擎（可解析复合指令、多步调度）。
import { q, getSetting } from './db.js';
import { jparse, clamp } from './util.js';
import { arkEnabled, arkChat } from './ark.js';
import { toolSchemas, runTool } from './tools.js';

// ---------- 可调参数（设置页持久化） ----------
export function agentParams() {
  return {
    temperature: clamp(Number(getSetting('agent_temperature', 0.5)), 0, 1.3),
    maxSteps: Math.round(clamp(Number(getSetting('agent_max_steps', 10)), 1, 24)),
    autorun: getSetting('agent_autorun', true) !== false,    // false = 只规划、等确认
    thinking: getSetting('agent_thinking', true) !== false,  // 是否展示思考过程
    planFirst: getSetting('agent_plan_first', true) !== false // 是否先做意图分析再执行
  };
}

const GENRES = ['末日生存', '都市逆袭', '赘婿战神', '甜宠虐恋', '甜宠', '悬疑反转', '悬疑', '古装宫斗', '古装', '废土科幻', '科幻', '战争', '武侠', '校园', '职场', '家庭伦理', '谍战', '悬疑惊悚'];
const STYLES = ['美式复古好莱坞', '末日废土', '赛博朋克', '国风水墨', '日式动漫', '3D皮克斯', '电影感', '港风', '胶片'];

/** 从自然语言里抽取创作要素 */
export function extractEntities(text) {
  const t = String(text || '');
  const title = (t.match(/[《"「'']([^》"」'']{2,24})[》"」'']/) || [])[1] || '';
  const genre = GENRES.find((g) => t.includes(g)) || '';
  const style = STYLES.find((s) => t.includes(s)) || (/电影|大片/.test(t) ? '电影感' : '');
  const epMatch = t.match(/(\d+)\s*(集|幕)/) || (/电影|长片|大电影/.test(t) ? [null, '1'] : null);
  const episodes = epMatch ? Math.min(8, Math.max(1, Number(epMatch[1]) || 1)) : 1;
  const movie = /电影|长片|大电影|90\s*分钟|一个半小时/.test(t);
  const ratio = /竖屏|9:16|手机/.test(t) ? '9:16' : /16:9|横屏|宽屏/.test(t) ? '16:9' : '';
  const scenes = (t.match(/(\d+)\s*场/) || [])[1];
  return { title, genre, style, episodes, movie, ratio, numScenes: scenes ? Number(scenes) : undefined };
}

/** 把用户的话拆成有序意图动作（复合指令支持："建项目写剧本并解析生成全部图片"） */
export function planFromText(text) {
  const t = String(text || '');
  const plan = [];
  const want = (re) => re.test(t);
  const wantsCreate = want(/创建|新建|开个|来一[部个]|做一[部个]|帮我(做|建|写)|新项目/);
  const wantsScript = want(/剧本|脚本|故事|写一[个篇段]/);
  const wantsParse = want(/解析|拆分|分镜|拆镜|搭画布|画布/);
  const wantsImages = want(/图|形象|定妆|首帧|场景图|画面/);
  const wantsVideos = want(/视频|成片|出片|片子|镜头视频/);
  const wantsDub = want(/配音|台词朗读|语音/);
  const wantsFull = want(/全流程|一键|全部搞定|从头到尾|一条龙|做完|搞定|帮我做一[部个].*(短剧|电影|片)/);
  const wantsStatus = want(/状态|进度|怎么样|成本|花了|多少钱|看看|总览/);

  if (wantsFull && (wantsCreate || wantsScript)) return ['run_workflow'];
  if (wantsStatus && !wantsCreate && !wantsScript) return ['studio_overview'];

  if (wantsCreate) plan.push('create_project');
  if (wantsScript || wantsCreate) plan.push('generate_script');
  if (wantsParse || ((wantsImages || wantsVideos) && (wantsCreate || wantsScript))) plan.push('parse_script');
  if (wantsImages) plan.push('images');
  if (wantsVideos) plan.push('videos');
  if (wantsDub) plan.push('dub');
  if (!plan.length) {
    if (wantsParse) plan.push('parse_script');
    else if (wantsStatus) plan.push('studio_overview');
  }
  return plan;
}

const summarize = (r) => {
  if (r == null) return '';
  const s = typeof r === 'string' ? r : JSON.stringify(r);
  return s.length > 160 ? s.slice(0, 160) + '…' : s;
};
const latestProjectId = (pid) => pid || q.get('SELECT id FROM projects WHERE deleted_at = 0 ORDER BY updated_at DESC LIMIT 1')?.id;

// ---------- 本地意图引擎（无 Key / 兜底）：真正会"思考"——先分析再分步调度 ----------
export async function localAgent(text, projectId) {
  const p = agentParams();
  const ent = extractEntities(text);
  const plan = planFromText(text);
  const steps = [];
  const run = async (tool, args) => {
    const result = await runTool(tool, args, 'builtin');
    steps.push({ tool, args, ok: true, summary: summarize(result) });
    return result;
  };

  // 思考：把分析结果讲清楚
  const thinkBits = [];
  if (ent.genre) thinkBits.push(`类型=${ent.genre}`);
  if (ent.movie) thinkBits.push('形态=电影/长片');
  else if (ent.episodes > 1) thinkBits.push(`集数=${ent.episodes}`);
  if (ent.style) thinkBits.push(`风格=${ent.style}`);
  if (ent.ratio) thinkBits.push(`画幅=${ent.ratio}`);
  const thinking = plan.length
    ? `意图分析：${thinkBits.join('、') || '创作类请求'}。\n规划步骤：${plan.map(planLabel).join(' → ')}。`
    : `这像是一次普通对话或我暂未识别出明确的创作指令。`;

  if (!plan.length) {
    return {
      thinking, plan: [], steps, intent: 'chat', by_llm: false,
      reply: '我是灵境AI 创作 Agent。告诉我你想做什么，我会先分析意图、规划步骤再动手。例如：\n· “做一部末日生存的电影，写剧本并解析分镜，把图都生成出来”\n· “给这个项目生成全部视频”\n· “现在进度怎么样”'
    };
  }
  if (!p.autorun) {
    return { thinking, plan: plan.map(planLabel), steps, intent: 'plan', by_llm: false, reply: `我已规划好 ${plan.length} 步：${plan.map(planLabel).join(' → ')}。回复“执行”我就开始；或在设置里开启「自动执行」。` };
  }

  try {
    let pid = latestProjectId(projectId);
    let created = null;
    const done = [];
    for (const act of plan.slice(0, p.maxSteps)) {
      if (act === 'studio_overview') { const r = await run('studio_overview', {}); done.push(`总览：${r.projects} 项目 / ${r.assets} 资产 / 进行中 ${r.running_tasks}`); continue; }
      if (act === 'run_workflow') {
        if (!pid) { created = await run('create_project', { title: ent.title, idea: text.slice(0, 300), genre: ent.genre, style: ent.style, ratio: ent.ratio || undefined }); pid = created.id; }
        const w = await run('run_workflow', { project_id: pid });
        return { thinking, plan: plan.map(planLabel), steps, intent: 'fullrun', by_llm: false, reply: `已为${created ? `新项目《${created.title}》` : '当前项目'}启动全流程托管（工作流 ${w.workflow_id}）：${w.steps.join(' → ')}。进度可在项目页「全流程」弹窗或任务中心查看。` };
      }
      if (act === 'create_project') { created = await run('create_project', { title: ent.title, idea: text.slice(0, 300), genre: ent.genre, style: ent.style, ratio: ent.ratio || undefined }); pid = created.id; done.push(`建项目《${created.title}》`); continue; }
      if (act === 'generate_script') {
        if (!pid) { created = await run('create_project', { idea: text.slice(0, 300), genre: ent.genre, style: ent.style }); pid = created.id; }
        const r = await run('generate_script', { project_id: pid, idea: text.slice(0, 300), genre: ent.genre, style: ent.style, format: ent.movie ? 'movie' : 'series', num_episodes: ent.movie ? 1 : ent.episodes, num_scenes: ent.numScenes });
        done.push(`写剧本《${r.title}》`); continue;
      }
      if (act === 'parse_script') { if (!pid) break; const r = await run('parse_script', { project_id: pid }); done.push(`解析：${r.characters.length}角色/${r.scenes.length}场景/${r.shots.length}分镜/${r.episodes?.length || 1}${r.episodes?.[0]?.title?.includes('幕') ? '幕' : '段'}`); continue; }
      if (act === 'images') { if (!pid) break; const r = await run('generate_storyboard_media', { project_id: pid, target: 'images', limit: 40 }); done.push(`出图 ${r.generated} 张`); continue; }
      if (act === 'videos') { if (!pid) break; const r = await run('generate_storyboard_media', { project_id: pid, target: 'videos', limit: 40 }); done.push(`创建视频任务 ${r.created_tasks} 个`); continue; }
      if (act === 'dub') { if (!pid) break; try { const r = await run('generate_dubbing', { project_id: pid }); done.push(`配音 ${r.dubbed} 镜`); } catch (e) { done.push(`配音跳过（${e.message.slice(0, 40)}）`); } continue; }
    }
    return { thinking, plan: plan.map(planLabel), steps, intent: 'execute', by_llm: false, project_id: pid, reply: `已完成：${done.join('；')}。${pid ? `项目 id：${pid}。` : ''}下一步可以说“生成全部视频”“配音”或“现在进度怎么样”。` };
  } catch (e) {
    return { thinking, plan: plan.map(planLabel), steps, intent: 'execute', by_llm: false, reply: `执行中出错：${e.message}` };
  }
}

function planLabel(a) {
  return { create_project: '建项目', generate_script: '写剧本', parse_script: '解析分镜', images: '生成图片', videos: '生成视频', dub: '配音', run_workflow: '全流程托管', studio_overview: '查看总览' }[a] || a;
}

// ---------- 方舟意图分析（思考阶段，返回结构化计划） ----------
const ANALYZE_SYSTEM = `你是创作 Agent 的"意图分析与规划"模块。读用户最新一句话，结合上下文，只输出 JSON：
{"intent":"create_full(一键成片)|create_part(部分步骤)|edit(改某节点/参数)|query(查询状态)|chat(闲聊)",
 "summary":"用一句话复述你对用户意图的理解（以'我理解你想…'开头）",
 "entities":{"title":"","genre":"","movie":true/false,"episodes":1,"style":"","ratio":"","target":"images/videos/both/none"},
 "plan":["有序的中文步骤，如 建项目/写剧本/解析分镜/生成全部图片/生成全部视频/配音/全流程托管/查看总览"],
 "need_confirm":false}
只输出 JSON，不要解释。`;

export async function analyzeIntentLLM(messages, projectId, entHint = '') {
  const ctx = messages.slice(-6).map((m) => `${m.role === 'user' ? '用户' : '助手'}：${m.content}`).join('\n');
  const r = await arkChat({
    feature: 'agent-analyze', system: ANALYZE_SYSTEM, json: true, temperature: 0.2, maxTokens: 1200,
    prompt: `${projectId ? `当前项目 id：${projectId}。\n` : ''}${entHint ? `参考要素（程序预抽取，供校正）：${entHint}。\n` : ''}对话：\n${ctx}\n\n请分析最新一句用户意图并规划。`
  });
  return jparse(String(r.text).replace(/```(json)?/gi, '').replace(/```/g, ''), null);
}

// ---------- 方舟执行（函数调用循环） ----------
const EXEC_SYSTEM = (plan) => `你是「灵境AI」短剧创作工作室的驻场创作 Agent，通过调用工具完成创作。
${plan ? `本轮规划：${plan.join(' → ')}。按规划推进，但可根据工具返回灵活调整。\n` : ''}原则：
1. 先了解现状（studio_overview / get_project）再动手；缺项目就先 create_project；
2. 创作链路：项目 → generate_script → parse_script → generate_storyboard_media(images) → generate_storyboard_media(videos)；想一键成片用 run_workflow；
3. 电影/长片：generate_script 传 format="movie"（六幕长片）；短剧传 format="series" 与用户集数；
4. 视频/工作流是异步，创建后告知任务号即可，不必反复轮询；
5. 回复简洁中文：说清做了什么、产出在哪、建议下一步。`;

function toArkTools() {
  return toolSchemas().map((t) => ({ type: 'function', function: { name: t.name, description: t.description, parameters: t.input_schema } }));
}

export async function arkAgent(messages, projectId) {
  const p = agentParams();
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')?.content || '';
  const ent = extractEntities(lastUser);   // 确定性要素抽取，作为对话模型的硬提示
  const entHint = [
    ent.genre && `类型=${ent.genre}`, ent.movie ? '形态=电影长片(format=movie)' : (ent.episodes > 1 ? `短剧${ent.episodes}集` : ''),
    ent.style && `风格=${ent.style}`, ent.ratio && `画幅=${ent.ratio}`
  ].filter(Boolean).join('，');

  let analysis = null;
  if (p.planFirst) {
    try { analysis = await analyzeIntentLLM(messages, projectId, entHint); } catch (e) { console.warn('[agent] 意图分析失败：', e.message); }
  }
  const thinking = analysis?.summary ? `${analysis.summary}${analysis.plan?.length ? `\n规划：${analysis.plan.join(' → ')}` : ''}` : (entHint ? `意图要素：${entHint}` : '');
  const plan = analysis?.plan || [];

  // 仅规划不执行
  if (!p.autorun || analysis?.need_confirm) {
    return { thinking, plan, steps: [], intent: analysis?.intent || 'plan', by_llm: true, reply: plan.length ? `我的计划：${plan.join(' → ')}。确认后我就开始（回复“执行”，或在设置开启自动执行）。` : (thinking || '请告诉我你想创作什么。') };
  }

  const msgs = [
    { role: 'system', content: EXEC_SYSTEM(plan) + (entHint ? `\n已识别意图要素：${entHint}——据此给工具传对参数（如电影务必 format="movie"）。` : '') + (projectId ? `\n当前上下文项目 project_id：${projectId}。` : '') },
    ...messages.slice(-12)
  ];
  const steps = [];
  for (let i = 0; i < p.maxSteps; i++) {
    const r = await arkChat({ feature: 'agent', messages: msgs, tools: toArkTools(), temperature: p.temperature, maxTokens: 2500 });
    if (!r.toolCalls?.length) {
      return { thinking, plan, steps, intent: analysis?.intent || 'execute', by_llm: true, reply: r.text || '完成。' };
    }
    msgs.push({ role: 'assistant', content: r.text || '', tool_calls: r.toolCalls });
    for (const call of r.toolCalls) {
      const name = call.function?.name;
      const args = jparse(call.function?.arguments, {});
      let result; let ok = true;
      try { result = await runTool(name, args, 'builtin'); }
      catch (e) { ok = false; result = { error: e.message }; }
      steps.push({ tool: name, args, ok, summary: summarize(result) });
      msgs.push({ role: 'tool', tool_call_id: call.id, content: JSON.stringify(result).slice(0, 6000) });
    }
  }
  return { thinking, plan, steps, intent: analysis?.intent || 'execute', by_llm: true, reply: `已执行 ${steps.length} 步（达到本轮步数上限 ${p.maxSteps}）。回复“继续”我接着推进，或在设置调大「单轮最大步数」。` };
}

export async function runAgent(messages, projectId) {
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')?.content || '';
  if (arkEnabled()) {
    try { return await arkAgent(messages, projectId); }
    catch (e) { console.warn('[agent] 方舟失败，落本地意图：', e.message); }
  }
  return await localAgent(lastUser, projectId);
}
