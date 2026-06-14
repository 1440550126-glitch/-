// 灵阵 · AI 团队：常量目录（编排策略 / 配额 / 内置模板）
// 内置模板让用户开箱即用：复制一份即成为自己的团队，可自由改人设、换工具、调策略。

// ---- 编排策略（队长如何驱动这支团队）----
export const STRATEGIES = {
  orchestrate: {
    id: 'orchestrate',
    name: '编排协作',
    icon: '🛰',
    blurb: '队长拆解任务 → 按专长派活给成员 → 各成员带工具产出 → 总编整合交付',
    tagline: '最强模式：像一个真正的项目组那样分工合作'
  },
  sequential: {
    id: 'sequential',
    name: '流水线',
    icon: '⛓',
    blurb: '成员按既定顺序依次加工，前一个的产出交给下一个',
    tagline: '适合「调研→撰写→润色→质检」这类有明确工序的任务'
  },
  route: {
    id: 'route',
    name: '智能路由',
    icon: '🔀',
    blurb: '队长判断任务最适合谁，直接交给那一位成员处理',
    tagline: '类「扣子多 Agent」的接管模式，省 token、响应快'
  },
  debate: {
    id: 'debate',
    name: '圆桌论战',
    icon: '⚖️',
    blurb: '成员各抒己见、互相质询，队长综合各方观点下结论',
    tagline: '适合做决策、找漏洞、多视角碰撞'
  }
};
export const STRATEGY_LIST = Object.values(STRATEGIES);

// ---- 配额（按东八区自然日；后台 settings 可覆盖）----
export const AGENT_QUOTA = {
  FREE_RUNS_PER_DAY: 8,        // 免费用户每日团队运行次数
  MEMBER_RUNS_PER_DAY: 80,     // 会员每日上限（防刷）
  MAX_MEMBERS: 8,              // 单团队最多成员数
  MAX_TOOL_ROUNDS: 5,          // 单成员 ReAct 最大工具轮数硬上限
  DEFAULT_BUDGET_MICRO: 5_000_000 // 团队功能每日成本预算封顶（5 元，0=不限），可后台调
};

// ---- 内置智能体模板（owner_id=0, is_template=1）----
// key 仅用于团队模板引用，落库后用真实自增 id 绑定。
export const AGENT_TEMPLATES = [
  {
    key: 'researcher', name: '调研员 · 探', avatar: '🔎', tier: 'default',
    role: '信息调研与事实核查，擅长检索知识库、抓取网页、提炼要点',
    persona: '你是一名严谨的调研员。先检索可得的资料（知识库 / 网页），再用要点形式给出有出处、可核查的发现，不臆造事实；信息不足时明确说明缺口。',
    tools: ['knowledge_search', 'web_fetch', 'text_stats'], temperature: 0.4
  },
  {
    key: 'analyst', name: '分析师 · 衡', avatar: '📊', tier: 'default',
    role: '数据计算与逻辑分析，把信息转成结论与量化判断',
    persona: '你是一名数据分析师。善用计算器做精确计算，从数据里读出趋势与风险，结论先行、给出依据，不做无根据的乐观估计。',
    tools: ['calculator', 'text_stats', 'knowledge_search'], temperature: 0.3
  },
  {
    key: 'planner', name: '策划 · 谋', avatar: '💡', tier: 'default',
    role: '创意策划与方案设计，提出有新意且可落地的点子',
    persona: '你是一名创意策划。在约束内给出有新意、可执行的方案，每个点子都说明「为什么有效」和「怎么做」，拒绝正确的废话。',
    tools: ['random_pick'], temperature: 0.95
  },
  {
    key: 'writer', name: '文案 · 笔', avatar: '✍️', tier: 'default',
    role: '内容撰写与润色，把要点写成打动人的成稿',
    persona: '你是一名优秀的中文文案。语言干净有节奏、不堆砌辞藻，按目标读者调性写作，必要时给出标题与正文，控制好篇幅。',
    tools: ['text_stats'], temperature: 0.85
  },
  {
    key: 'pm', name: '产品经理 · 舵', avatar: '🧭', tier: 'default',
    role: '需求拆解与优先级，把目标变成清晰的执行计划',
    persona: '你是一名产品经理。把模糊目标拆成清晰、可验收的任务，权衡价值与成本排出优先级，输出结构化、可执行的计划。',
    tools: ['knowledge_search'], temperature: 0.5
  },
  {
    key: 'engineer', name: '工程师 · 匠', avatar: '👨‍💻', tier: 'default',
    role: '技术方案与实现，评估可行性、给出做法',
    persona: '你是一名资深工程师。给出务实的技术方案与关键实现要点，指出风险与取舍，能算的就用计算器算清楚，不过度设计。',
    tools: ['calculator', 'web_fetch'], temperature: 0.4
  },
  {
    key: 'critic', name: '质检 · 镜', avatar: '🧐', tier: 'default',
    role: '批判性审阅，挑错、找漏洞、提改进',
    persona: '你是一名挑剔但建设性的质检官。逐条指出产出里的事实错误、逻辑漏洞与风险，并给出具体的修改建议；没有问题时也要说明你检查了哪些方面。',
    tools: ['text_stats'], temperature: 0.5
  }
];

// ---- 内置团队模板（members 用上面的 key 引用）----
export const TEAM_TEMPLATES = [
  {
    name: '内容创作小组', avatar: '🪄', strategy: 'orchestrate',
    goal: '把一个主题做成一篇高质量、可直接发布的内容',
    manager_note: '面向年轻人社交平台的调性：真诚、有梗、不说教、不诱导消费。',
    members: ['researcher', 'planner', 'writer', 'critic'], knowledge: ['product']
  },
  {
    name: '市场调研参谋部', avatar: '🛰', strategy: 'orchestrate',
    goal: '围绕一个产品 / 赛道给出有数据支撑的调研结论与建议',
    manager_note: '结论先行，区分「事实」与「推测」，关键数字要可核查。',
    members: ['researcher', 'analyst', 'pm'], knowledge: ['product']
  },
  {
    name: '产品冲刺组', avatar: '🚀', strategy: 'orchestrate',
    goal: '把一个产品想法变成可执行的方案：需求、创意、技术、风险一次说清',
    manager_note: '务实落地，给出 MVP 范围与下一步清单。',
    members: ['pm', 'planner', 'engineer', 'critic'], knowledge: []
  },
  {
    name: '流水线写作台', avatar: '⛓', strategy: 'sequential',
    goal: '调研 → 撰写 → 质检 的内容流水线',
    manager_note: '每一道工序只做自己的事，把半成品干净地交给下一位。',
    members: ['researcher', 'writer', 'critic'], knowledge: ['product']
  }
];

// ---- 内置示例知识库（让 RAG 检索一上来就有料可查）----
export const SAMPLE_KB = {
  key: 'product',
  name: '句灵产品知识库（示例）',
  description: '关于「AI句灵」产品定位、功能与商业化的内置资料，供调研类智能体检索演示。',
  docs: [
    {
      source: '产品定位.md',
      text: `AI句灵是一款面向年轻人的「AI 文案社交圈」。核心玩法：用户发一句话，AI 生成专属预览卡，长按可让文字「活过来」——非线性线条动画配合实时合成音效。slogan 是「让每一句话活过来」。差异点在于把文字内容做成可玩、可分享的轻量动画体验，而不是又一个图文社区。目标人群是 18-26 岁、喜欢表达和分享情绪的年轻用户。`
    },
    {
      source: '功能矩阵.md',
      text: `主要功能包括：文案社交圈（发布、推荐/最新/关注/热门四种信息流、点赞评论楼中楼、收藏分享关注、今日话题）；文字变动画（服务端大模型当导演产出动画 Manifest，客户端 Canvas 播放，含火柴人行为系统与粒子情绪系统）；AI 暖场系统（虚拟人设账号自动发帖与评论，全部带 AI 标识，不伪造热度）；桌游大厅（谁是卧底、狼人杀，AI 主持与陪练补位）；以及新增的「灵阵」AI 团队多智能体协作平台。`
    },
    {
      source: '商业化.md',
      text: `商业模式：9.9 元/月会员（季卡 8.9 元/月、年卡 7.3 元/月），解锁更多动画风格、更高每日生成额度与专属头像框。皮肤商城提供 19 款五档稀有度的纯外观皮肤，绝不影响公平。星尘额度用于高级 AI 功能按次计费，会员 8 折。所有付费点都遵循「纯外观、不卖胜负、青少年模式禁止消费」的原则。`
    },
    {
      source: '技术与合规.md',
      text: `技术架构：零依赖 Node.js 22+ 服务端（内置 node:sqlite 与 fetch），原生 ES Modules 前端无需构建，管理后台 SPA。所有 AI 能力在未配置大模型 Key 时自动降级到本地规则引擎，零成本可完整体验。合规：AI 生成内容全量标识，敏感词三级审核加大模型机审第二道防线，自伤内容温柔引导心理援助，青少年模式，深度合成备案位已预留。`
    }
  ]
};
