// 爆款工厂 · Agent 工具注册表
// 同一套工具同时服务：① MCP Server（mcp/server.mjs） ② HTTP Agent API（/api/agent/v1）
import { q } from './db.js';
import { now, micro2yuan } from './util.js';
import { bad } from './httpx.js';
import { llmEnabled, imageEnabled, videoEnabled, cfg } from './llm.js';
import {
  createProject, getProject, projectOut, listProjects, parseProduct, productToAd,
  generateMedia, getTask, generateDubbing, localizeProject, exportSrt, usageStats, touchProject
} from './pipeline.js';
import { buildAdScript } from './adscript.js';
import { TONES, STYLES } from './adscript.js';
import { LANGS } from './i18n.js';

const str = (desc, extra = {}) => ({ type: 'string', description: desc, ...extra });
const num = (desc) => ({ type: 'number', description: desc });
const arr = (desc) => ({ type: 'array', items: { type: 'string' }, description: desc });
const obj = (desc) => ({ type: 'object', description: desc });

export const TOOLS = [
  {
    name: 'studio_overview',
    description: '查看工作室总览：项目/资产/任务数量、模型接入状态、累计成本。建议每次会话先调用。',
    input_schema: { type: 'object', properties: {} },
    execute() {
      const cost = q.get('SELECT COALESCE(SUM(cost_micro),0) c FROM usage_logs')?.c || 0;
      const c = cfg();
      return {
        app: '爆款工厂 · AI 电商带货视频',
        model: llmEnabled() ? `已接入大模型（对话 ${c.modelChat} / 图 ${c.modelImage} / 视频 ${c.modelVideo}）` : '本地引擎模式（未配置 Key，产出为占位预览，零成本）',
        capabilities: { script: llmEnabled() ? 'llm' : 'local', image: imageEnabled() ? 'provider' : 'local', video: videoEnabled() ? 'provider' : 'local' },
        projects: q.get('SELECT COUNT(*) c FROM projects WHERE deleted_at=0')?.c || 0,
        assets: q.get('SELECT COUNT(*) c FROM assets')?.c || 0,
        running_tasks: q.get(`SELECT COUNT(*) c FROM tasks WHERE status IN ('queued','running')`)?.c || 0,
        total_cost_yuan: micro2yuan(cost),
        recent_projects: q.all('SELECT id,title,kind,status FROM projects WHERE deleted_at=0 ORDER BY updated_at DESC LIMIT 5')
      };
    }
  },
  {
    name: 'list_tones_styles',
    description: '列出可用的脚本套路(tone)、画面风格(style)、本地化语言(lang)，供创建广告时选择。',
    input_schema: { type: 'object', properties: {} },
    execute() {
      return {
        tones: TONES, styles: STYLES.map((s) => ({ id: s.id, name: s.name })),
        langs: LANGS, ratios: ['9:16', '16:9', '1:1', '4:5']
      };
    }
  },
  {
    name: 'list_projects',
    description: '列出全部广告项目（id、标题、类型、状态）。',
    input_schema: { type: 'object', properties: {} },
    execute() { return listProjects(); }
  },
  {
    name: 'get_project',
    description: '查看项目详情：商品信息、广告分镜脚本(storyboard)、各分镜的图/视频地址、已有本地化语言。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    execute({ project_id }) { return projectOut(getProject(project_id)); }
  },
  {
    name: 'scrape_product',
    description: '解析电商商品页链接，抽取公开商品信息（标题/品牌/价格/主图/卖点）。仅读取公开 OG/JSON-LD，抓不到时请改用手填。',
    input_schema: { type: 'object', properties: { url: str('商品页链接，http(s) 开头') }, required: ['url'] },
    async execute({ url }) { return await parseProduct(url); }
  },
  {
    name: 'create_ad',
    description: '创建一个空白广告项目（之后可用 generate_ugc_script 写脚本）。product 可传 {title,brand,price,currency,points[],images[]}。',
    input_schema: {
      type: 'object',
      properties: {
        title: str('项目标题'), kind: str('类型', { enum: ['ad', 'ugc'] }),
        tone: str('脚本套路 id（见 list_tones_styles）'), product: obj('商品信息'),
        lang: str('主语言，如 zh/en'), style: str('画面风格 id/名/自定义提示词'),
        ratio: str('画幅', { enum: ['9:16', '16:9', '1:1', '4:5'] }), duration: num('单镜时长秒 3-12')
      }
    },
    execute(a) { return projectOut(createProject(a)); }
  },
  {
    name: 'product_to_video',
    description: '【招牌】商品链接或商品信息 → 自动新建项目并生成竖屏广告分镜脚本（钩子→卖点→促单）。传 url 或 product 之一。生成后用 generate_media 出图/出片。',
    input_schema: {
      type: 'object',
      properties: {
        url: str('商品页链接（与 product 二选一）'), product: obj('手填商品信息 {title,brand,price,currency,points[],images[]}'),
        tone: str('脚本套路 id：ugc/painpoint/unboxing/koc/feature'), kind: str('类型', { enum: ['ad', 'ugc'] }),
        lang: str('输出语言，如 zh/en'), style: str('画面风格'), ratio: str('画幅', { enum: ['9:16', '16:9', '1:1', '4:5'] }),
        duration: num('单镜时长秒'), title: str('项目标题（可选）')
      }
    },
    async execute(a) {
      if (!a.url && !(a.product && (a.product.title || a.product.url))) throw bad('请提供 url 或 product（至少含标题）');
      return await productToAd(a);
    }
  },
  {
    name: 'generate_ugc_script',
    description: '为已有项目（或直接给商品信息）生成 UGC/口播广告脚本，写入项目。返回分镜脚本。',
    input_schema: {
      type: 'object',
      properties: { project_id: str('项目 id'), tone: str('脚本套路 id'), lang: str('语言') }
    },
    async execute({ project_id, tone, lang }) {
      const p = getProject(project_id);
      const product = projectOut(p).product;
      const { storyboard, byLLM } = await buildAdScript(product, { tone: tone || p.tone, lang: lang || p.lang, ratio: p.ratio, duration: p.duration, style: p.style });
      touchProject(project_id, { storyboard: JSON.stringify(storyboard), status: 'scripted', ...(tone ? { tone } : {}) });
      return { project_id, by_llm: byLLM, storyboard };
    }
  },
  {
    name: 'generate_media',
    description: '为项目的每个分镜生成画面与视频（本地引擎即时出占位；配了模型则图像直出、视频返回 pending 任务用 get_task 轮询）。only 可限定 image/video。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id'), only: str('范围', { enum: ['all', 'image', 'video'] }) }, required: ['project_id'] },
    async execute({ project_id, only }) { return await generateMedia(project_id, { only: only || 'all' }); }
  },
  {
    name: 'get_task',
    description: '查询生成任务状态/结果（供应商视频异步任务在此轮询推进并写回分镜）。',
    input_schema: { type: 'object', properties: { task_id: str('任务 id') }, required: ['task_id'] },
    async execute({ task_id }) { return await getTask(task_id); }
  },
  {
    name: 'generate_dubbing',
    description: '为项目口播配音。标准版用浏览器语音合成朗读（零成本），返回各分镜口播文本与时长；配 TTS 供应商后产出 mp3。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id') }, required: ['project_id'] },
    execute({ project_id }) { return generateDubbing(project_id); }
  },
  {
    name: 'localize_project',
    description: '把项目的字幕/口播翻译成多种语言并生成分语言 SRT（对标 TopView 多语言本地化）。配了模型走真实翻译，否则透传待译。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id'), langs: arr('目标语言 id 列表，如 ["en","ja","es"]') }, required: ['project_id', 'langs'] },
    async execute({ project_id, langs }) { return await localizeProject(project_id, langs); }
  },
  {
    name: 'export_srt',
    description: '导出项目某语言的 SRT 字幕（不传 lang 用主语言原文；其他语言需先 localize_project）。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id'), lang: str('语言 id') }, required: ['project_id'] },
    execute({ project_id, lang }) { return exportSrt(project_id, lang || ''); }
  },
  {
    name: 'list_assets',
    description: '列出项目产物（图/视频/字幕）。',
    input_schema: { type: 'object', properties: { project_id: str('项目 id（可选）') } },
    execute({ project_id } = {}) {
      return project_id
        ? q.all('SELECT id,kind,name,url,lang,source,created_at FROM assets WHERE project_id=? ORDER BY created_at DESC LIMIT 200', project_id)
        : q.all('SELECT id,kind,name,url,lang,source,project_id,created_at FROM assets ORDER BY created_at DESC LIMIT 100');
    }
  },
  {
    name: 'get_usage_stats',
    description: '查看累计模型调用与成本（按功能拆分）。',
    input_schema: { type: 'object', properties: {} },
    execute() { return usageStats(); }
  }
];

const byName = new Map(TOOLS.map((t) => [t.name, t]));
export const toolSchemas = () => TOOLS.map((t) => ({ name: t.name, description: t.description, input_schema: t.input_schema }));

export async function runTool(name, args = {}, channel = 'http') {
  const tool = byName.get(name);
  if (!tool) throw bad(`未知工具：${name}`);
  const t0 = now();
  try {
    const result = await tool.execute(args || {});
    q.run('INSERT INTO agent_logs (channel,tool,args,ok,ms,created_at) VALUES (?,?,?,?,?,?)',
      channel, name, JSON.stringify(args).slice(0, 2000), 1, now() - t0, now());
    return result;
  } catch (e) {
    q.run('INSERT INTO agent_logs (channel,tool,args,ok,error,ms,created_at) VALUES (?,?,?,?,?,?,?)',
      channel, name, JSON.stringify(args).slice(0, 2000), 0, String(e.message || e).slice(0, 500), now() - t0, now());
    throw e;
  }
}
