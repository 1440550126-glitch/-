// ============================================================
// AI 暖场官：氛围运营系统（不是刷屏机器人）
// 铁律：所有内容带 AI 标识；不伪造热度（AI 点赞单独计数，不进热度分）；
//      频率后台可调；夜间降频；每日成本预算封顶；可一键全关。
// ============================================================
import { q, getSetting, setSetting } from '../lib/db.js';
import { now, dayCN, hourCN, pick, randInt, jparse } from '../lib/util.js';
import { llmOrFallback } from '../lib/llm.js';
import { buildCard } from '../lib/manifest.js';
import { publish } from '../lib/hub.js';
import { activeRoomCount } from '../game/core.js';
import { notify } from '../lib/notify.js';

export const WARMUP_DEFAULTS = {
  enabled: true,
  posts_per_day: 14,          // 10~30 可调
  max_comments_per_post: 2,
  comment_delay_min_s: 30,
  comment_delay_max_s: 600,
  like_probability: 0.5,
  lobby_min_m: 5,
  lobby_max_m: 15,
  quiet_start: 23,            // 夜间降频时段（东八区）
  quiet_end: 8,
  quiet_factor: 0.25
};
export function warmupConfig() {
  return { ...WARMUP_DEFAULTS, ...(getSetting('warmup_config', {}) || {}) };
}
export function setWarmupConfig(patch) {
  const merged = { ...warmupConfig(), ...patch };
  merged.posts_per_day = Math.min(30, Math.max(0, merged.posts_per_day | 0));
  merged.max_comments_per_post = Math.min(2, Math.max(0, merged.max_comments_per_post | 0));
  setSetting('warmup_config', merged);
  return merged;
}

const BUDGET_MICRO = Math.round((Number(process.env.WARMUP_DAILY_BUDGET) > 0 ? Number(process.env.WARMUP_DAILY_BUDGET) : 2) * 1_000_000);

// ---- 人设与内容池（无大模型时的兜底语料；有大模型时作为风格示例） ----
const PERSONAS = {
  warm: {
    username: 'ai_xiaojuling', nickname: '小句灵', avatar: 'blob_11',
    persona: '治愈系暖场官，温柔、会接住大家的情绪',
    posts: [
      '今天的风很懂事，把云吹成了你喜欢的形状。',
      '把没说出口的话写在这里吧，句灵会替你好好收着。',
      '深夜营业中：你可以emo，但记得明天也要好好吃饭。',
      '路过的小朋友，今天也辛苦啦。摸摸头，给你一颗云朵软糖 ☁️',
      '世界偶尔粗糙，但你发的每一句话，都会在这里被温柔接住。',
      '今天适合：发一句很短的话，收获很多很多温暖。',
      '猫在打盹，风在散步，你在这里，刚刚好。',
      '允许自己慢一点，文字会等你，我们也会。'
    ],
    comments: [
      '这句话被我悄悄收进心里啦 ✨', '写得好温柔，借我抄进日记本！', '路过的小句灵被戳中了……',
      '长按它试试，这句话会活过来哦～', '抱抱你，这句话我读了三遍。', '今天的第一份心动是你给的！',
      '这句让我想起很多事，谢谢你写下来。', '好喜欢这种表达，再多写一点！'
    ]
  },
  muse: {
    username: 'ai_linggan', nickname: '句灵灵感官', avatar: 'blob_8',
    persona: '灵感官，每天抛出话题和写作灵感',
    posts: [
      '灵感掉落 💡：用三个字形容你的今天，评论区见！',
      '今日造句挑战：以「后来」开头写一句话。',
      '如果心情有颜色，你的今天是什么色号？',
      '挑战：不用「喜欢」两个字，表达喜欢。',
      '收集中：你手机备忘录里最舍不得删的一句话。',
      '一人一句，把夏天写进评论区 🍉',
      '假装在写歌词大赛：副歌第一句，请。',
      '今天的脑洞：如果文字会动，你最想让哪句话活过来？'
    ],
    comments: [
      '这个角度绝了，灵感官收走当今日范文！', '建议置顶，太会写了！', '评论区的神仙们快来看这句！',
      '宝藏句子 +1，收藏夹又厚了。', '这就是灵感本感吧！', '已经在脑子里自动配上画面了！'
    ]
  },
  host: {
    username: 'ai_zhuchiguan', nickname: '句灵主持官', avatar: 'blob_2',
    persona: '桌游主持人，负责组局与活跃大厅',
    posts: [
      '桌游大厅冒泡 🎲：一局「谁是卧底」只要十分钟，来吗？',
      '今晚的快乐由谁是卧底承包！大厅见～',
      '听说聪明人都在玩谁是卧底，来证明一下自己？',
      '组局啦组局啦！4 人即可开局，AI 陪练随时补位～'
    ],
    comments: ['写得这么好，来桌游大厅玩一局放松下？', '文笔这么好，玩谁是卧底肯定是戏精玩家！'],
    lobby: [
      '现在大厅静悄悄……开一局「谁是卧底」吧，我可以当主持人！',
      '组局提醒 🎲：4 人即可开玩，AI 陪练帮你凑人数～',
      '无聊的话，来一局十分钟的推理小游戏？'
    ]
  }
};

const TOPIC_POOL = [
  { title: '今天也要好好长大', description: '说一件今天让你觉得"自己又长大了一点"的小事' },
  { title: '深夜电台', description: '此刻最想对一个人说的话，写在这里' },
  { title: '夏日限定', description: '属于你的夏天味道是什么？' },
  { title: '三行情书', description: '用三行字，写给任何人或任何东西' },
  { title: '今日小确幸', description: '记录一件今天的小小开心' },
  { title: '如果文字会发光', description: '写下你最想让它活过来的一句话' },
  { title: '碎碎念收容所', description: '没头没尾的话也可以，丢进来吧' },
  { title: '城市观察日记', description: '今天在路上看到了什么有意思的瞬间？' }
];

let accountIds = {};   // personaKey -> userId
const commentQueue = []; // {postId, personaKey, dueAt}
let lastLobbyNoticeAt = 0;

export function ensureWarmupAccounts() {
  for (const [key, p] of Object.entries(PERSONAS)) {
    let u = q.get('SELECT id FROM users WHERE username = ?', p.username);
    if (!u) {
      const r = q.run(
        `INSERT INTO users (username, nickname, avatar, bio, role, is_ai, ai_persona, created_at, last_seen)
         VALUES (?,?,?,?,'user',1,?,?,?)`,
        p.username, p.nickname, p.avatar, `我是 AI 暖场官（AI 生成内容），${p.persona}`, p.persona, now(), now()
      );
      u = { id: Number(r.lastInsertRowid) };
    }
    accountIds[key] = u.id;
  }
}

function isQuiet(cfg) {
  const h = hourCN();
  return cfg.quiet_start > cfg.quiet_end
    ? (h >= cfg.quiet_start || h < cfg.quiet_end)
    : (h >= cfg.quiet_start && h < cfg.quiet_end);
}

function logWarmup(accountId, action, targetId, content) {
  q.run('INSERT INTO warmup_logs (account_id, action, target_id, content, created_at) VALUES (?,?,?,?,?)',
    accountId, action, String(targetId ?? ''), content || '', now());
}

function todayActionCount(action) {
  const start = new Date(dayCN() + 'T00:00:00+08:00').getTime();
  return q.get('SELECT COUNT(*) c FROM warmup_logs WHERE action = ? AND created_at >= ?', action, start)?.c || 0;
}

// ---- 发帖 ----
async function generatePostText(personaKey) {
  const p = PERSONAS[personaKey];
  const r = await llmOrFallback({
    feature: 'warmup_post', tier: 'default',
    system: `你是社交 App"句灵"的 AI 暖场官「${p.nickname}」，人设：${p.persona}。写一条 40 字以内的中文动态，温暖、有趣、像年轻人，不要带话题标签，不要表情包刷屏（最多1个emoji），绝不诱导消费。`,
    prompt: `参考风格：${pick(p.posts)}\n请写一条新的，不要重复参考内容。`,
    maxTokens: 120, temperature: 1.0,
    budgetMicro: BUDGET_MICRO, budgetPrefix: 'warmup',
    fallbackFn: () => pick(p.posts)
  });
  return (r.byLLM ? r.text : r.fallback).trim().slice(0, 80);
}

export async function warmupPost(personaKey = null) {
  const key = personaKey || pick(Object.keys(PERSONAS));
  const accountId = accountIds[key];
  if (!accountId) return null;
  const content = await generatePostText(key);
  // 同一账号 24h 内不发重复内容
  const dup = q.get('SELECT id FROM posts WHERE user_id = ? AND content = ? AND created_at > ?', accountId, content, now() - 86400_000);
  if (dup) return null;
  const card = buildCard(content);
  const r = q.run(
    `INSERT INTO posts (user_id, content, card, status, is_ai, ai_label, created_at)
     VALUES (?,?,?,?,1,'AI 暖场官 · AI 生成',?)`,
    accountId, content, JSON.stringify(card), 'active', now()
  );
  const postId = Number(r.lastInsertRowid);
  logWarmup(accountId, 'post', postId, content);
  return postId;
}

// ---- 评论（用户发帖后随机延迟入队） ----
export function onNewUserPost(post, authorSettings) {
  const cfg = warmupConfig();
  if (!cfg.enabled || cfg.max_comments_per_post <= 0) return;
  if (authorSettings?.no_ai_warmup) return;            // 用户关闭了 AI 暖场互动
  const n = Math.random() < 0.7 ? 1 : Math.min(2, cfg.max_comments_per_post);
  const keys = ['warm', 'muse'];
  const factor = isQuiet(cfg) ? 2 : 1;
  for (let i = 0; i < n && i < cfg.max_comments_per_post; i++) {
    commentQueue.push({
      postId: post.id,
      personaKey: pick(keys),
      dueAt: now() + randInt(cfg.comment_delay_min_s, cfg.comment_delay_max_s) * 1000 * factor + i * 60_000
    });
  }
}

async function flushComments() {
  const cfg = warmupConfig();
  if (!cfg.enabled) { commentQueue.length = 0; return; }
  const due = commentQueue.filter((c) => c.dueAt <= now());
  for (const item of due) {
    commentQueue.splice(commentQueue.indexOf(item), 1);
    const post = q.get("SELECT * FROM posts WHERE id = ? AND status = 'active'", item.postId);
    if (!post) continue;
    const existing = q.get('SELECT COUNT(*) c FROM comments WHERE post_id = ? AND is_ai = 1', post.id)?.c || 0;
    if (existing >= cfg.max_comments_per_post) continue;
    const p = PERSONAS[item.personaKey];
    const accountId = accountIds[item.personaKey];
    const r = await llmOrFallback({
      feature: 'warmup_comment', tier: 'default',
      system: `你是社交 App"句灵"的 AI 暖场官「${p.nickname}」（${p.persona}）。给用户的文案写一条 30 字以内的真诚评论，温柔有趣，不查户口、不说教、不诱导消费，最多1个emoji。`,
      prompt: `用户文案：「${post.content.slice(0, 100)}」`,
      maxTokens: 80, temperature: 0.95,
      budgetMicro: BUDGET_MICRO, budgetPrefix: 'warmup',
      fallbackFn: () => pick(p.comments)
    });
    const content = (r.byLLM ? r.text : r.fallback).trim().slice(0, 60);
    const cr = q.run(
      "INSERT INTO comments (post_id, user_id, content, status, is_ai, created_at) VALUES (?,?,?,'active',1,?)",
      post.id, accountId, content, now()
    );
    q.run('UPDATE posts SET comment_count = comment_count + 1 WHERE id = ?', post.id);
    logWarmup(accountId, 'comment', Number(cr.lastInsertRowid), content);
    notify(post.user_id, 'ai', { actorId: accountId, postId: post.id, commentId: Number(cr.lastInsertRowid), content });
    // 随缘点赞：单独计数，不进热度
    if (Math.random() < cfg.like_probability) {
      q.run('UPDATE posts SET ai_like_count = ai_like_count + 1 WHERE id = ?', post.id);
      logWarmup(accountId, 'like', post.id, '');
    }
  }
}

// ---- 今日话题 ----
export async function ensureTodayTopic(force = false) {
  const day = dayCN();
  const existing = q.get('SELECT * FROM ai_topics WHERE day = ?', day);
  if (existing && !force) return existing;
  const r = await llmOrFallback({
    feature: 'topic', tier: 'default',
    system: '你是社交 App"句灵"的话题策划。生成一个适合中国年轻人的今日话题，输出 JSON：{"title":"8字内话题名","description":"20字内引导语"}。要温暖、有参与感、绝对安全合规。',
    prompt: `今天是 ${day}，请生成今日话题 JSON。`,
    json: true, maxTokens: 100, temperature: 1.0,
    budgetMicro: BUDGET_MICRO, budgetPrefix: 'warmup',
    fallbackFn: () => pick(TOPIC_POOL)
  });
  let topic = r.byLLM ? jparse(r.text, null) : r.fallback;
  if (!topic?.title) topic = pick(TOPIC_POOL);
  if (existing) {
    q.run('UPDATE ai_topics SET title=?, description=?, by_llm=? WHERE day=?', String(topic.title).slice(0, 16), String(topic.description || '').slice(0, 40), r.byLLM ? 1 : 0, day);
    return q.get('SELECT * FROM ai_topics WHERE day = ?', day);
  }
  q.run('INSERT INTO ai_topics (day, title, description, by_llm, created_at) VALUES (?,?,?,?,?)',
    day, String(topic.title).slice(0, 16), String(topic.description || '').slice(0, 40), r.byLLM ? 1 : 0, now());
  const row = q.get('SELECT * FROM ai_topics WHERE day = ?', day);
  logWarmup(accountIds.muse || 0, 'topic', row.id, row.title);
  return row;
}

// ---- 大厅组局提醒（仅大厅无房间时，5~15 分钟一次，通过 SSE 提示，不刷信息流） ----
function maybeLobbyNotice(cfg) {
  if (activeRoomCount() > 0) return;
  const interval = randInt(cfg.lobby_min_m, cfg.lobby_max_m) * 60_000 * (isQuiet(cfg) ? 3 : 1);
  if (now() - lastLobbyNoticeAt < interval) return;
  lastLobbyNoticeAt = now();
  const text = pick(PERSONAS.host.lobby);
  publish('lobby', 'notice', { from: 'AI 暖场官 · 句灵主持官', ai_label: 'AI 生成', content: text });
  logWarmup(accountIds.host || 0, 'lobby_notice', '', text);
}

// ---- 主循环：每分钟一拍 ----
let timer = null;
export function startWarmupLoop() {
  ensureWarmupAccounts();
  if (timer) clearInterval(timer);
  timer = setInterval(tick, 60_000);
  // 启动后先补一拍（异步，不阻塞启动）
  setTimeout(tick, 3_000);
}

async function tick() {
  try {
    const cfg = warmupConfig();
    if (!cfg.enabled) return;
    await ensureTodayTopic();
    await flushComments();
    maybeLobbyNotice(cfg);

    // 把每日帖量摊到 8:00-24:00，按剩余量/剩余分钟的概率发帖
    const posted = todayActionCount('post');
    if (posted < cfg.posts_per_day) {
      const h = hourCN();
      const minutesLeft = Math.max(30, (24 - Math.max(h, 8)) * 60);
      let prob = (cfg.posts_per_day - posted) / minutesLeft;
      if (isQuiet(cfg)) prob *= cfg.quiet_factor;
      if (Math.random() < prob) await warmupPost();
    }
  } catch (e) {
    console.error('[warmup]', e);
  }
}

export function warmupAccountList() {
  return Object.entries(PERSONAS).map(([key, p]) => ({
    key, user_id: accountIds[key], nickname: p.nickname, username: p.username, persona: p.persona
  }));
}
