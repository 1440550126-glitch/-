// 灵境AI · 多模型供应商：在火山方舟之外，接入 OpenAI GPT Image（图）与 Google Veo 3（视频）
// 各家用各自独立的 API Key / Base URL（设置页或环境变量配置）。零依赖：原生 fetch / FormData / Blob。
import fs from 'node:fs';
import path from 'node:path';
import { getSetting, UPLOAD_DIR } from './db.js';
import { uid } from './util.js';
import { downloadToUploads, logUsage } from './ark.js';

export const PROVIDER_DEFAULTS = {
  openai_base_url: 'https://api.openai.com/v1',
  google_base_url: 'https://generativelanguage.googleapis.com/v1beta',
  // 创作框「生成图片」可选的图像模型（每行「显示名|模型ID」），与视频模型列表对称
  model_image_options: [
    'Seedream 4.0（火山·默认）|doubao-seedream-4-0-250828',
    'GPT Image（OpenAI，需 OpenAI Key）|gpt-image-1'
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
    modelImageOptions: String(g('model_image_options', 'MODEL_IMAGE_OPTIONS', PROVIDER_DEFAULTS.model_image_options))
  };
}

export const openaiEnabled = () => !!providerCfg().openaiKey;
export const googleEnabled = () => !!providerCfg().googleKey;

// 按模型 ID 识别供应商：gpt-image*/dall* → OpenAI；veo*/gemini* → Google；其余 → 火山方舟
export function imageProviderOf(model) { return /^(gpt-image|dall)/i.test(String(model || '')) || /openai/i.test(String(model || '')) ? 'openai' : 'ark'; }
export function videoProviderOf(model) { return /^veo/i.test(String(model || '')) || /(google|gemini)/i.test(String(model || '')) ? 'google' : 'ark'; }

/** 选择图像供应商：返回 { provider, enabled, model }。arkEnabledFn/arkModel 由调用方注入，避免循环依赖。 */
export function pickImageProvider(model, { arkEnabled, arkModel } = {}) {
  const provider = imageProviderOf(model);
  if (provider === 'openai') return { provider, enabled: openaiEnabled(), model: model || 'gpt-image-1' };
  return { provider: 'ark', enabled: !!arkEnabled, model: model || arkModel || '' };
}
/** 选择视频供应商：返回 { provider, enabled, model }。 */
export function pickVideoProvider(model, { arkEnabled, arkModel } = {}) {
  const provider = videoProviderOf(model);
  if (provider === 'google') return { provider, enabled: googleEnabled(), model: model || 'veo-3.0-generate-001' };
  return { provider: 'ark', enabled: !!arkEnabled, model: model || arkModel || '' };
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
