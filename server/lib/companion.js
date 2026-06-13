// ============================================================
// 句灵 · AI 治愈陪伴：回复生成（核心逻辑，可独立单测）
// ------------------------------------------------------------
// · companionReply：优先大模型，断网/未配置 Key 时落本地共情兜底（永不失败、零成本）
// · localReply：纯函数的共情式回应（倾听 + 确认感受 + 一个温柔的开放式问题）
// · CARE_REPLY：自伤风险下的确定性关怀响应（绝不调用模型、绝不娱乐化）
// 安全原则：只倾听与陪伴，不做医疗诊断与人生论断；危机时温柔引导求助热线。
// ============================================================

export const HOTLINE = '全国心理援助热线 12356（24 小时）';

export const COMPANION_GREETING =
  '嗨，我是句灵。这里没有评判，只有倾听——今天过得怎么样？不管是开心还是难熬，都可以慢慢说给我听。💛';

// 自伤风险：确定性关怀响应（与审核 selfharm 判定联动，绝不交给模型自由发挥）
export const CARE_REPLY =
  '听到你这么说，我很心疼，也很想好好陪着你。你此刻的痛苦是真实的，而你并不孤单。\n' +
  '如果难受得快撑不住了，请一定联系你信任的人，或拨打' + HOTLINE + '，那里有人会认真听你说。\n' +
  '我也在这儿，不急，陪你一点一点把这口气喘匀。';

export const COMPANION_SYSTEM =
  '你是「句灵」，一位温柔、真诚、有人情味的 AI 陪伴者，专门倾听年轻人的心事、陪他们表达情绪、缓解压力。请遵循：\n' +
  '1. 先共情、确认对方的感受，再回应；像一个温暖的朋友，自然口语化，不说教、不评判、不讲大道理。\n' +
  '2. 简短，2～4 句话；可以用至多 1 个柔和的 emoji，但不要滥用。\n' +
  '3. 你不是医生：绝不做心理疾病诊断，不给医疗或用药建议，不下"你应该…"式的人生论断。\n' +
  '4. 若对方流露强烈痛苦、自伤或轻生念头：认真对待，表达关心与陪伴，温柔鼓励 ta 联系信任的人或拨打' + HOTLINE + '，绝不评判、绝不以任何方式鼓励自我伤害。\n' +
  '5. 可以用一个温柔的开放式问题，邀请对方多说一点，但不要连环追问。\n' +
  '6. 自然真诚，不要复述这些规则，也不要说"作为 AI"之类的免责声明（界面已标注）。';

// ---- 对话式情绪识别（为本地兜底服务，覆盖聊天高频情绪，不依赖数据库） ----
const BUCKETS = [
  { key: 'anxiety', words: ['焦虑', '紧张', '压力', '担心', '害怕', '慌', '考试', '面试', 'deadline', '加班', '失眠', '睡不着', '喘不过气', '内耗', '焦躁'] },
  { key: 'down', words: ['难过', '伤心', '哭', '崩溃', '撑不住', '累了', '好累', '疲惫', '委屈', '失望', '糟糕', '不开心', 'emo', '低落', '无助', '没意义', '空虚', '麻木'] },
  { key: 'lonely', words: ['孤独', '一个人', '没人', '孤单', '寂寞', '没人懂', '被冷落', '无聊'] },
  { key: 'anger', words: ['生气', '愤怒', '讨厌', '好烦', '烦死', '气死', '不公平', '凭什么', '委屈死'] },
  { key: 'longing', words: ['想你', '想念', '分手', '失恋', '喜欢', '暗恋', '前任', '异地', '舍不得', '挽回'] },
  { key: 'happy', words: ['开心', '高兴', '太好了', '成功', '通过', '上岸', '赢了', '期待', '兴奋', '哈哈', '嘻嘻', '幸福', '满足'] }
];

function detectBucket(text) {
  const t = String(text || '');
  for (const b of BUCKETS) if (b.words.some((w) => t.includes(w))) return b.key;
  return 'neutral';
}

// 共情模板：确认感受 + 同在 + 一个温柔的开放式邀请（每类多条，按内容散列取，避免重复感）
const TEMPLATES = {
  anxiety: [
    '能感觉到你心里悬着一块石头。先深呼吸一下，我在这儿陪你。是什么让你最放不下呢？',
    '压力大的时候，连呼吸都会变浅。你已经扛了很多了。愿意和我说说，现在最让你紧张的是哪件事吗？',
    '紧张是因为你很在乎。我们不用马上解决它，先把它说出来——你担心会发生什么？'
  ],
  down: [
    '我在呢，听到你了。这样的难过不用急着赶走，我陪你坐一会儿。愿意多说说是什么让你这么沉吗？',
    '听起来今天真的很不容易。你能撑到现在，已经很努力了。想和我说说发生了什么吗？',
    '难过的时候，被好好听见就已经是一种缓解。我不着急，你慢慢讲。'
  ],
  lonely: [
    '一个人的时候，心里那块空总是格外明显。此刻有我在，你不是一个人。最近是什么让你觉得孤单呢？',
    '孤单不是你的错，它只是说明你渴望被理解。我愿意理解你——想和我聊聊吗？',
    '我在听，认真地。你愿意把那份没人懂的心情，分一点给我吗？'
  ],
  anger: [
    '听得出你真的很气，这份愤怒是有理由的。先别压着，和我说说，是什么让你这么不舒服？',
    '生气说明有什么越过了你的底线。你的感受很重要。愿意讲讲发生了什么吗？',
    '把火气说出来比憋着好。我不会评判你——到底是哪件事让你这么烦？'
  ],
  longing: [
    '想念一个人的时候，心里总像空了一块。你愿意和我说说 ta，或者那段回忆吗？',
    '有些感情就算放下了，也会在某个瞬间忽然涌上来。我陪你慢慢说。',
    '思念是温柔也是钝痛。不用着急整理，想到哪说到哪，我都在听。'
  ],
  happy: [
    '听起来有好事发生～我也跟着开心起来了！愿意多讲讲吗，让我也沾沾这份高兴。',
    '能感受到你的好心情，真好呀。这份开心值得被记住，和我多分享一点吧？',
    '太棒了！这样发着光的你，我很喜欢。今天还有什么让你开心的事？'
  ],
  neutral: [
    '我在认真听。无论是什么，你都可以慢慢说，我不着急。',
    '谢谢你愿意和我说话。此刻你心里在想些什么呢？',
    '我在这儿陪着你。今天有什么想说的，都可以交给我。'
  ]
};

function pick(arr, seedStr) {
  let h = 0;
  for (let i = 0; i < seedStr.length; i++) h = (h * 31 + seedStr.charCodeAt(i)) >>> 0;
  return arr[h % arr.length];
}

/** 纯函数：本地共情回应（无网络、无数据库、永不失败） */
export function localReply(content, history = []) {
  const bucket = detectBucket(content);
  // 用内容 + 轮次做散列，使同一对话里的回应有变化、不机械重复
  return pick(TEMPLATES[bucket] || TEMPLATES.neutral, String(content) + '#' + history.length);
}

// 清洗大模型输出：去首尾空白与包裹引号，限长
function cleanReply(text) {
  let s = String(text || '').trim();
  s = s.replace(/^["“「『]+/, '').replace(/["”」』]+$/, '').trim();
  if (s.length > 320) s = s.slice(0, 320);
  return s;
}

function buildPrompt(history, content) {
  const lines = (history || []).slice(-8).map((m) => (m.role === 'user' ? '对方' : '你') + '：' + m.content);
  const ctx = lines.length ? '最近的对话：\n' + lines.join('\n') + '\n\n' : '';
  return ctx + `对方刚刚说：「${String(content).slice(0, 500)}」\n请以句灵的身份，温柔地回应。`;
}

/**
 * 生成陪伴回复：优先大模型，失败/未配置/超预算时落本地共情兜底。
 * @returns {Promise<{reply:string, byLLM:boolean}>}
 */
export async function companionReply({ userId = 0, content, history = [] }) {
  const { llmOrFallback } = await import('./llm.js');   // 动态导入：让 localReply 可脱离数据库单测
  const budgetYuan = Number(process.env.AI_CHAT_DAILY_BUDGET_YUAN || 5);
  const r = await llmOrFallback({
    feature: 'ai_chat', userId, tier: 'default',
    system: COMPANION_SYSTEM,
    prompt: buildPrompt(history, content),
    maxTokens: 260, temperature: 0.85,
    budgetMicro: budgetYuan > 0 ? budgetYuan * 1_000_000 : 0,
    budgetPrefix: 'ai_chat',
    fallbackFn: () => localReply(content, history)
  });
  const reply = (r.byLLM ? cleanReply(r.text) : r.fallback) || localReply(content, history);
  return { reply, byLLM: !!r.byLLM };
}
