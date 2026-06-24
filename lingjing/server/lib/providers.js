// 灵境AI · 多模型供应商：在火山方舟之外，接入 OpenAI GPT Image（图）与 Google Veo 3（视频）
// 各家用各自独立的 API Key / Base URL（设置页或环境变量配置）。零依赖：原生 fetch / FormData / Blob。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { getSetting, UPLOAD_DIR } from './db.js';
import { uid } from './util.js';
import { downloadToUploads, logUsage } from './ark.js';

export const PROVIDER_DEFAULTS = {
  openai_base_url: 'https://api.openai.com/v1',
  google_base_url: 'https://generativelanguage.googleapis.com/v1beta',
  dashscope_base_url: 'https://dashscope.aliyuncs.com',   // 阿里云百炼·统一 API（千问/通义万相 图与视频共用一个 Key）
  vidu_base_url: 'https://api.vidu.com',                   // Vidu（生数科技）·多主体参考「全能参考」视频，国产多图参考最强
  kling_base_url: 'https://api-beijing.klingai.com',       // 可灵 Kling（快手）·国产视频第一梯队；JWT(AccessKey/SecretKey) 鉴权
  // 创作框「生成图片」可选的图像模型（每行「显示名|模型ID」），与视频模型列表对称。2026 最新：Seedream 5.0 / 通义万相 2.5。
  model_image_options: [
    'Seedream 5.0（火山·最新，核对ID）|doubao-seedream-5-0',
    'Seedream 4.0（火山·默认）|doubao-seedream-4-0-250828',
    'GPT Image（OpenAI，需 OpenAI Key）|gpt-image-1',
    '通义万相 2.5 文生图（阿里·音画同步系列，核对ID）|wan2.5-t2i-preview',
    '通义万相 2.1 文生图 Turbo（阿里，需 DashScope Key）|wanx2.1-t2i-turbo',
    'Qwen-Image 文生图（阿里）|qwen-image'
  ].join('\n')
};

/** 供应商配置：设置页（数据库）优先，其次环境变量，最后默认值 */
export function providerCfg() {
  const env = process.env;
  const g = (key, envKey, dft) => {
    const v = getSetting(key, null);
    if (v !== null && v !== '') return v;
    if (envKey && env[envKey]) return env[envKey];
    return dft;
  };
  return {
    openaiKey: g('openai_api_key', 'OPENAI_API_KEY', ''),
    openaiBase: String(g('openai_base_url', 'OPENAI_BASE_URL', PROVIDER_DEFAULTS.openai_base_url)).replace(/\/+$/, ''),
    googleKey: g('google_api_key', 'GOOGLE_API_KEY', ''),
    googleBase: String(g('google_base_url', 'GOOGLE_BASE_URL', PROVIDER_DEFAULTS.google_base_url)).replace(/\/+$/, ''),
    dashscopeKey: g('dashscope_api_key', 'DASHSCOPE_API_KEY', ''),
    dashscopeBase: String(g('dashscope_base_url', 'DASHSCOPE_BASE_URL', PROVIDER_DEFAULTS.dashscope_base_url)).replace(/\/+$/, ''),
    viduKey: g('vidu_api_key', 'VIDU_API_KEY', ''),
    viduBase: String(g('vidu_base_url', 'VIDU_BASE_URL', PROVIDER_DEFAULTS.vidu_base_url)).replace(/\/+$/, ''),
    klingAccessKey: g('kling_access_key', 'KLING_ACCESS_KEY', ''),
    klingSecretKey: g('kling_secret_key', 'KLING_SECRET_KEY', ''),
    klingBase: String(g('kling_base_url', 'KLING_BASE_URL', PROVIDER_DEFAULTS.kling_base_url)).replace(/\/+$/, ''),
    modelImageOptions: String(g('model_image_options', 'MODEL_IMAGE_OPTIONS', PROVIDER_DEFAULTS.model_image_options))
  };
}

export const openaiEnabled = () => !!providerCfg().openaiKey;
export const googleEnabled = () => !!providerCfg().googleKey;
export const alibabaEnabled = () => !!providerCfg().dashscopeKey;
export const viduEnabled = () => !!providerCfg().viduKey;
export const klingEnabled = () => { const c = providerCfg(); return !!(c.klingAccessKey && c.klingSecretKey); };

// 按模型 ID 识别供应商：
//  图像：gpt-image*/dall* → OpenAI；qwen-image/wanx*t2i/wan* → 阿里通义万相；其余 → 火山方舟
//  视频：veo*/gemini* → Google；*t2v*/*i2v*/wanx 视频 → 阿里通义万相；其余 → 火山方舟
export function imageProviderOf(model) {
  const m = String(model || '');
  if (/^(gpt-image|dall)/i.test(m) || /openai/i.test(m)) return 'openai';
  if (/(qwen-image|wanx-v1|t2i)/i.test(m) || (/^wan/i.test(m) && !/(t2v|i2v)/i.test(m))) return 'alibaba';
  return 'ark';
}
export function videoProviderOf(model) {
  const m = String(model || '');
  if (/^veo/i.test(m) || /(google|gemini)/i.test(m)) return 'google';
  if (/^vidu/i.test(m)) return 'vidu';
  if (/^kling|kuaishou|可灵/i.test(m)) return 'kling';
  if (/(t2v|i2v)/i.test(m) || (/^wan/i.test(m) && /video/i.test(m))) return 'alibaba';
  return 'ark';
}

/** 选择图像供应商：返回 { provider, enabled, model }。arkEnabled/arkModel 由调用方注入，避免循环依赖。 */
export function pickImageProvider(model, { arkEnabled, arkModel } = {}) {
  const provider = imageProviderOf(model);
  if (provider === 'openai') return { provider, enabled: openaiEnabled(), model: model || 'gpt-image-1' };
  if (provider === 'alibaba') return { provider, enabled: alibabaEnabled(), model: model || 'wanx2.1-t2i-turbo' };
  return { provider: 'ark', enabled: !!arkEnabled, model: model || arkModel || '' };
}
/** 选择视频供应商：返回 { provider, enabled, model }。 */
export function pickVideoProvider(model, { arkEnabled, arkModel } = {}) {
  const provider = videoProviderOf(model);
  if (provider === 'google') return { provider, enabled: googleEnabled(), model: model || 'veo-3.0-generate-001' };
  if (provider === 'vidu') return { provider, enabled: viduEnabled(), model: model || 'viduq1' };
  if (provider === 'kling') return { provider, enabled: klingEnabled(), model: model || 'kling-v2-1' };
  if (provider === 'alibaba') return { provider, enabled: alibabaEnabled(), model: model || 'wanx2.1-i2v-turbo' };
  return { provider: 'ark', enabled: !!arkEnabled, model: model || arkModel || '' };
}

/** 是否支持「多主体参考」（全能参考）：Vidu / 可灵 支持多图主体一致；其余只吃首帧。 */
export function supportsMultiRef(model) {
  const p = videoProviderOf(model);
  return p === 'vidu' || p === 'kling';
}

/** 各模型支持的最大时长（秒）：Seedance 2.5→30、2.0→15，其余按各家上限，默认 12（Seedance 1.0）。 */
export function maxVideoDuration(model) {
  const m = String(model || '');
  if (/seedance[-.]?2[-.]?5/i.test(m)) return 30;
  if (/seedance[-.]?2[-.]?0/i.test(m)) return 15;
  if (/^kling/i.test(m)) return 10;                 // 可灵 5/10s
  if (/^veo/i.test(m)) return 8;                    // Veo ~8s
  if (/^vidu/i.test(m)) return 8;                   // Vidu 4/8s
  if (/wan|t2v|i2v/i.test(m)) return 10;            // 通义万相 ~10s
  return 12;
}

/** 创作框可选图像模型列表 [{label,id}]（默认模型自动置顶） */
export function imageModelOptions(arkModel = '') {
  const list = providerCfg().modelImageOptions.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
    const [label, id] = l.split('|').map((s) => s.trim());
    return id ? { label, id } : { label, id: label };
  });
  if (arkModel && !list.some((o) => o.id === arkModel)) list.unshift({ label: `默认（${arkModel}）`, id: arkModel });
  return list;
}

function localFilePath(url) {
  if (!url || !url.startsWith('/uploads/')) return null;
  const f = path.normalize(path.join(UPLOAD_DIR, url.slice('/uploads/'.length)));
  return f.startsWith(UPLOAD_DIR) && fs.existsSync(f) ? f : null;
}
function mimeOf(file) {
  const e = path.extname(file).toLowerCase();
  return e === '.jpg' || e === '.jpeg' ? 'image/jpeg' : e === '.webp' ? 'image/webp' : 'image/png';
}
// gpt-image-1 仅支持固定档位尺寸
function openaiSize(ratio) {
  if (/16\s*[:：]\s*9/.test(ratio)) return '1536x1024';
  if (/9\s*[:：]\s*16/.test(ratio)) return '1024x1536';
  return '1024x1024';
}
function gAspect(ratio) { return /9\s*[:：]\s*16/.test(ratio) ? '9:16' : '16:9'; }
// 通义万相用 宽*高 像素串
function wanSize(ratio) {
  if (/16\s*[:：]\s*9/.test(ratio)) return '1280*720';
  if (/9\s*[:：]\s*16/.test(ratio)) return '720*1280';
  return '1024*1024';
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * OpenAI GPT Image（gpt-image-1）。有参考图走 images/edits（多部分表单），否则 images/generations。
 * 返回 { url, model }。失败抛错。
 */
export async function openaiImage({ prompt, ratio = '1:1', refImages = [], model = 'gpt-image-1', feature = 'image' }) {
  const c = providerCfg();
  if (!c.openaiKey) throw new Error('未配置 OpenAI API Key（设置页填写）');
  const size = openaiSize(ratio);
  const refs = (refImages || []).map(localFilePath).filter(Boolean).slice(0, 4);
  let data;
  if (refs.length) {
    const fd = new FormData();
    fd.append('model', model); fd.append('prompt', prompt); fd.append('size', size); fd.append('n', '1');
    for (const f of refs) fd.append('image[]', new Blob([fs.readFileSync(f)], { type: mimeOf(f) }), path.basename(f));
    const res = await fetch(`${c.openaiBase}/images/edits`, { method: 'POST', headers: { Authorization: `Bearer ${c.openaiKey}` }, body: fd, signal: AbortSignal.timeout(180_000) });
    data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error?.message || `OpenAI 图片失败 HTTP ${res.status}`);
  } else {
    const res = await fetch(`${c.openaiBase}/images/generations`, {
      method: 'POST', headers: { Authorization: `Bearer ${c.openaiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, prompt, size, n: 1 }), signal: AbortSignal.timeout(180_000)
    });
    data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error?.message || `OpenAI 图片失败 HTTP ${res.status}`);
  }
  const item = data?.data?.[0] || {};
  let url;
  if (item.b64_json) {
    const name = `${uid('img')}.png`;
    fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(item.b64_json, 'base64'));
    url = `/uploads/${name}`;
  } else if (item.url) {
    url = await downloadToUploads(item.url, 'png');
  } else throw new Error('OpenAI 未返回图片');
  logUsage({ feature, provider: 'openai', model, images: 1 });
  return { url, model };
}

/**
 * Google Veo 3 创建（异步长任务）。图生视频可带首帧。返回 { remoteId, model }。
 * 端点：{base}/models/{model}:predictLongRunning?key=KEY
 */
export async function googleVeoCreate({ prompt, imageUrl = '', ratio = '16:9', model = 'veo-3.0-generate-001' }) {
  const c = providerCfg();
  if (!c.googleKey) throw new Error('未配置 Google API Key（设置页填写）');
  const instance = { prompt };
  const f = localFilePath(imageUrl);
  if (f) instance.image = { bytesBase64Encoded: fs.readFileSync(f).toString('base64'), mimeType: mimeOf(f) };
  const body = { instances: [instance], parameters: { aspectRatio: gAspect(ratio), sampleCount: 1 } };
  const res = await fetch(`${c.googleBase}/models/${encodeURIComponent(model)}:predictLongRunning?key=${encodeURIComponent(c.googleKey)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: AbortSignal.timeout(60_000)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error?.message || `Veo 任务创建失败 HTTP ${res.status}`);
  if (!data?.name) throw new Error('Veo 未返回操作 ID');
  return { remoteId: data.name, model };
}

/** Google Veo 3 查询长任务。成功时把视频落盘到本地。返回 { status, url? , error? }。 */
export async function googleVeoGet(opName, { feature = 'video', duration = 8 } = {}) {
  const c = providerCfg();
  if (!c.googleKey) throw new Error('未配置 Google API Key');
  const res = await fetch(`${c.googleBase}/${opName}?key=${encodeURIComponent(c.googleKey)}`, { signal: AbortSignal.timeout(30_000) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error?.message || `Veo 查询失败 HTTP ${res.status}`);
  if (!data.done) return { status: 'running' };
  if (data.error) { logUsage({ feature, provider: 'google', model: 'veo-3', ok: 0 }); return { status: 'failed', error: data.error.message || 'Veo 生成失败' }; }
  // 兼容多种返回形态
  const r = data.response || {};
  const sample = r.generateVideoResponse?.generatedSamples?.[0] || r.generatedVideos?.[0] || r.videos?.[0] || r.generatedSamples?.[0];
  const b64 = sample?.video?.bytesBase64Encoded || sample?.bytesBase64Encoded;
  if (b64) {
    const name = `${uid('veo')}.mp4`;
    fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(b64, 'base64'));
    logUsage({ feature, provider: 'google', model: 'veo-3', videoSeconds: duration });
    return { status: 'succeeded', url: `/uploads/${name}` };
  }
  const uri = sample?.video?.uri || sample?.video?.url || sample?.uri;
  if (uri) {
    const dl = /[?&]key=/.test(uri) ? uri : `${uri}${uri.includes('?') ? '&' : '?'}key=${c.googleKey}`;
    logUsage({ feature, provider: 'google', model: 'veo-3', videoSeconds: duration });
    try { return { status: 'succeeded', url: await downloadToUploads(dl, 'mp4') }; }
    catch { return { status: 'succeeded', url: uri }; }
  }
  return { status: 'failed', error: 'Veo 任务完成但未返回视频地址' };
}

// ===================== 阿里云 DashScope（统一 API）：通义万相 文生图 / 图·文生视频 =====================
function dashHeaders(key, async = false) {
  const h = { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };
  if (async) h['X-DashScope-Async'] = 'enable';
  return h;
}
/** 提交 DashScope 异步任务，返回 task_id。 */
async function dashSubmit(pathname, body) {
  const c = providerCfg();
  if (!c.dashscopeKey) throw new Error('未配置 DashScope（阿里云百炼）API Key');
  const res = await fetch(`${c.dashscopeBase}${pathname}`, { method: 'POST', headers: dashHeaders(c.dashscopeKey, true), body: JSON.stringify(body), signal: AbortSignal.timeout(60_000) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || `DashScope 任务创建失败 HTTP ${res.status}`);
  const id = data?.output?.task_id;
  if (!id) throw new Error('DashScope 未返回 task_id');
  return id;
}
/** 查询 DashScope 任务。kind=image 取图片 URL，video 取视频 URL。返回 { status, url?, error? }。 */
export async function dashscopeTaskGet(taskId, { kind = 'video', feature = 'video', duration = 5 } = {}) {
  const c = providerCfg();
  if (!c.dashscopeKey) throw new Error('未配置 DashScope API Key');
  const res = await fetch(`${c.dashscopeBase}/api/v1/tasks/${taskId}`, { headers: dashHeaders(c.dashscopeKey), signal: AbortSignal.timeout(30_000) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || `DashScope 查询失败 HTTP ${res.status}`);
  const st = String(data?.output?.task_status || '').toUpperCase();
  if (st === 'PENDING' || st === 'RUNNING') return { status: 'running' };
  if (st !== 'SUCCEEDED') { logUsage({ feature, provider: 'alibaba', model: 'wanx', ok: 0 }); return { status: 'failed', error: data?.output?.message || data?.message || 'DashScope 生成失败' }; }
  const out = data.output || {};
  const remote = kind === 'image'
    ? (out.results?.[0]?.url || out.results?.[0]?.image_url)
    : (out.video_url || out.results?.[0]?.video_url);
  if (!remote) return { status: 'failed', error: 'DashScope 任务完成但未返回结果地址' };
  logUsage({ feature, provider: 'alibaba', model: 'wanx', ...(kind === 'image' ? { images: 1 } : { videoSeconds: duration }) });
  try { return { status: 'succeeded', url: await downloadToUploads(remote, kind === 'image' ? 'png' : 'mp4') }; }
  catch { return { status: 'succeeded', url: remote }; }
}

/** 通义万相 文生图（异步任务，函数内轮询到完成；保持 generateImage 同步语义）。返回 { url, model }。 */
export async function dashscopeImage({ prompt, ratio = '1:1', model = 'wanx2.1-t2i-turbo', feature = 'image' }) {
  const taskId = await dashSubmit('/api/v1/services/aigc/text2image/image-synthesis', {
    model, input: { prompt }, parameters: { size: wanSize(ratio), n: 1 }
  });
  const deadline = Date.now() + 120_000;
  for (;;) {
    const r = await dashscopeTaskGet(taskId, { kind: 'image', feature });
    if (r.status === 'succeeded') return { url: r.url, model };
    if (r.status === 'failed') throw new Error(r.error || '通义万相出图失败');
    if (Date.now() > deadline) throw new Error('通义万相出图超时');
    await sleep(2500);
  }
}

// ===================== Vidu（生数科技）：多主体「全能参考」参考生视频（国产多图参考最强）=====================
// 本地图片转参考输入：http(s) 原样，本地 /uploads 转 base64 data URL（Vidu 接受 URL 或 base64）
function toRefImage(url) {
  if (!url) return null;
  if (/^https?:/i.test(url) || /^data:/i.test(url)) return url;
  const f = localFilePath(url);
  return f ? `data:${mimeOf(f)};base64,${fs.readFileSync(f).toString('base64')}` : null;
}
/** Vidu 参考生视频：images 为多张参考图（角色/场景，最多 7），prompt 内可按主体连贯叙事。返回 { remoteId, model }。 */
export async function viduReferenceVideoCreate({ prompt, images = [], ratio = '16:9', duration = 5, model = 'viduq1', resolution = '1080p', bgm = false }) {
  const c = providerCfg();
  if (!c.viduKey) throw new Error('未配置 Vidu API Key（设置页填写）');
  const imgs = images.map(toRefImage).filter(Boolean).slice(0, 7);
  if (!imgs.length) throw new Error('Vidu 全能参考至少需要 1 张参考图');
  const body = {
    model, images: imgs, prompt: String(prompt || '').slice(0, 1500),
    duration: Number(duration) >= 8 ? 8 : (Number(duration) >= 5 ? 5 : 4),
    aspect_ratio: /9\s*[:：]\s*16/.test(ratio) ? '9:16' : /1\s*[:：]\s*1/.test(ratio) ? '1:1' : '16:9',
    resolution, movement_amplitude: 'auto', bgm: !!bgm
  };
  const res = await fetch(`${c.viduBase}/ent/v2/reference2video`, {
    method: 'POST', headers: { Authorization: `Token ${c.viduKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body), signal: AbortSignal.timeout(60_000)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || data?.error || `Vidu 任务创建失败 HTTP ${res.status}`);
  const id = data?.task_id || data?.id;
  if (!id) throw new Error('Vidu 未返回 task_id');
  return { remoteId: id, model };
}
/** Vidu 任务查询。成功时落盘。返回 { status, url?, error? }。 */
export async function viduTaskGet(taskId, { feature = 'video', duration = 5 } = {}) {
  const c = providerCfg();
  if (!c.viduKey) throw new Error('未配置 Vidu API Key');
  const res = await fetch(`${c.viduBase}/ent/v2/tasks/${taskId}/creations`, {
    headers: { Authorization: `Token ${c.viduKey}` }, signal: AbortSignal.timeout(30_000)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || `Vidu 查询失败 HTTP ${res.status}`);
  const st = String(data?.state || data?.status || '').toLowerCase();
  if (st === 'failed' || st === 'error') { logUsage({ feature, provider: 'vidu', model: 'viduq1', ok: 0 }); return { status: 'failed', error: data?.err_code || data?.message || 'Vidu 生成失败' }; }
  if (st !== 'success' && st !== 'succeeded') return { status: 'running' };
  const remote = (data.creations || [])[0]?.url || data.creations?.[0]?.video_url;
  if (!remote) return { status: 'failed', error: 'Vidu 任务完成但未返回视频地址' };
  logUsage({ feature, provider: 'vidu', model: 'viduq1', videoSeconds: duration });
  try { return { status: 'succeeded', url: await downloadToUploads(remote, 'mp4') }; }
  catch { return { status: 'succeeded', url: remote }; }
}

// ===================== 可灵 Kling（快手）：国产视频第一梯队，JWT(AccessKey/SecretKey) 鉴权 =====================
const b64url = (buf) => Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
/** 生成 Kling JWT（HS256，30 分钟有效） */
function klingJWT(ak, sk) {
  const now = Math.floor(Date.now() / 1000);
  const head = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = b64url(JSON.stringify({ iss: ak, exp: now + 1800, nbf: now - 5 }));
  const sig = b64url(crypto.createHmac('sha256', sk).update(`${head}.${payload}`).digest());
  return `${head}.${payload}.${sig}`;
}
// Kling 图片入参：http(s) 原样；本地转【裸 base64】（不带 data: 前缀）
function toKlingImage(url) {
  if (!url) return null;
  if (/^https?:/i.test(url)) return url;
  const f = localFilePath(url);
  return f ? fs.readFileSync(f).toString('base64') : null;
}
/**
 * Kling 创建视频：多图→multi-image2video（全能参考·多主体一致），单图→image2video，无图→text2video。
 * remoteId 编码为 "type:task_id" 供轮询用对应端点。
 */
export async function klingVideoCreate({ prompt, imageUrl = '', images = [], ratio = '16:9', duration = 5, model = 'kling-v2-1' }) {
  const c = providerCfg();
  if (!c.klingAccessKey || !c.klingSecretKey) throw new Error('未配置 Kling AccessKey/SecretKey（设置页填写）');
  const jwt = klingJWT(c.klingAccessKey, c.klingSecretKey);
  const ar = /9\s*[:：]\s*16/.test(ratio) ? '9:16' : /1\s*[:：]\s*1/.test(ratio) ? '1:1' : '16:9';
  const dur = Number(duration) >= 10 ? '10' : '5';
  const refs = (images || []).map(toKlingImage).filter(Boolean).slice(0, 4);
  const p = String(prompt || '').slice(0, 2000);
  let type, body;
  if (refs.length > 1) {
    type = 'multi-image2video';
    body = { model_name: model, image_list: refs.map((im) => ({ image: im })), prompt: p, duration: dur, aspect_ratio: ar, mode: 'std' };
  } else {
    const one = refs[0] || toKlingImage(imageUrl);
    if (one) { type = 'image2video'; body = { model_name: model, image: one, prompt: p, duration: dur, aspect_ratio: ar, mode: 'std' }; }
    else { type = 'text2video'; body = { model_name: model, prompt: p, duration: dur, aspect_ratio: ar, mode: 'std' }; }
  }
  const res = await fetch(`${c.klingBase}/v1/videos/${type}`, {
    method: 'POST', headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body), signal: AbortSignal.timeout(60_000)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || (data?.code && data.code !== 0)) throw new Error(data?.message || `Kling 任务创建失败 HTTP ${res.status}`);
  const id = data?.data?.task_id;
  if (!id) throw new Error('Kling 未返回 task_id');
  return { remoteId: `${type}:${id}`, model };
}
/** Kling 任务查询（remoteId="type:task_id"）。成功落盘。返回 { status, url?, error? }。 */
export async function klingTaskGet(remoteId, { feature = 'video', duration = 5 } = {}) {
  const c = providerCfg();
  if (!c.klingAccessKey || !c.klingSecretKey) throw new Error('未配置 Kling Key');
  const i = String(remoteId).indexOf(':');
  const type = String(remoteId).slice(0, i) || 'image2video';
  const id = String(remoteId).slice(i + 1);
  const jwt = klingJWT(c.klingAccessKey, c.klingSecretKey);
  const res = await fetch(`${c.klingBase}/v1/videos/${type}/${id}`, { headers: { Authorization: `Bearer ${jwt}` }, signal: AbortSignal.timeout(30_000) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || `Kling 查询失败 HTTP ${res.status}`);
  const st = String(data?.data?.task_status || '').toLowerCase();
  if (st === 'failed') { logUsage({ feature, provider: 'kling', model: 'kling', ok: 0 }); return { status: 'failed', error: data?.data?.task_status_msg || 'Kling 生成失败' }; }
  if (st !== 'succeed' && st !== 'succeeded') return { status: 'running' };
  const remote = data?.data?.task_result?.videos?.[0]?.url;
  if (!remote) return { status: 'failed', error: 'Kling 完成但未返回视频地址' };
  logUsage({ feature, provider: 'kling', model: 'kling', videoSeconds: duration });
  try { return { status: 'succeeded', url: await downloadToUploads(remote, 'mp4') }; }
  catch { return { status: 'succeeded', url: remote }; }
}

/** 通义万相 图/文生视频（异步任务）。返回 { remoteId, model }，由 pollTask 轮询 dashscopeTaskGet。 */
export async function dashscopeVideoCreate({ prompt, imageUrl = '', ratio = '16:9', model = 'wanx2.1-i2v-turbo' }) {
  const input = { prompt };
  const f = localFilePath(imageUrl);
  // 图生视频需首帧；本地图片以 data URL 传入（若你的接入要求公网 URL，请改为可访问地址）
  if (f && /i2v/i.test(model)) input.img_url = `data:${mimeOf(f)};base64,${fs.readFileSync(f).toString('base64')}`;
  const remoteId = await dashSubmit('/api/v1/services/aigc/video-generation/video-synthesis', {
    model, input, parameters: { size: wanSize(ratio) }
  });
  return { remoteId, model };
}
