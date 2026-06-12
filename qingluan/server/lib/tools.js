// 青鸾 · Agent 工具注册表
// 同一套工具同时服务：① MCP Server（mcp/server.mjs） ② HTTP Agent API（/api/agent/v1）
// ③ 内置创作 Agent（/api/ai/agent 的函数调用循环）
import { q, getSetting } from './db.js';
import { jparse, micro2yuan, now } from './util.js';
import { arkEnabled, cfg } from './ark.js';
import {
  createProject, getProject, projectOut, touchProject, generateScript, parseScript, addEpisode,
  getCanvas, patchCanvasNode, generateImage, generateExpressions, createVideoTask, pollTask, addAsset, remakeViral, generateDubbing, checkConsistency
} from './pipeline.js';
import { STYLES, STYLE_CATS } from './styles.js';
import { bad } from './httpx.js';

const str = (desc, extra = {}) => ({ type: 'string', description: desc, ...extra });
const num = (desc) => ({ type: 'number', description: desc });

function shotSummary(sb) {
  return (sb?.shots || []).map((s) => ({ key: s.key, order: s.order, scene: s.scene, action: s.action.slice(0, 40), dialogue: s.dialogue.slice(0, 30), duration: s.duration }));
}

export const TOOLS = [
  {
    name: 'studio_overview',
    description: '查看工作室总览：项目/资产/任务数量、模型接入状态、累计成本。建议每次会话先调用以了解现状。',
    input_schema: { type: 'object', properties: {} },
    execute() {
      const cost = q.get('SELECT COALESCE(SUM(cost_micro),0) c FROM usage_logs')?.c || 0;
      return {
        app: '青鸾 · AI 短剧创作工坊',
        provider: arkEnabled() ? `火山方舟（${cfg().modelChat} / ${cfg().modelImage} / ${cfg().modelVideo}）` : '本地规则引擎（未配置方舟 Key，结果为占位预览）',
        projects: q.get('SELECT COUNT(*) c FROM projects')?.c || 0,
        assets: q.get('SELECT COUNT(*) c FROM assets')?.c || 0,
        running_tasks: q.get(`SELECT COUNT(*) c FROM tasks WHERE status IN ('queued','running')`)?.c || 0,
        total_cost_yuan: micro2yuan(cost),
        recent_projects: q.all('SELECT id, title, status, updated_at FROM projects ORDER BY updated_at DESC LIMIT 5')
      };
    }
  },
  {
    name: 'list_projects',
    description: '列出全部短剧项目（id、标题、状态、画布 id）。',
    input_schema: { type: 'object', properties: {} },
    execute() {
      return q.all('SELECT id, title, genre, ratio, status, canvas_id, created_at, updated_at FROM projects ORDER BY updated_at DESC LIMIT 50');
    }
  },
  {
    name: 'create_project',
    description: '创建一个新的短剧项目。',
    input_schema: {
      type: 'object',
      properties: { title: str('项目标题'), idea: str('核心创意/一句话故事'), genre: str('类型，如：都市逆袭/甜宠虐恋/悬疑反转/古装宫斗/废土科幻'), style: str('画面风格，如：美式复古好莱坞'), ratio: str('画幅', { enum: ['16:9', '9:16', '1:1', '4:3', '21:9'] }) }
    },
    execute(a) { return projectOut(createProject(a)); }
  },
  {
    name: 'get_project',
    description: '查看项目详情：剧本全文、结构化分镜（storyboard）、画布 id。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    execute({ project_id }) { return projectOut(getProject(project_id)); }
  },
  {
    name: 'update_project',
    description: '修改项目属性：标题/类型/画面风格/画幅/创意。风格建议先用 list_styles 查可选项（也可直接传自定义风格提示词）。改风格后新生成的图/视频自动套用。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), title: str('标题'), genre: str('类型'), style: str('风格名（见 list_styles）或自定义风格提示词'), ratio: str('画幅', { enum: ['16:9', '9:16', '1:1', '4:3', '21:9'] }), idea: str('核心创意'), seed: num('一致性种子（同项目出图共用，改它会整体换画面基调）') },
      required: ['project_id']
    },
    execute({ project_id, ...rest }) {
      getProject(project_id);
      const fields = {};
      for (const k of ['title', 'genre', 'style', 'ratio', 'idea']) {
        if (rest[k] !== undefined) fields[k] = String(rest[k]).slice(0, k === 'idea' ? 2000 : 300);
      }
      if (rest.seed !== undefined) fields.seed = Math.max(0, Math.floor(Number(rest.seed) || 0));
      if (!Object.keys(fields).length) throw bad('没有可更新字段');
      touchProject(project_id, fields);
      return projectOut(getProject(project_id));
    }
  },
  {
    name: 'list_styles',
    description: '查看风格库：可用的画面风格预设（电影感/真人/2D/3D），返回风格名与提示词。用 update_project 把风格名设到项目上。',
    input_schema: { type: 'object', properties: { cat: str('分类', { enum: ['film', 'real', 'd2', 'd3'] }) } },
    execute({ cat } = {}) {
      return {
        cats: STYLE_CATS,
        styles: STYLES.filter((s) => !cat || s.cat === cat).map((s) => ({ name: s.name, cat: s.cat, prompt: s.prompt }))
      };
    }
  },
  {
    name: 'write_script',
    description: '把剧本全文写入项目（覆盖原剧本）。写入后需调用 parse_script 重新解析分镜。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id'), script: str('剧本全文') }, required: ['project_id', 'script'] },
    execute({ project_id, script }) {
      if (!script?.trim()) throw bad('剧本内容为空');
      getProject(project_id);
      touchProject(project_id, { script: String(script).slice(0, 60_000), status: 'draft' });
      return { ok: true, length: String(script).length };
    }
  },
  {
    name: 'generate_script',
    description: 'AI 生成短剧剧本并存入项目（未传 project_id 时自动新建项目）。支持多集（num_episodes）。返回剧本全文。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id（可选）'), idea: str('核心创意'), genre: str('类型'), style: str('画面风格'), num_scenes: num('每集场次数量 2-8，默认 4'), num_episodes: num('集数 1-6，默认 1'), title: str('剧名（可选）') }
    },
    async execute(a) {
      const r = await generateScript({ projectId: a.project_id, idea: a.idea, genre: a.genre, style: a.style, numScenes: a.num_scenes || 4, numEpisodes: a.num_episodes || 1, title: a.title });
      return { project_id: r.project.id, title: r.project.title, by_llm: r.byLLM, script: r.script };
    }
  },
  {
    name: 'remake_viral',
    description: '爆款复刻：解析一段参考爆款文案/剧本的钩子与节奏结构，套用到新主题生成剧本（未传 project_id 自动建项目）。返回结构分析与项目 id。',
    input_schema: {
      type: 'object',
      properties: {
        reference: str('参考爆款文案/剧本全文'), topic: str('你的新主题/产品/故事方向'),
        genre: str('类型（可选）'), project_id: str('项目 id（可选，写入已有项目）'), num_scenes: num('场次 2-8，默认 4')
      },
      required: ['reference', 'topic']
    },
    async execute(a) {
      const r = await remakeViral({ reference: a.reference, topic: a.topic, projectId: a.project_id || '', genre: a.genre || '', numScenes: a.num_scenes || 4 });
      return { project_id: r.project.id, title: r.project.title, by_llm: r.byLLM, analysis: r.analysis, script_length: r.script.length };
    }
  },
  {
    name: 'add_episode',
    description: '给项目续写新的一集（沿用已有人物与场景，追加到剧本结尾），并自动重新解析分镜与画布。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), idea: str('本集创意/剧情方向（可选）') },
      required: ['project_id']
    },
    async execute({ project_id, idea }) {
      const r = await addEpisode({ projectId: project_id, idea: idea || '' });
      return {
        episode_order: r.episodeOrder, by_llm: r.byLLM,
        episodes: r.storyboard.episodes,
        total_shots: r.storyboard.shots.length,
        new_episode_shots: r.storyboard.shots.filter((s) => s.episode === `e${r.episodeOrder}`).length
      };
    }
  },
  {
    name: 'parse_script',
    description: '把项目剧本解析成结构化分镜（角色/场景/道具/镜头），并自动生成节点画布。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    async execute({ project_id }) {
      const r = await parseScript({ projectId: project_id });
      return {
        project_id, canvas_id: r.canvasId, by_llm: r.byLLM,
        episodes: r.storyboard.episodes,
        characters: r.storyboard.characters.map((c) => ({ key: c.key, name: c.name, role: c.role })),
        scenes: r.storyboard.scenes.map((s) => ({ key: s.key, name: s.name })),
        props: r.storyboard.props.map((p) => ({ key: p.key, name: p.name })),
        shots: shotSummary(r.storyboard)
      };
    }
  },
  {
    name: 'list_assets',
    description: '查看资产库（素材/角色图/视频）。',
    input_schema: { type: 'object', properties: { tab: str('分类', { enum: ['material', 'character'] }), keyword: str('搜索关键词') } },
    execute({ tab, keyword } = {}) {
      let rows = q.all('SELECT id, tab, kind, name, url, prompt, source, project_id, created_at FROM assets ORDER BY created_at DESC LIMIT 100');
      if (tab) rows = rows.filter((r) => r.tab === tab);
      if (keyword) rows = rows.filter((r) => r.name.includes(keyword) || r.prompt.includes(keyword));
      return rows;
    }
  },
  {
    name: 'import_asset',
    description: '把一个外部图片/视频 URL 登记进资产库。',
    input_schema: {
      type: 'object',
      properties: { url: str('http(s) 或 data: 地址'), name: str('资产名'), tab: str('分类', { enum: ['material', 'character'] }), kind: str('类型', { enum: ['image', 'video'] }) },
      required: ['url', 'name']
    },
    execute({ url, name, tab = 'material', kind = 'image' }) {
      if (!/^(https?:|data:|\/uploads\/)/.test(url)) throw bad('url 需为 http(s)/data:/本站 uploads 地址');
      return addAsset({ tab, kind, name, url, source: 'upload' });
    }
  },
  {
    name: 'generate_image',
    description: '文生图：生成角色形象/场景/道具/分镜首帧。返回图片地址并自动入资产库；传 node_id 时同步写到画布节点上。',
    input_schema: {
      type: 'object',
      properties: {
        prompt: str('图片提示词（中文，越具体越好）'),
        name: str('名称（用于资产库展示）'),
        kind: str('用途', { enum: ['character', 'scene', 'prop', 'frame'] }),
        ratio: str('画幅', { enum: ['16:9', '9:16', '1:1', '4:3', '21:9'] }),
        project_id: str('项目 id（可选）'), node_id: str('画布节点 id（可选，回写图片）'),
        ref_images: { type: 'array', items: { type: 'string' }, description: '参考图地址（角色一致性/图生图，可选）' }
      },
      required: ['prompt']
    },
    async execute(a) {
      const r = await generateImage({ prompt: a.prompt, name: a.name, kind: a.kind || 'scene', ratio: a.ratio, projectId: a.project_id, nodeId: a.node_id, refImages: a.ref_images || [] });
      return { url: r.url, provider: r.provider, asset_id: r.asset.id, task_id: r.taskId };
    }
  },
  {
    name: 'generate_expressions',
    description: '为角色节点生成表情集：同一角色多种情绪定妆照（自动以基础形象为参考保持一致性），写入节点 variants 并入资产库。',
    input_schema: {
      type: 'object',
      properties: {
        project_id: str('项目 id'), node_id: str('角色节点 id（或角色 key 如 c1）'),
        emotions: { type: 'array', items: { type: 'string' }, description: '情绪列表（可选），默认 冷酷/愤怒/狂喜/悲伤/微笑/惊恐' }
      },
      required: ['project_id', 'node_id']
    },
    async execute({ project_id, node_id, emotions }) {
      return await generateExpressions({ projectId: project_id, nodeId: node_id, emotions: emotions || [] });
    }
  },
  {
    name: 'generate_video',
    description: '生成视频（异步）：文生视频或首帧图生视频。返回 task_id，用 get_task 轮询直到 succeeded。',
    input_schema: {
      type: 'object',
      properties: {
        prompt: str('视频动态提示词（画面内容+运镜）'),
        image_url: str('首帧图地址（可选，强烈建议传，画面更稳定）'),
        last_image_url: str('尾帧图地址（可选，配合首帧实现「一镜到底」自然过渡）'),
        duration: num('时长（秒）2-12，默认 5'), ratio: str('画幅', { enum: ['16:9', '9:16', '1:1', '4:3', '21:9'] }),
        model: str('视频模型 ID（可选，覆盖默认；可用 ID 见设置页模型列表）'),
        resolution: str('分辨率（可选）', { enum: ['480p', '720p', '1080p'] }),
        project_id: str('项目 id（可选）'), node_id: str('画布分镜节点 id（可选，回写视频）'), name: str('名称')
      },
      required: ['prompt']
    },
    async execute(a) {
      return await createVideoTask({ prompt: a.prompt, imageUrl: a.image_url, lastImageUrl: a.last_image_url || '', duration: a.duration || 5, ratio: a.ratio, projectId: a.project_id, nodeId: a.node_id, name: a.name, model: a.model || '', resolution: a.resolution || '' });
    }
  },
  {
    name: 'generate_dubbing',
    description: '配音：把带台词的分镜逐镜合成为语音（火山 TTS，需在设置页配置语音合成凭证），写回分镜节点并入资产库；放映室自动同步播放。可按集（episode）或单个分镜（node_id）。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), episode: str('只配该集，如 e1（可选）'), node_id: str('只配该分镜（可选）') },
      required: ['project_id']
    },
    async execute({ project_id, episode, node_id }) {
      return await generateDubbing({ projectId: project_id, episode: episode || '', nodeId: node_id || '' });
    }
  },
  {
    name: 'get_task',
    description: '查询生成任务状态（视频为异步任务）。status: running/succeeded/failed；succeeded 时 result.url 是产物地址。',
    input_schema: { type: 'object', properties: { task_id: str('任务 id') }, required: ['task_id'] },
    async execute({ task_id }) {
      const t = await pollTask(task_id);
      return { id: t.id, kind: t.kind, status: t.status, provider: t.provider, result: t.result, error: t.error || undefined };
    }
  },
  {
    name: 'get_canvas',
    description: '读取项目画布：全部节点（角色/场景/道具/分镜及其媒体状态）与连线。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    execute({ project_id }) {
      const p = getProject(project_id);
      if (!p.canvas_id) throw bad('项目还没有画布，先调用 parse_script');
      const c = getCanvas(p.canvas_id);
      return {
        canvas_id: c.id, name: c.name, ratio: c.ratio,
        nodes: c.nodes.map((n) => ({ id: n.id, type: n.type, x: n.x, y: n.y, ...n.data })),
        edges: c.edges
      };
    }
  },
  {
    name: 'update_node',
    description: '修改画布节点（名称/描述/提示词/台词/时长/位置等字段按需传）。',
    input_schema: {
      type: 'object',
      properties: {
        project_id: str('项目 id'), node_id: str('节点 id（或分镜 key 如 sh3）'),
        patch: { type: 'object', description: '要修改的字段，如 {"dialogue":"新台词","duration":6,"image_prompt":"..."}' }
      },
      required: ['project_id', 'node_id', 'patch']
    },
    execute({ project_id, node_id, patch }) {
      const p = getProject(project_id);
      if (!p.canvas_id) throw bad('项目还没有画布');
      const allowed = ['name', 'desc', 'prompt', 'role', 'action', 'dialogue', 'duration', 'shot_type', 'camera', 'emotion', 'image_prompt', 'video_prompt', 'image', 'video', 'x', 'y'];
      const clean = Object.fromEntries(Object.entries(patch || {}).filter(([k]) => allowed.includes(k)));
      if (!Object.keys(clean).length) throw bad(`没有可修改字段，允许：${allowed.join('/')}`);
      const node = patchCanvasNode(p.canvas_id, node_id, clean);
      return { id: node.id, type: node.type, ...node.data };
    }
  },
  {
    name: 'check_consistency',
    description: '画面一致性体检：扫描风格缺失、角色/场景缺定妆照、分镜未连线、提示词漏人名等会导致画面漂移的问题，返回评分（0-100）、统计与修复建议。批量生成前建议先调用并修复 err 级问题。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    execute({ project_id }) { return checkConsistency(project_id); }
  },
  {
    name: 'generate_storyboard_media',
    description: '按分镜批量生成：target=images 为所有缺图的角色/场景/道具/分镜生成图片（同步）；target=videos 为所有有首帧图的分镜创建视频任务（异步，返回 task_ids）。可用 episode 只处理某一集（如 "e2"）。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), target: str('生成目标', { enum: ['images', 'videos'] }), episode: str('只处理该集的分镜，如 e1/e2（可选，角色场景图不受限）'), limit: num('本次最多处理数量，默认 8') },
      required: ['project_id', 'target']
    },
    async execute({ project_id, target, episode = '', limit = 8 }) {
      const p = getProject(project_id);
      if (!p.canvas_id) throw bad('项目还没有画布，先调用 parse_script');
      const c = getCanvas(p.canvas_id);
      if (episode) c.nodes = c.nodes.filter((n) => n.type !== 'shot' || (n.data.episode || 'e1') === episode);
      const done = [];
      if (target === 'images') {
        const todo = c.nodes.filter((n) => !n.data.image && (n.data.prompt || n.data.image_prompt)).slice(0, limit);
        for (const n of todo) {
          const r = await generateImage({
            prompt: n.data.image_prompt || n.data.prompt, name: n.data.name,
            kind: n.type === 'shot' ? 'frame' : n.type, projectId: project_id, nodeId: n.id
          });
          done.push({ node_id: n.id, name: n.data.name, url: r.url });
        }
        return { generated: done.length, items: done, remaining: c.nodes.filter((n) => !n.data.image).length - done.length };
      }
      const todo = c.nodes.filter((n) => n.type === 'shot' && !n.data.video && n.data.task_status !== 'running').slice(0, limit);
      for (const n of todo) {
        const r = await createVideoTask({
          prompt: n.data.video_prompt || n.data.action, imageUrl: n.data.image, duration: n.data.duration,
          projectId: project_id, nodeId: n.id, name: n.data.name, order: n.data.order
        });
        done.push({ node_id: n.id, name: n.data.name, task_id: r.taskId });
      }
      return { created_tasks: done.length, items: done, hint: '用 get_task 轮询 task_id 直到 succeeded' };
    }
  },
  {
    name: 'run_workflow',
    description: '一键托管全流程工作流：剧本→解析→一致性体检→定妆照与首帧→分镜视频→配音→导出（TTS/ffmpeg 未配置的步骤自动跳过）。异步执行，返回 workflow_id，用 get_workflow 轮询进度。',
    input_schema: {
      type: 'object',
      properties: {
        project_id: str('项目 id'),
        episode: str('只跑某一集，如 e2（可选）'),
        steps: { type: 'array', items: { type: 'string', enum: ['script', 'parse', 'check', 'images', 'videos', 'dub', 'export'] }, description: '自定义步骤子集（可选，默认全流程）' }
      },
      required: ['project_id']
    },
    async execute({ project_id, episode, steps }) {
      const { startWorkflow } = await import('./workflow.js');
      const w = startWorkflow({ projectId: project_id, episode: episode || '', steps: steps || null });
      return { workflow_id: w.id, status: w.status, steps: w.steps.map((s) => s.label) };
    }
  },
  {
    name: 'get_workflow',
    description: '查询工作流进度：各步骤状态（pending/running/done/skipped/failed）与详情；status 为 succeeded/failed/cancelled 时结束。',
    input_schema: { type: 'object', properties: { workflow_id: str('工作流 id'), cancel: { type: 'boolean', description: '传 true 取消该工作流' } }, required: ['workflow_id'] },
    async execute({ workflow_id, cancel }) {
      const { getWorkflow, cancelWorkflow } = await import('./workflow.js');
      if (cancel) cancelWorkflow(workflow_id);
      const w = getWorkflow(workflow_id);
      return { id: w.id, status: w.status, error: w.error || undefined, steps: w.steps };
    }
  },
  {
    name: 'get_usage_stats',
    description: '查看用量与成本统计（按功能聚合，单位元）。',
    input_schema: { type: 'object', properties: {} },
    execute() {
      const rows = q.all(`SELECT feature, provider, COUNT(*) calls, SUM(prompt_tokens) ptok, SUM(completion_tokens) ctok,
        SUM(images) imgs, SUM(video_seconds) vsec, SUM(cost_micro) cost FROM usage_logs GROUP BY feature, provider ORDER BY cost DESC`);
      return {
        total_cost_yuan: micro2yuan(q.get('SELECT COALESCE(SUM(cost_micro),0) c FROM usage_logs')?.c || 0),
        by_feature: rows.map((r) => ({ ...r, cost_yuan: micro2yuan(r.cost), cost: undefined }))
      };
    }
  }
];

export const toolByName = new Map(TOOLS.map((t) => [t.name, t]));

/** 工具的公开 schema（给 MCP tools/list、OpenAPI、内置 Agent 用） */
export function toolSchemas() {
  return TOOLS.map((t) => ({ name: t.name, description: t.description, input_schema: t.input_schema }));
}

/** 执行工具并记录调用日志 */
export async function runTool(name, args = {}, channel = 'http') {
  const tool = toolByName.get(name);
  if (!tool) throw bad(`未知工具：${name}，可用：${TOOLS.map((t) => t.name).join(', ')}`);
  const t0 = now();
  try {
    const result = await tool.execute(args || {});
    q.run('INSERT INTO agent_logs (channel, tool, args, ok, ms, created_at) VALUES (?,?,?,?,?,?)',
      channel, name, JSON.stringify(args || {}).slice(0, 2000), 1, now() - t0, now());
    return result;
  } catch (e) {
    q.run('INSERT INTO agent_logs (channel, tool, args, ok, error, ms, created_at) VALUES (?,?,?,?,?,?,?)',
      channel, name, JSON.stringify(args || {}).slice(0, 2000), 0, String(e.message).slice(0, 300), now() - t0, now());
    throw e;
  }
}
