// 青鸾 · 本地规则引擎：不配任何大模型 Key 也能走通「剧本 → 分镜 → 图 → 视频」全流程
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
  '废土科幻': { scenes: ['废土荒漠', '地下避难所', '机械城集市', '能源塔顶层', '旧世界图书馆'], hook: '一颗仍在跳动的能源核心' }
};

export function matchGenre(genre = '') {
  const keys = Object.keys(GENRES);
  return keys.find((k) => genre && (k.includes(genre) || genre.includes(k.slice(0, 2)))) || null;
}

export function localScript({ idea = '', genre = '', numScenes = 4, title = '' } = {}) {
  const rnd = seededRandom(hashCode(idea + genre + title));
  const gKey = matchGenre(genre) || pick(Object.keys(GENRES), rnd);
  const g = GENRES[gKey];
  const heroine = pick(FEMALE, rnd);
  const hero = pick(MALE, rnd);
  const villain = pick(VILLAIN, rnd);
  const side = pick(SIDE, rnd);
  const n = clamp(numScenes, 3, 6);
  const ideaLine = idea ? `灵感：${idea}` : `灵感：${g.hook}引发的命运反转`;
  const t = title || `${gKey}·${hero}与${heroine}`;

  const sc = (i, name) => `\n第 ${i} 场 ｜ 场景：${name} ｜ ${i % 2 ? '日' : '夜'} ｜ ${rnd() > 0.5 ? '内' : '外'}\n`;
  const S = g.scenes;
  const parts = [];
  parts.push(`《${t}》\n类型：${gKey} ｜ 共 ${n} 场\n${ideaLine}\n`);
  parts.push(`【人物】\n${heroine}（女主）：表面落魄却心性坚韧，身上藏着不为人知的秘密。\n${hero}（男主）：气场强大、身份神秘，唯独对${heroine}另眼相待。\n${villain}（反派）：势利刻薄，处处刁难${heroine}。\n${side}（配角）：关键时刻递出线索的小人物。\n`);
  parts.push(`【关键道具】\n${g.hook}：贯穿全剧的悬念之物。\n`);

  parts.push(sc(1, S[0]));
  parts.push(`（${heroine}被众人围在中央，${villain}把一份文件摔在她面前。）\n${villain}：就凭你？也配站在这里！今天不当众道歉，你就别想走出这扇门。\n${heroine}：（攥紧手心，抬头）道歉可以，但请先把事实查清楚。\n（人群里传来嗤笑，${heroine}的手机忽然震动——一条陌生号码的短信。）\n`);

  parts.push(sc(2, S[1]));
  parts.push(`（${hero}缓步走出，所有人噤声。他停在${heroine}身侧。）\n${hero}：她的事，从今天起我管了。\n${villain}：（脸色骤变）您……您怎么会为了她——\n${hero}：（俯身替${heroine}捡起文件）因为她手里，有${g.hook}。\n`);

  if (n >= 4) {
    parts.push(sc(3, S[2]));
    parts.push(`（${side}匆匆赶来，递上一只旧盒子。）\n${side}：${heroine}小姐，这是当年留给你的东西，我守了十年。\n${heroine}：（打开盒子，瞳孔骤缩）这是……${g.hook}？！\n（窗外雷声滚过，${villain}躲在暗处拍下了这一幕。）\n`);
  }
  if (n >= 5) {
    parts.push(sc(4, S[3]));
    parts.push(`（${villain}联合外人设局，${heroine}被逼到台前。）\n${villain}：各位都看见了，她手里的东西来路不明！\n${heroine}：（忽然轻笑，举起${g.hook}）来路不明？那不如让它的主人，亲自来说。\n（大门被推开，${hero}逆光而立。）\n`);
  }
  parts.push(sc(n, S[Math.min(n, S.length) - 1]));
  parts.push(`（真相揭晓：${heroine}的身世与${g.hook}牵出的旧案当众摊开，${villain}瘫坐在地。）\n${hero}：（看向${heroine}，伸出手）现在，轮到我们清算自己的事了。\n${heroine}：（与他对视，缓缓把手放上去）好啊。不过这一次——规则我来定。\n[钩子] 黑暗处，一只戴手套的手碾灭烟头：「${g.hook}……终于出现了。」\n`);

  return parts.join('');
}

// ---------- 剧本解析（任意文本 → 结构化分镜） ----------
const SHOT_TYPES = ['全景', '中景', '近景', '特写'];
const CAMERAS = ['固定机位', '缓慢推近', '环绕运镜', '跟随移动', '拉远收尾'];

export function localParse(script = '', { style = '', maxShots = 14 } = {}) {
  const text = String(script || '').trim();
  const rnd = seededRandom(hashCode(text.slice(0, 500)));
  const title = (text.match(/《(.+?)》/) || [])[1] || text.split('\n')[0]?.slice(0, 20) || '未命名短剧';
  const styleHint = style || '电影质感，胶片色调，高对比布光';

  // 人物：【人物】块 + 台词说话人
  const charMap = new Map();
  const block = text.match(/【人物】([\s\S]*?)(?=\n【|\n第\s*\d+\s*场|$)/);
  if (block) {
    for (const line of block[1].split('\n')) {
      const m = line.match(/^\s*([^\s（(:：】]{1,12})(（[^）]*）)?[:：](.+)$/);
      if (m) charMap.set(m[1], (m[2] || '').replace(/[（）]/g, '') + ' ' + m[3].trim());
    }
  }
  for (const m of text.matchAll(/^\s*([^\s（(:：【\][]{1,8})[:：](?!\/)/gm)) {
    const name = m[1];
    if (['场景', '类型', '灵感', '风格', '旁白', '字幕', '注', '画外音'].includes(name)) continue;
    if (!charMap.has(name)) charMap.set(name, '剧中人物');
  }
  if (!charMap.size) charMap.set('主角', '故事的核心人物');

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
        body: text.slice(start, end)
      });
    });
  } else {
    sceneBlocks.push({ name: '主场景', body: text });
  }

  // 道具
  const props = [];
  const propBlock = text.match(/【(?:关键)?道具】([\s\S]*?)(?=\n【|\n第\s*\d+\s*场|$)/);
  if (propBlock) {
    for (const line of propBlock[1].split('\n')) {
      const m = line.match(/^\s*([^\s:：]{1,14})[:：](.+)$/);
      if (m) props.push({ name: m[1], desc: m[2].trim() });
    }
  }

  const characters = [...charMap.entries()].slice(0, 6).map(([name, desc], i) => ({
    key: `c${i + 1}`, name, role: i === 0 ? '主角' : '角色', desc: desc.trim().slice(0, 80),
    image_prompt: `${styleHint}，人物肖像，${name}，${desc.trim().slice(0, 60)}，半身正面，浅景深`
  }));
  const charKeyByName = new Map(characters.map((c) => [c.name, c.key]));

  const scenes = sceneBlocks.slice(0, 8).map((s, i) => ({
    key: `s${i + 1}`, name: s.name, desc: s.body.trim().split('\n')[0]?.slice(0, 60) || s.name,
    image_prompt: `${styleHint}，场景概念图，${s.name}，空镜，氛围光影`
  }));
  const propList = props.slice(0, 4).map((p, i) => ({
    key: `p${i + 1}`, name: p.name, desc: p.desc.slice(0, 60),
    image_prompt: `${styleHint}，道具特写，${p.name}，${p.desc.slice(0, 40)}，置于桌面，戏剧布光`
  }));

  // 分镜：每场提取动作行（…）与台词行
  const shots = [];
  sceneBlocks.forEach((s, si) => {
    if (shots.length >= maxShots) return;
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
    const chosen = beats.length > 4 ? beats.filter((_, i) => i % Math.ceil(beats.length / 4) === 0).slice(0, 4) : beats;
    chosen.forEach((b) => {
      if (shots.length >= maxShots) return;
      const i = shots.length + 1;
      const speakKeys = b.speakers.map((n) => charKeyByName.get(n)).filter(Boolean);
      const who = b.speakers[0] || characters[0].name;
      const shotType = b.type === 'dialogue' ? pick(['近景', '特写'], rnd) : pick(SHOT_TYPES, rnd);
      shots.push({
        key: `sh${i}`, order: i, scene: scenes[Math.min(si, scenes.length - 1)].key,
        characters: speakKeys.length ? speakKeys : [characters[0].key],
        shot_type: shotType, camera: pick(CAMERAS, rnd),
        action: b.type === 'action' ? b.text.slice(0, 80) : `${who}说话，情绪随台词起伏`,
        dialogue: b.type === 'dialogue' ? b.text.slice(0, 60) : '',
        duration: 4 + Math.round(rnd() * 3),
        image_prompt: `${styleHint}，${shotType}，${scenes[Math.min(si, scenes.length - 1)].name}，${who}，${b.text.slice(0, 50)}`,
        video_prompt: `${b.text.slice(0, 60)}，${pick(CAMERAS, rnd)}，${styleHint}`
      });
    });
  });
  if (!shots.length) {
    shots.push({
      key: 'sh1', order: 1, scene: 's1', characters: ['c1'], shot_type: '全景', camera: '缓慢推近',
      action: text.slice(0, 60) || '开场空镜', dialogue: '', duration: 5,
      image_prompt: `${styleHint}，开场全景，${scenes[0].name}`, video_prompt: `开场氛围镜头，缓慢推近，${styleHint}`
    });
  }

  return { title, logline: text.replace(/\s+/g, ' ').slice(0, 80), style: styleHint, characters, scenes, props: propList, shots };
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
   <text x="${w - 87}" y="${h - 22}" font-size="13" fill="rgba(255,255,255,0.92)" text-anchor="middle" font-family="system-ui,'PingFang SC','Microsoft YaHei'">青鸾 · 本地生成 ${escapeXML(label)}</text></g>`;
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
function characterArt(rnd, w, h, hue) {
  const cx = w / 2, cy = h * 0.42;
  return `
  <circle cx="${cx}" cy="${cy - h * 0.115}" r="${h * 0.1}" fill="rgba(10,14,26,0.92)" stroke="hsl(${hue},70%,68%)" stroke-width="3"/>
  <path d="M ${cx - w * 0.26} ${h * 0.78} Q ${cx} ${cy + h * 0.04} ${cx + w * 0.26} ${h * 0.78} L ${cx + w * 0.3} ${h} L ${cx - w * 0.3} ${h} Z"
        fill="rgba(10,14,26,0.92)" stroke="hsl(${hue},70%,68%)" stroke-width="3"/>
  <circle cx="${cx - w * 0.052}" cy="${cy - h * 0.125}" r="4.5" fill="hsl(${hue},85%,75%)"/>
  <circle cx="${cx + w * 0.052}" cy="${cy - h * 0.125}" r="4.5" fill="hsl(${hue},85%,75%)"/>
  <path d="M ${cx - w * 0.04} ${cy - h * 0.085} Q ${cx} ${cy - h * 0.07} ${cx + w * 0.04} ${cy - h * 0.085}" stroke="hsl(${hue},85%,75%)" stroke-width="3" fill="none" stroke-linecap="round"/>`;
}
function propArt(rnd, w, h, hue) {
  const cx = w / 2, cy = h * 0.5;
  return `
  <ellipse cx="${cx}" cy="${h * 0.74}" rx="${w * 0.2}" ry="${h * 0.035}" fill="rgba(0,0,0,0.4)"/>
  <rect x="${cx - w * 0.13}" y="${h * 0.62}" width="${w * 0.26}" height="${h * 0.12}" rx="10" fill="rgba(16,20,36,0.9)" stroke="hsl(${hue},60%,55%)" stroke-width="2"/>
  <circle cx="${cx}" cy="${cy - h * 0.04}" r="${h * 0.13}" fill="hsl(${hue},80%,62%)" opacity="0.92"/>
  <circle cx="${cx}" cy="${cy - h * 0.04}" r="${h * 0.2}" fill="none" stroke="hsl(${hue},80%,70%)" stroke-width="2" stroke-dasharray="6 10" opacity="0.7"/>`;
}

/** 本地生成一张 SVG 图（kind: character|scene|prop|frame），返回 SVG 字符串 */
export function localImageSVG({ prompt = '', name = '', kind = 'scene', ratio = '16:9', order = 0 }) {
  const seed = hashCode(kind + name + prompt);
  const rnd = seededRandom(seed);
  const pal = PALETTES[seed % PALETTES.length];
  const hue = pal[1];
  const dim = kind === 'character' ? { w: 768, h: 960 } : ratioSize(ratio, 1280);
  const { w, h } = dim;
  const id = (seed % 9973).toString(36);

  let art = '';
  if (kind === 'character') art = characterArt(rnd, w, h, hue);
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

/** 把 SVG 落盘到 uploads，返回 /uploads/xxx.svg */
export function saveSVG(svg) {
  const name = `${uid('loc')}.svg`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), svg, 'utf8');
  return `/uploads/${name}`;
}
