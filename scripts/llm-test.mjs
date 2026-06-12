// 大模型连通性自检：node scripts/llm-test.mjs
// 读取 .env（或环境变量）→ 测试 Chat → 测试导演 JSON 模式，并给出可读的排障建议。
import fs from 'node:fs';

// 轻量 .env 加载（不引第三方库）
try {
  for (const line of fs.readFileSync('.env', 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.+?)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
} catch { /* 没有 .env 就用环境变量 */ }

const BASE = (process.env.LLM_BASE_URL || '').replace(/\/+$/, '');
const KEY = process.env.LLM_API_KEY || '';
const MODEL = process.env.LLM_MODEL_DEFAULT || '';

console.log('\n== 句灵 · 大模型自检 ==');
console.log(`提供方: ${process.env.LLM_PROVIDER || '(未配置)'}`);
console.log(`接口:   ${BASE || '(未配置)'}`);
console.log(`模型:   ${MODEL || '(未配置)'}`);
console.log(`Key:    ${KEY ? KEY.slice(0, 6) + '...' + KEY.slice(-4) : '(未配置)'}\n`);

if (!BASE || !KEY || !MODEL) {
  console.log('❌ 配置不完整。复制 .env.example 为 .env 并填写 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL_DEFAULT');
  process.exit(1);
}
if (/^AKLT/i.test(KEY)) {
  console.log('⚠️  注意：AKLT 开头的是火山引擎「AccessKey ID」（配合 SecretKey 做 OpenAPI 签名用），');
  console.log('   方舟 Chat API 需要的是【方舟控制台 → API Key 管理 → 创建 API Key】生成的密钥（UUID 形态）。');
  console.log('   仍会尝试请求，但大概率返回 401。\n');
}

async function call(name, body) {
  const t0 = Date.now();
  try {
    const resp = await fetch(`${BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(20_000)
    });
    const text = await resp.text();
    if (!resp.ok) {
      console.log(`❌ ${name}: HTTP ${resp.status}（${Date.now() - t0}ms）`);
      console.log('   响应: ' + text.slice(0, 300));
      if (resp.status === 401) console.log('   → Key 无效：去方舟控制台创建 API Key，并确认已开通模型/创建推理接入点');
      if (resp.status === 404) console.log('   → 模型名不对：填方舟的 Model ID（如 doubao-seed-1-6-flash-250615）或接入点 ID（ep-xxxx）');
      if (resp.status === 429) console.log('   → 触发限流/额度不足：检查方舟账户余额与 RPM 配额');
      return null;
    }
    const data = JSON.parse(text);
    const out = data.choices?.[0]?.message?.content || '';
    console.log(`✅ ${name}（${Date.now() - t0}ms，tokens ${data.usage?.prompt_tokens}+${data.usage?.completion_tokens}）`);
    console.log('   输出: ' + out.slice(0, 160).replace(/\n/g, ' '));
    return out;
  } catch (e) {
    console.log(`❌ ${name}: ${e.message}`);
    console.log('   → 网络不通：确认本机可访问 ' + BASE + '（云服务器注意出网策略/安全组）');
    return null;
  }
}

const a = await call('基础对话', {
  model: MODEL, max_tokens: 30,
  messages: [{ role: 'user', content: '用5个字夸一下今天的天气' }]
});

if (a) {
  await call('导演 JSON 模式（文字变动画）', {
    model: MODEL, max_tokens: 300, temperature: 0.7,
    response_format: { type: 'json_object' },
    messages: [
      { role: 'system', content: '你是"句灵"的动画导演。根据文案输出 JSON 补丁：{"scene_name":"短场景名","caption":"20字内画面旁白","arousal":0.4,"ambient":"wind","add_particles":[{"kind":"windline","density":0.5}]}。只输出 JSON。' },
      { role: 'user', content: '文案：「我在等风，也在等你。」' }
    ]
  });
  console.log('\n🎉 全部通过！服务端启动后即自动启用大模型导演/暖场/机审。');
} else {
  console.log('\n💡 未通过也不影响运行：句灵会自动使用本地规则引擎（零成本）。修好配置后重启即可。');
}
