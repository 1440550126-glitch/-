// 灵境AI · 火山方舟（Volcengine Ark）客户端
// 文档参考：https://www.volcengine.com/docs/82379 （模型服务 → API 参考）
//  - 文本对话  POST {base}/chat/completions          （OpenAI 兼容，支持 tools 函数调用）
//  - 图片生成  POST {base}/images/generations        （Seedream 系列）
//  - 视频生成  POST {base}/contents/generations/tasks（Seedance 系列，异步任务）
// 模型 ID / 价格随官网更新，全部可在设置页或 .env 覆盖（如 Seedance 2.0 上线后直接替换 ID）。
import fs from 'node:fs';
import path from 'node:path';
import { q, getSetting, UPLOAD_DIR } from './db.js';
import { now, estimateTokens, ratioSize, uid } from './util.js';

export const DEFAULTS = {
  ark_base_url: 'https://ark.cn-beijing.volces.com/api/v3',
  model_chat: 'doubao-seed-1-6-250615',
  model_image: 'doubao-seedream-4-0-250828',
  // 角色三视图 / 全场景图等"定海神针"参考图用的最强图像模型（控制台开通后可填更强的 ID 或 ep- 推理接入点）
  model_image_pro: 'doubao-seedream-4-0-250828',
  model_video: 'doubao-seedance-1-0-pro-250528',
  // 创作框可选的视频模型（每行「显示名|模型ID」）；以方舟控制台「开通管理」里的准确 ID 为准。
  // 想用最强：去控制台复制 Seedance 2.0 / Pro 的模型 ID 或推理接入点 ep-xxxx 替换下面对应行。
  model_video_options: [
    'Seedance 2.0 Pro（最强，请核对ID）|doubao-seedance-2-0-pro',
    'Seedance 2.0|doubao-seedance-2-0',
    'Seedance 1.0 Pro|doubao-seedance-1-0-pro-250528',
    'Seedance 1.0 Lite 图生视频|doubao-seedance-1-0-lite-i2v-250428',
    'Veo 3（Google，需 Google Key）|veo-3.0-generate-001',
    'Veo 3 Fast（Google）|veo-3.0-fast-generate-001',
    '通义万相 2.1 图生视频（阿里，需 DashScope Key）|wanx2.1-i2v-turbo',
    '通义万相 2.1 文生视频（阿里）|wanx2.1-t2v-turbo',
    '通义万相 2.2 图生视频 Plus（阿里）|wan2.2-i2v-plus',
    'Vidu Q1 全能参考（多主体一致，需 Vidu Key）|viduq1',
    'Vidu 2.0 全能参考（多图参考）|vidu2.0'
  ].join('\n'),
  video_extra_args: '',     // 追加到视频任务文本命令的参数，如 --camerafixed true
  watermark: false,
  // 价格仅用于成本预估展示（元），请按方舟控制台实际定价在设置页调整
  price_chat_in: 0.0008,    // 元 / 千 token
  price_chat_out: 0.008,    // 元 / 千 token
  price_image: 0.2,         // 元 / 张
  price_video_sec: 0.45     // 元 / 秒
};

/** 运行配置：设置页（数据库）优先，其次环境变量，最后默认值 */
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
    modelImagePro: g('model_image_pro', 'ARK_MODEL_IMAGE_PRO', DEFAULTS.model_image_pro),
    modelVideo: g('model_video', 'ARK_MODEL_VIDEO', DEFAULTS.model_video),
    modelVideoOptions: String(g('model_video_options', 'ARK_MODEL_VIDEO_OPTIONS', DEFAULTS.model_video_options)),
    videoExtraArgs: String(g('video_extra_args', '', DEFAULTS.video_extra_args)),
    watermark: !!g('watermark', '', DEFAULTS.watermark),
    priceChatIn: Number(g('price_chat_in', '', DEFAULTS.price_chat_in)),
    priceChatOut: Number(g('price_chat_out', '', DEFAULTS.price_chat_out)),
    priceImage: Number(g('price_image', '', DEFAULTS.price_image)),
    priceVideoSec: Number(g('price_video_sec', '', DEFAULTS.price_video_sec))
  };
}

export const arkEnabled = () => !!cfg().apiKey;

/** 创作框可选的视频模型列表 [{label, id}]（默认模型自动置顶） */
export function videoModelOptions() {
  const c = cfg();
  const list = c.modelVideoOptions.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
    const [label, id] = l.split('|').map((s) => s.trim());
    return id ? { label, id } : { label, id: label };
  });
  if (!list.some((o) => o.id === c.modelVideo)) list.unshift({ label: `默认（${c.modelVideo}）`, id: c.modelVideo });
  return list;
}

// ---- 成本记账（微元 = 元 × 1e6） ----
export function logUsage({ feature, provider = 'local', model = '', promptTokens = 0, completionTokens = 0, images = 0, videoSeconds = 0, ok = 1 }) {
  const c = cfg();
  const cost = provider === 'local' ? 0 : Math.round(
    promptTokens * c.priceChatIn * 1000 +        // 元/千token → 微元/token = price*1e6/1000
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

async function arkFetch(pathname, body, { timeoutMs = 30_000, method = 'POST', base = '', key = '' } = {}) {
  const c = cfg();
  const useBase = base || c.baseUrl;
  const useKey = key || c.apiKey;
  if (!useKey) throw new Error('ark-disabled');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(useBase + pathname, {
      method,
      signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${useKey}` },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const msg = data?.error?.message || data?.message || `HTTP ${resp.status}`;
      throw new Error(`模型接口错误：${msg}`);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

// ---- 对话模型路由：千问（Qwen/通义）走阿里云 DashScope OpenAI 兼容端点（统一 Key），否则走火山方舟 ----
const DASHSCOPE_DEFAULT_BASE = 'https://dashscope.aliyuncs.com';
const dashKey = () => getSetting('dashscope_api_key', '') || process.env.DASHSCOPE_API_KEY || '';
const dashBase = () => String(getSetting('dashscope_base_url', '') || process.env.DASHSCOPE_BASE_URL || DASHSCOPE_DEFAULT_BASE).replace(/\/+$/, '');
export const isQwenChat = (model) => /^(qwen|qwq|qvq|tongyi)/i.test(String(model || ''));
function chatTarget() {
  const c = cfg();
  if (isQwenChat(c.modelChat) && dashKey()) return { base: `${dashBase()}/compatible-mode/v1`, key: dashKey(), model: c.modelChat, provider: 'alibaba' };
  return { base: c.baseUrl, key: c.apiKey, model: c.modelChat, provider: 'ark' };
}
/** 对话/剧本/Agent 是否可用真实大模型（火山 Key，或选了千问且配了 DashScope Key）。 */
export const llmEnabled = () => !!chatTarget().key;

/**
 * 文本对话（支持 JSON 模式与 tools 函数调用）
 * @returns {Promise<{text:string, toolCalls:Array|null, usage:{promptTokens,completionTokens}, model:string}>}
 */
export async function arkChat({ system = '', messages = null, prompt = '', images = null, json = false, tools = null, maxTokens = 4096, temperature = 0.8, timeoutMs = 90_000, feature = 'chat' }) {
  const c = cfg();
  const t = chatTarget();   // 千问→DashScope 兼容端点；否则火山方舟
  const msgs = messages ? [...messages] : [];
  if (!messages) {
    if (system) msgs.push({ role: 'system', content: system });
    // 视觉输入：把图片作为多模态 content 附到用户消息（AIQC 让模型"看"图）
    if (images?.length) {
      const parts = [{ type: 'text', text: prompt }];
      for (const u of images.slice(0, 4)) {
        const url = toArkImageUrl(u);
        if (url) parts.push({ type: 'image_url', image_url: { url } });
      }
      msgs.push({ role: 'user', content: parts });
    } else {
      msgs.push({ role: 'user', content: prompt });
    }
  }
  const data = await arkFetch('/chat/completions', {
    model: t.model,
    messages: msgs,
    max_tokens: maxTokens,
    temperature,
    ...(json ? { response_format: { type: 'json_object' } } : {}),
    ...(tools?.length ? { tools } : {})
  }, { timeoutMs, base: t.base, key: t.key });

  const choice = data?.choices?.[0];
  const text = choice?.message?.content || '';
  const toolCalls = choice?.message?.tool_calls || null;
  const usage = {
    promptTokens: data?.usage?.prompt_tokens ?? estimateTokens(JSON.stringify(msgs)),
    completionTokens: data?.usage?.completion_tokens ?? estimateTokens(text)
  };
  logUsage({ feature, provider: t.provider, model: t.model, promptTokens: usage.promptTokens, completionTokens: usage.completionTokens });
  if (!text && !toolCalls?.length) throw new Error('模型返回了空内容');
  return { text, toolCalls, usage, model: t.model, raw: choice?.message };
}

/** 把本地 /uploads/ 文件转成 base64 data URL（方舟图生图 / 图生视频的参考图输入） */
export function toArkImageUrl(url) {
  if (!url) return null;
  if (/^(https?:|data:)/.test(url)) return url;
  const rel = url.replace(/^\/uploads\//, '');
  const file = path.normalize(path.join(UPLOAD_DIR, rel));
  if (!file.startsWith(UPLOAD_DIR) || !fs.existsSync(file)) return null;
  const ext = path.extname(file).toLowerCase().slice(1) || 'png';
  const mime = ext === 'jpg' ? 'jpeg' : ext;
  return `data:image/${mime};base64,${fs.readFileSync(file).toString('base64')}`;
}

/** 下载远端结果到本地 uploads（方舟返回的 URL 有有效期，必须落盘） */
export async function downloadToUploads(remoteUrl, ext) {
  const resp = await fetch(remoteUrl, { signal: AbortSignal.timeout(120_000) });
  if (!resp.ok) throw new Error(`下载生成结果失败 HTTP ${resp.status}`);
  const buf = Buffer.from(await resp.arrayBuffer());
  const name = `${uid('f')}.${ext}`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), buf);
  return `/uploads/${name}`;
}

/**
 * 图片生成（Seedream）。返回本地 /uploads/ 地址。
 * refImages：参考图（角色一致性 / 图生图），支持本地 uploads 路径或 http(s)/data URL。
 */
export async function arkImage({ prompt, ratio = '16:9', refImages = [], seed = 0, model = '', feature = 'image' }) {
  const c = cfg();
  const useModel = model || c.modelImage;   // 可按用途传入更强模型（角色三视图/全场景图）
  const { w, h } = ratioSize(ratio, 2048);
  const refs = refImages.map(toArkImageUrl).filter(Boolean);
  const data = await arkFetch('/images/generations', {
    model: useModel,
    prompt,
    size: `${w}x${h}`,
    response_format: 'b64_json',
    watermark: c.watermark,
    ...(seed > 0 ? { seed } : {}),     // 项目级种子：同项目画面更稳定、重生成可复现
    ...(refs.length ? { image: refs.length === 1 ? refs[0] : refs } : {})
  }, { timeoutMs: 120_000 });

  const item = data?.data?.[0];
  if (!item) throw new Error('方舟没有返回图片');
  let url;
  if (item.b64_json) {
    const name = `${uid('img')}.png`;
    fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(item.b64_json, 'base64'));
    url = `/uploads/${name}`;
  } else if (item.url) {
    url = await downloadToUploads(item.url, 'png');
  } else {
    throw new Error('方舟返回了未知的图片格式');
  }
  logUsage({ feature, provider: 'ark', model: useModel, images: 1 });
  return { url, model: useModel };
}

/**
 * 视频生成（Seedance，异步任务）。文本命令行参数随模型版本见官方文档。
 * @returns {Promise<{remoteId:string, model:string}>}
 */
export async function arkVideoCreate({ prompt, imageUrl = '', lastImageUrl = '', ratio = '16:9', duration = 5, model = '', resolution = '' }) {
  const c = cfg();
  const useModel = model || c.modelVideo;
  let text = `${prompt} --ratio ${ratio} --duration ${Math.round(duration)} --watermark ${c.watermark ? 'true' : 'false'}`;
  if (resolution) text += ` --resolution ${String(resolution).toLowerCase().replace(/P$/i, 'p')}`;
  if (c.videoExtraArgs) text += ` ${c.videoExtraArgs}`;
  const content = [{ type: 'text', text }];
  const ref = toArkImageUrl(imageUrl);
  if (ref) content.push({ type: 'image_url', image_url: { url: ref }, role: 'first_frame' });
  // 一镜到底：首尾帧之间生成自然过渡（Seedance 首尾帧能力）
  const ref2 = toArkImageUrl(lastImageUrl);
  if (ref && ref2) content.push({ type: 'image_url', image_url: { url: ref2 }, role: 'last_frame' });
  const data = await arkFetch('/contents/generations/tasks', { model: useModel, content }, { timeoutMs: 60_000 });
  if (!data?.id) throw new Error('方舟没有返回任务 ID');
  return { remoteId: data.id, model: useModel };
}

/** 查询视频任务。succeeded 时自动把视频落盘到本地。 */
export async function arkVideoGet(remoteId, { duration = 5, feature = 'video' } = {}) {
  const c = cfg();
  const data = await arkFetch(`/contents/generations/tasks/${remoteId}`, undefined, { method: 'GET', timeoutMs: 30_000 });
  const status = data?.status || 'running';
  if (status === 'succeeded') {
    const remoteUrl = data?.content?.video_url;
    if (!remoteUrl) throw new Error('任务成功但没有视频地址');
    let url = remoteUrl;
    try { url = await downloadToUploads(remoteUrl, 'mp4'); }
    catch (e) { console.warn('[ark] 视频落盘失败，暂用远端地址（有有效期）：', e.message); }
    logUsage({ feature, provider: 'ark', model: c.modelVideo, videoSeconds: duration });
    return { status, url };
  }
  if (status === 'failed' || status === 'cancelled') {
    logUsage({ feature, provider: 'ark', model: c.modelVideo, ok: 0 });
    return { status: 'failed', error: data?.error?.message || data?.failure_reason || '生成失败' };
  }
  return { status: status === 'queued' ? 'queued' : 'running' };
}
