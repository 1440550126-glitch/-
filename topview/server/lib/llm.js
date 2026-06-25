// 爆款工厂 · 模型客户端（OpenAI 兼容对话 + 图像 + 视频，零依赖 fetch）
// 默认接火山方舟（豆包/Seedream/Seedance），也兼容任意 OpenAI 兼容端点与 OpenAI GPT Image。
// 不配任何 Key 时全部能力由 lib/local.js 本地引擎兜底，零成本可演示。
import fs from 'node:fs';
import path from 'node:path';
import { q, getSetting, UPLOAD_DIR } from './db.js';
import { now, estimateTokens, ratioSize, uid } from './util.js';

export const DEFAULTS = {
  ark_base_url: 'https://ark.cn-beijing.volces.com/api/v3',
  model_chat: 'doubao-seed-1-6-250615',
  model_image: 'doubao-seedream-4-0-250828',
  model_video: 'doubao-seedance-1-0-pro-250528',
  openai_base_url: 'https://api.openai.com/v1',
  watermark: false,
  price_chat_in: 0.0008, price_chat_out: 0.008, price_image: 0.2, price_video_sec: 0.45
};

export function cfg() {
  const env = process.env;
  const g = (key, envKey, dft) => {
    const v = getSetting(key, null);
    if (v !== null && v !== '') return v;
    if (envKey && env[envKey]) return env[envKey];
    return dft;
  };
  return {
    apiKey: g('ark_api_key', 'ARK_API_KEY', ''),
    baseUrl: String(g('ark_base_url', 'ARK_BASE_URL', DEFAULTS.ark_base_url)).replace(/\/+$/, ''),
    modelChat: g('model_chat', 'ARK_MODEL_CHAT', DEFAULTS.model_chat),
    modelImage: g('model_image', 'ARK_MODEL_IMAGE', DEFAULTS.model_image),
    modelVideo: g('model_video', 'ARK_MODEL_VIDEO', DEFAULTS.model_video),
    openaiKey: g('openai_api_key', 'OPENAI_API_KEY', ''),
    openaiBase: String(g('openai_base_url', 'OPENAI_BASE_URL', DEFAULTS.openai_base_url)).replace(/\/+$/, ''),
    watermark: !!g('watermark', '', DEFAULTS.watermark),
    priceChatIn: Number(g('price_chat_in', '', DEFAULTS.price_chat_in)),
    priceChatOut: Number(g('price_chat_out', '', DEFAULTS.price_chat_out)),
    priceImage: Number(g('price_image', '', DEFAULTS.price_image)),
    priceVideoSec: Number(g('price_video_sec', '', DEFAULTS.price_video_sec))
  };
}

export const arkEnabled = () => !!cfg().apiKey;
export const llmEnabled = () => !!cfg().apiKey;            // 对话可用真实大模型
export const imageEnabled = () => !!cfg().apiKey || !!cfg().openaiKey;
export const videoEnabled = () => !!cfg().apiKey;

// ---- 成本记账（微元 = 元 × 1e6） ----
export function logUsage({ feature, provider = 'local', model = '', promptTokens = 0, completionTokens = 0, images = 0, videoSeconds = 0, ok = 1 }) {
  const c = cfg();
  const cost = provider === 'local' ? 0 : Math.round(
    promptTokens * c.priceChatIn * 1000 +
    completionTokens * c.priceChatOut * 1000 +
    images * c.priceImage * 1_000_000 +
    videoSeconds * c.priceVideoSec * 1_000_000
  );
  q.run(
    `INSERT INTO usage_logs (feature, provider, model, prompt_tokens, completion_tokens, images, video_seconds, cost_micro, ok, created_at)
     VALUES (?,?,?,?,?,?,?,?,?,?)`,
    feature, provider, model, promptTokens, completionTokens, images, videoSeconds, cost, ok, now()
  );
  return cost;
}

async function arkFetch(pathname, body, { timeoutMs = 90_000, method = 'POST', base = '', key = '' } = {}) {
  const c = cfg();
  const useBase = base || c.baseUrl;
  const useKey = key || c.apiKey;
  if (!useKey) throw new Error('模型未配置 Key');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(useBase + pathname, {
      method, signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${useKey}` },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(`模型接口错误：${data?.error?.message || data?.message || `HTTP ${resp.status}`}`);
    return data;
  } finally { clearTimeout(timer); }
}

/** 文本对话（支持 JSON 模式）。返回 {text, usage, model}。 */
export async function chat({ system = '', prompt = '', json = false, maxTokens = 3000, temperature = 0.8, feature = 'chat' }) {
  const c = cfg();
  const msgs = [];
  if (system) msgs.push({ role: 'system', content: system });
  msgs.push({ role: 'user', content: prompt });
  const data = await arkFetch('/chat/completions', {
    model: c.modelChat, messages: msgs, max_tokens: maxTokens, temperature,
    ...(json ? { response_format: { type: 'json_object' } } : {})
  });
  const text = data?.choices?.[0]?.message?.content || '';
  const usage = {
    promptTokens: data?.usage?.prompt_tokens ?? estimateTokens(JSON.stringify(msgs)),
    completionTokens: data?.usage?.completion_tokens ?? estimateTokens(text)
  };
  logUsage({ feature, provider: 'ark', model: c.modelChat, promptTokens: usage.promptTokens, completionTokens: usage.completionTokens });
  if (!text) throw new Error('模型返回了空内容');
  return { text, usage, model: c.modelChat };
}

/** 本地 /uploads 文件 → base64 data URL（参考图输入用） */
export function toImageUrl(url) {
  if (!url) return null;
  if (/^(https?:|data:)/.test(url)) return url;
  const rel = url.replace(/^\/uploads\//, '');
  const file = path.normalize(path.join(UPLOAD_DIR, rel));
  if (!file.startsWith(UPLOAD_DIR) || !fs.existsSync(file)) return null;
  const ext = path.extname(file).toLowerCase().slice(1) || 'png';
  return `data:image/${ext === 'jpg' ? 'jpeg' : ext};base64,${fs.readFileSync(file).toString('base64')}`;
}

/** 下载远端结果落盘（各家返回 URL 有有效期，必须落盘） */
export async function downloadToUploads(remoteUrl, ext) {
  const resp = await fetch(remoteUrl, { signal: AbortSignal.timeout(120_000) });
  if (!resp.ok) throw new Error(`下载生成结果失败 HTTP ${resp.status}`);
  const buf = Buffer.from(await resp.arrayBuffer());
  const name = `${uid('f')}.${ext}`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), buf);
  return `/uploads/${name}`;
}

function openaiSize(ratio) {
  if (/16\s*[:：]\s*9/.test(ratio)) return '1536x1024';
  if (/9\s*[:：]\s*16/.test(ratio) || /4\s*[:：]\s*5/.test(ratio)) return '1024x1536';
  return '1024x1024';
}

/** 图片生成。优先火山 Seedream；模型名是 gpt-image* 且配了 OpenAI Key 时走 OpenAI。返回 {url,model}。 */
export async function genImage({ prompt, ratio = '9:16', refImages = [], seed = 0, model = '', feature = 'image' }) {
  const c = cfg();
  const useModel = model || c.modelImage;
  // OpenAI GPT Image
  if (/^(gpt-image|dall)/i.test(useModel) && c.openaiKey) {
    const res = await fetch(`${c.openaiBase}/images/generations`, {
      method: 'POST', headers: { Authorization: `Bearer ${c.openaiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: useModel, prompt, size: openaiSize(ratio), n: 1 }), signal: AbortSignal.timeout(180_000)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error?.message || `OpenAI 图片失败 HTTP ${res.status}`);
    const item = data?.data?.[0] || {};
    let url;
    if (item.b64_json) { const name = `${uid('img')}.png`; fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(item.b64_json, 'base64')); url = `/uploads/${name}`; }
    else if (item.url) url = await downloadToUploads(item.url, 'png');
    else throw new Error('OpenAI 未返回图片');
    logUsage({ feature, provider: 'openai', model: useModel, images: 1 });
    return { url, model: useModel };
  }
  // 火山方舟 Seedream
  const { w, h } = ratioSize(ratio, 2048);
  const refs = refImages.map(toImageUrl).filter(Boolean);
  const data = await arkFetch('/images/generations', {
    model: useModel, prompt, size: `${w}x${h}`, response_format: 'b64_json', watermark: c.watermark,
    ...(seed > 0 ? { seed } : {}),
    ...(refs.length ? { image: refs.length === 1 ? refs[0] : refs } : {})
  }, { timeoutMs: 120_000 });
  const item = data?.data?.[0];
  if (!item) throw new Error('方舟没有返回图片');
  let url;
  if (item.b64_json) { const name = `${uid('img')}.png`; fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(item.b64_json, 'base64')); url = `/uploads/${name}`; }
  else if (item.url) url = await downloadToUploads(item.url, 'png');
  else throw new Error('方舟返回了未知的图片格式');
  logUsage({ feature, provider: 'ark', model: useModel, images: 1 });
  return { url, model: useModel };
}

/** 视频生成（Seedance 异步任务）。返回 {remoteId, model}。 */
export async function genVideoCreate({ prompt, imageUrl = '', ratio = '9:16', duration = 5, model = '' }) {
  const c = cfg();
  const useModel = model || c.modelVideo;
  let text = `${prompt} --ratio ${ratio} --duration ${Math.round(duration)} --watermark ${c.watermark ? 'true' : 'false'}`;
  const content = [{ type: 'text', text }];
  const ref = toImageUrl(imageUrl);
  if (ref) content.push({ type: 'image_url', image_url: { url: ref }, role: 'first_frame' });
  const data = await arkFetch('/contents/generations/tasks', { model: useModel, content }, { timeoutMs: 60_000 });
  if (!data?.id) throw new Error('方舟没有返回任务 ID');
  return { remoteId: data.id, model: useModel };
}

/** 查询视频任务，succeeded 时落盘。返回 {status, url?, error?}。 */
export async function genVideoGet(remoteId, { duration = 5, feature = 'video' } = {}) {
  const c = cfg();
  const data = await arkFetch(`/contents/generations/tasks/${remoteId}`, undefined, { method: 'GET', timeoutMs: 30_000 });
  const status = data?.status || 'running';
  if (status === 'succeeded') {
    const remoteUrl = data?.content?.video_url;
    if (!remoteUrl) throw new Error('任务成功但没有视频地址');
    let url = remoteUrl;
    try { url = await downloadToUploads(remoteUrl, 'mp4'); } catch { /* 落盘失败暂用远端 */ }
    logUsage({ feature, provider: 'ark', model: c.modelVideo, videoSeconds: duration });
    return { status, url };
  }
  if (status === 'failed' || status === 'cancelled') {
    logUsage({ feature, provider: 'ark', model: c.modelVideo, ok: 0 });
    return { status: 'failed', error: data?.error?.message || '生成失败' };
  }
  return { status: status === 'queued' ? 'queued' : 'running' };
}
