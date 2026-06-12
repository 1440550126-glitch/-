// 青鸾 · 工作台 REST 接口（本地单用户，无需登录；Agent 走 /api/agent/v1 带 Token）
import fs from 'node:fs';
import path from 'node:path';
import { GET, POST, PATCH, DEL, bad, notFound } from '../lib/httpx.js';
import { q, getSetting, setSetting, UPLOAD_DIR, DB_PATH } from '../lib/db.js';
import { uid, now, jparse, micro2yuan, token32 } from '../lib/util.js';
import { arkEnabled, cfg, arkChat, DEFAULTS, videoModelOptions } from '../lib/ark.js';
import { createProject, getProject, projectOut, touchProject, getCanvas, checkConsistency } from '../lib/pipeline.js';

// 画面一致性体检
GET('/api/projects/:id/consistency', async ({ params }) => checkConsistency(params.id));

// 工作流：一键托管全流程
POST('/api/workflows', async ({ body }) => {
  if (!body.project_id) throw bad('缺少 project_id');
  return startWorkflow({ projectId: body.project_id, episode: body.episode || '', steps: body.steps || null });
});
GET('/api/workflows/:id', async ({ params }) => getWorkflow(params.id));
POST('/api/workflows/:id/cancel', async ({ params }) => cancelWorkflow(params.id));
GET('/api/workflows', async ({ query }) => listWorkflows(query.get('project_id') || ''));
import { exportEpisode } from '../lib/export.js';
import { ttsCfg, ttsEnabled } from '../lib/tts.js';
import { startWorkflow, getWorkflow, cancelWorkflow, listWorkflows } from '../lib/workflow.js';
import { STYLES, STYLE_CATS } from '../lib/styles.js';

// 成片导出（拼接分镜 MP4，需本机有 ffmpeg）
POST('/api/projects/:id/export', async ({ params, body }) => {
  return await exportEpisode({ projectId: params.id, episode: body.episode || '' });
});

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
  q.all('SELECT id, title, genre, style, ratio, status, cover, canvas_id, created_at, updated_at FROM projects WHERE deleted_at = 0 ORDER BY updated_at DESC LIMIT 100'));

// 回收站
GET('/api/projects/trash', async () =>
  q.all('SELECT id, title, genre, cover, deleted_at FROM projects WHERE deleted_at > 0 ORDER BY deleted_at DESC LIMIT 100'));

POST('/api/projects/:id/restore', async ({ params }) => {
  getProject(params.id);
  q.run('UPDATE projects SET deleted_at = 0, updated_at = ? WHERE id = ?', now(), params.id);
  return projectOut(getProject(params.id));
});

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

DEL('/api/projects/:id', async ({ params, query }) => {
  const p = getProject(params.id);
  if (query.get('purge') === '1') {
    if (p.canvas_id) q.run('DELETE FROM canvases WHERE id = ?', p.canvas_id);
    q.run('DELETE FROM projects WHERE id = ?', params.id);
    return { deleted: true, purged: true };
  }
  q.run('UPDATE projects SET deleted_at = ?, updated_at = ? WHERE id = ?', now(), now(), params.id);
  return { deleted: true, trashed: true };
});

// ---------- 资产 ----------
GET('/api/assets', async ({ query }) => {
  const tab = query.get('tab') || '';
  const kw = (query.get('q') || '').trim();
  let rows = q.all('SELECT * FROM assets ORDER BY created_at DESC LIMIT 2000');
  if (tab) rows = rows.filter((r) => r.tab === tab);
  if (kw) rows = rows.filter((r) => r.name.includes(kw) || r.prompt.includes(kw));
  // paged=1 时分页返回（资产库页用）；否则保持旧数组形态（选择器/Agent 兼容）
  if (query.get('paged') === '1') {
    const offset = Math.max(0, Number(query.get('offset')) || 0);
    const limit = Math.min(120, Math.max(1, Number(query.get('limit')) || 48));
    return { total: rows.length, offset, limit, items: rows.slice(offset, offset + limit) };
  }
  return rows.slice(0, 300);
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
const EXT_BY_MIME = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg', 'video/mp4': 'mp4', 'video/webm': 'webm', 'audio/mpeg': 'mp3', 'audio/wav': 'wav' };
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
  const kind = m[1].startsWith('video') ? 'video' : m[1].startsWith('audio') ? 'audio' : 'image';
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
const SETTING_KEYS = ['ark_base_url', 'model_chat', 'model_image', 'model_video', 'model_video_options', 'video_extra_args', 'watermark', 'price_chat_in', 'price_chat_out', 'price_image', 'price_video_sec', 'user_name', 'default_ratio', 'tts_appid', 'tts_voice', 'tts_cluster', 'tts_endpoint'];

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
    tts_enabled: ttsEnabled(),
    tts_appid: ttsCfg().appid,
    tts_token_masked: ttsCfg().token ? `${ttsCfg().token.slice(0, 4)}****` : '',
    tts_voice: ttsCfg().voice,
    defaults: DEFAULTS, db_path: DB_PATH, upload_dir: UPLOAD_DIR
  };
});

PATCH('/api/settings', async ({ body }) => {
  if (body.tts_token !== undefined) {
    const t = String(body.tts_token).trim();
    setSetting('tts_token', t === 'clear' ? '' : t);
  }
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

POST('/api/settings/tts-test', async () => {
  const { synthesize } = await import('../lib/tts.js');
  const url = await synthesize('青鸾在此，配音已就绪。');
  return { ok: true, url };
});

POST('/api/settings/agent-token/rotate', async () => {
  const token = token32();
  setSetting('agent_token', token);
  return { agent_token: token };
});
