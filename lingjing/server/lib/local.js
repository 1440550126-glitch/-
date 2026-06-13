// 灵境AI · 本地规则引擎：不配任何大模型 Key 也能走通「剧本 → 分镜 → 图 → 视频」全流程
// （演示/开发用，接入火山方舟后自动切换为真实模型，本文件作为断网/超额兜底）
import fs from 'node:fs';
import path from 'node:path';
import { UPLOAD_DIR } from './db.js';
import { hashCode, seededRandom, pick, escapeXML, ratioSize, uid, clamp } from './util.js';

// ---------- 剧本生成 ----------
const FEMALE = ['林晚', '苏念', '沈青禾', '顾盼', '江雪', '温言夏'];
const MALE = ['顾沉舟', '陆时砚', '沈惊鸿', '霍霆深', '谢临渊', '季慎行'];
const VILLAIN = ['赵总', '王经理', '继母刘氏', '表姐周曼', '二叔', '马副总'];
const SIDE = ['司机老周', '前台小妹', '神秘老人', '管家福伯'];

const GENRES = {
  '都市逆袭': { scenes: ['写字楼大堂', '公司天台', '咖啡馆', '豪宅客厅', '地下车库'], hook: '一张隐藏身份的黑卡' },
  '赘婿战神': { scenes: ['岳家祠堂', '婚宴酒店', '老宅书房', '江边码头', '拍卖行'], hook: '一枚归隐战神的徽章' },
  '甜宠虐恋': { scenes: ['民政局门口', '顶层公寓', '医院走廊', '雨夜街头', '游艇甲板'], hook: '一纸隐婚协议' },
  '悬疑反转': { scenes: ['废弃工厂', '老式公寓', '审讯室', '深夜便利店', '天台边缘'], hook: '一段被删除的监控' },
  '古装宫斗': { scenes: ['冷宫偏殿', '御花园', '凤仪宫', '宫墙夹道', '太医署'], hook: '一支先皇御赐的金簪' },
  '废土科幻': { scenes: ['废土荒漠', '地下避难所', '机械城集市', '能源塔顶层', '旧世界图书馆'], hook: '一颗仍在跳动的能源核心' },
  '末日生存': { scenes: ['废弃高速公路', '地下避难所', '暴雨中的加油站', '辐射隔离带', '黎明的旷野'], hook: '一台被人动过手脚的盖革计数器' }
};

export function matchGenre(genre = '') {
  const keys = Object.keys(GENRES);
  return keys.find((k) => genre && (k.includes(genre) || genre.includes(k.slice(0, 2)))) || null;
}

export function localScript({ idea = '', genre = '', numScenes = 4, numEpisodes = 1, title = '' } = {}) {
  const rnd = seededRandom(hashCode(idea + genre + title));
  const gKey = matchGenre(genre) || pick(Object.keys(GENRES), rnd);
  const g = GENRES[gKey];
  const heroine = pick(FEMALE, rnd);
  const hero = pick(MALE, rnd);
  const villain = pick(VILLAIN, rnd);
  const side = pick(SIDE, rnd);
  const n = clamp(numScenes, 3, 6);
  const eps = clamp(numEpisodes, 1, 6);
  const ideaLine = idea ? `灵感：${idea}` : `灵感：${g.hook}引发的命运反转`;
  const t = title || `${gKey}·${hero}与${heroine}`;
  const ctx = { g, gKey, heroine, hero, villain, side, rnd };

  const parts = [];
  parts.push(`《${t}》\n类型：${gKey} ｜ ${eps > 1 ? `共 ${eps} 集 · 每集约 ${n} 场` : `共 ${n} 场`}\n${ideaLine}\n`);
  parts.push(`【人物】\n${heroine}（女主）：表面落魄却心性坚韧，身上藏着不为人知的秘密。\n${hero}（男主）：气场强大、身份神秘，唯独对${heroine}另眼相待。\n${villain}（反派）：势利刻薄，处处刁难${heroine}。\n${side}（配角）：关键时刻递出线索的小人物。\n`);
  parts.push(`【关键道具】\n${g.hook}：贯穿全剧的悬念之物。\n`);

  const EP_TITLES = ['初露锋芒', '暗流涌动', '步步为营', '图穷匕见', '风暴中心', '尘埃落定'];
  for (let e = 1; e <= eps; e++) {
    if (eps > 1) parts.push(`\n第 ${e} 集 ｜ ${e === eps ? '尘埃落定' : EP_TITLES[(e - 1) % EP_TITLES.length]}\n`);
    parts.push(episodeBody({ ...ctx, ep: e, eps, n }));
  }
  return parts.join('');
}

/** 单集正文（场次 + 节拍）；多集时剧情按 集数 递进 */
function episodeBody({ g, heroine, hero, villain, side, rnd, ep, eps, n }) {
  const sc = (i, name) => `\n第 ${i} 场 ｜ 场景：${name} ｜ ${i % 2 ? '日' : '夜'} ｜ ${rnd() > 0.5 ? '内' : '外'}\n`;
  const S = g.scenes;
  const sceneAt = (i) => S[(i + (ep - 1) * 2) % S.length];
  const out = [];
  const isFinal = ep === eps;

  out.push(sc(1, sceneAt(0)));
  if (ep === 1) {
    out.push(`（${heroine}被众人围在中央，${villain}把一份文件摔在她面前。）\n${villain}：就凭你？也配站在这里！今天不当众道歉，你就别想走出这扇门。\n${heroine}：（攥紧手心，抬头）道歉可以，但请先把事实查清楚。\n（人群里传来嗤笑，${heroine}的手机忽然震动——一条陌生号码的短信。）\n`);
  } else {
    out.push(`（上集风波未平，${villain}纠集人手再次堵住${heroine}的去路。）\n${villain}：上次让你侥幸过关，这回我看谁还能保你！\n${heroine}：（不退反进）正好，我也有几笔旧账，想当面算清。\n`);
  }

  out.push(sc(2, sceneAt(1)));
  if (ep === 1) {
    out.push(`（${hero}缓步走出，所有人噤声。他停在${heroine}身侧。）\n${hero}：她的事，从今天起我管了。\n${villain}：（脸色骤变）您……您怎么会为了她——\n${hero}：（俯身替${heroine}捡起文件）因为她手里，有${g.hook}。\n`);
  } else {
    out.push(`（${hero}递来一份新的线索，神色前所未有地凝重。）\n${hero}：${g.hook}背后还有人，比我们想的更深。\n${heroine}：（指尖收紧）那就把它连根挖出来。\n`);
  }

  if (n >= 4) {
    out.push(sc(3, sceneAt(2)));
    out.push(`（${side}匆匆赶来，带来一段关键往事。）\n${side}：当年的事，我只敢说给${heroine}小姐听……\n${heroine}：（瞳孔骤缩）原来${ep > 1 ? '上一次的局，也是他们设的' : `这就是${g.hook}的来历`}？！\n（暗处，${villain}举起手机拍下了这一幕。）\n`);
  }
  if (n >= 5) {
    out.push(sc(4, sceneAt(3)));
    out.push(`（${villain}设局发难，${heroine}被逼到台前。）\n${villain}：各位都看见了，她根本经不起查！\n${heroine}：（轻笑，举起${g.hook}）那不如让它的主人，亲自来说。\n（大门被推开，${hero}逆光而立。）\n`);
  }

  out.push(sc(n, sceneAt(n - 1)));
  if (isFinal) {
    out.push(`（真相揭晓：${heroine}的身世与${g.hook}牵出的旧案当众摊开，${villain}瘫坐在地。）\n${hero}：（看向${heroine}，伸出手）现在，轮到我们清算自己的事了。\n${heroine}：（与他对视，缓缓把手放上去）好啊。不过这一次——规则我来定。\n[钩子] 黑暗处，一只戴手套的手碾灭烟头：「${g.hook}……终于出现了。」\n`);
  } else {
    out.push(`（${heroine}刚要松口气，一个意想不到的身影出现在门口。）\n${heroine}：（怔住）怎么会是你……\n[钩子] 来人摘下帽檐，露出与${hero}七分相似的脸：「他没告诉你吗？${g.hook}，本来是我的。」\n`);
  }
  return out.join('');
}

/** 续写下一集（沿用既有角色/场景，本地兜底用） */
export function localNextEpisode({ storyboard = null, order = 2, idea = '', genre = '' } = {}) {
  const rnd = seededRandom(hashCode(`ep${order}` + idea));
  const gKey = matchGenre(genre || '') || pick(Object.keys(GENRES), rnd);
  const g = GENRES[gKey];
  const chars = storyboard?.characters || [];
  const heroine = (chars.find((c) => /女主|主角/.test(c.role)) || chars[0])?.name || '主角';
  const hero = (chars.find((c) => /男主/.test(c.role)) || chars[1])?.name || '同伴';
  const villain = (chars.find((c) => /反派/.test(c.role)) || chars[2])?.name || '神秘人';
  const scenes = (storyboard?.scenes || []).map((s) => s.name);
  const s1 = scenes[(order - 1) % Math.max(1, scenes.length)] || '旧地重游';
  const s2 = scenes[order % Math.max(1, scenes.length)] || '雨夜街头';
  const hook = (storyboard?.props || [])[0]?.name || g.hook;
  const ideaLine = idea ? `（本集围绕：${idea}）\n` : '';
  return `第 ${order} 集 ｜ 风云再起\n${ideaLine}
第 1 场 ｜ 场景：${s1} ｜ 日 ｜ 内
（${villain}留下的余党卷土重来，${heroine}收到一封没有署名的请柬。）
${heroine}：敢用${hook}做局，就别怪我掀了这张桌子。
${hero}：（按住她的手背）这次，我们一起去。

第 2 场 ｜ 场景：${s2} ｜ 夜 ｜ 外
（局中局被层层揭开，幕后之人终于露出冰山一角。）
${villain}：你以为赢了？真正的庄家，还没下场呢。
${heroine}：（迎着风站定）那就让他来。我等着。
[钩子] 一辆黑色轿车缓缓驶过，车窗降下一条缝——里面的人，拿着和${hook}一模一样的东西。\n`;
}

// ---------- 剧本解析（任意文本 → 结构化分镜） ----------
const SHOT_TYPES = ['全景', '中景', '近景', '特写'];
const CAMERAS = ['固定机位', '缓慢推近', '环绕运镜', '跟随移动', '拉远收尾'];

// 非角色「说话人」黑名单（精确匹配）：技术/旁白/场景标签
const NON_CHAR_LABELS = new Set([
  '场景', '类型', '灵感', '风格', '旁白', '字幕', '注', '注释', '备注', '提示', '画外音', '内心', '内心独白', 'OS', 'VO', 'V.O', 'O.S',
  '画面', '镜头', '特写', '全景', '近景', '中景', '远景', '空镜', '黑场', '插卡', '字幕卡', '片名', '标题', '音乐', '音效', '背景音',
  '时间', '地点', '日', '夜', '内', '外', '蒙太奇', '闪回', '导演', '编剧', '出品', '声音', '解说', '介绍', '说明', '人物', '道具', '关键道具'
]);
// 含动作/技术动词的 token 不是人名（如：字幕浮现 / 在另一头喊 / 画上）
const VERB_RE = /浮现|出现|响起|传来|喊|叫|喊道|说道|说|道|问|答|想|看|望|走|跑|打|拿|举|画|写|响|亮|灭|切|推|拉|摇|升|降|闪|爬|冲|抓|按|踢|踹|低语|怒吼|嘶吼|尖叫|低吼|咆哮|画上|上方|下方|远处|身后|另一头|另一边/;

/** 判断一个台词说话人 token 是否像真实角色名 */
function looksLikeName(tok) {
  const t = String(tok).trim();
  if (!t || t.length > 6 || t.length < 1) return false;
  if (NON_CHAR_LABELS.has(t)) return false;
  if (VERB_RE.test(t)) return false;
  if (/[，。、！？!?.,；;…—\-（）()【】"'《》0-9a-zA-Z]/.test(t)) return false; // 含标点/数字/英文一般是描述
  return true;
}
/** 从人设描述里推断性别 */
export function guessGender(desc = '', name = '') {
  const s = desc + name;
  const female = /女主|女一|女二|女子|女人|女孩|女性|少女|姑娘|妈|母亲|母|姐|妹|婆|奶奶|外婆|阿姨|大妈|女医生|女兵|妻|寡|嫂|姨|娘|她/;
  const male = /男主|男一|男二|男子|男人|男孩|男性|少年|大叔|老汉|爸|父亲|父|哥|弟|爷|爷爷|外公|叔|伯|丈夫|和尚|道士|男医生|男兵|他/;
  const f = (s.match(female) || []).length;
  const m = (s.match(male) || []).length;
  if (f > m) return '女';
  if (m > f) return '男';
  return '';
}
function ageHint(desc = '') {
  if (/老|年迈|苍老|花甲|古稀|白发|爷|奶|婆|大爷|老汉/.test(desc)) return '老年';
  if (/少年|少女|小孩|儿童|小学|稚嫩|十[一二三四五六七八九]岁|孩子/.test(desc)) return '少年';
  if (/中年|大叔|大妈|四十|五十/.test(desc)) return '中年';
  return '青年';
}

/**
 * 把长剧本切成有序段落（供 LLM 分段解析，避免一次性截断）。
 * 优先按「第 N 幕/集」切；否则按场次分组成若干幕；短剧本返回单段。
 * @returns {Array<{title:string, body:string, unit:'幕'|'集'}>}
 */
export function splitScriptSegments(script = '', { maxChars = 9000 } = {}) {
  const text = String(script || '');
  const head = (text.match(/^[\s\S]*?(?=^第\s*[一二三四五六七八九十\d]+\s*[幕集场]|^(?:INT|EXT)[.． ]|^场景[:：])/m) || [''])[0]; // 剧名/人物表/道具块
  const unit = /^第\s*[一二三四五六七八九十\d]+\s*幕/m.test(text) ? '幕' : (/^第\s*\d+\s*集/m.test(text) ? '集' : '幕');

  // 1) 显式分段标记
  const segRe = unit === '集' ? /^第\s*\d+\s*集.*$/gm : /^第\s*[一二三四五六七八九十\d]+\s*幕.*$/gm;
  let marks = [...text.matchAll(segRe)];
  // 2) 无标记 → 用场次头分组
  if (!marks.length) {
    const heads = [...text.matchAll(/^第\s*\d+\s*场.*$|^(?:INT|EXT)[.． ].*$|^场景[:：].*$/gm)];
    if (heads.length <= 1 || text.length <= maxChars) return [{ title: '全片', body: text, unit }];
    const acts = Math.min(8, Math.max(3, Math.ceil(text.length / maxChars), Math.round(heads.length / 5)));
    const per = Math.ceil(heads.length / acts);
    const ACT_NAMES = ['序幕', '崩塌', '逃亡', '裂变', '困局', '反转', '决战', '终幕'];
    const segs = [];
    for (let a = 0; a < acts; a++) {
      const start = a === 0 ? 0 : heads[a * per].index;
      const end = (a + 1) * per < heads.length ? heads[(a + 1) * per].index : text.length;
      segs.push({ title: ACT_NAMES[a] || `第 ${a + 1} 幕`, body: (a === 0 ? '' : head) + text.slice(start, end), unit });
    }
    return segs;
  }
  // 显式标记 → 每段带上剧名/人物表（让每段解析都知道人物全貌）
  const segs = [];
  const firstSceneIdx = text.search(/^第\s*\d+\s*场|^(?:INT|EXT)[.． ]|^场景[:：]/m);
  if (firstSceneIdx >= 0 && firstSceneIdx < marks[0].index) {
    segs.push({ title: `第一${unit}`, body: text.slice(0, marks[0].index), unit });
  }
  marks.forEach((m, i) => {
    const end = i + 1 < marks.length ? marks[i + 1].index : text.length;
    const t = (m[0].replace(/^第\s*[一二三四五六七八九十\d]+\s*[幕集]\s*[｜|:：]?\s*/, '') || '').trim().slice(0, 20);
    segs.push({ title: t || `第 ${segs.length + 1} ${unit}`, body: head + text.slice(m.index, end), unit });
  });
  return segs;
}

export function localParse(script = '', { style = '', maxShots = 14 } = {}) {
  const text = String(script || '').trim();
  const rnd = seededRandom(hashCode(text.slice(0, 500)));
  const title = (text.match(/《(.+?)》/) || [])[1] || text.split('\n')[0]?.slice(0, 20) || '未命名作品';
  const styleHint = style || '电影质感，胶片色调，高对比布光';

  // 人物：①【人物/角色】块（权威来源） ②台词说话人（严格过滤 + 出现次数门槛）
  const charMeta = new Map();   // name -> {desc, gender, fromBlock, count}
  const block = text.match(/【(?:人物|角色|主要人物|人物表)】([\s\S]*?)(?=\n【|\n第\s*[一二三四五六七八九十\d]+\s*[幕集场]|$)/);
  if (block) {
    for (const line of block[1].split('\n')) {
      const m = line.match(/^\s*[·•\-*]?\s*([^\s（(:：】]{1,8})\s*(（[^）]*）)?\s*[:：](.+)$/);
      if (m && looksLikeName(m[1].replace(/（.*/, ''))) {
        const nm = m[1].replace(/（.*/, '').trim();
        const role = (m[2] || '').replace(/[（）]/g, '');
        const d = (role ? role + '，' : '') + m[3].trim();
        charMeta.set(nm, { desc: d, gender: guessGender(d, nm), fromBlock: true, count: 99 });
      }
    }
  }
  // 台词说话人：统计出现次数，非 block 角色需出现 ≥2 次才采纳（过滤偶发误判）
  for (const m of text.matchAll(/^\s*([^\s（(:：【\][]{1,8})\s*[:：](?!\/)/gm)) {
    const name = m[1].trim();
    if (!looksLikeName(name)) continue;
    if (charMeta.has(name)) { if (!charMeta.get(name).fromBlock) charMeta.get(name).count++; continue; }
    charMeta.set(name, { desc: '', gender: '', fromBlock: false, count: 1 });
  }
  // 过滤：保留 block 角色 + 出现≥2次的说话人
  const charMap = new Map();
  for (const [name, meta] of charMeta) {
    if (meta.fromBlock || meta.count >= 2) charMap.set(name, meta);
  }
  if (!charMap.size) charMap.set('主角', { desc: '故事的核心人物', gender: '', fromBlock: true, count: 99 });

  // 分段切分：支持「第 N 幕」(电影/话剧) 与「第 N 集」(短剧)；长剧本无标记时自动分幕
  const unit = /^第\s*[一二三四五六七八九十\d]+\s*幕/m.test(text) ? '幕' : '集';
  const segRe = unit === '幕' ? /^第\s*[一二三四五六七八九十\d]+\s*幕.*$/gm : /^第\s*\d+\s*集.*$/gm;
  const epMarks = [...text.matchAll(segRe)];
  let episodes = [];
  if (epMarks.length) {
    const firstSceneIdx = text.search(/^第\s*\d+\s*场|^(?:INT|EXT)[.． ]|^场景[:：]/m);
    if (firstSceneIdx >= 0 && firstSceneIdx < epMarks[0].index) episodes.push({ title: `第一${unit}`, summary: '', offset: 0 });
    epMarks.forEach((m) => {
      const t = (m[0].match(new RegExp(`^第\\s*[一二三四五六七八九十\\d]+\\s*${unit}\\s*[｜|:：]?\\s*(.*)$`))?.[1] || '').trim().slice(0, 20);
      episodes.push({ title: t || `第 ${episodes.length + 1} ${unit}`, summary: '', offset: m.index });
    });
  }
  // 无分段标记但剧本很长（电影/长片）→ 按场次自动分幕，便于分批生成与管理
  if (!episodes.length) {
    const sceneHeads = [...text.matchAll(/^第\s*\d+\s*场|^(?:INT|EXT)[.． ]|^场景[:：]/gm)];
    if (text.length > 6000 && sceneHeads.length >= 6) {
      const acts = Math.min(8, Math.max(3, Math.round(sceneHeads.length / 4)));
      const per = Math.ceil(sceneHeads.length / acts);
      const ACT_NAMES = ['序幕', '崩塌', '逃亡', '裂变', '困局', '反转', '决战', '终幕'];
      for (let a = 0; a < acts; a++) {
        const head = sceneHeads[a * per];
        episodes.push({ title: ACT_NAMES[a] || `第 ${a + 1} 幕`, summary: '', offset: a === 0 ? 0 : head.index });
      }
    } else {
      episodes.push({ title: unit === '幕' ? '第一幕' : '全片', summary: '', offset: 0 });
    }
  }
  episodes.forEach((e, i) => { e.key = `e${i + 1}`; e.order = i + 1; });
  const epForOffset = (off) => {
    let cur = episodes[0];
    for (const e of episodes) { if (e.offset <= off) cur = e; else break; }
    return cur.key;
  };

  // 场次切分
  const sceneRe = /^第\s*\d+\s*场.*$|^(?:INT|EXT)[.． ].*$|^场景[:：].*$/gim;
  const headers = [...text.matchAll(sceneRe)];
  const sceneBlocks = [];
  if (headers.length) {
    headers.forEach((h, i) => {
      const start = h.index + h[0].length;
      const end = i + 1 < headers.length ? headers[i + 1].index : text.length;
      const nameM = h[0].match(/场景[:：]\s*([^｜|]+)/) || h[0].match(/^第\s*\d+\s*场\s*[｜|]?\s*(.*)$/);
      sceneBlocks.push({
        name: (nameM?.[1] || h[0]).replace(/[｜|].*$/, '').trim().slice(0, 16) || `场次 ${i + 1}`,
        body: text.slice(start, end),
        episode: epForOffset(h.index)
      });
    });
  } else {
    sceneBlocks.push({ name: '主场景', body: text, episode: 'e1' });
  }

  // 道具
  const props = [];
  const propBlock = text.match(/【(?:关键)?道具】([\s\S]*?)(?=\n【|\n第\s*[一二三四五六七八九十\d]+\s*[幕集场]|$)/);
  if (propBlock) {
    for (const line of propBlock[1].split('\n')) {
      const m = line.match(/^\s*([^\s:：]{1,14})[:：](.+)$/);
      if (m) props.push({ name: m[1], desc: m[2].trim() });
    }
  }

  const characters = [...charMap.entries()].slice(0, 12).map(([name, meta], i) => {
    const d = (meta.desc || '剧中人物').trim();
    const gender = meta.gender || guessGender(d, name);
    // 优先用人设里的明确标签判定角色定位（避免"坏掉的收音机"误判反派）
    const role = /女主|男主|主角|主人公|女一|男一/.test(d) ? '主角'
      : /反派|大反派|反一|boss|首领|凶手|幕后|敌人|坏人/i.test(d) ? '反派'
        : /配角|龙套|路人|群演/.test(d) ? '配角'
          : i === 0 ? '主角' : '配角';
    const gtag = gender === '男' ? '男性' : gender === '女' ? '女性' : '';
    return {
      key: `c${i + 1}`, name, role, gender, desc: d.slice(0, 120),
      image_prompt: `${styleHint}，人物肖像，${gtag}${ageHint(d)}，${name}，${d.slice(0, 70)}，半身正面，浅景深，写实`
    };
  });
  const charKeyByName = new Map(characters.map((c) => [c.name, c.key]));

  // 场景按名字去重（多集会复用同名场景）
  const scenes = [];
  const sceneKeyByName = new Map();
  const blockSceneKey = [];
  for (const s of sceneBlocks) {
    let key = sceneKeyByName.get(s.name);
    if (!key && scenes.length < 20) {
      key = `s${scenes.length + 1}`;
      sceneKeyByName.set(s.name, key);
      scenes.push({
        key, name: s.name, desc: s.body.trim().split('\n')[0]?.slice(0, 60) || s.name,
        image_prompt: `${styleHint}，场景概念图，${s.name}，空镜，氛围光影`
      });
    }
    blockSceneKey.push(key || scenes[scenes.length - 1]?.key || 's1');
  }
  const propList = props.slice(0, 4).map((p, i) => ({
    key: `p${i + 1}`, name: p.name, desc: p.desc.slice(0, 60),
    image_prompt: `${styleHint}，道具特写，${p.name}，${p.desc.slice(0, 40)}，置于桌面，戏剧布光`
  }));

  // 分镜上限随剧本体量放大：长片（90分钟≈数万字）可拆上百个分镜，而非固定 40
  const byLength = Math.round(text.length / 220);            // 约每 220 字一个关键分镜
  const byScenes = sceneBlocks.length * 5;                   // 每场最多 ~5 个分镜
  const shotCap = clamp(Math.max(byLength, byScenes, maxShots), maxShots, 160);
  const shots = [];
  sceneBlocks.forEach((s, si) => {
    if (shots.length >= shotCap) return;
    const beats = [];
    for (const raw of s.body.split('\n')) {
      const line = raw.trim();
      if (!line || /^【|^\[钩子\]|^类型|^灵感/.test(line)) {
        const hookM = line.match(/^\[钩子\]\s*(.+)/);
        if (hookM) beats.push({ type: 'action', text: hookM[1], speakers: [] });
        continue;
      }
      const act = line.match(/^[（(](.+?)[）)]$/);
      if (act) { beats.push({ type: 'action', text: act[1], speakers: [...charMap.keys()].filter((n) => act[1].includes(n)) }); continue; }
      const dlg = line.match(/^([^\s（(:：]{1,8})[:：]\s*(.+)$/);
      if (dlg && charKeyByName.has(dlg[1])) {
        const sayText = dlg[2].replace(/^（[^）]*）/, '').trim();
        beats.push({ type: 'dialogue', text: sayText, speakers: [dlg[1]] });
      } else if (line.length > 8 && !headers.length) {
        beats.push({ type: 'action', text: line.slice(0, 60), speakers: [] });
      }
    }
    // 每场最多取 6 个关键节拍（动作/台词均匀采样）
    const perScene = 6;
    const chosen = beats.length > perScene ? beats.filter((_, i) => i % Math.ceil(beats.length / perScene) === 0).slice(0, perScene) : beats;
    const sceneKey = blockSceneKey[si];
    const sceneName = scenes.find((x) => x.key === sceneKey)?.name || '主场景';
    chosen.forEach((b) => {
      if (shots.length >= shotCap) return;
      const i = shots.length + 1;
      const speakKeys = b.speakers.map((n) => charKeyByName.get(n)).filter(Boolean);
      const who = b.speakers[0] || characters[0].name;
      const shotType = b.type === 'dialogue' ? pick(['近景', '特写'], rnd) : pick(SHOT_TYPES, rnd);
      const emoGuess = /怒|吼|摔|瞪/.test(b.text) ? '愤怒'
        : /哭|泪|哽咽/.test(b.text) ? '悲伤'
          : /笑|喜|兴奋/.test(b.text) ? '微笑'
            : /惊|骤缩|愣|？！/.test(b.text) ? '惊恐' : '';
      shots.push({
        key: `sh${i}`, order: i, scene: sceneKey, episode: s.episode || 'e1',
        characters: speakKeys.length ? speakKeys : [characters[0].key],
        shot_type: shotType, camera: pick(CAMERAS, rnd), emotion: emoGuess,
        action: b.type === 'action' ? b.text.slice(0, 80) : `${who}说话，情绪随台词起伏`,
        dialogue: b.type === 'dialogue' ? b.text.slice(0, 60) : '',
        duration: 4 + Math.round(rnd() * 3),
        image_prompt: `${styleHint}，${shotType}，${sceneName}，${who}，${b.text.slice(0, 50)}`,
        video_prompt: `${b.text.slice(0, 60)}，${pick(CAMERAS, rnd)}，${styleHint}`
      });
    });
  });
  if (!shots.length) {
    shots.push({
      key: 'sh1', order: 1, scene: 's1', episode: 'e1', characters: ['c1'], shot_type: '全景', camera: '缓慢推近',
      action: text.slice(0, 60) || '开场空镜', dialogue: '', duration: 5,
      image_prompt: `${styleHint}，开场全景，${scenes[0].name}`, video_prompt: `开场氛围镜头，缓慢推近，${styleHint}`
    });
  }

  return {
    title, logline: text.replace(/\s+/g, ' ').slice(0, 80), style: styleHint, unit,
    episodes: episodes.map(({ offset, ...e }) => e),
    characters, scenes, props: propList, shots
  };
}

// ---------- 本地图像（生成式 SVG，按提示词确定性出图） ----------
const PALETTES = [
  [210, 260], [330, 20], [160, 200], [25, 45], [270, 320], [190, 150]
];

function svgWrap(w, h, inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${inner}</svg>`;
}
function bgDefs(rnd, id, [h1, h2]) {
  return `<defs>
  <linearGradient id="bg${id}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl(${h1},42%,${18 + rnd() * 8}%)"/>
    <stop offset="1" stop-color="hsl(${h2},48%,${30 + rnd() * 10}%)"/>
  </linearGradient>
  <radialGradient id="glow${id}" cx="0.5" cy="0.42" r="0.65">
    <stop offset="0" stop-color="hsl(${h2},70%,72%)" stop-opacity="0.55"/>
    <stop offset="1" stop-color="hsl(${h1},60%,20%)" stop-opacity="0"/>
  </radialGradient>
</defs>`;
}
const badge = (w, h, label) =>
  `<g opacity="0.85"><rect x="${w - 158}" y="${h - 40}" rx="13" width="142" height="26" fill="rgba(0,0,0,0.45)"/>
   <text x="${w - 87}" y="${h - 22}" font-size="13" fill="rgba(255,255,255,0.92)" text-anchor="middle" font-family="system-ui,'PingFang SC','Microsoft YaHei'">灵境AI · 本地生成 ${escapeXML(label)}</text></g>`;
const caption = (w, h, title, sub) => `
  <text x="${w / 2}" y="${h - 64}" font-size="${Math.round(w / 24)}" font-weight="700" fill="rgba(255,255,255,0.95)" text-anchor="middle" font-family="system-ui,'PingFang SC','Microsoft YaHei'">${escapeXML(title)}</text>
  ${sub ? `<text x="${w / 2}" y="${h - 34}" font-size="${Math.round(w / 52)}" fill="rgba(255,255,255,0.62)" text-anchor="middle" font-family="system-ui,'PingFang SC','Microsoft YaHei'">${escapeXML(sub)}</text>` : ''}`;

function sceneArt(rnd, w, h, hue) {
  const m1 = `0,${h * 0.78} ${w * 0.22},${h * 0.5} ${w * 0.4},${h * 0.72} ${w * 0.62},${h * 0.46} ${w * 0.8},${h * 0.66} ${w},${h * 0.52} ${w},${h} 0,${h}`;
  const m2 = `0,${h * 0.9} ${w * 0.3},${h * 0.66} ${w * 0.55},${h * 0.84} ${w * 0.78},${h * 0.62} ${w},${h * 0.8} ${w},${h} 0,${h}`;
  const stars = Array.from({ length: 26 }, () =>
    `<circle cx="${(rnd() * w).toFixed(0)}" cy="${(rnd() * h * 0.45).toFixed(0)}" r="${(0.8 + rnd() * 1.6).toFixed(1)}" fill="rgba(255,255,255,${(0.25 + rnd() * 0.5).toFixed(2)})"/>`).join('');
  return `${stars}
  <circle cx="${w * (0.24 + rnd() * 0.5)}" cy="${h * 0.3}" r="${h * 0.11}" fill="hsl(${hue},75%,78%)" opacity="0.9"/>
  <polygon points="${m1}" fill="rgba(8,12,24,0.55)"/>
  <polygon points="${m2}" fill="rgba(4,6,14,0.78)"/>`;
}
// 表情集：本地角色画像的五官随情绪变化（对应方舟模式的表情提示词）
export const EMO_STYLE = {
  '冷酷': { hue: 192, eyes: 'line', mouth: 'flat' },
  '愤怒': { hue: 6, eyes: 'angry', mouth: 'zig' },
  '狂喜': { hue: 322, eyes: 'star', mouth: 'big' },
  '悲伤': { hue: 216, eyes: 'down', mouth: 'frown' },
  '微笑': { hue: 146, eyes: 'dot', mouth: 'smile' },
  '惊恐': { hue: 268, eyes: 'wide', mouth: 'o' },
  '魅惑': { hue: 300, eyes: 'wink', mouth: 'smirk' },
  '羞涩': { hue: 350, eyes: 'dot', mouth: 'small' }
};
function face(cx, cy, w, h, hue, emo) {
  const s = EMO_STYLE[emo] || { eyes: 'dot', mouth: 'smile' };
  const ex = w * 0.052, ey = cy - h * 0.125, er = 4.5;
  const C = `hsl(${hue},85%,75%)`;
  let eyes = '';
  if (s.eyes === 'line') eyes = `<path d="M ${cx - ex - 5} ${ey} h 10 M ${cx + ex - 5} ${ey} h 10" stroke="${C}" stroke-width="3" stroke-linecap="round"/>`;
  else if (s.eyes === 'angry') eyes = `<path d="M ${cx - ex - 6} ${ey - 4} l 12 6 M ${cx + ex + 6} ${ey - 4} l -12 6" stroke="${C}" stroke-width="3.4" stroke-linecap="round"/>`;
  else if (s.eyes === 'star') eyes = `<text x="${cx - ex}" y="${ey + 5}" font-size="14" text-anchor="middle" fill="${C}">✦</text><text x="${cx + ex}" y="${ey + 5}" font-size="14" text-anchor="middle" fill="${C}">✦</text>`;
  else if (s.eyes === 'down') eyes = `<path d="M ${cx - ex - 5} ${ey + 2} q 5 -6 10 0 M ${cx + ex - 5} ${ey + 2} q 5 -6 10 0" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  else if (s.eyes === 'wide') eyes = `<circle cx="${cx - ex}" cy="${ey}" r="6.5" fill="none" stroke="${C}" stroke-width="2.6"/><circle cx="${cx + ex}" cy="${ey}" r="6.5" fill="none" stroke="${C}" stroke-width="2.6"/>`;
  else if (s.eyes === 'wink') eyes = `<circle cx="${cx - ex}" cy="${ey}" r="${er}" fill="${C}"/><path d="M ${cx + ex - 5} ${ey} h 10" stroke="${C}" stroke-width="3" stroke-linecap="round"/>`;
  else eyes = `<circle cx="${cx - ex}" cy="${ey}" r="${er}" fill="${C}"/><circle cx="${cx + ex}" cy="${ey}" r="${er}" fill="${C}"/>`;
  const my = cy - h * 0.085, mw = w * 0.04;
  let mouth = '';
  if (s.mouth === 'flat') mouth = `<path d="M ${cx - mw} ${my} h ${mw * 2}" stroke="${C}" stroke-width="3" stroke-linecap="round"/>`;
  else if (s.mouth === 'zig') mouth = `<path d="M ${cx - mw} ${my} l ${mw * 0.7} -4 l ${mw * 0.7} 8 l ${mw * 0.7} -4" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  else if (s.mouth === 'big') mouth = `<path d="M ${cx - mw * 1.4} ${my - 3} q ${mw * 1.4} ${mw * 2.4} ${mw * 2.8} 0 z" fill="${C}"/>`;
  else if (s.mouth === 'frown') mouth = `<path d="M ${cx - mw} ${my + 4} q ${mw} -10 ${mw * 2} 0" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  else if (s.mouth === 'o') mouth = `<ellipse cx="${cx}" cy="${my + 2}" rx="${mw * 0.8}" ry="${mw * 1.1}" fill="none" stroke="${C}" stroke-width="3"/>`;
  else if (s.mouth === 'smirk') mouth = `<path d="M ${cx - mw} ${my} q ${mw * 1.2} 6 ${mw * 2} -3" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  else if (s.mouth === 'small') mouth = `<path d="M ${cx - mw * 0.5} ${my} q ${mw * 0.5} 4 ${mw} 0" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  else mouth = `<path d="M ${cx - mw} ${my} Q ${cx} ${my + 7} ${cx + mw} ${my}" stroke="${C}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  return eyes + mouth;
}
function characterArt(rnd, w, h, hue, emotion = '') {
  const cx = w / 2, cy = h * 0.42;
  return `
  <circle cx="${cx}" cy="${cy - h * 0.115}" r="${h * 0.1}" fill="rgba(10,14,26,0.92)" stroke="hsl(${hue},70%,68%)" stroke-width="3"/>
  <path d="M ${cx - w * 0.26} ${h * 0.78} Q ${cx} ${cy + h * 0.04} ${cx + w * 0.26} ${h * 0.78} L ${cx + w * 0.3} ${h} L ${cx - w * 0.3} ${h} Z"
        fill="rgba(10,14,26,0.92)" stroke="hsl(${hue},70%,68%)" stroke-width="3"/>
  ${face(cx, cy, w, h, hue, emotion)}`;
}
function propArt(rnd, w, h, hue) {
  const cx = w / 2, cy = h * 0.5;
  return `
  <ellipse cx="${cx}" cy="${h * 0.74}" rx="${w * 0.2}" ry="${h * 0.035}" fill="rgba(0,0,0,0.4)"/>
  <rect x="${cx - w * 0.13}" y="${h * 0.62}" width="${w * 0.26}" height="${h * 0.12}" rx="10" fill="rgba(16,20,36,0.9)" stroke="hsl(${hue},60%,55%)" stroke-width="2"/>
  <circle cx="${cx}" cy="${cy - h * 0.04}" r="${h * 0.13}" fill="hsl(${hue},80%,62%)" opacity="0.92"/>
  <circle cx="${cx}" cy="${cy - h * 0.04}" r="${h * 0.2}" fill="none" stroke="hsl(${hue},80%,70%)" stroke-width="2" stroke-dasharray="6 10" opacity="0.7"/>`;
}

/** 本地生成一张 SVG 图（kind: character|scene|prop|frame；emotion 仅角色表情集用），返回 SVG 字符串 */
export function localImageSVG({ prompt = '', name = '', kind = 'scene', ratio = '16:9', order = 0, emotion = '' }) {
  const seed = hashCode(kind + name + prompt);
  const rnd = seededRandom(seed);
  const pal = PALETTES[seed % PALETTES.length];
  const hue = kind === 'character' && EMO_STYLE[emotion] ? EMO_STYLE[emotion].hue : pal[1];
  const dim = kind === 'character' ? { w: 768, h: 960 } : ratioSize(ratio, 1280);
  const { w, h } = dim;
  const id = (seed % 9973).toString(36);

  let art = '';
  if (kind === 'character') art = characterArt(rnd, w, h, hue, emotion);
  else if (kind === 'prop') art = propArt(rnd, w, h, hue);
  else art = sceneArt(rnd, w, h, hue);

  const frameBars = kind === 'frame'
    ? `<rect x="0" y="0" width="${w}" height="${h * 0.07}" fill="rgba(0,0,0,0.82)"/><rect x="0" y="${h * 0.93}" width="${w}" height="${h * 0.07}" fill="rgba(0,0,0,0.82)"/>
       <text x="24" y="${h * 0.052}" font-size="${Math.round(w / 56)}" fill="rgba(255,255,255,0.8)" font-family="ui-monospace,monospace">SHOT ${String(order || 1).padStart(2, '0')}</text>`
    : '';

  const inner = `${bgDefs(rnd, id, pal)}
  <rect width="${w}" height="${h}" fill="url(#bg${id})"/>
  <rect width="${w}" height="${h}" fill="url(#glow${id})"/>
  ${art}${frameBars}
  ${caption(w, h, name || prompt.slice(0, 14), prompt.slice(0, 36))}
  ${badge(w, h, '')}`;
  return svgWrap(w, h, inner);
}

/** 本地"视频"：带 SMIL 动画的 SVG（镜头缓推 + 光斑流动 + 进度条），<img> 即可播放 */
export function localVideoSVG({ prompt = '', name = '', ratio = '16:9', duration = 5, order = 0 }) {
  const seed = hashCode('v' + name + prompt);
  const rnd = seededRandom(seed);
  const pal = PALETTES[seed % PALETTES.length];
  const hue = pal[1];
  const { w, h } = ratioSize(ratio, 1280);
  const id = (seed % 9973).toString(36);
  const dur = clamp(duration, 2, 12);

  const inner = `${bgDefs(rnd, id, pal)}
  <rect width="${w}" height="${h}" fill="url(#bg${id})"/>
  <g>
    <animateTransform attributeName="transform" type="scale" values="1;1.07;1" dur="${dur * 2}s" repeatCount="indefinite" additive="sum"/>
    <animateTransform attributeName="transform" type="translate" values="0 0;${-w * 0.03} ${-h * 0.02};0 0" dur="${dur * 2}s" repeatCount="indefinite" additive="sum"/>
    <rect width="${w}" height="${h}" fill="url(#glow${id})"/>
    ${sceneArt(rnd, w, h, hue)}
  </g>
  <circle r="${h * 0.3}" fill="hsl(${hue},80%,70%)" opacity="0.12">
    <animate attributeName="cx" values="${-w * 0.2};${w * 1.2}" dur="${dur}s" repeatCount="indefinite"/>
    <animate attributeName="cy" values="${h * 0.3};${h * 0.5}" dur="${dur}s" repeatCount="indefinite"/>
  </circle>
  <rect x="0" y="0" width="${w}" height="${h * 0.07}" fill="rgba(0,0,0,0.82)"/>
  <rect x="0" y="${h * 0.93}" width="${w}" height="${h * 0.07}" fill="rgba(0,0,0,0.82)"/>
  <text x="24" y="${h * 0.052}" font-size="${Math.round(w / 56)}" fill="rgba(255,255,255,0.8)" font-family="ui-monospace,monospace">SHOT ${String(order || 1).padStart(2, '0')} · ${dur}s · LOCAL PREVIEW</text>
  <rect x="0" y="${h - 5}" height="5" fill="hsl(${hue},85%,65%)" width="0">
    <animate attributeName="width" values="0;${w}" dur="${dur}s" repeatCount="indefinite"/>
  </rect>
  ${caption(w, h, name || `镜头 ${order || 1}`, prompt.slice(0, 36))}
  ${badge(w, h, '预览')}`;
  return svgWrap(w, h, inner);
}

/** 爆款结构本地分析（无 Key 兜底）：规则识别钩子手法与节奏 */
export function localViralAnalysis(reference = '') {
  const t = String(reference);
  let hook = '冲突前置钩子';
  if (/^[^。！？\n]{0,24}[?？]/.test(t.trim())) hook = '悬念提问钩子';
  else if (/千万别|你绝对|你一定|99%的人/.test(t)) hook = '直击观众钩子';
  else if (/没想到|竟然|结果|万万没/.test(t)) hook = '反转预告钩子';
  else if (/\d+[条个秒天万倍]/.test(t)) hook = '数字冲击钩子';
  const sentences = t.split(/[。！？!?\n]/).filter((s) => s.trim().length > 2);
  const beats = Math.min(5, Math.max(3, Math.round(sentences.length / 3)));
  return {
    hook,
    structure: `${beats} 段式：3 秒${hook.slice(0, 4)}开场 → 中段层层加码 → 结尾强钩子留人`,
    emotion: '好奇 → 紧张/共情 → 爽点释放 → 意犹未尽',
    selling_points: [
      `开场即${hook.replace('钩子', '')}，前 3 秒不浪费`,
      '每 10-15 秒一个小反转，信息密度拉满',
      '结尾埋下一集悬念，引导追更'
    ]
  };
}

/** 把 SVG 落盘到 uploads，返回 /uploads/xxx.svg */
export function saveSVG(svg) {
  const name = `${uid('loc')}.svg`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), svg, 'utf8');
  return `/uploads/${name}`;
}
