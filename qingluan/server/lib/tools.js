// 青鸾 · Agent 工具注册表
// 同一套工具同时服务：① MCP Server（mcp/server.mjs） ② HTTP Agent API（/api/agent/v1）
// ③ 内置创作 Agent（/api/ai/agent 的函数调用循环）
import { q, getSetting } from './db.js';
import { jparse, micro2yuan, now } from './util.js';
import { arkEnabled, cfg } from './ark.js';
import {
  createProject, getProject, projectOut, touchProject, generateScript, parseScript,
  getCanvas, patchCanvasNode, generateImage, createVideoTask, pollTask, addAsset
} from './pipeline.js';
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
    description: 'AI 生成短剧剧本并存入项目（未传 project_id 时自动新建项目）。返回剧本全文。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id（可选）'), idea: str('核心创意'), genre: str('类型'), style: str('画面风格'), num_scenes: num('场次数量 2-8，默认 4'), title: str('剧名（可选）') }
    },
    async execute(a) {
      const r = await generateScript({ projectId: a.project_id, idea: a.idea, genre: a.genre, style: a.style, numScenes: a.num_scenes || 4, title: a.title });
      return { project_id: r.project.id, title: r.project.title, by_llm: r.byLLM, script: r.script };
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
    name: 'generate_video',
    description: '生成视频（异步）：文生视频或首帧图生视频。返回 task_id，用 get_task 轮询直到 succeeded。',
    input_schema: {
      type: 'object',
      properties: {
        prompt: str('视频动态提示词（画面内容+运镜）'),
        image_url: str('首帧图地址（可选，强烈建议传，画面更稳定）'),
        duration: num('时长（秒）2-12，默认 5'), ratio: str('画幅', { enum: ['16:9', '9:16', '1:1', '4:3', '21:9'] }),
        project_id: str('项目 id（可选）'), node_id: str('画布分镜节点 id（可选，回写视频）'), name: str('名称')
      },
      required: ['prompt']
    },
    async execute(a) {
      return await createVideoTask({ prompt: a.prompt, imageUrl: a.image_url, duration: a.duration || 5, ratio: a.ratio, projectId: a.project_id, nodeId: a.node_id, name: a.name });
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
      const allowed = ['name', 'desc', 'prompt', 'role', 'action', 'dialogue', 'duration', 'shot_type', 'camera', 'image_prompt', 'video_prompt', 'image', 'video', 'x', 'y'];
      const clean = Object.fromEntries(Object.entries(patch || {}).filter(([k]) => allowed.includes(k)));
      if (!Object.keys(clean).length) throw bad(`没有可修改字段，允许：${allowed.join('/')}`);
      const node = patchCanvasNode(p.canvas_id, node_id, clean);
      return { id: node.id, type: node.type, ...node.data };
    }
  },
  {
    name: 'generate_storyboard_media',
    description: '按分镜批量生成：target=images 为所有缺图的角色/场景/道具/分镜生成图片（同步）；target=videos 为所有有首帧图的分镜创建视频任务（异步，返回 task_ids）。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), target: str('生成目标', { enum: ['images', 'videos'] }), limit: num('本次最多处理数量，默认 8') },
      required: ['project_id', 'target']
    },
    async execute({ project_id, target, limit = 8 }) {
      const p = getProject(project_id);
      if (!p.canvas_id) throw bad('项目还没有画布，先调用 parse_script');
      const c = getCanvas(p.canvas_id);
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
