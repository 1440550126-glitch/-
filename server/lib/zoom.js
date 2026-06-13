// ============================================================
// 句灵 · 无限放大（Infinite Semantic Zoom）
// ------------------------------------------------------------
// 取「无限语义放大」demo 之神：从一句话/一种情绪出发，逐层放大下钻，
// 每一层由 AI 现生成更深入的「世界帧」（标题 + 一句旁白 + 若干可继续
// 放大的子焦点）。面包屑记录路径。无图像模型——用程序化插画呈现，
// LLM 不可用时落本地生成器，零成本、离线、永不失败。
// ============================================================

const MOTIFS = ['city', 'nature', 'cosmos', 'heart', 'memory', 'abstract'];

const MOTIF_RULES = [
  { motif: 'heart', words: ['爱', '喜欢', '心', '想你', '思念', '拥抱', '眼泪', '孤独', '难过', '温柔', '告白', '心动', '失恋', '陪'] },
  { motif: 'city', words: ['城市', '街', '楼', '地铁', '咖啡', '霓虹', '车', '巴黎', '夜晚', '灯', '人群', '广场'] },
  { motif: 'nature', words: ['海', '山', '树', '花', '风', '雨', '雪', '森林', '溪', '草', '云', '春', '叶'] },
  { motif: 'cosmos', words: ['星', '宇宙', '银河', '月', '光年', '黑洞', '太空', '星云', '极光', '深空'] },
  { motif: 'memory', words: ['回忆', '童年', '从前', '旧', '那年', '记得', '外婆', '故乡', '老', '曾经', '信'] }
];

const HOTSPOTS = {
  city: ['街角的灯', '一扇亮着的窗', '屋顶之上', '地铁的尽头', '钟楼里', '旧书摊', '雨后的路面', '深夜咖啡馆'],
  nature: ['一片叶脉', '溪流尽头', '林间空地', '花的内部', '一滴露水', '远山之后', '风的来处', '苔藓深处'],
  cosmos: ['一颗孤星', '星云深处', '黑洞边缘', '光年之外', '一粒宇宙尘', '引力的形状', '绝对的寂静', '极光之下'],
  heart: ['那句没说出口的话', '心跳之间', '眼泪里', '一次拥抱', '旧照片背面', '一个名字', '余温', '裂缝里的光'],
  memory: ['童年的夏天', '一扇旧木门', '走廊的尽头', '褪色的信', '那年的歌', '厨房的香气', '空荡的操场', '停摆的钟'],
  abstract: ['更深的一层', '缝隙之间', '第七种颜色', '沉默的形状', '边界之外', '水面的倒影', '一阵回声', '折叠的时间']
};

const EMOJI = {
  city: ['🌆', '🪟', '🏙', '🚇', '🔔', '📚', '🌧', '☕'],
  nature: ['🍃', '💧', '🌲', '🌸', '✨', '⛰', '🌬', '🍄'],
  cosmos: ['⭐', '🌌', '🕳', '🚀', '✦', '🌠', '🌑', '🌈'],
  heart: ['💗', '💓', '💧', '🤍', '📷', '🔖', '🔥', '🌱'],
  memory: ['🌻', '🚪', '🕯', '✉️', '🎵', '🍲', '🛝', '🕰'],
  abstract: ['🌀', '🔮', '🎨', '🫧', '🧭', '🪞', '📡', '⏳']
};

const BLURBS = {
  city: ['霓虹在水洼里碎成星河，这座城从不真正入睡。', '推开这扇窗，是另一个人的整个夜晚。', '钢筋与心跳一起，在街角拐了个弯。'],
  nature: ['世界在一片叶子里重新开始呼吸。', '风走过的地方，都留下了温柔的形状。', '万物在此刻安静地、用力地活着。'],
  cosmos: ['在这里，光也要走上千年才能抵达。', '尘埃与星辰，本是同一种孤独。', '宇宙用寂静，回答着所有的喧嚣。'],
  heart: ['有些话太重，只能轻轻地放在这里。', '心跳之间的缝隙，藏着整个你。', '原来温柔，是可以被放大的。'],
  memory: ['时间在这里打了个结，舍不得松开。', '那个夏天还没结束，只是被你藏起来了。', '旧物不说话，却记得所有的事。'],
  abstract: ['再放大一点，意义就溶解成了光。', '越往深处，越接近某种说不出的真相。', '这里没有答案，只有更美的问题。']
};

function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}
function sampleDistinct(arr, n, seed) {
  const idx = arr.map((_, i) => i);
  let s = seed >>> 0;
  for (let i = idx.length - 1; i > 0; i--) { s = (s * 1103515245 + 12345) >>> 0; const j = s % (i + 1); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  return idx.slice(0, Math.min(n, arr.length)).map((i) => arr[i]);
}

export function pickMotif(focus, path = []) {
  const t = String(focus || '') + ' ' + path.join(' ');
  for (const r of MOTIF_RULES) if (r.words.some((w) => t.includes(w))) return r.motif;
  // 无命中 → 由文本散列稳定地选一个（同输入同结果）
  return MOTIFS[hashStr(String(focus || '此刻')) % MOTIFS.length];
}

/** 纯函数：本地生成一帧（无网络/无数据库，永不失败） */
export function localFrame(path = [], focus = '此刻') {
  const f = String(focus || '此刻').trim() || '此刻';
  const depth = path.length;
  const motif = pickMotif(f, path);
  const seed = hashStr(f + '#' + depth);
  const labels = sampleDistinct(HOTSPOTS[motif], 4, seed);
  const emo = EMOJI[motif];
  const hotspots = labels.map((label, i) => ({ label, emoji: emo[(seed + i) % emo.length], hint: '继续放大 →' }));
  const blurb = BLURBS[motif][seed % BLURBS[motif].length];
  return { title: f.slice(0, 14), blurb, hotspots, motif, depth, by: 'local' };
}

const SAFE_MOTIF = (m) => (MOTIFS.includes(m) ? m : 'abstract');

function sanitizeFrame(raw, path, focus) {
  if (!raw || typeof raw !== 'object') return localFrame(path, focus);
  const base = localFrame(path, focus);
  const title = typeof raw.title === 'string' && raw.title.trim() ? raw.title.trim().slice(0, 16) : base.title;
  const blurb = typeof raw.blurb === 'string' && raw.blurb.trim() ? raw.blurb.trim().slice(0, 48) : base.blurb;
  const motif = SAFE_MOTIF(raw.motif);
  let hotspots = Array.isArray(raw.hotspots) ? raw.hotspots
    .filter((h) => h && typeof h.label === 'string' && h.label.trim())
    .slice(0, 5)
    .map((h, i) => ({
      label: h.label.trim().slice(0, 12),
      emoji: (typeof h.emoji === 'string' && [...h.emoji].length <= 2 && h.emoji.trim()) ? h.emoji.trim() : EMOJI[motif][i % EMOJI[motif].length],
      hint: typeof h.hint === 'string' ? h.hint.trim().slice(0, 16) : '继续放大 →'
    })) : [];
  if (hotspots.length < 2) hotspots = base.hotspots;   // 至少要能继续放大
  return { title, blurb, hotspots, motif, depth: path.length, by: 'llm' };
}

/** AI 生成下一帧：优先大模型，失败/未配置/超预算时落本地生成器 */
export async function generateFrame({ path = [], focus = '此刻', userId = 0 }) {
  const { llmOrFallback } = await import('./llm.js');   // 动态导入：localFrame 可脱离数据库单测
  const trail = path.length ? path.join(' → ') : '（起点）';
  const system =
    '你是「句灵·无限放大」的世界生成器。用户正在从一句话/一种情绪出发，一层层向内放大探索。' +
    '根据当前路径与正在聚焦的点，生成"再深入一层"的一帧，要有诗意、有想象力、彼此连贯，像在潜入一个无限世界。' +
    `只输出 JSON：{"title":"≤14字的这一层标题","blurb":"≤40字的一句旁白","motif":"${MOTIFS.join('/')} 之一(画面基调)","hotspots":[{"label":"≤8字可继续放大的子焦点","emoji":"1个emoji","hint":"≤12字提示"}]}（hotspots 给 3~5 个）。不要输出其他内容。`;
  const prompt = `探索路径：${trail}\n当前聚焦：「${String(focus).slice(0, 40)}」\n请生成更深一层的世界帧 JSON。`;
  const { jparse } = await import('./util.js');
  const r = await llmOrFallback({
    feature: 'zoom', userId, tier: 'default',
    system, prompt, json: true, maxTokens: 320, temperature: 0.95,
    budgetMicro: Number(process.env.ZOOM_DAILY_BUDGET_YUAN || 3) * 1_000_000, budgetPrefix: 'zoom',
    fallbackFn: () => null
  });
  if (r.byLLM) return sanitizeFrame(jparse(r.text, null), path, focus);
  return localFrame(path, focus);
}
