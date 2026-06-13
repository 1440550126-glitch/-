#!/usr/bin/env node
// 灵境AI · 模型连通诊断（在你本地终端运行：node lingjing/scripts/diagnose.mjs）
// 逐个真实调用 对话/图像/视频 模型，打印火山方舟返回的【原始报错】，定位"视频走本地"等问题。
// Key 从 .env 或设置页数据库读取，全程脱敏，不会打印或上传。
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..', '..');
try { process.loadEnvFile(path.join(ROOT, '.env')); } catch { /* 没有 .env 就用数据库里的 */ }
try { process.loadEnvFile(path.join(ROOT, 'lingjing', '.env')); } catch { /* 可选 */ }

const { cfg, arkEnabled } = await import('../server/lib/ark.js');
const c = cfg();
const mask = (k) => (k ? k.slice(0, 4) + '****' + k.slice(-4) + `（${k.length}字符）` : '（空）');

console.log('\n========== 灵境AI 模型诊断 ==========');
console.log('接口地址 :', c.baseUrl);
console.log('API Key  :', mask(c.apiKey), c.apiKey ? '' : '← 没读到 Key！请在设置页填写或写进 .env 的 ARK_API_KEY');
console.log('对话模型 :', c.modelChat);
console.log('图像模型 :', c.modelImage);
console.log('视频模型 :', c.modelVideo);
if (/^AKLT/i.test(c.apiKey)) console.log('⚠️  你的 Key 是 AKLT 开头的 AccessKey，这是错的！要用方舟控制台「API Key 管理」创建的 UUID 形态 Key。');
console.log('=====================================\n');

if (!arkEnabled()) { console.log('❌ 未检测到有效 Key，无法诊断。先配置后再跑。\n'); process.exit(1); }

// 直接打原始 HTTP，拿到火山最详细的报错体
async function rawCall(label, pathname, body, hint) {
  process.stdout.write(`【${label}】${pathname}\n`);
  const t0 = Date.now();
  try {
    const resp = await fetch(c.baseUrl + pathname, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${c.apiKey}` },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60_000)
    });
    const text = await resp.text();
    const ms = Date.now() - t0;
    if (resp.ok) {
      console.log(`  ✅ 成功 HTTP ${resp.status}（${ms}ms）`);
    } else {
      console.log(`  ❌ 失败 HTTP ${resp.status}（${ms}ms）`);
      console.log(`  火山原始返回：${text.slice(0, 500)}`);
      if (hint) console.log(`  👉 ${hint}`);
    }
  } catch (e) {
    console.log(`  ❌ 请求异常：${e.message}`);
    console.log('  👉 可能是网络/地域问题：确认能访问 ' + c.baseUrl + '，或换成你模型所在地域的接口地址。');
  }
  console.log('');
}

await rawCall('① 对话/剧本', '/chat/completions',
  { model: c.modelChat, messages: [{ role: 'user', content: '回复:1' }], max_tokens: 8 },
  '对话模型没开通或 ID 不对：去控制台「开通管理」开通豆包语言模型，把准确 Model ID 或推理接入点 ep-xxxx 填到设置页。');

await rawCall('② 图像 Seedream', '/images/generations',
  { model: c.modelImage, prompt: '一只猫坐在窗边，写实', size: '1024x1024', response_format: 'b64_json', watermark: false },
  '图像模型没开通/ID 不对，或该模型不收 size 参数：核对控制台里 Seedream 的准确 Model ID。');

await rawCall('③ 视频 Seedance（重点）', '/contents/generations/tasks',
  { model: c.modelVideo, content: [{ type: 'text', text: '一只猫眨眼 --ratio 16:9 --duration 5' }] },
  '视频走本地多半因此：①很多账号视频要用「推理接入点 ep-xxxx」而非模型名——控制台「在线推理→创建接入点」拿到 ep- ID 填到设置页"视频模型"；②该 Seedance 未开通；③地域与接口地址不符。');

console.log('诊断完成。把上面失败那行的「火山原始返回」复制发给开发者即可（不要发 Key）。\n');
