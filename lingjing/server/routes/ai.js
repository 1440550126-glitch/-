// 灵境AI · AI 能力接口：剧本 / 解析 / 图像 / 视频 / 内置创作 Agent
import { GET, POST, bad, notFound } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { jparse } from '../lib/util.js';
import { arkEnabled, arkChat } from '../lib/ark.js';
import { generateScript, parseScript, addEpisode, generateImage, generateExpressions, createVideoTask, pollTask, getProject, remakeViral, generateDubbing } from '../lib/pipeline.js';
import { toolSchemas, runTool } from '../lib/tools.js';
import { runAgent } from '../lib/agent.js';

POST('/api/ai/script', async ({ body }) => {
  const r = await generateScript({
    projectId: body.project_id, idea: body.idea, genre: body.genre,
    numScenes: body.num_scenes || 4, numEpisodes: body.num_episodes || 1, style: body.style, title: body.title, format: body.format || 'series'
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
  return { project: r.project, storyboard: r.storyboard, canvas_id: r.canvasId, by_llm: r.byLLM, warn: r.warn || '' };
});

POST('/api/ai/image', async ({ body }) => {
  return await generateImage({
    prompt: body.prompt, name: body.name, kind: body.kind || 'scene', ratio: body.ratio,
    projectId: body.project_id, nodeId: body.node_id, refImages: body.ref_images || [], tab: body.tab,
    model: body.model || ''
  });
});

// 爆款复刻：参考文案结构 → 新主题剧本
POST('/api/ai/remake', async ({ body }) => {
  return await remakeViral({
    reference: body.reference, topic: body.topic, projectId: body.project_id || '',
    genre: body.genre || '', numScenes: body.num_scenes || 4
  });
}, { maxBytes: 256 * 1024 });

// 配音：台词 → 语音（火山 TTS，未配置时报错引导）
POST('/api/ai/dub', async ({ body }) => {
  if (!body.project_id) throw bad('缺少 project_id');
  return await generateDubbing({ projectId: body.project_id, episode: body.episode || '', nodeId: body.node_id || '' });
});

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
  return { id: t.id, kind: t.kind, status: t.status, provider: t.provider, prompt: t.prompt, result: t.result, params: t.params, error: t.error || '', created_at: t.created_at };
});

GET('/api/ai/tasks', async ({ query }) => {
  const kind = query.get('kind') || '';
  const status = query.get('status') || '';
  let rows = q.all(`SELECT id, kind, status, provider, model, prompt, params, result, error, project_id, node_id, created_at FROM tasks ORDER BY created_at DESC LIMIT 120`);
  if (kind) rows = rows.filter((t) => t.kind === kind);
  if (status) rows = rows.filter((t) => status === 'active' ? ['queued', 'running'].includes(t.status) : t.status === status);
  return rows.map((t) => ({
    ...t, prompt: t.prompt.slice(0, 80),
    params: jparse(t.params, {}), result: jparse(t.result, {}), error: (t.error || '').slice(0, 160)
  }));
});

// 失败/卡住的视频任务重试（force 可对任意视频任务强制重出）
POST('/api/ai/task/:id/retry', async ({ params, body }) => {
  const t = q.get('SELECT * FROM tasks WHERE id = ?', params.id);
  if (!t) throw notFound('任务不存在');
  if (t.kind !== 'video') throw bad('只支持视频任务重试（图片是同步生成，直接重新生成即可）');
  if (!['failed'].includes(t.status) && !body?.force) throw bad('任务未失败；如需强制重出请传 force: true');
  const p = jparse(t.params, {});
  return await createVideoTask({
    prompt: t.prompt, imageUrl: p.imageUrl || '', lastImageUrl: p.lastImageUrl || '',
    duration: p.duration || 5, ratio: p.ratio, projectId: t.project_id, nodeId: t.node_id,
    name: p.name, order: p.order, model: p.model || '', resolution: p.resolution || ''
  });
});

// ---------------- 内置创作 Agent（意图分析 → 思考规划 → 智能调度，见 lib/agent.js） ----------------
POST('/api/ai/agent', async ({ body }) => {
  const messages = Array.isArray(body.messages) ? body.messages.filter((m) => m?.role && typeof m.content === 'string') : null;
  if (!messages?.length) throw bad('缺少 messages');
  if (body.project_id) getProject(body.project_id);
  return await runAgent(messages, body.project_id || '');
}, { maxBytes: 256 * 1024 });
