// utils/store.js — 数据层（离线优先：本地缓存为同步读源，云开发负责双向同步）
//
// 设计说明：
//  · 所有读取走 read()，所有写入走 write()；页面拿到的永远是同步的本地缓存，不感知云端。
//  · write() 会为「情侣共享数据」打时间戳并防抖触发云同步（见底部「云同步」）。
//  · 共享数据双向同步：愿望/纪念日/回忆/猫/小金库/菜单/在一起日期；
//    心情/纸条/每日一问按作者(openid)拆分后也已同步——存绝对作者、读取时翻译成 self/partner；
//    昵称/头像是各自的称呼偏好，留在本地不同步。
//  · 未开通云开发 / 未绑定情侣时，云同步自动跳过，纯本地照常运行。
//  · 小金库金额按 ¥ 记，余额由流水汇总得出，不涉及真实支付与提现。

const cloud = require('./cloud.js');

const K = {
  COUPLE: 'couple_info',
  MOOD: 'mood_today',
  DAILYQ: 'daily_question',
  NOTES: 'love_notes',
  WISH: 'wish_list',
  CAT: 'cat_state',
  ANNIV: 'anniversaries',
  MEMORY: 'memories',
  STAT: 'daily_stat',
  THEME: 'app_theme',
  MEMBER: 'member_status',
  VERIFY: 'verify_status',
  VAULT: 'vault_data',
  VAULT_TX: 'vault_txns',
  DINING: 'dining_menu',
  USAGE: 'usage_stat',
  PARTNER: 'partner_status',
  REMIND: 'remind_setting',
  LINK: 'couple_link',   // 设备本地：{ coupleId, inviteCode, role, openid }
  META: 'sync_meta',     // { key: 时间戳 } 每个共享键最后修改时间
  TOMB: 'sync_tomb',     // { key: [已删除 id] } 墓碑，保证删除能同步
  PRESENCE: 'presence',  // 在场：{ byAuthor:{ openid:{ts,battery,locOn,lat,lng,pokeTs,pokeType} } }（同步）
  PSEEN: 'presence_seen' // 设备本地：上次已读的对方 pokeTs
};

// 参与云同步的「共享键」及其合并类型
//  array     = 列表，按 id 并集合并 + 墓碑删除
//  authormap = 按作者(openid)存储的记录 { date, byAuthor:{openid:值} }，按作者并集合并
//  object    = 整体按时间戳取新（后写覆盖）
//  couple    = 仅同步 startDate（昵称/头像是视角相关，留在本地）
const SYNC = {};
SYNC[K.WISH] = 'array';
SYNC[K.ANNIV] = 'array';
SYNC[K.MEMORY] = 'array';
SYNC[K.DINING] = 'array';
SYNC[K.VAULT_TX] = 'array';
SYNC[K.NOTES] = 'array';      // 纸条：按作者标注，列表并集
SYNC[K.MOOD] = 'authormap';   // 心情：每人各存自己的
SYNC[K.DAILYQ] = 'authormap'; // 每日一问：每人各存自己的答案
SYNC[K.PRESENCE] = 'authormap'; // 在场/电量/位置/戳一戳：每人各存自己的
SYNC[K.CAT] = 'object';
SYNC[K.COUPLE] = 'couple';

function rnd(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }
// 全局唯一 id：毫秒时间戳 + 随机位，避免同一毫秒（含两台设备各自）创建时 id 冲突导致合并丢项
function uid() { return Date.now() * 1000 + Math.floor(Math.random() * 1000); }

/* ───────── 基础读写 ───────── */
function read(key, def) {
  try {
    const v = wx.getStorageSync(key);
    return (v === '' || v === null || v === undefined) ? def : v;
  } catch (e) { return def; }
}
// 原始写入：不打时间戳、不触发同步（用于 meta/tomb/采纳云端数据，避免递归）
function writeRaw(key, val) {
  try { wx.setStorageSync(key, val); } catch (e) {}
  return val;
}
function write(key, val) {
  writeRaw(key, val);
  if (SYNC[key]) { bumpMeta(key); scheduleSync(); }  // 共享键：打时间戳 + 防抖同步
  return val;
}

/* ───────── 日期工具 ───────── */
function pad(n) { return n < 10 ? '0' + n : '' + n; }
function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}
function dayOfYear() {
  const d = new Date();
  const start = new Date(d.getFullYear(), 0, 0);
  return Math.floor((d - start) / 86400000);
}
function daysBetween(a, b) {
  const da = new Date(a + 'T00:00:00');
  const db = new Date(b + 'T00:00:00');
  return Math.round((db - da) / 86400000);
}

/* ───────── 主题 ───────── */
function getTheme() { return read(K.THEME, 'coral'); }
function setTheme(t) { return write(K.THEME, t); }

/* ───────── 会员 ───────── */
function getMember() { return read(K.MEMBER, { isMember: false, tier: '', since: '' }); }
function isMember() { return !!getMember().isMember; }
function openMember(tier) {
  return write(K.MEMBER, { isMember: true, tier: tier || 'monthly', since: todayStr() });
}
function cancelMember() { return write(K.MEMBER, { isMember: false, tier: '', since: '' }); }

/* ───────── 实名认证 ───────── */
function getVerify() { return read(K.VERIFY, { status: 'unverified', name: '' }); }
function isVerified() { return getVerify().status === 'verified'; }
function setVerified(name) { return write(K.VERIFY, { status: 'verified', name: name || '已实名用户' }); }

/* ───────── 情侣信息 ───────── */
function getCouple() {
  return read(K.COUPLE, {
    bound: false, selfName: '我', partnerName: 'TA',
    selfAvatar: '🐱', partnerAvatar: '🐰', startDate: todayStr()
  });
}
function setCouple(patch) { return write(K.COUPLE, Object.assign({}, getCouple(), patch)); }
function loveDays() {
  const c = getCouple();
  return Math.max(1, daysBetween(c.startDate, todayStr()) + 1);
}

/* ───────── 心情同步 ───────── */
const PARTNER_MOODS = [
  { e: '😊', t: '今天很好' }, { e: '🥰', t: '想你了' }, { e: '😌', t: '平静温柔' },
  { e: '😴', t: '有点困' }, { e: '🤗', t: '想抱抱' }, { e: '😋', t: '吃得开心' }
];
function simPartnerMood() { return PARTNER_MOODS[dayOfYear() % PARTNER_MOODS.length]; }
// 存储：{ date, byAuthor: { openid: {e,t} } }；读取时翻译成 self/partner（页面形状不变）
function getMood() {
  const today = todayStr(), me = myId();
  const m = read(K.MOOD, null);
  if (!m || m.date !== today) return { date: today, self: null, partner: syncEnabled() ? null : simPartnerMood() };
  const by = m.byAuthor || {};
  let partner = null;
  Object.keys(by).forEach(k => { if (k !== me) partner = by[k]; });   // 对方 = 不是我的那位作者
  if (!partner && !syncEnabled()) partner = simPartnerMood();          // 未绑定时给个温柔模拟
  return { date: today, self: by[me] || null, partner: partner };
}
function setSelfMood(emoji, text) {
  const today = todayStr();
  let m = read(K.MOOD, null);
  if (!m || m.date !== today) m = { date: today, byAuthor: {} };
  if (!m.byAuthor) m.byAuthor = {};
  m.byAuthor[myId()] = { e: emoji, t: text || '' };
  logInteraction('mood');
  return write(K.MOOD, m);
}

/* ───────── 每日一问 ───────── */
const QUESTIONS = [
  '今天最想和TA一起做的一件小事是什么？', '上一次因为对方笑出声，是什么时候？',
  '如果现在能瞬移到TA身边，你想说的第一句话是？', '你们的第一次约会，你记得哪个细节？',
  '最近TA做的哪件事让你心动了？', '如果一起养一只宠物，你想给它取什么名字？',
  '今天想对TA说一句平时不好意思说的话？', '你最喜欢和TA待在一起的哪个时刻？',
  '下一个想和TA一起去的地方是哪里？', '在你心里，TA最可爱的一个习惯是？',
  '如果今晚一起做饭，你想做什么菜？', '最近有没有一首歌让你想起TA？',
  '你们之间有没有只有彼此懂的暗号？', '想和TA一起养成的一个小习惯是什么？',
  '今天最想被TA夸的一点是什么？', '如果要给这段关系拍一张照片，会是什么画面？'
];
const SIM_ANSWERS = ['我也在想同一件事呢～', '只要和你一起就好啦', '想到了就好开心', '等你回家说给你听', '这个问题我想了好久', '答案当然是你呀', '今晚见面告诉你', '嘿嘿，秘密'];
// 存储：{ date, index, byAuthor: { openid: 答案 } }；读取时翻译成 selfAnswer/partnerAnswer
function getDailyQuestion() {
  const idx = dayOfYear() % QUESTIONS.length, today = todayStr(), me = myId();
  const data = read(K.DAILYQ, null);
  if (!data || data.date !== today) return { date: today, index: idx, question: QUESTIONS[idx], selfAnswer: '', partnerAnswer: '' };
  const qi = data.index != null ? data.index : idx;
  const by = data.byAuthor || {};
  let partnerAns = '';
  Object.keys(by).forEach(k => { if (k !== me) partnerAns = by[k]; });
  if (!partnerAns && !syncEnabled()) partnerAns = SIM_ANSWERS[dayOfYear() % SIM_ANSWERS.length];
  return { date: today, index: qi, question: QUESTIONS[qi], selfAnswer: by[me] || '', partnerAnswer: partnerAns };
}
function answerDailyQuestion(text) {
  const today = todayStr(), idx = dayOfYear() % QUESTIONS.length;
  let data = read(K.DAILYQ, null);
  if (!data || data.date !== today) data = { date: today, index: idx, byAuthor: {} };
  if (!data.byAuthor) data.byAuthor = {};
  data.byAuthor[myId()] = text;
  logInteraction('question');
  return write(K.DAILYQ, data);
}

/* ───────── 爱的小纸条 ───────── */
// 存储：每条带 author(openid)；读取时按"是不是我"翻译成 from:'self'/'partner'（页面不变）
function rawNotes() {
  let list = read(K.NOTES, null);
  if (list === null) { list = [{ id: 1, author: 'system', text: '欢迎来到我们的小屋子，以后每天都要一起呀 🏠', time: Date.now() }]; write(K.NOTES, list); }
  return list;
}
function getNotes() {
  const me = myId();
  return rawNotes().map(n => Object.assign({}, n, { from: n.author === me ? 'self' : 'partner' }));
}
function addNote(text) {
  const list = rawNotes();
  list.unshift({ id: uid(), author: myId(), text: text, time: Date.now() });
  logInteraction('note');
  write(K.NOTES, list);
  return getNotes();
}
function removeNote(id) { addTomb(K.NOTES, id); return write(K.NOTES, rawNotes().filter(n => n.id !== id)); }

/* ───────── 共同愿望清单 ───────── */
function getWishes() {
  return read(K.WISH, [
    { id: 1, text: '一起去看一次海', done: false },
    { id: 2, text: '拍一组情侣写真', done: false }
  ]);
}
function addWish(text) { const l = getWishes(); l.unshift({ id: uid(), text: text, done: false }); return write(K.WISH, l); }
function toggleWish(id) { return write(K.WISH, getWishes().map(w => { if (w.id === id) w.done = !w.done; return w; })); }
function removeWish(id) { addTomb(K.WISH, id); return write(K.WISH, getWishes().filter(w => w.id !== id)); }

/* ───────── 一起养的猫 ───────── */
const CAT_MOODS = {
  happy: { e: '😻', t: '心情超好' }, normal: { e: '🐱', t: '懒洋洋' },
  hungry: { e: '🙀', t: '有点饿了' }, sleepy: { e: '😺', t: '困困的' }
};
function getCat() {
  let cat = read(K.CAT, null);
  if (!cat) {
    cat = { name: '奶团', level: 1, exp: 0, intimacy: 30, fullness: 70, lastDate: todayStr(), fedToday: 0, playedToday: 0 };
    write(K.CAT, cat);
  }
  if (cat.lastDate !== todayStr()) {
    cat.fullness = Math.max(0, cat.fullness - 25);
    cat.fedToday = 0; cat.playedToday = 0; cat.lastDate = todayStr();
    write(K.CAT, cat);
  }
  cat.moodKey = catMoodKey(cat);
  cat.mood = CAT_MOODS[cat.moodKey];
  cat.expMax = cat.level * 100;
  return cat;
}
function catMoodKey(cat) {
  if (cat.fullness < 30) return 'hungry';
  if (cat.intimacy >= 80) return 'happy';
  if (cat.fullness < 55) return 'sleepy';
  return 'normal';
}
function gainCat(expGain, intimacyGain, fullnessGain) {
  const cat = getCat();
  cat.exp += expGain;
  cat.intimacy = Math.min(100, cat.intimacy + (intimacyGain || 0));
  cat.fullness = Math.min(100, cat.fullness + (fullnessGain || 0));
  let leveledUp = false;
  while (cat.exp >= cat.level * 100) { cat.exp -= cat.level * 100; cat.level += 1; leveledUp = true; }
  write(K.CAT, cat);
  return { cat: getCat(), leveledUp: leveledUp };
}
function feedCat() {
  const cat = getCat();
  if (cat.fedToday >= 5) return { limited: true, msg: '今天喂得够多啦，明天再来～' };
  cat.fedToday += 1; write(K.CAT, cat); logInteraction('cat');
  return Object.assign({ msg: cat.name + ' 吃得好满足 🍚' }, gainCat(12, 4, 20));
}
function petCat() {
  logInteraction('cat');
  const r = gainCat(8, 6, 0);
  return Object.assign({ msg: r.cat.name + ' 蹭了蹭你 🐾' }, r);
}
function playCat() {
  const cat = getCat();
  if (cat.playedToday >= 5) return { limited: true, msg: '玩累啦，让猫咪歇会儿～' };
  cat.playedToday += 1; write(K.CAT, cat); logInteraction('cat');
  return Object.assign({ msg: cat.name + ' 玩得好开心 🎀' }, gainCat(15, 8, 0));
}
function renameCat(name) { const cat = getCat(); cat.name = (name || '').trim() || cat.name; return write(K.CAT, cat); }
function catNameSafe() { return getCat().name; }

/* ───────── 纪念日 / 倒数日 ───────── */
function getAnniversaries() {
  const c = getCouple();
  const list = read(K.ANNIV, [{ id: 1, name: '在一起纪念日', date: c.startDate, repeatYearly: true }]);
  const today = todayStr();
  return list.map(a => {
    const item = Object.assign({}, a);
    let target = a.date;
    if (a.repeatYearly) {
      const md = a.date.slice(5);
      const y = new Date().getFullYear();
      let t = y + '-' + md;
      if (daysBetween(today, t) < 0) t = (y + 1) + '-' + md;
      target = t;
    }
    item.target = target;
    item.diff = daysBetween(today, target);
    item.passedDays = daysBetween(a.date, today);
    return item;
  }).sort((x, y) => Math.abs(x.diff) - Math.abs(y.diff));
}
function addAnniversary(name, date, repeatYearly) {
  const list = read(K.ANNIV, []);
  list.push({ id: uid(), name: name, date: date, repeatYearly: !!repeatYearly });
  return write(K.ANNIV, list);
}
function removeAnniversary(id) { addTomb(K.ANNIV, id); return write(K.ANNIV, read(K.ANNIV, []).filter(a => a.id !== id)); }
function nearestEvent() {
  const list = getAnniversaries();
  const future = list.filter(a => a.diff >= 0).sort((x, y) => x.diff - y.diff);
  return future[0] || list[0] || null;
}

/* ───────── 时光回忆 ───────── */
function getMemories() {
  return read(K.MEMORY, [
    { id: 1, date: '2023-05-20', text: '第一次一起看的那场日落 🌅', photo: '' },
    { id: 2, date: '2023-10-04', text: '一起爬山，累但笑得很傻 ⛰️', photo: '' }
  ]);
}
function addMemory(mem) { const l = getMemories(); l.unshift(Object.assign({ id: uid(), date: todayStr() }, mem)); return write(K.MEMORY, l); }
function removeMemory(id) { addTomb(K.MEMORY, id); return write(K.MEMORY, getMemories().filter(m => m.id !== id)); }

/* ───────── 情侣点餐 ───────── */
function getMenu() {
  return read(K.DINING, [
    { id: 1, name: '火锅', emoji: '🍲' }, { id: 2, name: '日料', emoji: '🍣' },
    { id: 3, name: '烧烤', emoji: '🍢' }, { id: 4, name: '麻辣烫', emoji: '🌶️' },
    { id: 5, name: '炸鸡', emoji: '🍗' }, { id: 6, name: '寿喜锅', emoji: '🍲' },
    { id: 7, name: '螺蛳粉', emoji: '🍜' }, { id: 8, name: '披萨', emoji: '🍕' },
    { id: 9, name: '家常小炒', emoji: '🥘' }, { id: 10, name: '轻食沙拉', emoji: '🥗' }
  ]);
}
function addDish(name, emoji) {
  const l = getMenu();
  l.push({ id: uid(), name: name, emoji: emoji || '🍽️' });
  return write(K.DINING, l);
}
function removeDish(id) { addTomb(K.DINING, id); return write(K.DINING, getMenu().filter(d => d.id !== id)); }

/* ───────── 小金库（共同记账/存钱） ───────── */
function getVault() { return read(K.VAULT, { balance: 0 }); }
function getVaultTx() { return read(K.VAULT_TX, []); }
function vaultDeposit(amount, note) {
  amount = Math.max(0, parseFloat(amount) || 0);
  const v = getVault(); v.balance = Math.round((v.balance + amount) * 100) / 100; write(K.VAULT, v);
  const tx = getVaultTx(); tx.unshift({ id: uid(), type: 'in', amount: amount, note: note || '存入', time: Date.now() });
  write(K.VAULT_TX, tx);
  logInteraction('vault');
  return v;
}
function vaultSpend(amount, note) {
  amount = Math.max(0, parseFloat(amount) || 0);
  const v = getVault(); v.balance = Math.round((v.balance - amount) * 100) / 100; write(K.VAULT, v);
  const tx = getVaultTx(); tx.unshift({ id: uid(), type: 'out', amount: amount, note: note || '支出', time: Date.now() });
  write(K.VAULT_TX, tx);
  return v;
}
function vaultStats() {
  const tx = getVaultTx();
  let totalIn = 0, totalOut = 0;
  tx.forEach(t => { if (t.type === 'in') totalIn += t.amount; else totalOut += t.amount; });
  return { totalIn: Math.round(totalIn * 100) / 100, totalOut: Math.round(totalOut * 100) / 100, count: tx.length };
}

/* ───────── 每日互动统计 ───────── */
function getStat() {
  const s = read(K.STAT, {});
  if (s.date !== todayStr()) return { date: todayStr(), count: 0, types: {} };
  return s;
}
function logInteraction(type) {
  const s = getStat();
  s.count = (s.count || 0) + 1;
  s.types = s.types || {};
  s.types[type] = (s.types[type] || 0) + 1;
  write(K.STAT, s);
  if (type !== 'cat') {
    const cat = read(K.CAT, null);
    if (cat) { cat.intimacy = Math.min(100, (cat.intimacy || 0) + 2); cat.exp = (cat.exp || 0) + 3; write(K.CAT, cat); }
  }
  return s;
}

/* ───────── 使用情况（打开次数 / 在线时长 / 多久没看） ───────── */
function fmtDuration(ms) {
  if (!ms || ms < 0) return '刚刚';
  const min = Math.floor(ms / 60000);
  if (min < 1) return '刚刚';
  if (min < 60) return min + ' 分钟';
  const h = Math.floor(min / 60);
  if (h < 24) return h + ' 小时' + (min % 60 ? (min % 60) + ' 分' : '');
  return Math.floor(h / 24) + ' 天';
}
function getUsageRaw() {
  const u = read(K.USAGE, { date: '', opensToday: 0, opensTotal: 0, inAppMsToday: 0, lastHideTs: 0, lastOpenTs: 0, sessionStart: 0, sinceGap: 0 });
  if (u.date !== todayStr()) { u.date = todayStr(); u.opensToday = 0; u.inAppMsToday = 0; }
  return u;
}
// App 进入前台
function recordOpen() {
  const u = getUsageRaw();
  u.sinceGap = u.lastHideTs ? (Date.now() - u.lastHideTs) : 0;   // 上次离开到这次回来 = "多久没看"
  u.opensToday += 1;
  u.opensTotal = (u.opensTotal || 0) + 1;
  u.lastOpenTs = Date.now();
  u.sessionStart = Date.now();
  return write(K.USAGE, u);
}
// App 退到后台
function recordHide() {
  const u = getUsageRaw();
  if (u.sessionStart) u.inAppMsToday = (u.inAppMsToday || 0) + (Date.now() - u.sessionStart);
  u.lastHideTs = Date.now();
  u.sessionStart = 0;
  return write(K.USAGE, u);
}
function getUsage() {
  const u = getUsageRaw();
  const sessionMs = u.sessionStart ? (Date.now() - u.sessionStart) : 0;
  return {
    opensToday: u.opensToday || 0,
    opensTotal: u.opensTotal || 0,
    inAppTodayStr: fmtDuration((u.inAppMsToday || 0) + sessionMs),
    sinceLastStr: fmtDuration(u.sinceGap || 0),
    interactToday: getStat().count || 0
  };
}

/* ───────── TA 的状态（绑定后双方上报真实在线/电量/位置；未绑定时温柔模拟） ───────── */
// 上报"我"的在场信息：电量必报，位置仅在 locShare 打开时报。页面采集后传入，store 不直接调权限接口。
function reportPresence(info) {
  if (!syncEnabled()) return;   // 未绑定无对方，不必上报
  info = info || {};
  const all = read(K.PRESENCE, { byAuthor: {} });
  if (!all.byAuthor) all.byAuthor = {};
  const me = myId(), prev = all.byAuthor[me] || {};
  const entry = { ts: Date.now(), battery: info.battery != null ? info.battery : (prev.battery || 0), charging: !!info.charging, locOn: !!info.locOn, pokeTs: prev.pokeTs || 0, pokeType: prev.pokeType || '' };
  if (info.locOn && info.lat != null) { entry.lat = info.lat; entry.lng = info.lng; }
  all.byAuthor[me] = entry;
  write(K.PRESENCE, all);
}
function partnerEntry() {
  const all = read(K.PRESENCE, null), me = myId();
  if (!all || !all.byAuthor) return null;
  let p = null; Object.keys(all.byAuthor).forEach(k => { if (k !== me) p = all.byAuthor[k]; });
  return p;
}
function getPartnerStatus() {
  const now = Date.now();
  if (syncEnabled()) {
    const p = partnerEntry();
    if (p && p.ts) {
      const gapMs = now - p.ts;
      return { real: true, battery: p.battery || 0, charging: !!p.charging, lastActiveTs: p.ts, gapMs: gapMs, lastActiveStr: fmtDuration(gapMs), online: gapMs < 5 * 60000, hasLoc: !!(p.locOn && p.lat != null), lat: p.lat, lng: p.lng };
    }
    return { real: true, battery: 0, charging: false, lastActiveTs: 0, gapMs: Infinity, lastActiveStr: '还没上线过', online: false, hasLoc: false, waiting: true };
  }
  // 未绑定：温柔模拟（保留单人体验）
  let p = read(K.PARTNER, null);
  if (!p) { p = { lastActiveTs: now - rnd(10, 240) * 60000, battery: rnd(45, 95) }; writeRaw(K.PARTNER, p); }
  if (now - p.lastActiveTs > 36 * 3600000) { p.lastActiveTs = now - rnd(10, 240) * 60000; p.battery = rnd(45, 95); writeRaw(K.PARTNER, p); }
  const gapMs = now - p.lastActiveTs;
  return { real: false, battery: p.battery, charging: false, lastActiveTs: p.lastActiveTs, gapMs: gapMs, lastActiveStr: fmtDuration(gapMs), online: gapMs < 5 * 60000, hasLoc: false };
}
// 戳一戳：记下我的 pokeTs，随同步发给对方；对方在 getIncomingPoke 取到并提示
function pokePartner(type) {
  if (!syncEnabled()) {   // 未绑定 → 模拟回应（与原型一致）
    const p = read(K.PARTNER, {}); const responded = Math.random() < 0.5; if (responded) p.lastActiveTs = Date.now(); writeRaw(K.PARTNER, p);
    return { ok: true, sim: true, responded: responded };
  }
  const all = read(K.PRESENCE, { byAuthor: {} }); if (!all.byAuthor) all.byAuthor = {};
  const me = myId(), prev = all.byAuthor[me] || {};
  prev.ts = Date.now(); prev.pokeTs = Date.now(); prev.pokeType = type || 'poke';
  all.byAuthor[me] = prev; write(K.PRESENCE, all);
  return { ok: true, sim: false };
}
// 对方是否有"新的"戳（与上次已读比较），用于实时提示。返回 {poked,type,ts} 或 null
function getIncomingPoke() {
  const p = partnerEntry(); if (!p || !p.pokeTs) return null;
  const seen = read(K.PSEEN, 0);
  if (p.pokeTs > seen) { writeRaw(K.PSEEN, p.pokeTs); return { poked: true, type: p.pokeType || 'poke', ts: p.pokeTs }; }
  return null;
}
// 关心提醒设置：enabled + 阈值分钟 + 是否共享位置（locShare 不同步，纯本地隐私开关）
function getRemind() { return read(K.REMIND, { enabled: true, minutes: 120, locShare: false }); }
function setRemind(patch) { return write(K.REMIND, Object.assign(getRemind(), patch)); }
// TA 是否"好久没看手机"（达到提醒阈值）；对方还没上报过则不打扰
function partnerNeedsCare() {
  const r = getRemind(); if (!r.enabled) return false;
  const st = getPartnerStatus(); if (st.waiting) return false;
  return st.gapMs >= r.minutes * 60000;
}

/* ───────── 云同步（情侣双向同步；离线优先，未开通/未绑定自动跳过） ───────── */
let _syncReady = false;   // 首次拉取完成后才允许推送，避免用本地默认值覆盖云端
let _syncTimer = null;
let _syncing = false;
let _lastUpdatedAt = 0;   // 已知的云端最后更新时间（用于轮询判断"对方有没有改"）
let _rtTimer = null, _watcher = null;

function getLink() { return read(K.LINK, { coupleId: '', inviteCode: '', role: '', openid: '' }); }
function setLink(patch) { return writeRaw(K.LINK, Object.assign(getLink(), patch)); }
function getCoupleId() { return getLink().coupleId; }
function cloudReady() { return cloud.enabled(); }
function syncEnabled() { return cloud.enabled() && !!getCoupleId(); }
// 当前用户的作者标识：绑定后用 openid；未绑定/未开通云开发时用本地哨兵 'me'
function myId() { return getLink().openid || 'me'; }

function getMeta() { return read(K.META, {}); }
function bumpMeta(key) { const m = getMeta(); m[key] = Date.now(); writeRaw(K.META, m); }
function getTomb() { return read(K.TOMB, {}); }
function addTomb(key, id) { const t = getTomb(); t[key] = t[key] || []; if (t[key].indexOf(id) < 0) t[key].push(id); writeRaw(K.TOMB, t); }

// 绑定后把绑定前用 'me' 记的纸条/心情/每日一问改成真实 openid，使其能正确同步
function migrateAuthor(openid) {
  if (!openid || openid === 'me') return;
  const notes = read(K.NOTES, []); let nc = false;
  notes.forEach(n => { if (n.author === 'me') { n.author = openid; nc = true; } });
  if (nc) { writeRaw(K.NOTES, notes); bumpMeta(K.NOTES); }
  [K.MOOD, K.DAILYQ].forEach(key => {
    const d = read(key, null);
    if (d && d.byAuthor && Object.prototype.hasOwnProperty.call(d.byAuthor, 'me')) {
      d.byAuthor[openid] = d.byAuthor['me']; delete d.byAuthor['me'];
      writeRaw(key, d); bumpMeta(key);
    }
  });
}

// 余额由流水汇总得出（避免并发存取时余额被覆盖丢钱）
function recomputeVault() {
  let bal = 0;
  read(K.VAULT_TX, []).forEach(t => { bal += (t.type === 'in' ? 1 : -1) * (parseFloat(t.amount) || 0); });
  writeRaw(K.VAULT, Object.assign(getVault(), { balance: Math.round(bal * 100) / 100 }));
}

// 导出本地共享快照（原始值；未写过的键 meta=0，交由云端做权威方）
function exportLocal() {
  const data = {};
  Object.keys(SYNC).forEach(key => {
    if (SYNC[key] === 'couple') data[key] = { startDate: getCouple().startDate };
    else if (SYNC[key] === 'array') data[key] = read(key, []);
    else data[key] = read(key, null);
  });
  return { data: data, meta: getMeta(), tomb: getTomb() };
}

// 采纳云端文档：force 时无条件覆盖（首拉/绑定）；否则仅当云端不比本地旧时覆盖
function adopt(doc, force) {
  if (!doc || !doc.data) return;
  const localMeta = getMeta(), rMeta = doc.meta || {};
  Object.keys(doc.data).forEach(key => {
    if (!SYNC[key]) return;
    const lv = localMeta[key] || 0, rv = rMeta[key] || 0;
    if (!force && rv < lv) return;            // 本地更新 → 保留本地，下次推上去
    const val = doc.data[key];
    if (SYNC[key] === 'couple') { if (val && val.startDate) writeRaw(K.COUPLE, Object.assign({}, getCouple(), { startDate: val.startDate })); }
    else writeRaw(key, val);
    localMeta[key] = Math.max(lv, rv);
  });
  writeRaw(K.META, localMeta);
  if (doc.tomb) writeRaw(K.TOMB, doc.tomb);
  recomputeVault();
}

function markJoined(res) { if (res && res.joined && !getCouple().bound) setCouple({ bound: true }); }

function scheduleSync() {
  if (!_syncReady) return;
  clearTimeout(_syncTimer);
  _syncTimer = setTimeout(function () { syncNow(); }, 1500);
}

// 启动：首次「只拉取」采纳云端，再开放推送（避免本地默认值反向覆盖云端）
function beginSync(cb) {
  if (!syncEnabled()) { if (cb) cb(false); return; }
  cloud.call('pull', {}).then(res => {
    if (res && res.ok) { adopt(res.doc, true); markJoined(res); if (res.updatedAt) _lastUpdatedAt = res.updatedAt; }
    _syncReady = true;
    if (cb) cb(!!(res && res.ok));
  }).catch(() => { if (cb) cb(false); });
}

// 合并同步：本地推上去 + 取回云端合并结果（云端为权威合并方）
function syncNow(cb) {
  if (!syncEnabled() || _syncing) { if (cb) cb(false); return; }
  _syncing = true;
  cloud.call('sync', { payload: exportLocal() }).then(res => {
    _syncing = false;
    if (res && res.ok) { _syncReady = true; adopt(res.doc, false); markJoined(res); if (res.updatedAt) _lastUpdatedAt = res.updatedAt; }
    if (cb) cb(!!(res && res.ok));
  }).catch(() => { _syncing = false; if (cb) cb(false); });
}

/* ───────── 准实时：优先云数据库 watch（即时），失败/无权限则前台轮询 ───────── */
// 轻量探测：只问云端 updatedAt，比本地已知的新（多半是对方改了）就拉一次合并
function pingNow(cb) {
  if (!syncEnabled()) { if (cb) cb(false); return; }
  cloud.call('ping', {}).then(res => {
    if (res && res.ok && res.updatedAt && res.updatedAt > _lastUpdatedAt) syncNow(ok => { if (cb) cb(!!ok); });
    else if (cb) cb(false);
  }).catch(() => { if (cb) cb(false); });
}
function startPolling(onChange) {
  if (_rtTimer) return;
  _rtTimer = setInterval(() => { pingNow(changed => { if (changed && onChange) onChange(); }); }, 10000);
}
// onUpdate({ poke }) 在有新数据落地后回调（poke 为对方新发起的戳，或 null）
function startRealtime(onUpdate) {
  if (!syncEnabled()) return;
  stopRealtime();
  const fire = () => { const poke = getIncomingPoke(); if (onUpdate) onUpdate({ poke: poke }); };
  try {
    _watcher = wx.cloud.database().collection('couples').doc(getCoupleId()).watch({
      onChange: snap => {
        const d = snap && snap.docs && snap.docs[0];
        if (d && d.sync) { adopt(d.sync, false); if (d.updatedAt) _lastUpdatedAt = d.updatedAt; fire(); }
      },
      onError: () => { startPolling(fire); }   // 多数情况集合为"仅管理端"→ watch 无权限 → 回退轮询
    });
  } catch (e) { startPolling(fire); }
  if (!_watcher) startPolling(fire);
}
function stopRealtime() {
  if (_rtTimer) { clearInterval(_rtTimer); _rtTimer = null; }
  if (_watcher) { try { _watcher.close(); } catch (e) {} _watcher = null; }
}

// 绑定：code 为空=生成邀请码并建立关系；有 code=用对方邀请码加入
// 注意：加入方加入时不能直接覆盖本地（会丢自己绑定前的数据），改为 migrateAuthor + syncNow 合并
function bindCouple(code, cb) {
  if (!cloud.enabled()) { setCouple({ bound: true }); if (cb) cb({ ok: true, local: true }); return; }  // 未开通云开发 → 本地绑定
  cloud.call('bind', { code: (code || '').trim().toUpperCase() }).then(res => {
    if (!res || !res.ok) { if (cb) cb(res || { ok: false }); return; }
    setLink({ coupleId: res.coupleId, inviteCode: res.inviteCode || '', role: res.role || '', openid: res.openid || '' });
    migrateAuthor(res.openid);   // 绑定前的 'me' 记录改挂到真实 openid
    markJoined(res);
    _syncReady = true;
    syncNow(() => { if (cb) cb(res); });   // 本地↔云端合并（双方数据都不丢）
  }).catch(() => { if (cb) cb({ ok: false }); });
}

function unbindCouple(cb) {
  setCouple({ bound: false });
  if (!cloud.enabled() || !getCoupleId()) { if (cb) cb({ ok: true, local: true }); return; }
  cloud.call('unbind', {}).then(res => {
    setLink({ coupleId: '', inviteCode: '', role: '' });
    if (cb) cb(res || { ok: true });
  }).catch(() => { if (cb) cb({ ok: false }); });
}

/* ───────── 初始化 ───────── */
function ensureDefaults() { getCouple(); getCat(); getNotes(); }

module.exports = {
  todayStr, daysBetween, dayOfYear,
  getTheme, setTheme,
  getMember, isMember, openMember, cancelMember,
  getVerify, isVerified, setVerified,
  getCouple, setCouple, loveDays,
  getMood, setSelfMood,
  getDailyQuestion, answerDailyQuestion,
  getNotes, addNote, removeNote,
  getWishes, addWish, toggleWish, removeWish,
  getCat, feedCat, petCat, playCat, renameCat, catNameSafe,
  getAnniversaries, addAnniversary, removeAnniversary, nearestEvent,
  getMemories, addMemory, removeMemory,
  getMenu, addDish, removeDish,
  getVault, getVaultTx, vaultDeposit, vaultSpend, vaultStats,
  getLink, getCoupleId, cloudReady, syncEnabled, beginSync, syncNow, bindCouple, unbindCouple,
  pingNow, startRealtime, stopRealtime,
  getStat, logInteraction,
  recordOpen, recordHide, getUsage, fmtDuration,
  getPartnerStatus, reportPresence, pokePartner, getIncomingPoke, getRemind, setRemind, partnerNeedsCare,
  ensureDefaults
};
