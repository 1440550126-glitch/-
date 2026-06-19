// 《墨修》AI 出图：火山方舟 Seedream 文生图（独立脚本，不依赖 lingjing 服务端/DB）
// 运行： node --env-file=../../.env aigen.mjs [female|male|scene|start|all]
import fs from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = (process.env.ARK_BASE_URL || 'https://ark.cn-beijing.volces.com/api/v3').replace(/\/+$/, '');
const KEY = process.env.ARK_API_KEY;
const MODEL = process.env.ARK_MODEL_IMAGE || 'doubao-seedream-4-0-250828';
const SEED = 70017;  // 固定种子：同一套美术风格更稳定、可复现
if (!KEY) { console.error('✗ 缺少 ARK_API_KEY。请用： node --env-file=../../.env aigen.mjs'); process.exit(1); }

// 比例 -> 尺寸（长边 2048，8 的倍数）
function ratioSize(ratio) {
  const [a, b] = ratio.split(':').map(Number);
  let w, h;
  if (a >= b) { w = 2048; h = Math.round((2048 * b / a) / 8) * 8; }
  else { h = 2048; w = Math.round((2048 * a / b) / 8) * 8; }
  return `${w}x${h}`;
}

async function gen({ prompt, ratio = '3:4', out, refImages = [] }) {
  const body = {
    model: MODEL, prompt, size: ratioSize(ratio), response_format: 'b64_json',
    watermark: false, seed: SEED,
    ...(refImages.length ? { image: refImages.length === 1 ? refImages[0] : refImages } : {}),
  };
  const r = await fetch(`${BASE}/images/generations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`HTTP ${r.status} · ${JSON.stringify(data).slice(0, 500)}`);
  const item = data?.data?.[0];
  if (!item?.b64_json && !item?.url) throw new Error('无图片返回 · ' + JSON.stringify(data).slice(0, 400));
  const buf = item.b64_json
    ? Buffer.from(item.b64_json, 'base64')
    : Buffer.from(await (await fetch(item.url)).arrayBuffer());
  fs.writeFileSync(join(HERE, out), buf);
  console.log('✓', out, (buf.length / 1024 | 0) + 'KB', '·', ratioSize(ratio));
}

/* ============ 水墨修仙 · 提示词 ============ */
const STYLE = '中国传统水墨画风格，国风手绘插画，宣纸质感，水墨晕染，淡雅墨色，大量留白意境，仅以朱砂红与石青色少量点缀，柔和氛围光，精致细腻，高质量，干净背景，画面中没有任何文字和水印';

const PROMPTS = {
  female: {
    ratio: '3:4', out: 'ai-female.png',
    prompt: `${STYLE}。一个Q版可爱的修仙少女全身立绘，约两头身的萌系比例，大大的清澈眼睛，温婉微笑。穿白色飘逸的道袍长裙，黛青色腰带系结垂下，腰间挂一枚青玉佩。乌黑长发束成高髻，配一支金簪步摇，额心一点朱砂花钿。手中握一柄长剑，剑柄系朱红色剑穗。脚踏祥云薄雾，周身仙气缭绕，几片墨色花瓣飘落。竖构图，居中，全身可见。`,
  },
  male: {
    ratio: '3:4', out: 'ai-male.png',
    prompt: `${STYLE}。一个Q版可爱的修仙少年剑客全身立绘，约两头身的萌系比例，剑眉星目，英气而灵动。穿月白色道袍，朱红色腰带，乌黑头发束成高马尾配木簪。手持一柄出鞘长剑，姿态潇洒。脚踏祥云薄雾，周身仙气缭绕。竖构图，居中，全身可见。`,
  },
  scene: {
    ratio: '9:16', out: 'ai-scene.png',
    prompt: `${STYLE}。一幅竖构图的水墨山水画，作为修仙手游的背景：层层叠叠的远山隐入云雾，淡墨远山、浓墨近峰，中间留白处是蜿蜒的江水，江上一叶孤舟。近景有一棵苍劲的松树和几块礁石。意境空灵悠远，烟雨朦胧。画面中没有人物。`,
  },
  start: {
    ratio: '9:16', out: 'ai-start.png',
    prompt: `${STYLE}。竖屏手游开始界面背景：上方是云雾缭绕的水墨远山天空，中间大片留白，下方是淡墨山峦与江水，整体空灵，预留出中央放置角色和按钮的空间。画面唯美，没有文字。`,
  },
};

const which = process.argv[2] || 'female';
const jobs = which === 'all' ? Object.keys(PROMPTS) : [which];
for (const k of jobs) {
  const p = PROMPTS[k];
  if (!p) { console.error('未知任务:', k); continue; }
  console.log('… 生成', k, '…');
  try { await gen(p); } catch (e) { console.error('✗', k, e.message); }
}
