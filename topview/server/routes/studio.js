// 爆款工厂 · Web REST（给前端工作台用；与 Agent API 共用同一套管线）
import { GET, POST, DEL, bad } from '../lib/httpx.js';
import { q, getSetting, setSetting } from '../lib/db.js';
import { now } from '../lib/util.js';
import { cfg, llmEnabled, imageEnabled, videoEnabled } from '../lib/llm.js';
import { TONES, STYLES } from '../lib/adscript.js';
import { LANGS } from '../lib/i18n.js';
import {
  createProject, getProject, projectOut, listProjects, parseProduct, productToAd,
  generateMedia, getTask, generateDubbing, localizeProject, exportSrt, usageStats, touchProject
} from '../lib/pipeline.js';
import { buildAdScript } from '../lib/adscript.js';

GET('/api/bootstrap', async () => ({
  app: '爆款工厂 · AI 电商带货视频',
  capabilities: { script: llmEnabled() ? 'llm' : 'local', image: imageEnabled() ? 'provider' : 'local', video: videoEnabled() ? 'provider' : 'local' },
  tones: TONES, styles: STYLES.map((s) => ({ id: s.id, name: s.name })), langs: LANGS, ratios: ['9:16', '16:9', '1:1', '4:5'],
  agent_token: getSetting('agent_token', '')
}));

// ---- 项目 ----
GET('/api/projects', async () => ({ projects: listProjects() }));
POST('/api/projects', async ({ body }) => projectOut(createProject(body)));
GET('/api/projects/:id', async ({ params }) => projectOut(getProject(params.id)));
DEL('/api/projects/:id', async ({ params }) => { getProject(params.id); touchProject(params.id, { deleted_at: now() }); return { ok: true }; });

// ---- 商品 → 广告片 ----
POST('/api/commerce/parse', async ({ body }) => {
  if (!body.url) throw bad('请填写商品页链接');
  return await parseProduct(body.url);
}, { maxBytes: 8 * 1024 });

POST('/api/commerce/product-to-video', async ({ body }) => await productToAd(body), { maxBytes: 256 * 1024 });

// 重新生成脚本
POST('/api/projects/:id/script', async ({ params, body }) => {
  const p = getProject(params.id);
  const product = projectOut(p).product;
  const { storyboard, byLLM } = await buildAdScript(product, { tone: body.tone || p.tone, lang: body.lang || p.lang, ratio: p.ratio, duration: p.duration, style: p.style });
  touchProject(params.id, { storyboard: JSON.stringify(storyboard), status: 'scripted', ...(body.tone ? { tone: body.tone } : {}) });
  return { project: projectOut(getProject(params.id)), by_llm: byLLM };
});

// ---- 生成画面/视频 ----
POST('/api/projects/:id/media', async ({ params, body }) => await generateMedia(params.id, { only: body.only || 'all' }));
GET('/api/task/:id', async ({ params }) => await getTask(params.id));

// ---- 配音 / 本地化 / 导出 ----
POST('/api/projects/:id/dubbing', async ({ params }) => generateDubbing(params.id));
POST('/api/projects/:id/localize', async ({ params, body }) => await localizeProject(params.id, body.langs || []));
GET('/api/projects/:id/srt', async ({ params, query }) => exportSrt(params.id, query.get('lang') || ''));

// ---- 资产 / 统计 ----
GET('/api/assets', async ({ query }) => {
  const pid = query.get('project_id');
  return {
    assets: pid
      ? q.all('SELECT id,kind,name,url,lang,source,created_at FROM assets WHERE project_id=? ORDER BY created_at DESC LIMIT 200', pid)
      : q.all('SELECT id,kind,name,url,lang,source,project_id,created_at FROM assets ORDER BY created_at DESC LIMIT 100')
  };
});
GET('/api/usage', async () => usageStats());

// ---- 设置 ----
const SETTABLE = ['ark_api_key', 'ark_base_url', 'model_chat', 'model_image', 'model_video', 'openai_api_key', 'watermark'];
GET('/api/settings', async () => {
  const c = cfg();
  return {
    ark_api_key_set: !!c.apiKey, openai_api_key_set: !!c.openaiKey,
    ark_base_url: c.baseUrl, model_chat: c.modelChat, model_image: c.modelImage, model_video: c.modelVideo,
    watermark: c.watermark, capabilities: { script: llmEnabled() ? 'llm' : 'local', image: imageEnabled() ? 'provider' : 'local', video: videoEnabled() ? 'provider' : 'local' },
    agent_token: getSetting('agent_token', '')
  };
});
POST('/api/settings', async ({ body }) => {
  for (const k of SETTABLE) if (body[k] !== undefined) setSetting(k, body[k]);
  return { ok: true };
}, { maxBytes: 16 * 1024 });
