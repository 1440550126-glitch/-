require('./env');
const { run } = require('./db');
const pickModel = (task) => {
  const gateway = process.env.MODEL_GATEWAY_ENABLED === 'true';
  const key = task === 'cheap' ? 'CHEAP_TEXT_MODEL' : task === 'strong' ? 'STRONG_TEXT_MODEL' : task === 'code' ? 'CODE_MODEL' : task === 'vision' ? 'VISION_MODEL' : task === 'embedding' ? 'EMBEDDING_MODEL' : 'DEFAULT_TEXT_MODEL';
  return gateway && process.env[`MODEL_GATEWAY_${key}`] ? process.env[`MODEL_GATEWAY_${key}`] : process.env[key];
};
async function callOpenAICompat({ baseUrl, apiKey, model, prompt }) {
  const url = `${baseUrl.replace(/\/$/, '')}/chat/completions`;
  const res = await fetch(url, { method:'POST', headers:{ 'Authorization':`Bearer ${apiKey}`, 'Content-Type':'application/json' }, body: JSON.stringify({ model, messages:[{role:'user', content:prompt}], temperature:0.7 }) });
  if (!res.ok) throw new Error(`provider_http_${res.status}`);
  const json = await res.json();
  return json.choices?.[0]?.message?.content || JSON.stringify(json).slice(0, 2000);
}
function mockText(module, prompt) {
  return `LingMirror AI v1.0 LTS 商用冻结版 mockProvider fallback\nModule: ${module}\n\nCommercial output plan:\n- Core idea: ${prompt.slice(0, 140)}\n- Audience: overseas buyers and operators\n- Deliverables: script, offer angle, scene plan, visual direction, CTA, memory notes\n- Compliance: no automatic payment crediting, no fake real-video success.`;
}
async function aiGenerate({ userId, projectId = null, module, task = 'default', prompt }) {
  let provider = 'mockProvider', model = pickModel(task) || 'mock-model', gateway_used = 0, fallback_used = 1, error_message = null, text = '';
  const attempts = [];
  if (process.env.MODEL_GATEWAY_ENABLED === 'true' && process.env.MODEL_GATEWAY_BASE_URL && process.env.MODEL_GATEWAY_API_KEY) attempts.push(['gateway', process.env.MODEL_GATEWAY_BASE_URL, process.env.MODEL_GATEWAY_API_KEY, pickModel(task)]);
  if (process.env.ENABLE_REAL_API === 'true' && process.env.VOLCENGINE_ARK_API_KEY && process.env.VOLCENGINE_ENABLE_TEXT !== 'false') attempts.push(['volcengine', process.env.VOLCENGINE_ARK_BASE_URL, process.env.VOLCENGINE_ARK_API_KEY, process.env[task === 'cheap' ? 'CHEAP_TEXT_MODEL' : task === 'strong' ? 'STRONG_TEXT_MODEL' : 'DEFAULT_TEXT_MODEL'] || pickModel(task)]);
  for (const [p, base, key, m] of attempts) {
    try { text = await callOpenAICompat({ baseUrl: base, apiKey: key, model: m, prompt }); provider = p; model = m; gateway_used = p === 'gateway' ? 1 : 0; fallback_used = 0; error_message = null; break; }
    catch (e) { error_message = `${p}:${e.message}`; }
  }
  if (!text) text = mockText(module, prompt);
  const input_tokens = Math.ceil(prompt.length / 4), output_tokens = Math.ceil(text.length / 4);
  const estimated_cost = fallback_used ? 0 : Number(((input_tokens + output_tokens) * 0.000002).toFixed(6));
  const user_charge = module === 'copy-lab' ? 0.05 : module === 'project' ? 2 : 0.1;
  const actual_cost = estimated_cost, profit = Number((user_charge - actual_cost).toFixed(6));
  const profit_margin = user_charge ? Number((profit / user_charge).toFixed(4)) : 0;
  await run(`INSERT INTO api_usage_logs (user_id,project_id,module,provider,model,gateway_used,fallback_used,input_tokens,output_tokens,estimated_cost,actual_cost,user_charge,profit,profit_margin,error_message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`, [userId, projectId, module, provider, model, gateway_used, fallback_used, input_tokens, output_tokens, estimated_cost, actual_cost, user_charge, profit, profit_margin, error_message]);
  return { text, provider, model, gateway_used: !!gateway_used, fallback_used: !!fallback_used, real_api: !fallback_used };
}
module.exports = { aiGenerate, pickModel };
