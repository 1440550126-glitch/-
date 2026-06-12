// 青鸾 · AI 能力接口：剧本 / 解析 / 图像 / 视频 / 内置创作 Agent
import { GET, POST, bad } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { jparse } from '../lib/util.js';
import { arkEnabled, arkChat } from '../lib/ark.js';
import { generateScript, parseScript, addEpisode, generateImage, generateExpressions, createVideoTask, pollTask, getProject, remakeViral } from '../lib/pipeline.js';
import { toolSchemas, runTool } from '../lib/tools.js';

POST('/api/ai/script', async ({ body }) => {
  const r = await generateScript({
    projectId: body.project_id, idea: body.idea, genre: body.genre,
    numScenes: body.num_scenes || 4, numEpisodes: body.num_episodes || 1, style: body.style, title: body.title
  });
  return { project: { ...r.project, storyboard: jparse(r.project.storyboard, null) }, script: r.script, by_llm: r.byLLM };
});

// 续写一集（追加到剧本结尾并自动重新解析）
POST('/api/ai/episode', async ({ body }) => {
  if (!body.project_id) throw bad('缺少 project_id');
  const r = await addEpisode({ projectId: body.project_id, idea: body.idea || '' });
  return { episode_order: r.episodeOrder, project: r.project, storyboard: r.storyboard, by_llm: r.byLLM };
});

POST('/api/ai/parse', async ({ body }) => {
  if (!body.project_id) throw bad('缺少 project_id');
  const r = await parseScript({ projectId: body.project_id });
  return { project: r.project, storyboard: r.storyboard, canvas_id: r.canvasId, by_llm: r.byLLM };
});

POST('/api/ai/image', async ({ body }) => {
  return await generateImage({
    prompt: body.prompt, name: body.name, kind: body.kind || 'scene', ratio: body.ratio,
    projectId: body.project_id, nodeId: body.node_id, refImages: body.ref_images || [], tab: body.tab
  });
});

// 爆款复刻：参考文案结构 → 新主题剧本
POST('/api/ai/remake', async ({ body }) => {
  return await remakeViral({
    reference: body.reference, topic: body.topic, projectId: body.project_id || '',
    genre: body.genre || '', numScenes: body.num_scenes || 4
  });
}, { maxBytes: 256 * 1024 });

// 角色表情集（多情绪定妆照）
POST('/api/ai/expressions', async ({ body }) => {
  if (!body.project_id || !body.node_id) throw bad('缺少 project_id / node_id');
  return await generateExpressions({ projectId: body.project_id, nodeId: body.node_id, emotions: body.emotions || [] });
});

POST('/api/ai/video', async ({ body }) => {
  return await createVideoTask({
    prompt: body.prompt, imageUrl: body.image_url, lastImageUrl: body.last_image_url || '',
    duration: body.duration || 5, ratio: body.ratio,
    projectId: body.project_id, nodeId: body.node_id, name: body.name, order: body.order,
    model: body.model || '', resolution: body.resolution || ''
  });
});

GET('/api/ai/task/:id', async ({ params }) => {
  const t = await pollTask(params.id);
  return { id: t.id, kind: t.kind, status: t.status, provider: t.provider, result: t.result, params: t.params, error: t.error || '', created_at: t.created_at };
});

GET('/api/ai/tasks', async () => {
  return q.all(`SELECT id, kind, status, provider, prompt, project_id, node_id, created_at FROM tasks ORDER BY created_at DESC LIMIT 50`)
    .map((t) => ({ ...t, prompt: t.prompt.slice(0, 60) }));
});

// ---------------- 内置创作 Agent ----------------
// 方舟可用：大模型函数调用循环（与 MCP 同一套工具）；未配 Key：本地意图规则，保证可演示。
const AGENT_SYSTEM = () => `你是「青鸾」短剧创作工作室的驻场创作 Agent。你可以调用工具完成：建项目、写剧本、解析分镜、生成角色/场景图、生成分镜视频、改画布节点、查任务与成本。
原则：
1. 先用 studio_overview / get_project 了解现状再动手；
2. 创作类请求按「项目 → 剧本 → parse_script 解析 → 图 → 视频」推进，一次回复内尽量多完成几步；
3. 视频是异步任务，创建后告诉用户任务号即可，不必反复轮询；
4. 回复用简洁中文，说明你做了什么、产出在哪（项目/画布/资产库）、建议的下一步。`;

function toArkTools() {
  return toolSchemas().map((t) => ({
    type: 'function',
    function: { name: t.name, description: t.description, parameters: t.input_schema }
  }));
}

async function agentLLM(messages, projectId) {
  const msgs = [
    { role: 'system', content: AGENT_SYSTEM() + (projectId ? `\n当前上下文项目 project_id：${projectId}（用户说"这个项目"即指它）` : '') },
    ...messages.slice(-12)
  ];
  const steps = [];
  for (let i = 0; i < 8; i++) {
    const r = await arkChat({ feature: 'agent', messages: msgs, tools: toArkTools(), temperature: 0.5, maxTokens: 2500 });
    if (!r.toolCalls?.length) {
      return { reply: r.text, steps };
    }
    msgs.push({ role: 'assistant', content: r.text || '', tool_calls: r.toolCalls });
    for (const call of r.toolCalls) {
      const name = call.function?.name;
      const args = jparse(call.function?.arguments, {});
      let result;
      let ok = true;
      try { result = await runTool(name, args, 'builtin'); }
      catch (e) { ok = false; result = { error: e.message }; }
      steps.push({ tool: name, args, ok, summary: summarize(result) });
      msgs.push({ role: 'tool', tool_call_id: call.id, content: JSON.stringify(result).slice(0, 6000) });
    }
  }
  return { reply: '步骤较多，本轮先执行到这里。继续说"接着做"我会接续推进。', steps };
}

function summarize(r) {
  if (r == null) return '';
  const s = typeof r === 'string' ? r : JSON.stringify(r);
  return s.length > 160 ? s.slice(0, 160) + '…' : s;
}

// 本地意图兜底：覆盖演示主路径
async function agentLocal(text, projectId) {
  const steps = [];
  const run = async (tool, args) => {
    const result = await runTool(tool, args, 'builtin');
    steps.push({ tool, args, ok: true, summary: summarize(result) });
    return result;
  };
  const latestProject = () => projectId || q.get('SELECT id FROM projects ORDER BY updated_at DESC LIMIT 1')?.id;

  try {
    if (/(创建|新建|开个|来一个).*(项目|短剧)|^新项目/.test(text)) {
      const title = (text.match(/[《"「']([^》"」']{2,20})[》"」']/) || [])[1] || '';
      const genre = (text.match(/(都市逆袭|赘婿战神|甜宠虐恋|甜宠|悬疑反转|悬疑|古装宫斗|古装|废土科幻|科幻)/) || [])[1] || '';
      const p = await run('create_project', { title, idea: text.slice(0, 200), genre });
      if (/剧本/.test(text)) {
        await run('generate_script', { project_id: p.id, idea: text.slice(0, 200), genre });
        return { reply: `已创建项目《${p.title}》并生成了剧本（本地引擎）。下一步可以说："解析分镜"。`, steps };
      }
      return { reply: `已创建项目《${p.title}》（id: ${p.id}）。可以继续说："给它写一个${genre || '都市逆袭'}剧本"。`, steps };
    }
    if (/(写|生成|来).*(剧本)/.test(text)) {
      const pid = latestProject();
      const genre = (text.match(/(都市逆袭|赘婿战神|甜宠虐恋|甜宠|悬疑反转|悬疑|古装宫斗|古装|废土科幻|科幻)/) || [])[1] || '';
      const r = await run('generate_script', { project_id: pid, idea: text.slice(0, 300), genre });
      return { reply: `剧本已生成并写入项目《${r.title}》。接下来说"解析分镜"，我会拆出角色/场景/镜头并搭好画布。`, steps };
    }
    if (/(解析|拆|分镜|画布)/.test(text)) {
      const pid = latestProject();
      if (!pid) return { reply: '还没有项目。先说"创建一个项目并写剧本"。', steps };
      const r = await run('parse_script', { project_id: pid });
      return { reply: `解析完成：${r.characters.length} 个角色、${r.scenes.length} 个场景、${r.shots.length} 个分镜，画布已生成（canvas: ${r.canvas_id}）。下一步："生成全部图片"。`, steps };
    }
    if (/(生成|出).*(图|形象|首帧|场景图)/.test(text)) {
      const pid = latestProject();
      if (!pid) return { reply: '还没有项目，先创建项目并解析分镜。', steps };
      const r = await run('generate_storyboard_media', { project_id: pid, target: 'images', limit: 12 });
      return { reply: `已生成 ${r.generated} 张图（角色/场景/分镜首帧），画布与资产库已更新。继续说"生成全部视频"即可。`, steps };
    }
    if (/(生成|出).*(视频|成片)/.test(text)) {
      const pid = latestProject();
      if (!pid) return { reply: '还没有项目，先创建项目并解析分镜。', steps };
      const r = await run('generate_storyboard_media', { project_id: pid, target: 'videos', limit: 12 });
      return { reply: `已为 ${r.created_tasks} 个分镜创建视频任务，画布上会实时显示进度（本地模式数秒内完成）。`, steps };
    }
    if (/(状态|进度|怎么样|成本|花了)/.test(text)) {
      const r = await run('studio_overview', {});
      return { reply: `当前：${r.projects} 个项目、${r.assets} 个资产、${r.running_tasks} 个进行中任务；累计成本 ¥${r.total_cost_yuan}（${r.provider}）。`, steps };
    }
    return {
      reply: '我是青鸾创作 Agent（当前为本地规则模式，配置方舟 Key 后将由大模型驱动）。可以试试：\n· "创建一个都市逆袭项目并写剧本"\n· "解析分镜" → "生成全部图片" → "生成全部视频"\n· "现在进度怎么样"',
      steps
    };
  } catch (e) {
    return { reply: `执行出错：${e.message}`, steps };
  }
}

POST('/api/ai/agent', async ({ body }) => {
  const messages = Array.isArray(body.messages) ? body.messages.filter((m) => m?.role && typeof m.content === 'string') : null;
  if (!messages?.length) throw bad('缺少 messages');
  if (body.project_id) getProject(body.project_id);
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')?.content || '';

  if (arkEnabled()) {
    try {
      const r = await agentLLM(messages, body.project_id);
      return { ...r, by_llm: true };
    } catch (e) {
      console.warn('[agent] 方舟失败，落本地意图：', e.message);
    }
  }
  const r = await agentLocal(lastUser, body.project_id);
  return { ...r, by_llm: false };
}, { maxBytes: 256 * 1024 });
