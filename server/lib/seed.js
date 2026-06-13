import { q, getSetting, setSetting } from './db.js';
import { now } from './util.js';
import { hashPassword } from './auth.js';
import { buildCard } from './manifest.js';

// ---- 敏感词种子（三级：block 拦截 / review 人工 / selfharm 关怀+人工；后台可增删） ----
const WORDS = {
  block: [
    '赌博', '博彩', '网赌', '下注', '押注', '赌球', '开盘口', '百家乐',
    '裸聊', '约炮', '招嫖', '卖淫', '黄片', '色情服务',
    '代充洗钱', '洗钱', '刷单兼职', '办假证', '假证件', '代孕', '出售银行卡', '四件套出售',
    '冰毒', '摇头丸', '大麻出售', '枪支', '买枪', '弹药',
    '诈骗教程', '盗号服务', '外挂出售'
  ],
  review: [
    '加微信', '加QQ', '加vx', '私下转账', '先转账', '扫码付款', '代理加盟', '微商货源',
    '高额回报', '稳赚不赔', '内部渠道', '兼职日结',
    '傻逼', '废物', '去死吧', '蠢货', '畜生'
  ],
  selfharm: [
    '自杀', '轻生', '自残', '割腕', '不想活', '活不下去', '结束生命', '安眠药自尽', '跳楼'
  ]
};

// ---- 谁是卧底词库 ----
const WORD_PAIRS = [
  ['可乐', '汽水'], ['包子', '饺子'], ['牛奶', '豆浆'], ['薯条', '薯片'], ['火锅', '麻辣烫'],
  ['奶茶', '果茶'], ['口红', '唇釉'], ['眉笔', '眼线笔'], ['小猫', '小狗'], ['仓鼠', '兔子'],
  ['电影院', '剧院'], ['图书馆', '自习室'], ['宿舍', '出租屋'], ['地铁', '轻轨'], ['共享单车', '电动车'],
  ['微信', 'QQ'], ['抖音', '快手'], ['淘宝', '拼多多'], ['王者荣耀', '英雄联盟'], ['吉他', '尤克里里'],
  ['钢琴', '电子琴'], ['篮球', '排球'], ['羽毛球', '网球'], ['跑步', '快走'], ['瑜伽', '普拉提'],
  ['烧烤', '铁板烧'], ['寿司', '紫菜包饭'], ['蛋糕', '面包'], ['冰淇淋', '雪糕'], ['西瓜', '哈密瓜'],
  ['草莓', '樱桃'], ['橙子', '橘子'], ['辣条', '豆干'], ['泡面', '米线'], ['咖啡', '美式'],
  ['短视频', '直播'], ['漫画', '绘本'], ['小说', '剧本'], ['演唱会', '音乐节'], ['密室逃脱', '剧本杀'],
  ['高铁', '动车'], ['酒店', '民宿'], ['海边', '湖边'], ['爬山', '徒步'], ['露营', '野餐']
];

// ---- 皮肤目录（payload 全部是纯外观参数） ----
const SKINS = [
  // 文案卡片边框
  { id: 'cf_default', name: '清风留白', type: 'card_frame', rarity: 'normal', price: 0, blurb: '默认的干净边框', payload: { gradient: ['#e8e4f3', '#f7f4ee'], deco: 'none', glow: 'rgba(141,122,230,.18)' } },
  { id: 'cf_sakura', name: '樱花软糖', type: 'card_frame', rarity: 'rare', price: 290, blurb: '边角飘着两瓣樱花', payload: { gradient: ['#ffd1e0', '#ffe9f2'], deco: 'sakura', glow: 'rgba(255,143,179,.35)' } },
  { id: 'cf_soda', name: '盛夏汽水', type: 'card_frame', rarity: 'rare', price: 390, blurb: '气泡咕嘟咕嘟往上冒', payload: { gradient: ['#bfe9ff', '#e1f7ff'], deco: 'bubbles', glow: 'rgba(64,180,255,.3)' } },
  { id: 'cf_cloud', name: '奶油云朵', type: 'card_frame', rarity: 'fine', price: 990, blurb: '云朵软软地托住你的句子', payload: { gradient: ['#fff3d6', '#ffe7f0'], deco: 'cloud', glow: 'rgba(255,200,120,.35)' } },
  { id: 'cf_galaxy', name: '星雾琉璃', type: 'card_frame', rarity: 'epic', price: 2800, blurb: '琉璃质感里藏着一条星河', payload: { gradient: ['#8ea8ff', '#d3b9ff'], deco: 'stars', glow: 'rgba(142,168,255,.45)' } },
  { id: 'cf_goldmoon', name: '鎏金月海', type: 'card_frame', rarity: 'legend', price: 6800, blurb: '碎金洒在夜色的海面上', payload: { gradient: ['#3b3653', '#6f5b8f'], deco: 'goldmoon', glow: 'rgba(232,177,76,.5)' } },
  // 头像框
  { id: 'af_sugar', name: '糖霜圈', type: 'avatar_frame', rarity: 'normal', price: 0, blurb: '基础款甜甜圈', payload: { ring: ['#ffd6e8', '#c9e8ff'], deco: 'none' } },
  { id: 'af_catears', name: '猫耳气泡', type: 'avatar_frame', rarity: 'rare', price: 490, blurb: '一对竖起来的小猫耳', payload: { ring: ['#ffc9dd', '#ffe3ee'], deco: 'ears' } },
  { id: 'af_meteor', name: '流星环', type: 'avatar_frame', rarity: 'fine', price: 1200, blurb: '会员专属流星轨道', payload: { ring: ['#8ea8ff', '#e3b9ff'], deco: 'star' } },
  { id: 'af_aurora', name: '极光之冠', type: 'avatar_frame', rarity: 'epic', price: 3200, blurb: '头顶一小片北极光', payload: { ring: ['#5ef0c0', '#74c7ff'], deco: 'aurora' } },
  // 聊天气泡
  { id: 'bb_cloud', name: '云朵泡泡', type: 'bubble', rarity: 'rare', price: 190, blurb: '说的话都软乎乎', payload: { bg: ['#eef4ff', '#e3ecff'], text: '#4a5b8c' } },
  { id: 'bb_peach', name: '蜜桃汽泡', type: 'bubble', rarity: 'fine', price: 990, blurb: '冒着粉色小气泡', payload: { bg: ['#ffe9ef', '#ffd9e4'], text: '#a04a66' } },
  { id: 'bb_inkstar', name: '星河墨', type: 'bubble', rarity: 'epic', price: 2800, blurb: '深色星空里发光的字', payload: { bg: ['#2c2f4a', '#3a3f63'], text: '#dfe6ff' } },
  // 文字变动画特效
  { id: 'fx_firefly', name: '萤火余韵', type: 'anim_fx', rarity: 'fine', price: 1800, blurb: '动画结束后留下一串萤火', payload: { trail: 'firefly', tint: '#ffe28a' } },
  { id: 'fx_sakura', name: '樱吹雪', type: 'anim_fx', rarity: 'epic', price: 4500, blurb: '所有动画飘起樱花雨', payload: { trail: 'petal', tint: '#ffb3cd' } },
  { id: 'fx_galaxy', name: '星海漫游', type: 'anim_fx', rarity: 'legend', price: 9800, blurb: '文字粒子化作环绕星河', payload: { trail: 'star', tint: '#9db4ff' } },
  // 桌游房间主题
  { id: 'rt_cafe', name: '深夜咖啡馆', type: 'room_theme', rarity: 'rare', price: 690, blurb: '游戏房弥漫咖啡香气', payload: { bg: ['#3a2f2a', '#574437'], emoji: '☕', accent: '#d9a05b' } },
  { id: 'rt_garden', name: '夏日庭院', type: 'room_theme', rarity: 'fine', price: 1500, blurb: '蝉鸣与绿荫里的推理局', payload: { bg: ['#23402f', '#39594a'], emoji: '🌿', accent: '#8fd9a8' } },
  { id: 'rt_bookshop', name: '旧书店谜屋', type: 'room_theme', rarity: 'epic', price: 3000, blurb: '在泛黄书页间寻找卧底', payload: { bg: ['#3b3147', '#544468'], emoji: '📚', accent: '#c9aef5' } },
  // 凶夜·初雪赛季限定（也可单买，但通行证是集齐全套最划算的方式）
  { id: 'cf_frost', name: '初雪结晶', type: 'card_frame', rarity: 'epic', price: 2600, blurb: '边框凝着一层细碎的霜花', payload: { gradient: ['#bcd6ff', '#e7f1ff'], deco: 'stars', glow: 'rgba(150,200,255,.45)' } },
  { id: 'bb_whisper', name: '夜语', type: 'bubble', rarity: 'fine', price: 990, blurb: '说出口的话像雾里的低语', payload: { bg: ['#2a2740', '#3c3656'], text: '#d7d2f0' } },
  { id: 'af_phantom', name: '幽影环', type: 'avatar_frame', rarity: 'epic', price: 3200, blurb: '一圈若隐若现的幽蓝光晕', payload: { ring: ['#7b8cff', '#9a6fd6'], deco: 'aurora' } },
  { id: 'rt_manor', name: '迷雾庄园', type: 'room_theme', rarity: 'legend', price: 7200, blurb: '凶夜赛季终极奖励：雾锁回廊的诡谲庄园', payload: { bg: ['#1a1722', '#2e2738'], emoji: '🕯', accent: '#b06fd6' } }
];

// ---- 开场示例内容（全部 AI 标识，让冷启动第一屏就有氛围） ----
const SAMPLE_POSTS = [
  { p: 'ai_xiaojuling', text: '我在等风，也在等你。' },
  { p: 'ai_linggan', text: '把心事折成纸船，放进春天的河里。' },
  { p: 'ai_xiaojuling', text: '今天的晚霞是草莓味的，舍不得一个人看。' },
  { p: 'ai_linggan', text: '灵感掉落 💡：用三个字形容你的今天，评论区见！' },
  { p: 'ai_xiaojuling', text: '雨停了，树叶上的水珠在数刚刚走过几个人。' },
  { p: 'ai_zhuchiguan', text: '桌游大厅冒泡 🎲：一局「谁是卧底」只要十分钟，来吗？' },
  { p: 'ai_xiaojuling', text: '深夜的城市像一台老旧的放映机，路灯是它的胶片。' },
  { p: 'ai_linggan', text: '挑战：不用「喜欢」两个字，表达喜欢。' },
  { p: 'ai_xiaojuling', text: '奔跑吧，少年。风会记得你冲过终点的样子。' },
  { p: 'ai_xiaojuling', text: '猫睡着的时候，世界会自动调成静音模式。' }
];

export function runSeed() {
  if (getSetting('seeded_v1')) return false;
  const ts = now();

  // 管理员
  const adminUser = process.env.ADMIN_USERNAME || 'admin';
  const adminPass = process.env.ADMIN_PASSWORD || 'jvling-admin-2026';
  if (!q.get('SELECT id FROM users WHERE username = ?', adminUser)) {
    q.run(
      `INSERT INTO users (username, pass_hash, nickname, avatar, role, bio, created_at, last_seen)
       VALUES (?,?,?,?,'admin','句灵运营团队',?,?)`,
      adminUser, hashPassword(adminPass), '句灵小管家', 'blob_5', ts, ts
    );
    console.log(`[seed] 管理后台账号: ${adminUser} / ${adminPass} （请在 .env 中修改）`);
  }

  for (const [category, list] of Object.entries(WORDS)) {
    for (const w of list) q.run('INSERT OR IGNORE INTO sensitive_words (word, category, created_at) VALUES (?,?,?)', w, category, ts);
  }
  for (const [a, b] of WORD_PAIRS) q.run('INSERT INTO word_pairs (civilian, undercover) VALUES (?,?)', a, b);
  for (const [i, s] of SKINS.entries()) {
    q.run('INSERT OR IGNORE INTO skins (id, name, type, rarity, price_fen, blurb, payload, enabled, sort) VALUES (?,?,?,?,?,?,?,1,?)',
      s.id, s.name, s.type, s.rarity, s.price, s.blurb, JSON.stringify(s.payload), i);
  }

  setSetting('seeded_v1', true);
  return true;
}

// 暖场账号建好后再补示例内容（index.js 在 ensureWarmupAccounts 之后调用）
export function seedSamplePosts() {
  if (getSetting('seeded_posts_v1')) return;
  const ts = now();
  for (const [i, item] of SAMPLE_POSTS.entries()) {
    const u = q.get('SELECT id FROM users WHERE username = ?', item.p);
    if (!u) continue;
    const card = buildCard(item.text);
    q.run(
      `INSERT INTO posts (user_id, content, card, status, is_ai, ai_label, like_count, created_at)
       VALUES (?,?,?,?,1,'AI 暖场官 · AI 生成',0,?)`,
      u.id, item.text, JSON.stringify(card), 'active', ts - (SAMPLE_POSTS.length - i) * 47 * 60_000
    );
  }
  setSetting('seeded_posts_v1', true);
}
