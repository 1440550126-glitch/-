// 爆款工厂 · 广告脚本引擎：商品信息 → 结构化口播分镜（钩子→痛点→卖点→促单）
// 配了大模型走真实生成（JSON 模式），否则本地规则套路兜底。对标 TopView 的 UGC/广告脚本。
import { chat, llmEnabled } from './llm.js';
import { hashCode, seededRandom, pick, clamp } from './util.js';

export const TONES = [
  { id: 'ugc', name: 'UGC 测评种草', desc: '达人第一人称真实测评，先惊喜后安利' },
  { id: 'painpoint', name: '痛点-方案', desc: '戳中痛点 → 给出解决方案 → 促单' },
  { id: 'unboxing', name: '开箱体验', desc: '开箱仪式感 → 细节展示 → 上手感受' },
  { id: 'koc', name: '口播带货', desc: '主播直给卖点 + 限时优惠催单' },
  { id: 'feature', name: '卖点罗列', desc: '快节奏逐条打出核心卖点' }
];
export const TONE_IDS = TONES.map((t) => t.id);

export const STYLES = [
  { id: 'clean-studio', name: '极简棚拍', prompt: '极简电商棚拍，纯色渐变背景，柔和环形光，高级感产品摄影，干净通透' },
  { id: 'lifestyle', name: '生活场景', prompt: '生活方式场景，温暖自然光，居家/户外真实环境，达人手持产品，竖屏短视频质感' },
  { id: 'tech-dark', name: '科技暗调', prompt: '科技产品暗调质感，黑金配色，硬光勾边，反光台面，未来感光晕' },
  { id: 'fresh-bright', name: '清新明亮', prompt: '清新明亮高饱和，奶油色调，柔光过曝，ins 风电商画面' },
  { id: 'street-ugc', name: '街拍 UGC', prompt: '手机直拍 UGC 质感，轻微噪点，自然抖动，真实街头/室内光，接地气' }
];

export function resolveStyle(style = '') {
  const s = String(style || '').trim();
  if (!s) return STYLES[0].prompt;
  return STYLES.find((x) => x.name === s || x.id === s)?.prompt || s;
}

const HOOKS = [
  '我居然现在才发现它', '这东西我吹爆', '别再乱花钱了', '原来大家都在偷偷用这个',
  '后悔没早点买', '这价格我直接闭眼入', '用过就回不去了'
];
const CTAS = [
  '点击下方链接，限时到手价带走', '库存不多，先到先得', '现在下单立减，手慢无',
  '左下角小黄车，冲就完了', '点关注+下单，今天最划算'
];

/** 本地规则套路：商品 → 分镜脚本 */
export function localAdScript(product = {}, { tone = 'ugc', ratio = '9:16', duration = 6 } = {}) {
  const rnd = seededRandom(hashCode((product.title || '') + tone));
  const name = product.title || '这款好物';
  const brand = product.brand || '';
  const priceStr = product.price ? `${product.currency || '¥'}${product.price}` : '';
  const pts = (product.points && product.points.length ? product.points : ['品质在线', '颜值能打', '用着省心']).slice(0, 4);
  const hook = pick(HOOKS, rnd);
  const cta = product.price ? `${priceStr} 到手，${pick(CTAS, rnd)}` : pick(CTAS, rnd);
  const visualBase = `${name}${brand ? '（' + brand + '）' : ''}`;
  const isUgc = tone === 'ugc' || tone === 'unboxing';
  const presenter = isUgc || tone === 'koc';
  const mk = (role, onscreen, voiceover, visual) => ({ role, onscreen, voiceover, visual });

  let beats = [];
  if (tone === 'painpoint') {
    beats = [
      mk('hook', `还在为这个头疼？`, `你是不是也经常遇到这种烦恼`, `痛点情景再现，皱眉烦恼，竖屏特写`),
      mk('pain', `我也踩过坑`, `试了好多办法都没用，直到遇到${name}`, `对比旧方案的狼狈，${visualBase}登场`),
      ...pts.slice(0, 2).map((p, i) => mk('benefit', p, `它${p}，一下就解决了`, `${visualBase}展示「${p}」的细节特写`)),
      mk('cta', cta, cta, `${visualBase}+价格弹窗，引导点击小黄车`)
    ];
  } else if (tone === 'feature') {
    beats = [
      mk('hook', `${name} 凭什么火`, `${hook}，${name}的卖点我一条条说`, `${visualBase}快速亮相，节奏感转场`),
      ...pts.map((p) => mk('benefit', p, p, `${visualBase}逐条打出「${p}」，图标+大字`)),
      mk('cta', cta, cta, `${visualBase}+优惠信息，强促单`)
    ];
  } else {
    // ugc / unboxing / koc
    beats = [
      mk('hook', hook, `${hook}！${tone === 'unboxing' ? '今天来开箱' : '真的安利给你们'}${name}`, `${presenter ? '达人手持' : ''}${visualBase}，惊喜表情，竖屏特写`),
      mk('pain', `我之前的顾虑`, `本来还担心${pts[0] ? '没那么' + pts[0] : '不好用'}`, `${tone === 'unboxing' ? '开箱仪式，拆封细节' : '使用前的犹豫'}，${visualBase}`),
      ...pts.slice(0, 2).map((p) => mk('benefit', p, `结果它真的${p}，太惊喜了`, `${visualBase}展示「${p}」，上手实拍`)),
      mk('proof', priceStr ? `这价格 ${priceStr}` : `这质价比`, `关键是这个价格，真的可以闭眼入`, `${visualBase}+价格标签，对比同类`),
      mk('cta', cta, cta, `${presenter ? '达人比心' : ''}指向小黄车，${visualBase}收尾`)
    ];
  }
  const per = clamp(duration, 3, 10);
  const shots = beats.map((b, i) => ({
    key: `sh${i + 1}`, order: i + 1, role: b.role,
    onscreen: b.onscreen, voiceover: b.voiceover, visual: b.visual,
    duration: per, image: '', video: '', audio: ''
  }));
  return { hook, cta, shots };
}

const SYS = `你是顶级电商短视频广告编剧，擅长 TikTok/抖音 带货爆款脚本。根据商品信息产出竖屏口播分镜。
只输出 JSON：{"hook":"开场钩子","cta":"促单话术","shots":[{"role":"hook|pain|benefit|proof|cta","onscreen":"屏幕大字幕(≤14字)","voiceover":"口播旁白(口语、有情绪)","visual":"画面/运镜描述","duration":秒}]}。
要求：3秒强钩子开场；中段用商品卖点层层加码；结尾强促单。5-6 个分镜。语言与商品一致。不要任何多余解释。`;

/** 商品 → 广告分镜脚本。配了模型走真实生成，否则本地兜底。返回 {storyboard, byLLM}。 */
export async function buildAdScript(product = {}, { tone = 'ugc', lang = 'zh', ratio = '9:16', duration = 6, style = '' } = {}) {
  if (llmEnabled()) {
    try {
      const toneName = TONES.find((t) => t.id === tone)?.name || tone;
      const prompt = `商品标题：${product.title}\n品牌：${product.brand || '未知'}\n价格：${product.currency || ''}${product.price || '未知'}\n卖点：${(product.points || []).join('、') || '未提供'}\n描述：${product.desc || '无'}\n脚本套路：${toneName}\n输出语言：${lang}\n单镜时长约 ${duration} 秒。`;
      const { text } = await chat({ system: SYS, prompt, json: true, feature: 'adscript', temperature: 0.85 });
      const data = JSON.parse(text);
      const shots = (data.shots || []).slice(0, 8).map((s, i) => ({
        key: `sh${i + 1}`, order: i + 1, role: String(s.role || 'benefit'),
        onscreen: String(s.onscreen || '').slice(0, 40), voiceover: String(s.voiceover || '').slice(0, 200),
        visual: String(s.visual || '').slice(0, 200), duration: clamp(s.duration || duration, 2, 12),
        image: '', video: '', audio: ''
      }));
      if (shots.length) return { storyboard: { hook: String(data.hook || '').slice(0, 60), cta: String(data.cta || '').slice(0, 80), shots }, byLLM: true };
    } catch { /* 模型失败 → 本地兜底 */ }
  }
  return { storyboard: localAdScript(product, { tone, ratio, duration }), byLLM: false };
}
