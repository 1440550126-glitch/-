// ============================================================
// 文字变动画：文案 → Animation Manifest（服务端是"导演"，客户端是"播放器"）
// 大模型可选增强；本地规则引擎保证零成本、离线、永不失败。
// ============================================================
import { clamp, hashCode, seededRand, jparse } from './util.js';
import { llmOrFallback } from './llm.js';

// ---- 情绪词典（valence 情绪正负 / arousal 唤醒度） ----
const EMOTIONS = [
  { key: '热血', valence: 0.7, arousal: 0.95, words: ['冲', '奔跑', '赢', '燃', '出发', '少年', '梦想', '加油', '热烈', '不服', '拼', '逆风'] },
  { key: '心动', valence: 0.85, arousal: 0.6, words: ['喜欢', '爱', '心动', '见你', '牵手', '吻', '在一起', '怦然', '甜', '恋爱', '告白'] },
  { key: '搞笑', valence: 0.6, arousal: 0.75, words: ['哈哈', '离谱', '笑死', '打工', '摆烂', '救命', '蚌', '绷不住', '乐', '搞笑'] },
  { key: '治愈', valence: 0.55, arousal: 0.3, words: ['温柔', '慢慢', '晒太阳', '好好', '治愈', '拥抱自己', '春天', '花开', '猫', '柔软', '没关系'] },
  { key: '平静', valence: 0.2, arousal: 0.15, words: ['安静', '呼吸', '发呆', '夜空', '入睡', '平静', '茶', '云朵', '停下来'] },
  { key: '思念', valence: -0.1, arousal: 0.3, words: ['想你', '远方', '信', '旧', '回忆', '故乡', '从前', '想念', '梦见'] },
  { key: '孤独', valence: -0.45, arousal: 0.25, words: ['一个人', '孤独', '等', '失眠', '空', '无人', '沉默', '深夜', '路灯'] },
  { key: '难过', valence: -0.75, arousal: 0.45, words: ['哭', '碎', '破防', '难过', '算了', '眼泪', '失去', '再见', '遗憾', '散了'] }
];

// ---- 语义元素规则：文案出现什么，画面就出现什么 ----
const ELEMENT_RULES = [
  { words: ['风', '吹'], particle: 'windline', flow: 'windline', ambient: 'wind', scene: '有风经过的地方' },
  { words: ['雨', '淋', '雨声'], weather: 'rain', particle: 'raindrop', ambient: 'rain', scene: '落雨的街' },
  { words: ['伞'], actor: 'umbrella', scene: '落雨的街' },
  { words: ['雪'], weather: 'snow', particle: 'snowflake', ambient: 'wind', scene: '落雪的夜' },
  { words: ['樱', '花瓣', '花开', '春'], particle: 'petal', scene: '开花的季节' },
  { words: ['星', '银河', '宇宙', '星空'], particle: 'star', ambient: 'night', scene: '星空下' },
  { words: ['月'], actor: 'moon', ambient: 'night', scene: '月亮升起的晚上' },
  { words: ['太阳', '晒', '日落', '黄昏'], actor: 'sun', scene: '有光的下午' },
  { words: ['海', '浪', '岸'], ground: 'sea', ambient: 'waves', scene: '海边' },
  { words: ['云'], actor: 'cloud', scene: '云很低的一天' },
  { words: ['猫', '喵'], actor: 'cat', sound: 'purr', scene: '有猫出没的角落' },
  { words: ['萤', '灯火', '路灯', '光'], particle: 'firefly', scene: '亮着光的地方' },
  { words: ['火', '燃', '焰'], particle: 'spark', ambient: 'fire', scene: '燃烧的时刻' },
  { words: ['城市', '街', '楼', '地铁'], skyline: true, scene: '城市边缘' },
  { words: ['心动', '心跳', '喜欢', '爱', '想你'], actor: 'heart', sound: 'heartbeat' },
  { words: ['碎', '心碎', '破防', '失去', '裂'], actor: 'brokenheart', sound: 'crack', particle: 'shard' },
  { words: ['等', '原地', '守', '站在'], behavior: 'wait' },
  { words: ['走', '离开', '散步', '路过'], behavior: 'walk', sound: 'steps' },
  { words: ['跑', '冲', '奔', '追'], behavior: 'run', sound: 'steps' },
  { words: ['拥抱', '抱'], actor: 'figure2', behavior: 'hug', sound: 'heartbeat' },
  { words: ['抬头', '仰望', '看天'], behavior: 'look_up' },
  { words: ['睡', '梦', '晚安'], behavior: 'sleep', ambient: 'night' }
];

// ---- 动画风格（皮肤只换外观；高级风格走高级额度） ----
export const ANIM_STYLES = [
  { id: 'ink', name: '清墨', tier: 'free', blurb: '极简白线，像呼吸一样安静' },
  { id: 'sakura', name: '樱粉', tier: 'member', blurb: '粉雾与花瓣，温柔到融化' },
  { id: 'neon', name: '霓夜', tier: 'member', blurb: '深夜霓虹，情绪在发光' },
  { id: 'starry', name: '星海', tier: 'member', blurb: '把文字撒进银河里' },
  { id: 'aurora', name: '极光幻境', tier: 'premium', credits: 10, blurb: '高级模型导演的流体极光' },
  { id: 'inkgold', name: '鎏金墨', tier: 'premium', credits: 10, blurb: '墨色与碎金，电影感收藏级' }
];

const STYLE_PALETTES = {
  ink: { day: { bg: ['#f7f4ee', '#e8e4f3'], ink: '#3a3550', accent: '#8d7ae6', glow: '#b9aaff' }, night: { bg: ['#1c1d2e', '#272a44'], ink: '#e8e6f7', accent: '#9d8cff', glow: '#7c6cff' } },
  sakura: { day: { bg: ['#fff0f4', '#ffe1ec'], ink: '#7a4a5e', accent: '#ff8fb3', glow: '#ffc7da' }, night: { bg: ['#2e1f2c', '#46283f'], ink: '#ffd9e6', accent: '#ff8fb3', glow: '#ff6fa5' } },
  neon: { day: { bg: ['#15162b', '#1f2040'], ink: '#d8f4ff', accent: '#41e0d0', glow: '#34d2ff' }, night: { bg: ['#0e0f22', '#1b1038'], ink: '#e3f9ff', accent: '#ff5fd2', glow: '#37e2ff' } },
  starry: { day: { bg: ['#1b2347', '#28315e'], ink: '#eef1ff', accent: '#86a8ff', glow: '#a9c0ff' }, night: { bg: ['#111634', '#1d2452'], ink: '#eef1ff', accent: '#86a8ff', glow: '#8ea8ff' } },
  aurora: { day: { bg: ['#102036', '#143a4e'], ink: '#e7fff7', accent: '#5ef0c0', glow: '#74f7ff' }, night: { bg: ['#0c1830', '#123c4a'], ink: '#e7fff7', accent: '#5ef0c0', glow: '#63ffd8' } },
  inkgold: { day: { bg: ['#23211f', '#363028'], ink: '#f4ead2', accent: '#e8b14c', glow: '#ffd479' }, night: { bg: ['#1b1916', '#2c2620'], ink: '#f4ead2', accent: '#e8b14c', glow: '#ffcd66' } }
};

const VALID = {
  actors: ['figure', 'figure2', 'cat', 'heart', 'brokenheart', 'moon', 'sun', 'cloud', 'umbrella'],
  particles: ['windline', 'raindrop', 'snowflake', 'petal', 'star', 'spark', 'shard', 'firefly', 'bubble'],
  behaviors: ['wait', 'walk', 'run', 'hug', 'look_up', 'breathe', 'sleep', 'bounce'],
  weather: ['none', 'rain', 'snow'],
  grounds: ['line', 'sea', 'none'],
  ambients: ['none', 'wind', 'rain', 'waves', 'night', 'fire'],
  sounds: ['chime', 'swoosh', 'heartbeat', 'crack', 'pop', 'steps', 'purr', 'wind', 'rain', 'waves', 'night', 'fire']
};

// ---- 文案分析 ----
export function analyzeText(text) {
  const t = String(text || '').trim();
  const scores = EMOTIONS.map((e) => ({ e, n: e.words.reduce((acc, w) => acc + (t.includes(w) ? 1 : 0), 0) }));
  scores.sort((a, b) => b.n - a.n);
  const top = scores[0].n > 0 ? scores[0].e : EMOTIONS.find((e) => e.key === '治愈');
  const intensity = clamp(0.45 + scores[0].n * 0.18 + Math.min(t.length / 80, 0.2), 0.3, 1);

  const found = { actors: [], particles: [], flows: [], ambients: [], sounds: [], behaviors: [], weather: 'none', ground: 'line', skyline: false, scenes: [] };
  for (const rule of ELEMENT_RULES) {
    if (!rule.words.some((w) => t.includes(w))) continue;
    if (rule.actor && !found.actors.includes(rule.actor)) found.actors.push(rule.actor);
    if (rule.particle && !found.particles.includes(rule.particle)) found.particles.push(rule.particle);
    if (rule.flow && !found.flows.includes(rule.flow)) found.flows.push(rule.flow);
    if (rule.ambient && !found.ambients.includes(rule.ambient)) found.ambients.push(rule.ambient);
    if (rule.sound && !found.sounds.includes(rule.sound)) found.sounds.push(rule.sound);
    if (rule.behavior && !found.behaviors.includes(rule.behavior)) found.behaviors.push(rule.behavior);
    if (rule.weather) found.weather = rule.weather;
    if (rule.ground) found.ground = rule.ground;
    if (rule.skyline) found.skyline = true;
    if (rule.scene) found.scenes.push(rule.scene);
  }

  const night = /夜|晚|月|星|梦|睡|失眠|凌晨/.test(t) || top.valence < -0.3;
  const scene = found.scenes[0] || (night ? '安静的夜里' : '留白的文案空间');
  const keywords = t.split(/[，。、,.!?！？\s~…—]+/).filter(Boolean).slice(0, 6);
  return {
    emotion: { key: top.key, valence: top.valence, arousal: top.arousal, intensity },
    found, night, scene, keywords, length: t.length
  };
}

// ---- 预览卡（每个帖子免费生成，纯本地零成本） ----
const CARD_PATTERNS = { windline: 'wind', raindrop: 'rain', snowflake: 'snow', petal: 'petal', star: 'star', firefly: 'firefly', spark: 'spark', shard: 'shard' };
export function buildCard(text, seedStr = '') {
  const a = analyzeText(text);
  const rnd = seededRand(hashCode(text + seedStr));
  const pal = STYLE_PALETTES.ink[a.night ? 'night' : 'day'];
  const soft = {
    '热血': ['#fff0e3', '#ffd9c2'], '心动': ['#fff0f5', '#ffdcec'], '搞笑': ['#fffbe0', '#ffeebb'],
    '治愈': ['#f1faf3', '#dcf2e4'], '平静': ['#eef4fb', '#dde9f7'], '思念': ['#f3f0fa', '#e4ddf5'],
    '孤独': ['#23243a', '#33365a'], '难过': ['#262736', '#3a3d55']
  }[a.emotion.key] || pal.bg;
  const dark = a.emotion.valence < -0.3;
  return {
    v: 2,
    layout: a.length > 36 ? 'poem' : a.length > 14 ? 'note' : 'hero',
    emotion: a.emotion.key,
    scene: a.scene,
    bg: soft,
    ink: dark ? '#eceaf6' : '#41395c',
    accent: dark ? '#9d8cff' : '#8d7ae6',
    pattern: CARD_PATTERNS[a.found.particles[0]] || (a.night ? 'star' : 'wind'),
    seed: Math.floor(rnd() * 1e9),
    hint: '长按卡片，让这句话活过来',
    ai_label: 'AI 辅助生成'
  };
}

// ---- Manifest 主体（规则引擎） ----
export function buildManifest(text, { style = 'ink', seed } = {}) {
  const a = analyzeText(text);
  const sd = seed ?? hashCode(text + style);
  const rnd = seededRand(sd);
  const stylePal = STYLE_PALETTES[style] || STYLE_PALETTES.ink;
  const palette = stylePal[a.night || ['neon', 'starry'].includes(style) ? 'night' : 'day'];
  const { emotion, found } = a;

  // 人物与行为：文案说等待就等待，说奔跑就奔跑
  let behavior = found.behaviors[0];
  if (!behavior) {
    behavior = emotion.arousal > 0.8 ? 'run'
      : emotion.key === '搞笑' ? 'bounce'
      : emotion.key === '孤独' || emotion.key === '思念' ? 'wait'
      : found.particles.includes('star') || found.actors.includes('moon') ? 'look_up'
      : 'breathe';
  }
  const actors = [];
  if (found.behaviors.includes('hug') || found.actors.includes('figure2')) {
    actors.push({ id: 'p2', type: 'figure2', x: 0.5, y: 0.74, scale: 1, behavior: 'hug' });
  } else {
    actors.push({ id: 'p1', type: 'figure', x: behavior === 'run' ? 0.3 : 0.5, y: 0.74, scale: 1, behavior });
  }
  for (const t of found.actors) {
    if (t === 'figure2') continue;
    const posMap = { moon: [0.78, 0.18], sun: [0.76, 0.2], cloud: [0.3, 0.18], heart: [0.5, 0.34], brokenheart: [0.5, 0.34], cat: [0.72, 0.78], umbrella: [0.5, 0.6] };
    const [x, y] = posMap[t] || [0.35 + rnd() * 0.3, 0.3 + rnd() * 0.2];
    actors.push({ id: t, type: t, x, y, scale: 1, behavior: t === 'heart' ? 'pulse' : 'float' });
    if (actors.length >= 4) break;
  }

  // 粒子：密度跟随情绪强度
  const baseDensity = 0.35 + emotion.intensity * 0.45;
  const particles = found.particles.slice(0, 3).map((kind) => ({ kind, density: +clamp(baseDensity * (kind === 'shard' ? 0.5 : 1), 0.15, 1).toFixed(2) }));
  if (!particles.length) particles.push({ kind: a.night ? 'star' : 'firefly', density: 0.25 });

  // 环境音：取第一个；安静情绪压低音量
  const ambient = found.ambients[0] || (a.night ? 'night' : 'wind');
  const volume = +clamp(0.25 + emotion.arousal * 0.5, 0.2, 0.8).toFixed(2);

  // 时间轴：入场 → 文字粒子重组 → 元素依次苏醒 → 情绪节拍 → 循环
  const timeline = [
    { t: 0, target: 'text', action: 'glow', dur: 0.7, sound: 'chime' },
    { t: 0.6, target: 'text', action: 'assemble', dur: 1.5, sound: 'swoosh' },
    { t: 1.2, target: 'scene', action: 'wake', dur: 1.0 }
  ];
  let tt = 2.1;
  for (const ac of actors) {
    timeline.push({ t: +tt.toFixed(2), target: ac.id, action: 'enter', dur: 0.8 });
    tt += 0.35;
  }
  if (found.sounds.includes('heartbeat')) timeline.push({ t: 3.6, target: 'heart', action: 'beat', dur: 1.2, sound: 'heartbeat' });
  if (found.sounds.includes('crack')) timeline.push({ t: 4.0, target: 'brokenheart', action: 'crack', dur: 1.0, sound: 'crack' });
  if (found.sounds.includes('steps')) timeline.push({ t: 2.4, target: 'p1', action: 'move', dur: 3.0, sound: 'steps' });
  if (found.sounds.includes('purr')) timeline.push({ t: 3.2, target: 'cat', action: 'purr', dur: 1.5, sound: 'purr' });

  return {
    v: 2,
    style,
    seed: sd,
    emotion,
    scene: { name: a.scene, weather: found.weather, ground: found.ground, skyline: found.skyline, night: a.night },
    palette,
    text: { mode: 'particle_assemble', glow: true },
    actors,
    particles,
    flows: found.flows.map((kind) => ({ from: 'text', kind, strength: +emotion.intensity.toFixed(2) })),
    timeline,
    soundscape: { ambient, volume },
    behavior: {
      loop: true,
      loopFrom: 3.2,
      breath: +(0.4 + emotion.arousal * 0.8).toFixed(2),     // 呼吸/起伏频率
      jitter: +(0.15 + emotion.arousal * 0.35).toFixed(2),   // 随机微动幅度
      speedCurve: emotion.arousal > 0.6 ? 'eager' : 'gentle' // 非线性速度曲线
    },
    duration: 9,
    caption: null,
    meta: { generated_by: 'rule', ai_label: '内容由 AI 辅助生成' }
  };
}

// ---- 大模型增强（导演模式）：返回 JSON 补丁，经白名单校验后合并 ----
function sanitizePatch(patch, manifest) {
  if (!patch || typeof patch !== 'object') return manifest;
  const m = { ...manifest };
  if (typeof patch.scene_name === 'string') m.scene = { ...m.scene, name: patch.scene_name.slice(0, 24) };
  if (typeof patch.caption === 'string') m.caption = patch.caption.slice(0, 60);
  if (Array.isArray(patch.add_particles)) {
    for (const p of patch.add_particles.slice(0, 2)) {
      if (VALID.particles.includes(p?.kind) && !m.particles.some((x) => x.kind === p.kind)) {
        m.particles = [...m.particles, { kind: p.kind, density: clamp(p.density ?? 0.4, 0.1, 1) }];
      }
    }
  }
  if (Array.isArray(patch.add_actors)) {
    for (const ac of patch.add_actors.slice(0, 2)) {
      if (VALID.actors.includes(ac?.type) && m.actors.length < 5) {
        m.actors = [...m.actors, {
          id: `${ac.type}_x${m.actors.length}`, type: ac.type,
          x: clamp(ac.x ?? 0.5, 0.05, 0.95), y: clamp(ac.y ?? 0.4, 0.05, 0.95),
          scale: clamp(ac.scale ?? 1, 0.5, 1.6),
          behavior: VALID.behaviors.includes(ac.behavior) ? ac.behavior : 'float'
        }];
      }
    }
  }
  if (VALID.ambients.includes(patch.ambient)) m.soundscape = { ...m.soundscape, ambient: patch.ambient };
  if (patch.palette && /^#[0-9a-fA-F]{6}$/.test(patch.palette.accent || '')) {
    m.palette = { ...m.palette, accent: patch.palette.accent, glow: /^#[0-9a-fA-F]{6}$/.test(patch.palette.glow || '') ? patch.palette.glow : m.palette.glow };
  }
  if (typeof patch.arousal === 'number') m.emotion = { ...m.emotion, arousal: clamp(patch.arousal, 0, 1) };
  return m;
}

export async function buildManifestEnhanced(text, { style, seed, userId, premium = false }) {
  const base = buildManifest(text, { style, seed });
  const system = '你是"句灵"的动画导演。根据用户文案输出一个 JSON 补丁，让线条动画更贴合文案的情绪与画面。' +
    `只能输出 JSON，字段：scene_name(短场景名), caption(20字内的一句画面旁白), arousal(0-1), ambient(${VALID.ambients.join('/')}), ` +
    `add_particles(数组,kind∈${VALID.particles.join('/')},density0-1,最多2个), add_actors(数组,type∈${VALID.actors.join('/')},x,y0-1,behavior∈${VALID.behaviors.join('/')},最多2个), ` +
    'palette({accent,glow}十六进制颜色)。不要输出其他内容。';
  const r = await llmOrFallback({
    feature: premium ? 'manifest_premium' : 'manifest',
    userId,
    tier: premium ? 'premium' : 'default',
    system,
    prompt: `文案：「${String(text).slice(0, 200)}」\n当前情绪判定：${base.emotion.key}。请给出补丁 JSON。`,
    json: true,
    maxTokens: 400,
    temperature: 0.7,
    fallbackFn: () => null
  });
  if (r.byLLM) {
    const merged = sanitizePatch(jparse(r.text, null), base);
    merged.meta = { generated_by: premium ? 'llm_premium' : 'llm', ai_label: '内容由 AI 生成' };
    return merged;
  }
  return base;
}
