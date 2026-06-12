// 青鸾 · 工作台 REST 接口（本地单用户，无需登录；Agent 走 /api/agent/v1 带 Token）
import fs from 'node:fs';
import path from 'node:path';
import { GET, POST, PATCH, DEL, bad, notFound } from '../lib/httpx.js';
import { q, getSetting, setSetting, UPLOAD_DIR, DB_PATH } from '../lib/db.js';
import { uid, now, jparse, micro2yuan, token32 } from '../lib/util.js';
import { arkEnabled, cfg, arkChat, DEFAULTS, videoModelOptions } from '../lib/ark.js';
import { createProject, getProject, projectOut, touchProject, getCanvas } from '../lib/pipeline.js';
import { STYLES, STYLE_CATS } from '../lib/styles.js';

// ---------- 风格库 ----------
GET('/api/styles', async () => ({ cats: STYLE_CATS, styles: STYLES }));

// ---------- 启动信息 ----------
GET('/api/bootstrap', async () => {
  const c = cfg();
  return {
    app: { name: '青鸾', full: '青鸾 · AI 短剧创作工坊', slogan: '比云雀飞得更高', version: '0.1.0' },
    user_name: getSetting('user_name', '创作者'),
    ark: { enabled: arkEnabled(), base_url: c.baseUrl, model_chat: c.modelChat, model_image: c.modelImage, model_video: c.modelVideo },
    video_models: videoModelOptions(),
    video_resolutions: ['', '480p', '720p', '1080p'],
    agent_token: getSetting('agent_token', ''),
    mcp_path: path.join(path.dirname(new URL(import.meta.url).pathname), '..', '..', 'mcp', 'server.mjs'),
    stats: statsSummary()
  };
});

function statsSummary() {
  const total = q.get('SELECT COALESCE(SUM(cost_micro),0) c, COUNT(*) n FROM usage_logs');
  const dayStart = new Date(); dayStart.setHours(0, 0, 0, 0);
  const today = q.get('SELECT COALESCE(SUM(cost_micro),0) c, COUNT(*) n FROM usage_logs WHERE created_at >= ?', dayStart.getTime());
  return {
    projects: q.get('SELECT COUNT(*) c FROM projects')?.c || 0,
    assets: q.get('SELECT COUNT(*) c FROM assets')?.c || 0,
    canvases: q.get('SELECT COUNT(*) c FROM canvases')?.c || 0,
    running_tasks: q.get(`SELECT COUNT(*) c FROM tasks WHERE status IN ('queued','running')`)?.c || 0,
    cost_total_yuan: micro2yuan(total?.c || 0),
    cost_today_yuan: micro2yuan(today?.c || 0)
  };
}
GET('/api/stats', async () => ({
  ...statsSummary(),
  by_feature: q.all(`SELECT feature, provider, COUNT(*) calls, SUM(prompt_tokens) ptok, SUM(completion_tokens) ctok,
    SUM(images) imgs, SUM(video_seconds) vsec, SUM(cost_micro) cost_micro FROM usage_logs GROUP BY feature, provider ORDER BY cost_micro DESC LIMIT 30`),
  agent_logs: q.all('SELECT channel, tool, ok, error, ms, created_at FROM agent_logs ORDER BY id DESC LIMIT 30')
}));

// ---------- 项目 ----------
GET('/api/projects', async () =>
  q.all('SELECT id, title, genre, style, ratio, status, cover, canvas_id, created_at, updated_at FROM projects ORDER BY updated_at DESC LIMIT 100'));

POST('/api/projects', async ({ body }) => projectOut(createProject(body || {})));

GET('/api/projects/:id', async ({ params }) => projectOut(getProject(params.id)));

PATCH('/api/projects/:id', async ({ params, body }) => {
  getProject(params.id);
  const fields = {};
  for (const k of ['title', 'idea', 'genre', 'style', 'ratio', 'script', 'status', 'cover']) {
    if (body[k] !== undefined) fields[k] = String(body[k]).slice(0, k === 'script' ? 60_000 : 2000);
  }
  if (!Object.keys(fields).length) throw bad('没有可更新的字段');
  touchProject(params.id, fields);
  return projectOut(getProject(params.id));
}, { maxBytes: 512 * 1024 });

DEL('/api/projects/:id', async ({ params }) => {
  const p = getProject(params.id);
  if (p.canvas_id) q.run('DELETE FROM canvases WHERE id = ?', p.canvas_id);
  q.run('DELETE FROM projects WHERE id = ?', params.id);
  return { deleted: true };
});

// ---------- 资产 ----------
GET('/api/assets', async ({ query }) => {
  const tab = query.get('tab') || '';
  const kw = (query.get('q') || '').trim();
  let rows = q.all('SELECT * FROM assets ORDER BY created_at DESC LIMIT 300');
  if (tab) rows = rows.filter((r) => r.tab === tab);
  if (kw) rows = rows.filter((r) => r.name.includes(kw) || r.prompt.includes(kw));
  return rows;
});

POST('/api/assets', async ({ body }) => {
  const { name, url, tab = 'material', kind = 'image', prompt = '', project_id = '' } = body;
  if (!url || !/^(https?:|data:|\/uploads\/)/.test(url)) throw bad('url 需为 http(s)/data:/uploads 地址');
  const id = uid('a');
  q.run('INSERT INTO assets (id, tab, kind, name, url, prompt, source, project_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, tab, kind, String(name || '未命名').slice(0, 50), url, String(prompt).slice(0, 500), 'upload', project_id, now());
  return q.get('SELECT * FROM assets WHERE id = ?', id);
});

PATCH('/api/assets/:id', async ({ params, body }) => {
  const a = q.get('SELECT * FROM assets WHERE id = ?', params.id);
  if (!a) throw notFound('资产不存在');
  q.run('UPDATE assets SET name = ?, note = ?, tab = ? WHERE id = ?',
    String(body.name ?? a.name).slice(0, 50), String(body.note ?? a.note).slice(0, 200), body.tab === 'character' ? 'character' : body.tab === 'material' ? 'material' : a.tab, params.id);
  return q.get('SELECT * FROM assets WHERE id = ?', params.id);
});

DEL('/api/assets/:id', async ({ params }) => {
  q.run('DELETE FROM assets WHERE id = ?', params.id);
  return { deleted: true };
});

// 上传（JSON + dataURL，落盘到 var/qingluan-uploads）
const EXT_BY_MIME = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg', 'video/mp4': 'mp4', 'video/webm': 'webm' };
POST('/api/upload', async ({ body }) => {
  const { name = '上传素材', data, tab = 'material' } = body;
  const m = /^data:([\w/+.-]+);base64,(.+)$/s.exec(data || '');
  if (!m) throw bad('data 需为 base64 dataURL');
  const ext = EXT_BY_MIME[m[1]];
  if (!ext) throw bad(`暂不支持的类型：${m[1]}（支持 png/jpg/webp/gif/svg/mp4/webm）`);
  const buf = Buffer.from(m[2], 'base64');
  if (buf.length > 25 * 1024 * 1024) throw bad('文件超过 25MB');
  const fname = `${uid('up')}.${ext}`;
  fs.writeFileSync(path.join(UPLOAD_DIR, fname), buf);
  const kind = m[1].startsWith('video') ? 'video' : 'image';
  const id = uid('a');
  q.run('INSERT INTO assets (id, tab, kind, name, url, source, created_at) VALUES (?,?,?,?,?,?,?)',
    id, tab === 'character' ? 'character' : 'material', kind, String(name).slice(0, 50), `/uploads/${fname}`, 'upload', now());
  return q.get('SELECT * FROM assets WHERE id = ?', id);
}, { maxBytes: 36 * 1024 * 1024 });

// ---------- 画布 ----------
GET('/api/canvases', async () => {
  return q.all('SELECT id, project_id, name, ratio, created_at, updated_at FROM canvases ORDER BY updated_at DESC LIMIT 100')
    .map((c) => ({ ...c, node_count: (jparse(q.get('SELECT nodes FROM canvases WHERE id = ?', c.id)?.nodes, []) || []).length }));
});

POST('/api/canvases', async ({ body }) => {
  const id = uid('cv');
  q.run('INSERT INTO canvases (id, project_id, name, ratio, created_at, updated_at) VALUES (?,?,?,?,?,?)',
    id, body.project_id || '', String(body.name || '未命名画布').slice(0, 50), body.ratio || '16:9', now(), now());
  if (body.project_id) {
    const p = getProject(body.project_id, { required: false });
    if (p && !p.canvas_id) touchProject(p.id, { canvas_id: id });
  }
  return getCanvas(id);
});

GET('/api/canvases/:id', async ({ params }) => {
  const c = getCanvas(params.id);
  const project = c.project_id ? getProject(c.project_id, { required: false }) : null;
  return { ...c, project: project ? { id: project.id, title: project.title, status: project.status } : null };
});

PATCH('/api/canvases/:id', async ({ params, body }) => {
  const c = getCanvas(params.id);
  q.run('UPDATE canvases SET nodes = ?, edges = ?, doodles = ?, viewport = ?, name = ?, ratio = ?, updated_at = ? WHERE id = ?',
    JSON.stringify(Array.isArray(body.nodes) ? body.nodes : c.nodes),
    JSON.stringify(Array.isArray(body.edges) ? body.edges : c.edges),
    JSON.stringify(Array.isArray(body.doodles) ? body.doodles : c.doodles),
    JSON.stringify(body.viewport ?? c.viewport ?? null),
    String(body.name ?? c.name).slice(0, 50), body.ratio || c.ratio, now(), params.id);
  return { saved: true, at: now() };
}, { maxBytes: 4 * 1024 * 1024 });

DEL('/api/canvases/:id', async ({ params }) => {
  q.run('DELETE FROM canvases WHERE id = ?', params.id);
  q.run(`UPDATE projects SET canvas_id = '' WHERE canvas_id = ?`, params.id);
  return { deleted: true };
});

// ---------- 设置 ----------
const SETTING_KEYS = ['ark_base_url', 'model_chat', 'model_image', 'model_video', 'model_video_options', 'video_extra_args', 'watermark', 'price_chat_in', 'price_chat_out', 'price_image', 'price_video_sec', 'user_name', 'default_ratio'];

GET('/api/settings', async () => {
  const c = cfg();
  const key = c.apiKey;
  return {
    ark_api_key_masked: key ? `${key.slice(0, 4)}****${key.slice(-4)}` : '',
    ark_key_source: getSetting('ark_api_key', '') ? 'settings' : (process.env.ARK_API_KEY ? 'env' : ''),
    ark_base_url: c.baseUrl, model_chat: c.modelChat, model_image: c.modelImage, model_video: c.modelVideo,
    model_video_options: c.modelVideoOptions, video_extra_args: c.videoExtraArgs,
    watermark: c.watermark,
    price_chat_in: c.priceChatIn, price_chat_out: c.priceChatOut, price_image: c.priceImage, price_video_sec: c.priceVideoSec,
    user_name: getSetting('user_name', '创作者'),
    default_ratio: getSetting('default_ratio', '16:9'),
    defaults: DEFAULTS, db_path: DB_PATH, upload_dir: UPLOAD_DIR
  };
});

PATCH('/api/settings', async ({ body }) => {
  if (body.ark_api_key !== undefined) {
    const k = String(body.ark_api_key).trim();
    if (k && /^AKLT/i.test(k)) throw bad('AKLT 开头的是火山引擎 AccessKey，不能直接当方舟 API Key；请到方舟控制台「API Key 管理」创建（UUID 形态）');
    setSetting('ark_api_key', k);
  }
  for (const k of SETTING_KEYS) {
    if (body[k] !== undefined) setSetting(k, body[k]);
  }
  return { saved: true, ark_enabled: arkEnabled() };
});

POST('/api/settings/test', async () => {
  if (!arkEnabled()) throw bad('还没有配置方舟 API Key');
  const t0 = now();
  const r = await arkChat({ feature: 'settings-test', prompt: '回复两个字：在线', maxTokens: 16, temperature: 0, timeoutMs: 20_000 });
  return { ok: true, latency_ms: now() - t0, model: r.model, reply: r.text.slice(0, 40) };
});

POST('/api/settings/agent-token/rotate', async () => {
  const token = token32();
  setSetting('agent_token', token);
  return { agent_token: token };
});
