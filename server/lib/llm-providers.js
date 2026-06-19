// 灵阵 · 推荐大模型清单（全部 OpenAI 兼容）。用户自带 Key(BYOK)，自由选择。
// 只存元信息与默认型号，便于前端选择器预填；用户可改 base_url / 模型名。
export const LLM_PROVIDERS = [
  {
    id: 'doubao', name: '豆包 Doubao', vendor: '字节·火山方舟', emoji: '🅑',
    base_url: 'https://ark.cn-beijing.volces.com/api/v3',
    models: { default: 'doubao-seed-1-6-flash-250615', premium: 'doubao-seed-1-6-250615' },
    apply: 'https://console.volcengine.com/ark', recommend: '中文强、最便宜、低延迟，首选',
    key_hint: '方舟控制台 → API Key 管理 创建（不是 AKLT 开头的 AccessKey）'
  },
  {
    id: 'deepseek', name: 'DeepSeek', vendor: '深度求索', emoji: '🐋',
    base_url: 'https://api.deepseek.com/v1',
    models: { default: 'deepseek-chat', premium: 'deepseek-chat' },
    apply: 'https://platform.deepseek.com', recommend: '推理强、性价比高，验收/整合更狠',
    key_hint: 'platform.deepseek.com → API keys 创建'
  },
  {
    id: 'qwen', name: '通义千问 Qwen', vendor: '阿里·百炼', emoji: '🟣',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: { default: 'qwen-turbo', premium: 'qwen-plus' },
    apply: 'https://bailian.console.aliyun.com', recommend: '生态全、稳定',
    key_hint: '百炼控制台 → API-KEY 创建'
  },
  {
    id: 'moonshot', name: 'Kimi', vendor: '月之暗面', emoji: '🌙',
    base_url: 'https://api.moonshot.cn/v1',
    models: { default: 'moonshot-v1-8k', premium: 'moonshot-v1-32k' },
    apply: 'https://platform.moonshot.cn', recommend: '超长上下文',
    key_hint: 'platform.moonshot.cn → API Key'
  },
  {
    id: 'zhipu', name: '智谱 GLM', vendor: '智谱 AI', emoji: '🧠',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: { default: 'glm-4-flash', premium: 'glm-4-plus' },
    apply: 'https://open.bigmodel.cn', recommend: 'flash 免费额度大，适合先试',
    key_hint: 'open.bigmodel.cn → API Keys'
  },
  {
    id: 'openai', name: 'OpenAI', vendor: 'OpenAI', emoji: '🟢',
    base_url: 'https://api.openai.com/v1',
    models: { default: 'gpt-4o-mini', premium: 'gpt-4o' },
    apply: 'https://platform.openai.com', recommend: '质量稳；海外、USD 计费',
    key_hint: 'platform.openai.com → API keys（需海外网络）'
  },
  {
    id: 'custom', name: '自定义', vendor: '任意 OpenAI 兼容端点', emoji: '⚙️',
    base_url: '', models: { default: '', premium: '' },
    apply: '', recommend: '自建 / 其它兼容服务，自填 base_url 与模型名',
    key_hint: '填写 /chat/completions 所在的 base_url'
  }
];

export const findProvider = (id) => LLM_PROVIDERS.find((p) => p.id === id);
