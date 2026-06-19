// 灵境AI · 创作流水线：剧本 → 分镜 → 画布 → 图像 → 视频
// 配置了火山方舟 Key 走真实模型；否则自动落到本地规则引擎（结果带 provider 标识）
import { q, getSetting, setSetting } from './db.js';
import { uid, now, jparse, clamp } from './util.js';
import { arkEnabled, llmEnabled, arkChat, arkImage, arkVideoCreate, arkVideoGet, cfg } from './ark.js';
import { pickImageProvider, pickVideoProvider, openaiImage, googleVeoCreate, googleVeoGet, dashscopeImage, dashscopeVideoCreate, dashscopeTaskGet } from './providers.js';
import { localScript, localParse, localImageSVG, localVideoSVG, saveSVG, localNextEpisode, localViralAnalysis, guessGender, splitScriptSegments } from './local.js';
import { resolveStylePrompt } from './styles.js';
import { bad, notFound } from './httpx.js';

// 已接入方舟时，生成失败是否静默落本地占位（默认否：诚实暴露真实错误，便于排查模型配置）
export const localFallbackOn = () => getSetting('local_fallback', false) === true;

// ---------- Agent 进化大脑：累积用户对「角色/场景/道具」的人工校正，越用越准；夸赞给经验值 ----------
// 存在 settings.agent_brain：{ labels:{名字:类型}, confirms, corrections, xp, streak }
const BRAIN_KEY = 'agent_brain';
const ENTITY_TYPES = new Set(['character', 'scene', 'prop']);
export function getAgentBrain() {
  const b = getSetting(BRAIN_KEY, null) || {};
  const xp = b.xp || 0;
  const total = (b.confirms || 0) + (b.corrections || 0);
  return {
    labels: b.labels || {}, confirms: b.confirms || 0, corrections: b.corrections || 0,
    xp, streak: b.streak || 0,
    level: Math.floor(xp / 100) + 1,
    title: ['新手', '学徒', '熟练', '资深', '专家', '宗师'][Math.min(5, Math.floor(xp / 100))],
    accuracy: total ? Math.round((b.confirms || 0) / total * 100) : null,
    learned: Object.keys(b.labels || {}).length
  };
}
function saveBrain(patch) {
  const b = getSetting(BRAIN_KEY, null) || { labels: {}, confirms: 0, corrections: 0, xp: 0, streak: 0 };
  b.labels = { ...(b.labels || {}), ...(patch.labels || {}) };
  for (const k of ['confirms', 'corrections', 'xp', 'streak']) if (patch[k] != null) b[k] = patch[k] === '+' ? 0 : (b[k] || 0) + patch[k];
  if (patch.resetStreak) b.streak = 0;
  setSetting(BRAIN_KEY, b);
  return b;
}
/** 查询某名字的已学类型（用户校正/确认过的，权威覆盖启发式） */
function learnedTypeOf(name) {
  const t = (getSetting(BRAIN_KEY, null)?.labels || {})[name];
  return ENTITY_TYPES.has(t) ? t : null;
}
/** 夸赞：分类全对时调用，涨经验、连击、确认计数 */
export function praiseAgent() {
  saveBrain({ confirms: 1, xp: 12, streak: 1 });
  return getAgentBrain();
}

// ---------- 画风锚定：全片只用一种画风，杜绝"一会儿日漫一会儿2D热血"的前后跳风 ----------
function styleAnchor(sb) { return String(sb.style || '统一电影质感').replace(/\s+/g, ' ').slice(0, 120); }
const STYLE_DRIFT_NEG = '禁止在不同镜头间切换画风/画质/渲染方式（写实↔动漫、2D↔3D、日系↔美系、厚涂↔扁平、水墨↔赛璐璐等一律不得混用），全片线条·上色·色调·光影风格严格统一。';
/** 把项目选定的画风强制写进分镜（解析后/校正后调用），统一 style 并重建锁定/总纲/对齐 */
export function lockStyle(sb, styleName) {
  const sp = resolveStylePrompt(styleName);
  if (sp) sb.style = sp.slice(0, 120);
  buildLocks(sb); sb.bible = buildBible(sb); alignStoryboard(sb);
  return sb;
}


// 构图/解剖护栏：解决"上半身在地面、下半身不见、只漏个头、穿模"等残缺问题。
// 按用途与景别给出明确的取景、姿态与解剖约束 + 负向词，追加到任何来源的提示词上。
// 用户硬性【禁止项】——注入每一张图、每一段视频：
export const FORBIDDEN_RULES = [
  '角色身体埋进地面或墙体（穿模）', '只显示头部、其余身体缺失', '角色悬空漂浮',
  '脚底穿过地面、双脚悬在地面下', '人物重心/碰撞中心错误导致姿态失衡', '身体各部位缩放比例异常、头身比失调',
  '人物下沉、半身陷入地面', '肢体残缺/多余、上下半身错位分离、面部扭曲畸形/恐怖谷',
  '多出的手·手臂·手指（如三只手、六根手指）、手部结构错乱', '同一角色身高·体型·头身比在镜头间突变',
  '笑容或表情狰狞凶恶、儿童面容诡异老成（儿童须自然童真、笑容温和）'
];
const NEG_TAIL = `【禁止出现】${FORBIDDEN_RULES.join('；')}。要求：人物完整、双脚稳踏地面、双手结构正确（每只手五根手指、不多手不畸形）、解剖正确、比例协调、表情自然真实、与地面关系合理。`;
// 视频额外禁止项（动画/一致性）：
const VIDEO_NEG = `【视频禁止】角色播放中下沉/陷地/穿模/漂浮；改变角色外观·服装·武器·发型·身材比例；身高/头身比突变；出现多手多指或手部畸形；表情变狰狞；中途换成另一个人。要求：全程锁定同一角色形象与身高体型，双脚始终踏实地面，手部正常，表情自然，物理稳定。`;
function framingGuide(kind, shotType = '') {
  if (kind === 'character') {
    return `，角色三视图设定图（character turnaround / model sheet）：同一角色【正面、四分之三侧面、背面】三个全身视角横向并排，三个视角的五官·发型·服装·配色·身高体型完全一致，自然站姿、全身完整入镜（含双脚不被裁断），纯白背景、无投影、无文字标注，五官清晰对称、表情自然不诡异（避免恐怖谷、笑容温和不狰狞），双手结构正确（五指、不多手不畸形），外貌特征鲜明辨识度高（与其他角色明显区分、不撞脸）。${NEG_TAIL}`;
  }
  if (kind === 'scene') {
    return `，场景空镜，无人物出现，环境陈设完整，层次分明，电影级布光与大气透视。`;
  }
  if (kind === 'prop') {
    return `，道具静物特写，物件完整居中、细节清晰，纯净或虚化背景，无人物。${NEG_TAIL}`;
  }
  // frame：按景别决定取景，强约束人物完整
  const st = String(shotType || '');
  let framing = '人物完整入镜、不被画框裁断';
  if (/特写/.test(st)) framing = '面部或局部特写，五官完整清晰、不畸变';
  else if (/近景/.test(st)) framing = '胸部以上半身，头部完整在画面内、不被裁断';
  else if (/中景/.test(st)) framing = '腰部或膝盖以上，身体比例完整连贯';
  else if (/全景|远景/.test(st)) framing = '人物全身完整入镜，站立或动作姿态清晰，脚部在画面内';
  return `，${framing}，人物站位与地面关系合理（站立时双脚着地、坐姿明确），全身比例连贯不分离。${NEG_TAIL}`;
}

/** 项目风格注入：prompt 未包含该风格时自动前置（风格名自动展开成完整提示词） */
function applyStyle(prompt, style) {
  const sp = resolveStylePrompt(style);
  if (!sp) return prompt;
  if (prompt.includes(sp.slice(0, 12))) return prompt;
  return `${sp}，${prompt}`;
}

// ---------- 项目 ----------
export function getProject(id, { required = true } = {}) {
  const p = q.get('SELECT * FROM projects WHERE id = ?', id);
  if (!p && required) throw notFound('项目不存在');
  return p;
}
export function projectOut(p) {
  return { ...p, storyboard: jparse(p.storyboard, null) };
}
export function touchProject(id, fields = {}) {
  const sets = Object.keys(fields).map((k) => `${k} = ?`).join(', ');
  q.run(`UPDATE projects SET ${sets ? sets + ', ' : ''}updated_at = ? WHERE id = ?`, ...Object.values(fields), now(), id);
}
export function createProject({ title = '', idea = '', genre = '', style = '', ratio = '16:9' } = {}) {
  const id = uid('p');
  const seed = 1 + Math.floor(Math.random() * 2_147_483_000);   // 项目级一致性种子
  q.run(
    'INSERT INTO projects (id, title, idea, genre, style, ratio, seed, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, String(title || '未命名短剧').slice(0, 50), String(idea).slice(0, 2000), String(genre).slice(0, 20),
    String(style).slice(0, 300), ratio, seed, now(), now()
  );
  return q.get('SELECT * FROM projects WHERE id = ?', id);
}

// ---------- 剧本生成 ----------
const SCRIPT_SYSTEM = `你是资深编剧，电影长片与短剧皆精。严格按格式输出，便于程序解析：
1. 第一行《剧名》；第二行可写"类型：xx"；
2. 【人物】块：每行"名字（性别+年龄+身份，性格）：人设描述"——必须写明性别（男/女）；
3. 【关键道具】块（如有）；
4. 分段：电影用"第 N 幕 ｜ 幕标题"，短剧多集用"第 N 集 ｜ 集标题"，单段可省略；
5. 每场以"第 N 场 ｜ 场景：场景名 ｜ 日/夜 ｜ 内/外"单独成行开头；
6. 动作描写用中文圆括号（…）单独成行；台词行用"名字：台词"；旁白/字幕请写"旁白："或"字幕："（不要伪装成人物名）；
7. 每幕/每集结尾用"[钩子] …"留悬念。只输出剧本本体，不要解释。`;

export async function generateScript({ projectId = '', idea = '', genre = '', numScenes = 4, numEpisodes = 1, style = '', title = '', format = 'series' }) {
  let project = projectId ? getProject(projectId) : createProject({ title, idea, genre, style });
  idea = idea || project.idea || project.title;
  genre = genre || project.genre;
  style = style || project.style;
  const movie = format === 'movie';

  let script = '';
  let byLLM = false;
  if (llmEnabled()) {
    try {
      const eps = clamp(numEpisodes, 1, 6);
      const prompt = movie
        ? `请创作一部${genre ? `「${genre}」类型的` : ''}电影长片剧本（约 90 分钟，标准六幕结构）。\n要求：\n1. 每幕以"第 N 幕 ｜ 幕标题"单独成行；全片共 24-30 场；\n2. 5-8 个性格鲜明的人物，每个在【人物】块写明性别、年龄、外貌、性格；\n3. 冲突层层递进，至少 2-3 个有力反转，结尾留余韵；\n4. 每场 4-6 个动作/台词节拍。${style ? `\n整体影像风格：${resolveStylePrompt(style)}。` : ''}\n核心创意：${idea || '自由发挥一个反转强烈、人物鲜活的故事'}`
        : `请创作一部${genre ? `「${genre}」类型的` : ''}短剧剧本，${eps > 1 ? `共 ${eps} 集，每集 ${clamp(numScenes, 2, 8)} 场，集与集之间用强钩子衔接` : `共 ${clamp(numScenes, 2, 8)} 场`}，每场 3-6 个动作/台词节拍。人物在【人物】块写明性别身份。${style ? `整体影像风格：${resolveStylePrompt(style)}。` : ''}\n核心创意：${idea || '自由发挥一个反转强烈的故事'}`;
      const r = await arkChat({
        feature: 'script', system: SCRIPT_SYSTEM, prompt,
        temperature: 0.9,
        maxTokens: movie ? 8000 : (eps > 1 ? 6000 : 3000)
      });
      script = r.text.trim();
      byLLM = true;
    } catch (e) {
      console.warn('[pipeline] 方舟剧本生成失败，落本地引擎：', e.message);
    }
  }
  if (!script) script = localScript({ idea, genre, numScenes, numEpisodes, format, title: title || (projectId ? project.title : '') });

  const newTitle = (script.match(/《(.+?)》/) || [])[1];
  touchProject(project.id, {
    script,
    idea: idea.slice(0, 2000),
    genre,
    ...(style ? { style: String(style).slice(0, 300) } : {}),
    ...(newTitle && (project.title === '未命名短剧' || !projectId) ? { title: newTitle.slice(0, 50) } : {})
  });
  return { project: q.get('SELECT * FROM projects WHERE id = ?', project.id), script, byLLM };
}

// ---------- 爆款复刻：解析参考文案的爆点结构 → 套用到新主题 ----------
const REMAKE_SYSTEM = `你是短剧爆款结构分析师兼编剧。先解析参考文案/剧本的爆点结构，再把同样的结构套用到新主题上创作剧本。只输出 JSON：
{"analysis":{"hook":"开场钩子手法","structure":"节奏结构描述","emotion":"情绪曲线","selling_points":["可复用爆点1","2","3"]},
 "title":"新剧名",
 "script":"完整剧本（严格遵循格式：第一行《剧名》；【人物】块每行 名字（身份）：人设；每场以 第 N 场 ｜ 场景：xx ｜ 日/夜 ｜ 内/外 开头；动作行用（…）单独成行；台词行用 名字：台词；结尾 [钩子] …）"}`;

export async function remakeViral({ reference, topic, projectId = '', genre = '', numScenes = 4 }) {
  if (!reference?.trim()) throw bad('缺少参考爆款文案 reference');
  if (!topic?.trim()) throw bad('缺少你的主题 topic');
  let analysis = null;
  let script = '';
  let title = '';
  let byLLM = false;
  if (llmEnabled()) {
    try {
      const r = await arkChat({
        feature: 'remake', system: REMAKE_SYSTEM, json: true, temperature: 0.85, maxTokens: 5000,
        prompt: `参考爆款文案/剧本：\n${reference.slice(0, 6000)}\n\n请解析其爆点结构，并用同样的结构为新主题创作${genre ? `「${genre}」类型` : ''}短剧剧本（${clamp(numScenes, 2, 8)} 场）。新主题：${topic.slice(0, 500)}`
      });
      const j = jparse(r.text.replace(/```(json)?/g, ''), {});
      if (j.script) {
        analysis = j.analysis || null;
        script = String(j.script);
        title = String(j.title || '');
        byLLM = true;
      }
    } catch (e) {
      console.warn('[pipeline] 方舟爆款复刻失败，落本地引擎：', e.message);
    }
  }
  if (!script) {
    analysis = localViralAnalysis(reference);
    script = localScript({ idea: `${topic}（复刻爆款结构：${analysis.hook}，${analysis.structure}）`, genre, numScenes });
    title = (script.match(/《(.+?)》/) || [])[1] || '';
  }
  const project = projectId ? getProject(projectId) : createProject({ title: title || '爆款复刻', idea: topic, genre });
  touchProject(project.id, {
    script: script.slice(0, 60_000),
    idea: topic.slice(0, 2000),
    status: 'draft',
    ...(title && (project.title === '未命名短剧' || !projectId) ? { title: title.slice(0, 50) } : {})
  });
  return { project: projectOut(q.get('SELECT * FROM projects WHERE id = ?', project.id)), analysis, script, byLLM };
}

// ---------- 剧本解析 → 分镜 ----------
const PARSE_SYSTEM = `你是资深电影分镜师。把剧本（或剧本的一幕/一集）解析为可拍摄的结构化 JSON，只输出 JSON、不要任何解释或 markdown。schema：
{"title":"片名","logline":"一句话故事","style":"画面风格","unit":"幕或集",
 "episodes":[{"key":"e1","title":"本段标题","summary":"本段一句话梗概"}],
 "characters":[{"key":"c1","name":"准确人物名","role":"主角/反派/配角","gender":"男或女","desc":"年龄段+性别+外貌+服装+性格，尽量具体","image_prompt":"人物定妆照文生图提示词，必须含性别年龄外貌服装，并给独特鲜明的外貌锚点（发型/脸型/标志物）确保与其他角色不撞脸"}],
 "scenes":[{"key":"s1","name":"场景名","desc":"环境/时间/氛围","image_prompt":"场景空镜提示词"}],
 "props":[{"key":"p1","name":"关键道具","desc":"","image_prompt":"道具特写提示词"}],
 "shots":[{"key":"sh1","order":1,"episode":"e1","scene":"s1","characters":["c1"],"shot_type":"远景/全景/中景/近景/特写","camera":"运镜描述（如：固定机位/缓推/拉镜/横移/摇镜/跟随/手持抖动/升降臂，可加速度如'缓慢推进'/'快速横移'，电影感镜语优先）","emotion":"主要角色情绪(可空：冷酷/愤怒/狂喜/悲伤/微笑/惊恐/魅惑/羞涩)","action":"画面内发生的事","dialogue":"台词(可空)","duration":4,"image_prompt":"该镜头首帧文生图提示词，写明出场人物名与场景","video_prompt":"图生视频动态提示词（重点描述动作/表情/物理变化，不重复运镜，30字以内）"}]}
铁律：
1. character 只放"有名有姓的活人/角色（人或拟人生物）"。绝不要把以下当成 character：
   - 技术/旁白：字幕、画外音、旁白、镜头、特写、字幕浮现、在另一头喊、画上；
   - 物件/道具：能源核心、收音机、盖革计数器、钥匙、武器、仪器、芯片、徽章等——这些一律放进 props，不得出现在 characters；
2. 每个人物必须判断 gender（只能填"男"或"女"）与年龄段，写进 desc 与 image_prompt；desc 要含外貌/服装/性格；
3. 场景尽量识别全（室内外/废墟/车内/避难所…）；关键物件放 props（写明外形）；
4. 这是一部电影/长片的一个段落，请尽量细分镜：本段输出 12-30 个 shots，覆盖每个关键动作与台词；
5. 同一人物/场景/道具在本段内复用同一 key，不重复建，也不要在 characters 与 props 里重复同一个名字。`;

// 物件关键词：用于把被误判成"角色"的道具纠正回 props
const PROP_RE = /核心|计数器|收音机|钥匙|胰岛素|卡片?|徽章|装置|仪器|晶体|晶片|芯片|数据|能源|匕首|枪|手枪|刀|剑|药剂?|瓶|盒|囊|袋|罐|戒指|项链|地图|信件|手机|电脑|引擎|武器|护符|令牌|徽记|宝石|文件|账本|怀表|罗盘|面具|头盔|铠甲|盔甲|护甲|电池|核弹|炸弹|食物|粮|水/;
// 名字以明确物体名词结尾 → 一定是道具（无视 LLM 误标的性别）
const STRONG_OBJECT = /(核心|芯片|晶片|计数器|收音机|钥匙|徽章|装置|仪器|匕首|手枪|步枪|药剂|戒指|项链|地图|信件|引擎|令牌|怀表|罗盘|面具|头盔|铠甲|盔甲|护甲|电池|炸弹|核弹|晶体|宝石|卡片|囊|袋|罐|瓶|盒|数据|能源块?)$/;
const PERSON_HINT = /[男女]性?|\d+\s*岁|性格|眼神|穿着|身材|头发|发型|脸型|主角|反派|配角|队长|博士|教授|医生|士兵|老人|少年|少女|孩子|护士|警察|战士|杀手|猎人|拾荒者|幸存者/;
const PERSON_NAME = /(队长|博士|教授|医生|护士|老|小|大叔|大妈|爷|奶|哥|姐|弟|妹|先生|女士|王|李|张|刘|陈|赵|孙|周|吴|郑)/;
/** 在桶之间移动一个实体（按名字），离开角色时清掉分镜里对它的连线键。返回移动记录或 null。 */
function moveEntity(sb, name, to) {
  if (!ENTITY_TYPES.has(to)) return null;
  sb.characters ||= []; sb.scenes ||= []; sb.props ||= [];
  const buckets = { character: sb.characters, scene: sb.scenes, prop: sb.props };
  let ent = null, from = null;
  // 扫描所有桶：可能被同时塞进多个桶——首个命中留作迁移源，其余同名一律移除（彻底去重，不再只处理第一个桶）
  for (const t of ['character', 'scene', 'prop']) {
    for (let i = buckets[t].length - 1; i >= 0; i--) {
      if (!buckets[t][i] || buckets[t][i].name !== name) continue;
      if (!ent) { ent = buckets[t][i]; from = t; }
      if (t !== to) buckets[t].splice(i, 1);
    }
  }
  if (!ent || from === to) return null;
  if (ent.key) for (const sh of (sb.shots || [])) {
    if (from === 'character') sh.characters = (sh.characters || []).filter((k) => k !== ent.key);
    if (from === 'scene' && sh.scene === ent.key) sh.scene = '';   // 清掉悬空场景引用，重排时回落默认场景
  }
  // 目标桶尚无同名才添加，避免重复
  if (!buckets[to].some((x) => x && x.name === name)) {
    const moved = { key: ent.key, name: ent.name, desc: ent.desc || ent.image_prompt || '', image_prompt: '' };
    if (to === 'character') { moved.role = ent.role || '角色'; moved.gender = ent.gender || ''; }
    buckets[to].push(moved);
  }
  return { name, from, to };
}

/** 应用 Agent 进化大脑里学到的人工校正（用户权威）：把已知名字强制归位到学过的类型 */
function applyLearnedLabels(sb) {
  const labels = getSetting(BRAIN_KEY, null)?.labels || {};
  for (const [name, to] of Object.entries(labels)) moveEntity(sb, name, to);
}

/** 把被 LLM 误放进 characters 的物件迁回 props（如"能源核心""数据芯片""净水囊"），并做跨桶去重，就地修改 sb */
function reclassifyProps(sb) {
  if (!Array.isArray(sb.characters)) return;
  sb.props ||= []; sb.scenes ||= [];
  const propNames = new Set(sb.props.map((p) => p.name));
  const sceneNames = new Set(sb.scenes.map((s) => s.name));
  const keep = [];
  for (const c of sb.characters) {
    const name = String(c.name || '');
    const desc = String(c.desc || '');
    // 用户已确认为角色的名字 → 权威保留，并清掉其它桶里的同名条目（人物优先，杜绝重复）
    if (learnedTypeOf(name) === 'character') {
      sb.props = sb.props.filter((p) => p.name !== name);
      sb.scenes = sb.scenes.filter((s) => s.name !== name);
      keep.push(c); continue;
    }
    // 同名已存在于道具/场景桶 → 多为大模型把同一条目同时塞进两个桶，丢弃这条重复的人物条目
    // （道具/场景已正确识别，优先保留，杜绝"人物识别里还有那个道具"的重复）
    if (propNames.has(name) || sceneNames.has(name)) continue;
    // 描述里有"性格/眼神/穿着/发型/身材/职业"等真人线索才算真人（性别字段易被大模型瞎填，不作准）
    const personDesc = PERSON_HINT.test(desc);
    // 名字以物体名词结尾 → 强判道具（无视瞎填的性别与姓氏子串）；或中部含物件词且无任何人物线索
    const isProp = (STRONG_OBJECT.test(name) && !personDesc)
      || (PROP_RE.test(name) && !c.gender && !personDesc && !PERSON_HINT.test(name));
    if (isProp) {
      sb.props.push({ key: c.key, name, desc: desc || c.image_prompt || '', image_prompt: c.image_prompt || '' });
      propNames.add(name);
    } else keep.push(c);
  }
  sb.characters = keep;
}

export function normalizeStoryboard(sb) {
  applyLearnedLabels(sb);   // 先用人工校正记忆归位（Agent 进化），再跑启发式
  reclassifyProps(sb);
  const out = {
    title: String(sb.title || '未命名作品').slice(0, 50),
    logline: String(sb.logline || '').slice(0, 200),
    style: String(sb.style || '').slice(0, 100),
    unit: sb.unit === '幕' ? '幕' : '集',
    episodes: [], characters: [], scenes: [], props: [], shots: []
  };
  const remap = {};
  const epRemap = {};
  (Array.isArray(sb.episodes) ? sb.episodes : []).slice(0, 12).forEach((e, i) => {
    const key = `e${i + 1}`;
    epRemap[e.key || key] = key;
    out.episodes.push({ key, order: i + 1, title: String(e.title || `第 ${i + 1} ${out.unit}`).slice(0, 30), summary: String(e.summary || '').slice(0, 120) });
  });
  if (!out.episodes.length) out.episodes.push({ key: 'e1', order: 1, title: `第一${out.unit}`, summary: '' });
  (Array.isArray(sb.characters) ? sb.characters : []).slice(0, 14).forEach((c, i) => {
    const key = `c${i + 1}`;
    remap[c.key || key] = key;
    const desc = String(c.desc || '').slice(0, 200);
    const gender = c.gender === '男' || c.gender === '女' ? c.gender : guessGender(desc, String(c.name || ''));
    out.characters.push({ key, name: String(c.name || `角色${i + 1}`).slice(0, 20), role: String(c.role || '角色').slice(0, 10), gender, desc, image_prompt: String(c.image_prompt || c.name || '').slice(0, 400) });
  });
  (Array.isArray(sb.scenes) ? sb.scenes : []).slice(0, 22).forEach((s, i) => {
    const key = `s${i + 1}`;
    remap[s.key || key] = key;
    out.scenes.push({ key, name: String(s.name || `场景${i + 1}`).slice(0, 20), desc: String(s.desc || '').slice(0, 200), image_prompt: String(s.image_prompt || s.name || '').slice(0, 400) });
  });
  (Array.isArray(sb.props) ? sb.props : []).slice(0, 10).forEach((p, i) => {
    const key = `p${i + 1}`;
    remap[p.key || key] = key;
    out.props.push({ key, name: String(p.name || `道具${i + 1}`).slice(0, 20), desc: String(p.desc || '').slice(0, 200), image_prompt: String(p.image_prompt || p.name || '').slice(0, 400) });
  });
  if (!out.characters.length) out.characters.push({ key: 'c1', name: '主角', role: '主角', gender: '', desc: '', image_prompt: '电影感人物肖像' });
  if (!out.scenes.length) out.scenes.push({ key: 's1', name: '主场景', desc: '', image_prompt: '电影感场景空镜' });
  const epOrder = new Map(out.episodes.map((e) => [e.key, e.order]));
  const rawShots = (Array.isArray(sb.shots) ? sb.shots : []).slice(0, 200)
    .map((sh, idx) => ({ sh, idx, ep: epOrder.get(epRemap[sh.episode] || 'e1') || 1 }))
    .sort((a, b) => a.ep - b.ep || a.idx - b.idx);   // 按幕/集分组，段内保持原顺序
  rawShots.forEach(({ sh }, i) => {
    out.shots.push({
      key: `sh${i + 1}`, order: i + 1,
      episode: epRemap[sh.episode] || 'e1',
      scene: remap[sh.scene] || 's1',
      characters: (Array.isArray(sh.characters) ? sh.characters : []).map((k) => remap[k]).filter(Boolean),
      shot_type: String(sh.shot_type || '中景').slice(0, 8), camera: String(sh.camera || '固定机位').slice(0, 20),
      emotion: String(sh.emotion || '').slice(0, 6),
      action: String(sh.action || '').slice(0, 200), dialogue: String(sh.dialogue || '').slice(0, 120),
      duration: clamp(sh.duration || 5, 2, 12),
      image_prompt: String(sh.image_prompt || sh.action || '').slice(0, 400),
      video_prompt: String(sh.video_prompt || sh.action || '').slice(0, 400)
    });
  });
  if (!out.shots.length) throw bad('解析结果里没有分镜');
  out.bible = buildBible(out);
  buildLocks(out);
  out.bible = buildBible(out);
  alignStoryboard(out);
  return out;
}

const cleanDesc = (s) => String(s || '').replace(/\s+/g, '').replace(/^[，,。.；;、]+|[，,。.；;、]+$/g, '');
const ageTag = (d) => /老|年迈|苍老|花甲|白发|爷|奶/.test(d) ? '老年' : /少年|少女|小孩|儿童|孩子/.test(d) ? '少年' : /中年|大叔|大妈/.test(d) ? '中年' : '青年';
// 从描述里抽身高（"一米五/1.5米/150cm/身高158"），锁进档案防镜头间忽高忽低
const HEIGHT_RE = /((?:[一二三四五六七八九两]米[一二三四五六七八九半]?)|(?:\d(?:\.\d{1,2})?\s*米\d?)|(?:1[.．]\d{1,2}\s*[mM])|(?:\d{2,3}\s*(?:cm|CM|公分|厘米)))/;
/** 身高/体型锁定文案：显式身高 + 儿童头身比，全片逐字复用 */
function bodyLock(desc, age) {
  const m = desc.match(HEIGHT_RE);
  const parts = [];
  if (m) parts.push(`身高${m[1].replace(/\s+/g, '')}`);
  if (age === '少年') parts.push('儿童头身比例·身量矮小·童颜');
  else if (age === '老年') parts.push('年长体态');
  return parts.join('、');
}

/** 为每个角色/场景/道具建【完整锁定档案】——全片每处逐字复用同一段，保证细节一致 */
function buildLocks(sb) {
  const style = styleAnchor(sb);
  for (const c of sb.characters) {
    const d = cleanDesc(c.desc).slice(0, 110);
    const g = c.gender === '男' ? '男性' : c.gender === '女' ? '女性' : '';
    const age = ageTag(d);
    const body = bodyLock(d, age);
    // 角色锁定档案：性别+年龄+完整外貌/服装/身高体型/特征，固定不变
    c.lock = `${c.name}（${g}${age}/${c.role}：${d}${body ? '，' + body : ''}，五官·发型·服装·身高体型比例全程固定不变）`;
    // 角色三视图设定图（正/侧/背 全身并排）＝全片定海神针参考；含锁定档案 + 抗畸变（防脸鱼眼/比例失真）
    c.image_prompt = `${style} ｜ 角色三视图设定图（正面·四分之三侧面·背面 全身并排，纯白背景） ｜ ${c.lock} ｜ 三视角外观完全一致、面部五官比例真实、自然透视无畸变`;
  }
  for (const s of sb.scenes) {
    const d = cleanDesc(s.desc).slice(0, 90);
    s.lock = `${s.name}（${d || s.name}，环境陈设光线固定一致）`;
    s.image_prompt = `${style} ｜ 场景空镜 ｜ ${s.lock}`;
  }
  for (const p of sb.props) {
    const d = cleanDesc(p.desc).slice(0, 70);
    p.lock = `${p.name}（${d || p.name}，外形固定）`;
    p.image_prompt = `${style} ｜ 道具特写 ｜ ${p.lock}`;
  }
}

// 摄影机参数：景别 → 镜头/光圈/景深 + 抗畸变约束（描述越细，Seedream/Seedance 越不容易把画面拍失真：鱼眼、脸变形、身体拉伸）
const LENS_MAP = {
  '特写': { lens: '85mm 中长焦人像定焦镜头', dof: 'T1.8 大光圈、极浅景深、焦点锐利、背景奶油般虚化', fix: '面部五官比例真实、绝不鱼眼变形' },
  '近景': { lens: '50mm 标准定焦镜头', dof: 'T2.0 浅景深、背景柔和虚化', fix: '透视自然、零畸变、人体比例真实' },
  '中景': { lens: '35mm 定焦镜头', dof: 'T2.8 适中景深、主体清晰', fix: '人物比例真实、低畸变' },
  '全景': { lens: '24-28mm 广角定焦镜头', dof: 'T4 深景深、人物与环境同清晰', fix: '边缘畸变校正、人物不被拉伸变形' },
  '远景': { lens: '18-24mm 广角镜头', dof: 'T5.6 全景深', fix: '大气透视、地平线与建筑几何线条笔直不弯曲' },
};
const MOVE_RULES = [
  [/缓推|慢推|推镜|推进|前推/, '缓慢推进（dolly-in）'],
  [/快推/, '快速推进'],
  [/拉镜|拉远|后拉/, '拉镜（dolly-out）'],
  [/横移|侧移|移镜/, '横向跟踪移动（tracking shot）'],
  [/摇镜|左摇|右摇|摇/, '水平摇摄（pan）'],
  [/俯拍|俯|鸟瞰/, '俯拍，高角度'],
  [/仰拍|仰/, '仰拍，低角度'],
  [/升降|升镜|降镜|起重/, '升降臂（crane/jib）'],
  [/跟镜|跟拍|跟随/, '跟随拍摄（tracking follow）'],
  [/甩镜|甩/, '甩镜（whip pan）'],
  [/环绕|围绕|旋转/, '环绕弧线运动（orbit/arc）'],
  [/手持|抖动/, '手持轻微抖动，真实记录感'],
  [/斯坦尼康|稳定器|云台/, '斯坦尼康稳定跟随（steadicam）'],
  [/固定|静止|锁定/, '三脚架固定机位（locked-off）、画面稳定'],
];
// 机身按画风选择：写实/实拍 → 真实电影摄影机（堆传感器/动态范围术语提升真实感）；动漫/2D/3D → 虚拟电影机位，不堆胶片术语以免与画风冲突
function cameraBody(style) {
  return /写实|实拍|真人|纪实|超写实|电影质感|质感|photo|真实|写真/i.test(style || '')
    ? 'ARRI Alexa Mini LF 专业电影摄影机、全画幅传感器、14 档高动态范围、广色域、电影级肤色还原'
    : '电影级虚拟摄影机机位、专业构图、画面干净稳定';
}
/** 把景别 + 运镜 + 画风转成【细节化摄影机参数】，注入图与视频提示词，抑制画面失真/畸变 */
function shotCinema(shotType, camera, style = '') {
  const L = LENS_MAP[String(shotType || '').replace(/\s/g, '')] || LENS_MAP['中景'];
  let move = String(camera || '').trim();
  for (const [re, desc] of MOVE_RULES) { if (re.test(move)) { move = desc; break; } }
  if (!move) move = '三脚架固定机位';
  return `${cameraBody(style)}，${L.lens}，${L.dof}，${L.fix}，${move}`;
}

/** 故事总纲（总控提示词）：写进每一张参考图，全片防跑偏 */
function buildBible(sb) {
  const chars = sb.characters.map((c) => c.lock).join('；');
  return `【全片总控】影像风格：${styleAnchor(sb)}。【画风铁律】全片只用这一种画风，${STYLE_DRIFT_NEG}【角色档案锁定】${chars}。【铁律】各角色五官·发型·服装·身材比例全片严格一致，不同角色外貌明显区分不可撞脸，不得中途换人或改外观。`;
}

/** 慢思考自动对齐：把每个分镜重建为【确定性规范提示词】——同一角色/场景永远是同一段锁定文字 */
function alignStoryboard(sb) {
  const charByKey = new Map(sb.characters.map((c) => [c.key, c]));
  const sceneByKey = new Map(sb.scenes.map((s) => [s.key, s]));
  const propByKey = new Map(sb.props.map((p) => [p.key, p]));
  const style = styleAnchor(sb);
  for (const sh of sb.shots) {
    const chars = (sh.characters || []).map((k) => charByKey.get(k)).filter(Boolean);
    const sc = sceneByKey.get(sh.scene);
    const props = (sh.props || []).map((k) => propByKey.get(k)).filter(Boolean);
    const action = cleanDesc(sh.action).slice(0, 80) || sh.name;
    const cinema = shotCinema(sh.shot_type, sh.camera, style);   // 细节化摄影机参数（机身/镜头/光圈/景深/抗畸变/运镜）
    // 规范化首帧提示词：画风锚点 + 景别 + 摄影机参数 + 角色锁定档案 + 场景锁定 + 画面动作 + 情绪
    const parts = [style, sh.shot_type || '中景', `【摄影机】${cinema}`];
    if (chars.length) parts.push(`【角色】${chars.map((c) => c.lock).join('；')}`);
    if (sc) parts.push(`【场景】${sc.lock}`);
    if (props.length) parts.push(`【道具】${props.map((p) => p.name).join('、')}`);
    parts.push(`【画面】${action}`);
    if (sh.emotion) parts.push(`【情绪】${chars[0]?.name || '主角'}：${sh.emotion}`);
    sh.image_prompt = parts.join(' ｜ ').slice(0, 1000);
    // 视频提示词：动作 + 摄影机参数 + 该镜角色锁定档案（总控随片：把五官/发型/服装/身高体型逐字带进视频，防动画里变形/换人/身高突变）
    const vp = cleanDesc(sh.video_prompt).slice(0, 70) || action;
    const head = `${vp}｜【摄影机】${cinema}`;   // 动作+摄影机参数优先保留，锁定档案放尾部（截断只会少几个锁定细节）
    const lockLine = chars.length ? `｜【角色锁定】${chars.map((c) => c.lock).join('；')}` : '｜角色外观全程一致';
    sh.video_prompt = (head + lockLine).slice(0, 600);
  }
}

/** 大模型分类校正：判断被标为"角色"的条目里哪些其实是道具/场景，自动归位（细节决定一致性） */
async function refineEntitiesLLM(sb) {
  if (!llmEnabled() || !sb.characters?.length) return sb;
  try {
    const list = sb.characters.map((c) => `${c.name}：${cleanDesc(c.desc).slice(0, 36)}`).join('\n');
    // 进化：把用户历史校正作为已知样例喂给模型，越用越准
    const labels = getSetting(BRAIN_KEY, null)?.labels || {};
    const examples = Object.entries(labels).slice(0, 40).map(([n, t]) => `${n}→${t === 'prop' ? '道具' : t === 'scene' ? '场景' : '角色'}`).join('；');
    const r = await arkChat({
      feature: 'classify', json: true, temperature: 0, maxTokens: 800,
      system: '你是剧本实体分类器。下列条目当前都被标为"角色"，请判断哪些其实是【道具/物体】(非人、非拟人生物，如：芯片/计数器/钥匙/能源核心/水囊/武器等)，哪些其实是【场景/地点】。只输出 JSON：{"props":["误标的物体名"],"scenes":["误标的地点名"]}，没有则空数组。' +
        (examples ? `\n已知正确分类（用户校正过，务必遵循）：${examples}。` : ''),
      prompt: list
    });
    const j = jparse(String(r.text).replace(/```(json)?/gi, '').replace(/```/g, ''), {});
    const toProp = new Set((j.props || []).map(String));
    const toScene = new Set((j.scenes || []).map(String));
    if (!toProp.size && !toScene.size) return sb;
    const keep = [];
    const movedKeys = new Set();
    for (const c of sb.characters) {
      if (toProp.has(c.name)) { if (!sb.props.some((p) => p.name === c.name)) sb.props.push({ key: c.key, name: c.name, desc: c.desc, image_prompt: '' }); movedKeys.add(c.key); }
      else if (toScene.has(c.name)) { if (!sb.scenes.some((s) => s.name === c.name)) sb.scenes.push({ key: c.key, name: c.name, desc: c.desc, image_prompt: '' }); movedKeys.add(c.key); }
      else keep.push(c);
    }
    if (!movedKeys.size) return sb;
    sb.characters = keep;
    for (const sh of sb.shots) sh.characters = (sh.characters || []).filter((k) => !movedKeys.has(k));
    return normalizeStoryboard(sb);   // 重排 key + 重建锁定/总纲/对齐
  } catch (e) { console.warn('[parse] LLM 分类校正失败：', e.message); return sb; }
}

/** 合并多段解析结果：角色/场景/道具按名字去重，分镜顺序拼接、段落映射到 episode */
function mergeStoryboards(parts) {
  const merged = { title: '', logline: '', style: '', unit: parts[0]?.unit || '幕', episodes: [], characters: [], scenes: [], props: [], shots: [] };
  const charByName = new Map(), sceneByName = new Map(), propByName = new Map();
  parts.forEach((sb, pi) => {
    if (!merged.title && sb.title) merged.title = sb.title;
    if (!merged.logline && sb.logline) merged.logline = sb.logline;
    if (!merged.style && sb.style) merged.style = sb.style;
    const epKey = `e${pi + 1}`;
    merged.episodes.push({ key: epKey, order: pi + 1, title: sb.episodes?.[0]?.title || `第 ${pi + 1} ${merged.unit}`, summary: sb.episodes?.[0]?.summary || sb.logline || '' });
    const localRemap = {};
    for (const c of sb.characters) {
      if (!charByName.has(c.name)) { const k = `c${charByName.size + 1}`; charByName.set(c.name, { ...c, key: k }); localRemap[c.key] = k; }
      else localRemap[c.key] = charByName.get(c.name).key;
    }
    for (const s of sb.scenes) {
      if (!sceneByName.has(s.name)) { const k = `s${sceneByName.size + 1}`; sceneByName.set(s.name, { ...s, key: k }); localRemap[s.key] = k; }
      else localRemap[s.key] = sceneByName.get(s.name).key;
    }
    for (const p of sb.props) {
      if (!propByName.has(p.name)) { const k = `p${propByName.size + 1}`; propByName.set(p.name, { ...p, key: k }); localRemap[p.key] = k; }
      else localRemap[p.key] = propByName.get(p.name).key;
    }
    for (const sh of sb.shots) {
      merged.shots.push({
        ...sh, key: `sh${merged.shots.length + 1}`, order: merged.shots.length + 1, episode: epKey,
        scene: localRemap[sh.scene] || 's1',
        characters: (sh.characters || []).map((k) => localRemap[k]).filter(Boolean)
      });
    }
  });
  merged.characters = [...charByName.values()];
  merged.scenes = [...sceneByName.values()];
  merged.props = [...propByName.values()];
  return normalizeStoryboard(merged);
}

const parseJSON = (txt) => jparse(String(txt).replace(/```(json)?/gi, '').replace(/```/g, '').trim(), null);

export async function parseScript({ projectId }) {
  const project = getProject(projectId);
  if (!project.script?.trim()) throw bad('项目还没有剧本，先写剧本或用 AI 生成');
  const styleNote = project.style ? `\n（项目预设风格：${resolveStylePrompt(project.style)}，所有 image_prompt/video_prompt 必须体现该风格）` : '';
  let sb = null;
  let byLLM = false;
  let warn = '';

  if (llmEnabled()) {
    // 长剧本（电影）分幕分段送 LLM，避免一次性截断导致解析失败/丢内容
    const segments = splitScriptSegments(project.script, { maxChars: 9000 });
    try {
      if (segments.length === 1) {
        const r = await arkChat({
          feature: 'parse', system: PARSE_SYSTEM, json: true, temperature: 0.3, maxTokens: 8000,
          prompt: `剧本如下，请解析：\n${segments[0].body.slice(0, 14000)}${styleNote}`
        });
        const j = parseJSON(r.text);
        if (!j) throw new Error('LLM 返回的 JSON 无法解析（可能输出被截断）');
        sb = normalizeStoryboard(j);
      } else {
        // 多段：逐段解析后合并（最多 8 段，控制时延/成本）
        const cap = segments.slice(0, 8);
        const parts = [];
        let failed = 0;
        for (let i = 0; i < cap.length; i++) {
          try {
            const r = await arkChat({
              feature: 'parse', system: PARSE_SYSTEM, json: true, temperature: 0.3, maxTokens: 7000,
              prompt: `这是一部「${segments[0].unit === '幕' ? '电影/长片' : '短剧'}」的第 ${i + 1}/${cap.length} ${cap[i].unit}「${cap[i].title}」。请解析这一段：\n${cap[i].body.slice(0, 12000)}${styleNote}\n（unit 填「${cap[i].unit}」；episodes 只放本段一项）`
            });
            const j = parseJSON(r.text);
            if (!j?.shots?.length) throw new Error('本段无有效分镜');
            j.unit = cap[i].unit;
            if (!j.episodes?.length) j.episodes = [{ key: 'e1', title: cap[i].title, summary: j.logline || '' }];
            else j.episodes[0].title = j.episodes[0].title || cap[i].title;
            parts.push(normalizeStoryboard(j));
          } catch (e) { failed++; console.warn(`[parse] 第 ${i + 1} 段失败：`, e.message); }
        }
        if (!parts.length) throw new Error('所有段落解析失败');
        sb = mergeStoryboards(parts);
        if (failed) warn = `${cap.length} 段中有 ${failed} 段解析失败，已跳过（可重新解析重试）`;
      }
      byLLM = true;
    } catch (e) {
      console.warn('[pipeline] 方舟解析失败，落本地引擎：', e.message);
      warn = `方舟解析未完成（${e.message}），已用本地引擎兜底——请检查对话模型是否支持长输出，或重试`;
    }
  }
  if (!sb) sb = normalizeStoryboard(localParse(project.script, { style: resolveStylePrompt(project.style) }));

  // 大模型分类校正：把误判为角色的道具/场景归位（仅 LLM 模式）
  if (byLLM) sb = await refineEntitiesLLM(sb);
  // 画风锚定：项目选了风格就强制全片统一这一种画风（杜绝前后跳风）
  if (project.style) lockStyle(sb, project.style);

  // 同步画布（已有画布则整体重建结构，保留画布 id）
  const canvasId = ensureCanvas(project, sb);
  touchProject(project.id, {
    storyboard: JSON.stringify(sb), status: 'parsed', canvas_id: canvasId,
    ...((project.title === '未命名短剧' || project.title === '未命名作品') && sb.title ? { title: sb.title } : {}),
    ...(sb.style && !project.style ? { style: sb.style.slice(0, 300) } : {})
  });
  return { project: projectOut(q.get('SELECT * FROM projects WHERE id = ?', project.id)), storyboard: sb, byLLM, warn, canvasId };
}

// ---------- 续写一集 ----------
export async function addEpisode({ projectId, idea = '' }) {
  const project = getProject(projectId);
  if (!project.script?.trim()) throw bad('项目还没有剧本，先写剧本或用 AI 生成');
  const sb = jparse(project.storyboard, null);
  const marks = [...project.script.matchAll(/^第\s*\d+\s*集/gm)];
  const nextOrder = Math.max(marks.length, sb?.episodes?.length || 1) + 1;

  let chunk = '';
  if (llmEnabled()) {
    try {
      const cast = (sb?.characters || []).map((c) => `${c.name}（${c.role}）`).join('、');
      const r = await arkChat({
        feature: 'episode', system: SCRIPT_SYSTEM, temperature: 0.9, maxTokens: 2500,
        prompt: `以下是短剧《${project.title}》已有剧本的结尾部分：\n${project.script.slice(-4000)}\n\n` +
          `请续写「第 ${nextOrder} 集」（以"第 ${nextOrder} 集 ｜ 集标题"开头，3-5 场，结尾留强钩子）。` +
          `沿用已有人物${cast ? `：${cast}` : ''}，不要新建【人物】块。${idea ? `本集创意：${idea}` : '剧情自然升级。'}`
      });
      chunk = r.text.trim();
      if (!/^第\s*\d+\s*集/m.test(chunk)) chunk = `第 ${nextOrder} 集 ｜ 风云再起\n` + chunk;
    } catch (e) {
      console.warn('[pipeline] 方舟续集失败，落本地引擎：', e.message);
    }
  }
  if (!chunk) chunk = localNextEpisode({ storyboard: sb, order: nextOrder, idea, genre: project.genre });

  touchProject(project.id, { script: (project.script.trimEnd() + '\n\n' + chunk).slice(0, 60_000) });
  const parsed = await parseScript({ projectId });
  return { episodeOrder: nextOrder, ...parsed };
}

// ---------- 画布 ----------
// 分镜多列网格布局参数（前端「整理」按钮与此保持一致）
export const LAYOUT = { left: 60, leftW: 270, midGap: 80, midW: 240, rightGap: 90, shotW: 310, shotPerCol: 5, leftPerCol: 6, midPerCol: 4 };

export function buildGraph(sb, ratio = '16:9') {
  const nodes = [];
  const edges = [];
  const keyToNode = {};
  const L = LAYOUT;

  // 左区：场景+道具；中区：角色；右区：分镜——各自按列折行，区与区动态错开
  const leftItems = [...sb.scenes.map((s) => ['scene', s]), ...sb.props.map((p) => ['prop', p])];
  leftItems.forEach(([type, it], i) => {
    const id = uid('n');
    keyToNode[it.key] = id;
    nodes.push({
      id, type, x: L.left + Math.floor(i / L.leftPerCol) * L.leftW, y: 60 + (i % L.leftPerCol) * 230,
      data: { key: it.key, name: it.name, desc: it.desc, prompt: it.image_prompt, image: '' }
    });
  });
  const midX = L.left + Math.max(1, Math.ceil(leftItems.length / L.leftPerCol)) * L.leftW + L.midGap;
  sb.characters.forEach((c, i) => {
    const id = uid('n');
    keyToNode[c.key] = id;
    nodes.push({
      id, type: 'character', x: midX + Math.floor(i / L.midPerCol) * L.midW, y: 60 + (i % L.midPerCol) * 300,
      data: { key: c.key, name: c.name, role: c.role, desc: c.desc, prompt: c.image_prompt, image: '' }
    });
  });
  const rightX = midX + Math.max(1, Math.ceil(sb.characters.length / L.midPerCol)) * L.midW + L.rightGap;
  sb.shots.forEach((sh, i) => {
    const id = uid('n');
    keyToNode[sh.key] = id;
    nodes.push({
      id, type: 'shot', x: rightX + Math.floor(i / L.shotPerCol) * L.shotW, y: 60 + (i % L.shotPerCol) * 350,
      data: {
        key: sh.key, order: sh.order, name: `镜头 ${sh.order}`, scene: sh.scene,
        episode: sh.episode || 'e1',
        ep: (sb.episodes?.length || 1) > 1 ? Number(String(sh.episode || 'e1').slice(1)) || 1 : 0,
        shot_type: sh.shot_type, camera: sh.camera, emotion: sh.emotion || '', action: sh.action, dialogue: sh.dialogue,
        duration: sh.duration, image_prompt: sh.image_prompt, video_prompt: sh.video_prompt,
        image: '', video: '', task_id: '', task_status: ''
      }
    });
    const link = (fromKey) => {
      if (keyToNode[fromKey]) edges.push({ id: uid('e'), from: keyToNode[fromKey], to: id });
    };
    link(sh.scene);
    sh.characters.forEach(link);
    sb.props.forEach((p) => { if (sh.action.includes(p.name) || sh.image_prompt.includes(p.name)) link(p.key); });
  });
  return { nodes, edges };
}

export function ensureCanvas(project, sb) {
  const { nodes, edges } = buildGraph(sb, project.ratio);
  const existing = project.canvas_id ? q.get('SELECT * FROM canvases WHERE id = ?', project.canvas_id) : null;
  if (existing) {
    // 保留旧节点上已生成的媒体（按 storyboard key 对齐）
    const oldNodes = jparse(existing.nodes, []);
    const mediaByKey = new Map(oldNodes.filter((n) => n.data?.key).map((n) => [n.type + ':' + n.data.key, n.data]));
    nodes.forEach((n) => {
      const old = mediaByKey.get(n.type + ':' + n.data.key);
      if (old) Object.assign(n.data, { image: old.image || '', video: old.video || '', task_id: old.task_id || '', task_status: old.task_status || '' });
    });
    q.run('UPDATE canvases SET nodes = ?, edges = ?, name = ?, ratio = ?, updated_at = ? WHERE id = ?',
      JSON.stringify(nodes), JSON.stringify(edges), sb.title || existing.name, project.ratio, now(), existing.id);
    return existing.id;
  }
  const id = uid('cv');
  q.run('INSERT INTO canvases (id, project_id, name, ratio, nodes, edges, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
    id, project.id, sb.title || project.title, project.ratio, JSON.stringify(nodes), JSON.stringify(edges), now(), now());
  return id;
}

export function getCanvas(id, { required = true } = {}) {
  const c = q.get('SELECT * FROM canvases WHERE id = ?', id);
  if (!c && required) throw notFound('画布不存在');
  return c ? { ...c, nodes: jparse(c.nodes, []), edges: jparse(c.edges, []), doodles: jparse(c.doodles, []), viewport: jparse(c.viewport, null) } : null;
}

export function patchCanvasNode(canvasId, nodeId, patch) {
  const c = getCanvas(canvasId);
  const node = c.nodes.find((n) => n.id === nodeId || n.data?.key === nodeId);
  if (!node) throw notFound('节点不存在');
  const { x, y, ...dataPatch } = patch || {};
  if (x !== undefined) node.x = Number(x);
  if (y !== undefined) node.y = Number(y);
  Object.assign(node.data, dataPatch);
  q.run('UPDATE canvases SET nodes = ?, updated_at = ? WHERE id = ?', JSON.stringify(c.nodes), now(), canvasId);
  return node;
}

// ---------- 资产 ----------
export function addAsset({ tab = 'material', kind = 'image', name, url, poster = '', prompt = '', source = 'local', projectId = '' }) {
  const id = uid('a');
  q.run('INSERT INTO assets (id, tab, kind, name, url, poster, prompt, source, project_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
    id, tab, kind, String(name || '未命名').slice(0, 50), url, poster, String(prompt).slice(0, 500), source, projectId, now());
  return q.get('SELECT * FROM assets WHERE id = ?', id);
}

// ---------- 图像生成（同步） ----------
export async function generateImage({ prompt, name = '', kind = 'scene', ratio = '', projectId = '', nodeId = '', refImages = [], tab = '', emotion = '', model = '', skipQC = false }) {
  if (!prompt?.trim()) throw bad('缺少图片提示词 prompt');
  const project = projectId ? getProject(projectId, { required: false }) : null;
  prompt = applyStyle(prompt.trim(), project?.style);
  ratio = ratio || project?.ratio || '16:9';

  // 画面一致性：自动选参考图（分镜首帧）——角色（含情绪表情集）优先→场景→道具→上一镜尾帧
  // 文本锁定由解析时的规范化 image_prompt 承担（每处逐字一致），此处不再临时截断拼接
  let refs = (refImages || []).filter(Boolean);
  let shotEmotion = '';
  let shotType = '';
  let chainRef = false;
  if (kind === 'frame' && nodeId && project?.canvas_id) {
    try {
      const c = getCanvas(project.canvas_id, { required: false });
      if (c) {
        const incoming = c.edges.filter((e) => e.to === nodeId).map((e) => c.nodes.find((n) => n.id === e.from)).filter(Boolean);
        const chars = incoming.filter((n) => n.type === 'character');
        const scenes = incoming.filter((n) => n.type === 'scene');
        const props = incoming.filter((n) => n.type === 'prop');
        const shotNode = c.nodes.find((n) => n.id === nodeId);
        shotEmotion = String(shotNode?.data.emotion || '').trim();
        shotType = String(shotNode?.data.shot_type || '').trim();
        if (!refs.length) {
          const okUrl = (u) => u && !/\.svg$/i.test(u);
          const charRef = (n) => {
            if (shotEmotion && Array.isArray(n.data.variants)) {
              const v = n.data.variants.find((x) => x.emotion === shotEmotion && okUrl(x.url));
              if (v) return v.url;
            }
            return okUrl(n.data.image) ? n.data.image : '';
          };
          refs = [...chars.map(charRef), ...scenes.map((n) => (okUrl(n.data.image) ? n.data.image : '')), ...props.map((n) => (okUrl(n.data.image) ? n.data.image : ''))].filter(Boolean).slice(0, 4);
          if (shotNode && refs.length < 3) {
            const prev = c.nodes.find((n) => n.type === 'shot' && (n.data.episode || 'e1') === (shotNode.data.episode || 'e1') && n.data.scene === shotNode.data.scene && n.data.order === shotNode.data.order - 1);
            if (prev && okUrl(prev.data.image)) { refs.push(prev.data.image); chainRef = true; }
          }
        }
      }
    } catch { /* 画布可能已删除 */ }
  }
  // 情绪（含手动改后的）补进提示词
  if (shotEmotion && !prompt.includes(`：${shotEmotion}`)) prompt += `，情绪：${shotEmotion}`;
  // 总控提示词（角色档案+风格+铁律）注入【每一张】参考图（角色/场景/道具/首帧），全片防跑偏
  if (project?.storyboard) {
    const bible = jparse(project.storyboard, {})?.bible;
    if (bible && !prompt.includes('【全片总控】')) prompt += `\n${bible}`;
  }
  if (chainRef) prompt += '，与上一镜画面无缝衔接、同一角色同一造型';
  // 追加构图/解剖护栏（修复人物残缺、上下身分离等问题）
  prompt += framingGuide(kind, shotType);
  const seed = project?.seed || 0;
  // 角色三视图需横向排布 正/侧/背 三个视角 → 角色用宽幅；场景/首帧/道具沿用项目画幅
  if (kind === 'character') ratio = '16:9';
  // 角色三视图 / 全场景图是全片"定海神针"参考，交给最强图像模型（model_image_pro）；分镜首帧/道具用默认模型。
  // 显式传入 model（创作框选择）> 顶配/默认。再按模型 ID 路由到 火山 Seedream 或 OpenAI GPT Image（各用各的 Key）。
  const proKind = (kind === 'character' || kind === 'scene');
  const chosenModel = model || (proKind ? cfg().modelImagePro : cfg().modelImage);
  const ip = pickImageProvider(chosenModel, { arkEnabled: arkEnabled(), arkModel: chosenModel });
  const imageModel = ip.enabled ? ip.model : 'local';
  const provLabel = ip.provider === 'openai' ? 'OpenAI GPT Image' : ip.provider === 'alibaba' ? '通义万相' : '方舟图像';

  const taskId = uid('t');
  q.run('INSERT INTO tasks (id, kind, status, provider, model, prompt, params, project_id, node_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
    taskId, 'image', 'running', ip.enabled ? ip.provider : 'local', imageModel, prompt.slice(0, 1500),
    JSON.stringify({ kind, ratio, name, ref_images: refs.length, seed, emotion: shotEmotion, chain_ref: chainRef, model: imageModel, provider: ip.enabled ? ip.provider : 'local', pro: proKind }), projectId, nodeId, now(), now());

  let url = '';
  let provider = 'local';
  try {
    if (ip.enabled) {
      const r = ip.provider === 'openai'
        ? await openaiImage({ prompt, ratio, refImages: refs, model: ip.model, feature: `image:${kind}` })
        : ip.provider === 'alibaba'
          ? await dashscopeImage({ prompt, ratio, model: ip.model, feature: `image:${kind}` })
          : await arkImage({ prompt, ratio, refImages: refs, seed, model: ip.model, feature: `image:${kind}` });
      url = r.url;
      provider = ip.provider;
    } else {
      url = saveSVG(localImageSVG({ prompt, name, kind, ratio, order: 0, emotion }));
    }
  } catch (e) {
    console.warn(`[pipeline] ${provLabel}失败：`, e.message);
    if (ip.enabled && !localFallbackOn()) {
      // 诚实模式：标记失败并抛出真实原因，而非伪装成功给占位图
      q.run('UPDATE tasks SET status = ?, error = ?, updated_at = ? WHERE id = ?', 'failed', `${provLabel}失败：${e.message}`, now(), taskId);
      throw bad(`${provLabel}生成失败：${e.message}。请到设置页确认该模型对应的 API Key/模型 ID 已正确配置；如需占位预览可在设置页开启「本地兜底」`);
    }
    url = saveSVG(localImageSVG({ prompt, name, kind, ratio, emotion }));
    q.run('UPDATE tasks SET error = ? WHERE id = ?', `${ip.provider}: ${e.message}（已用本地兜底）`, taskId);
  }

  const asset = addAsset({
    tab: tab || (kind === 'character' ? 'character' : 'material'), kind: 'image',
    name: name || prompt.slice(0, 20), url, prompt, source: provider, projectId
  });
  q.run('UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?',
    'succeeded', JSON.stringify({ url, asset_id: asset.id }), now(), taskId);

  if (nodeId && project?.canvas_id) {
    try { patchCanvasNode(project.canvas_id, nodeId, { image: url }); } catch { /* 节点可能已删除 */ }
    if (!project.cover) touchProject(project.id, { cover: url });
  }

  // 自动 AIQC：每生成一张【分镜首帧/角色】图就立刻质检（含自动修正），无需等工作流。
  // skipQC 防止修正时递归；本地 SVG 占位不质检（无接入方舟时）。
  if (!skipQC && (kind === 'frame' || kind === 'character') && nodeId && project?.canvas_id && !/\.svg$/i.test(url)) {
    try {
      const { qcEnabled, qcNode } = await import('./qc.js');
      if (qcEnabled()) await qcNode(projectId, nodeId, { stage: 'image' });
    } catch (e) { console.warn('[qc] 自动质检跳过：', e.message); }
  }
  return { taskId, url, provider, asset };
}

// ---------- 角色表情集（同一角色多情绪定妆照，基础形象作参考保持一致性） ----------
export const EMOTIONS = ['冷酷', '愤怒', '狂喜', '悲伤', '微笑', '惊恐'];

export async function generateExpressions({ projectId, nodeId, emotions = [] }) {
  const project = getProject(projectId);
  if (!project.canvas_id) throw bad('项目还没有画布，先解析剧本');
  const c = getCanvas(project.canvas_id);
  const node = c.nodes.find((n) => n.id === nodeId || n.data?.key === nodeId);
  if (!node) throw bad('节点不存在');
  if (node.type !== 'character') throw bad('表情集只能为角色节点生成');
  const list = (emotions.length ? emotions : EMOTIONS).slice(0, 8);
  // 已有非占位主形象时作为参考图（方舟模式保证同一角色五官一致）
  const refs = node.data.image && !/\.svg$/i.test(node.data.image) ? [node.data.image] : [];
  const variants = [...(node.data.variants || [])];
  const out = [];
  for (const emo of list) {
    const r = await generateImage({
      prompt: `${node.data.prompt || node.data.desc || node.data.name}，表情：${emo}，与参考图为同一个人（五官、发型、脸型、肤色、服装完全一致），仅表情变化，单人正脸表情定妆照，五官清晰对称、表情自然真实、不变形不诡异、避免恐怖谷，纯色背景`,
      name: `${node.data.name}·${emo}`, kind: 'character', projectId,
      refImages: refs, tab: 'character', emotion: emo
    });
    const v = { emotion: emo, url: r.url, asset_id: r.asset.id };
    const i = variants.findIndex((x) => x.emotion === emo);
    if (i >= 0) variants[i] = v; else variants.push(v);
    out.push(v);
  }
  patchCanvasNode(project.canvas_id, node.id, { variants });
  if (!node.data.image && out.length) patchCanvasNode(project.canvas_id, node.id, { image: out[0].url });
  return { node_id: node.id, name: node.data.name, variants: out, total: variants.length };
}

// ---------- 画面一致性体检：扫描可能导致画面漂移的问题，给出评分与修复建议 ----------
export function checkConsistency(projectId) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb) throw bad('项目还没有分镜，先解析剧本');
  const c = project.canvas_id ? getCanvas(project.canvas_id, { required: false }) : null;
  if (!c) throw bad('项目还没有画布');
  const byKey = new Map(c.nodes.filter((n) => n.data?.key).map((n) => [n.data.key, n]));

  const issues = [];
  let score = 100;
  const push = (level, text, fix = '') => {
    issues.push({ level, text, fix });
    score -= level === 'err' ? 10 : 4;
  };

  if (!project.style) push('warn', '未设置画面风格：不同镜头容易风格漂移', '顶栏「风格」选择预设或自定义，会自动注入所有生成');

  let charsReady = 0;
  for (const ch of sb.characters) {
    const img = byKey.get(ch.key)?.data.image || '';
    if (!img) push('err', `角色「${ch.name}」没有定妆照：相关分镜首帧缺少人物参考图`, '生成角色形象（或点下方一键补齐）');
    else if (/\.svg$/i.test(img)) push('warn', `角色「${ch.name}」是本地占位图：接入方舟后重新生成才能作为一致性参考`, '');
    else charsReady++;
  }
  let scenesReady = 0;
  for (const sc of sb.scenes) {
    const img = byKey.get(sc.key)?.data.image || '';
    if (!img) push('err', `场景「${sc.name}」没有场景图：该场景下的分镜画面容易跑偏`, '生成场景图（或一键补齐）');
    else if (!/\.svg$/i.test(img)) scenesReady++;
  }

  // 分镜级问题按类别聚合，避免刷屏
  const noCharLink = [];
  const noSceneLink = [];
  const promptMissName = [];
  for (const sh of sb.shots) {
    const n = byKey.get(sh.key);
    if (!n) continue;
    const incoming = c.edges.filter((e) => e.to === n.id).map((e) => c.nodes.find((x) => x.id === e.from)).filter(Boolean);
    if (sh.characters?.length && !incoming.some((x) => x.type === 'character')) noCharLink.push(sh.order);
    if (!incoming.some((x) => x.type === 'scene')) noSceneLink.push(sh.order);
    const names = (sh.characters || []).map((k) => sb.characters.find((cc) => cc.key === k)?.name).filter(Boolean);
    if (names.length && !names.some((nm) => (sh.image_prompt || '').includes(nm))) promptMissName.push(sh.order);
  }
  const fmtOrders = (a) => a.slice(0, 8).join('、') + (a.length > 8 ? ` 等 ${a.length} 个` : '');
  if (noCharLink.length) push('err', `镜头 ${fmtOrders(noCharLink)} 没有连接角色节点：首帧不会自动带人物参考`, '画布上从角色节点拖线到分镜');
  if (noSceneLink.length) push('warn', `镜头 ${fmtOrders(noSceneLink)} 没有连接场景节点`, '画布上从场景节点拖线到分镜');
  if (promptMissName.length) push('warn', `镜头 ${fmtOrders(promptMissName)} 的首帧提示词没有提到出场角色名`, '已自动注入锁定词兜底；建议在提示词中写明人物');

  const framed = sb.shots.filter((s) => byKey.get(s.key)?.data.image).length;
  return {
    score: Math.max(0, score),
    seed: project.seed || 0,
    stats: {
      characters_ready: `${charsReady}/${sb.characters.length}`,
      scenes_ready: `${scenesReady}/${sb.scenes.length}`,
      shots_framed: `${framed}/${sb.shots.length}`,
      style: project.style || '（未设置）'
    },
    issues: issues.slice(0, 40)
  };
}

// ---------- 角色预选标注：解析后让用户校验"谁是角色/场景/道具"，校正即训练 Agent，全对则夸赞奖励 ----------
/** 列出当前实体分类供用户检查（带画布缩略图与 Agent 进化状态） */
export function listEntities(projectId) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb) throw bad('项目还没有分镜，先解析剧本');
  const c = project.canvas_id ? getCanvas(project.canvas_id, { required: false }) : null;
  const byKey = new Map((c?.nodes || []).filter((n) => n.data?.key).map((n) => [n.data.key, n]));
  const real = (u) => (u && !/\.svg$/i.test(u) ? u : '');
  const pick = (arr, type) => (arr || []).map((e) => ({
    key: e.key, name: e.name, type, role: e.role || '', gender: e.gender || '',
    desc: cleanDesc(e.desc).slice(0, 60), image: real(byKey.get(e.key)?.data.image),
    learned: learnedTypeOf(e.name) === type   // 用户曾确认过该归类
  }));
  return {
    project_id: project.id,
    style: project.style || sb.style || '',
    entities: [...pick(sb.characters, 'character'), ...pick(sb.scenes, 'scene'), ...pick(sb.props, 'prop')],
    counts: { character: sb.characters.length, scene: sb.scenes.length, prop: sb.props.length },
    brain: getAgentBrain()
  };
}

/** 应用用户校正：moves=[{name,to}]；confirm=true 表示分类全对夸赞。两者都会让 Agent 进化。 */
export function annotateEntities({ projectId, moves = [], confirm = false }) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb) throw bad('项目还没有分镜，先解析剧本');

  const applied = [];
  const learnLabels = {};
  for (const m of (moves || [])) {
    if (!m?.name || !ENTITY_TYPES.has(m.to)) continue;
    learnLabels[m.name] = m.to;                 // 无论是否真的移动，都记住用户的判定
    const r = moveEntity(sb, m.name, m.to);
    if (r) applied.push(r);
  }

  let brain;
  if (applied.length || Object.keys(learnLabels).length) {
    // 训练：写入学习记忆 + 计入校正次数（断掉连击），重建一致性结构
    saveBrain({ labels: learnLabels, corrections: applied.length || 1, xp: 6 * (applied.length || 1), resetStreak: true });
    normalizeStoryboard(sb);
    if (project.style) lockStyle(sb, project.style);
    const canvasId = ensureCanvas(project, sb);
    touchProject(project.id, { storyboard: JSON.stringify(sb), canvas_id: canvasId });
    brain = getAgentBrain();
  } else brain = getAgentBrain();

  if (confirm) brain = praiseAgent();   // 夸赞奖励：涨经验、连击+1

  return {
    applied, praised: !!confirm, brain,
    project: projectOut(q.get('SELECT * FROM projects WHERE id = ?', project.id)),
    storyboard: jparse(q.get('SELECT storyboard FROM projects WHERE id = ?', project.id).storyboard, sb)
  };
}

/** 解析后改画风：重锚定整部作品（重建锁定/总纲/对齐 + 刷新画布节点提示词），保住已生成的媒体 */
export function restyleProject(projectId, styleName) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb) return null;
  lockStyle(sb, styleName);
  const canvasId = ensureCanvas(project, sb);
  touchProject(project.id, { storyboard: JSON.stringify(sb), canvas_id: canvasId });
  return sb;
}

// ---------- 角色记忆 character_profile.json：把锁定档案 + 已生成的定妆照/表情集导出为可查可下载的单一事实源 ----------
// 这就是「禁止忽略 character_profile.json 里的角色记忆」中所指的那份记忆：
// 解析时确定下来的逐字锁定档案，加上画布上真实生成的参考图 URL，全片生成都以此为准。
export function buildCharacterProfile(projectId) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb) throw bad('项目还没有分镜，先解析剧本');
  const c = project.canvas_id ? getCanvas(project.canvas_id, { required: false }) : null;
  const byKey = new Map((c?.nodes || []).filter((n) => n.data?.key).map((n) => [n.data.key, n]));
  const real = (u) => (u && !/\.svg$/i.test(u) ? u : '');   // 只认真实生成图（占位 SVG 不算定妆）

  const characters = (sb.characters || []).map((ch) => {
    const n = byKey.get(ch.key);
    const portrait = real(n?.data.image);
    const expressions = (n?.data.variants || [])
      .filter((v) => real(v.url))
      .map((v) => ({ emotion: v.emotion, image: v.url }));
    return {
      key: ch.key, name: ch.name, role: ch.role || '角色',
      gender: ch.gender || '未定', age: ageTag(cleanDesc(ch.desc)),
      appearance: cleanDesc(ch.desc),
      lock: ch.lock || '',                       // 全片每处逐字复用的锁定档案
      portrait,                                  // 主定妆照（首帧参考基准），空＝未生成
      expressions,                               // 各情绪表情集（同一张脸的变体）
      ready: !!portrait                          // 是否已锁定形象
    };
  });
  const scenes = (sb.scenes || []).map((s) => ({
    key: s.key, name: s.name, desc: cleanDesc(s.desc), lock: s.lock || '', image: real(byKey.get(s.key)?.data.image), ready: !!real(byKey.get(s.key)?.data.image)
  }));
  const props = (sb.props || []).map((p) => ({
    key: p.key, name: p.name, desc: cleanDesc(p.desc), lock: p.lock || '', image: real(byKey.get(p.key)?.data.image), ready: !!real(byKey.get(p.key)?.data.image)
  }));

  return {
    schema: 'lingjing.character_profile/1',
    project: { id: project.id, title: project.title, style: project.style || '', ratio: project.ratio || '16:9', seed: project.seed || 0 },
    master_control: sb.bible || buildBible(sb),   // 总控提示词：写进每一张参考图
    forbidden_rules: FORBIDDEN_RULES,             // 负面提示词（禁止项），注入每张图/每段视频
    video_forbidden: VIDEO_NEG,
    characters, scenes, props,
    locked_at: now(),
    note: '全片生成（首帧/视频）以本档案为唯一形象事实源：同名角色逐字复用 lock 文案 + 同一张 portrait 作参考图，禁止中途改外观或换人。'
  };
}

// ---------- 配音：带台词的分镜逐镜合成语音（火山 TTS），写回节点 audio ----------
export async function generateDubbing({ projectId, episode = '', nodeId = '' }) {
  const { synthesize } = await import('./tts.js');
  const project = getProject(projectId);
  if (!project.canvas_id) throw bad('项目还没有画布，先解析剧本');
  const c = getCanvas(project.canvas_id);
  let shots = c.nodes.filter((n) => n.type === 'shot' && n.data.dialogue?.trim());
  if (nodeId) shots = shots.filter((n) => n.id === nodeId || n.data.key === nodeId);
  else if (episode) shots = shots.filter((n) => (n.data.episode || 'e1') === episode);
  if (!shots.length) throw bad(nodeId ? '该分镜没有台词' : '没有带台词的分镜');

  const done = [];
  for (const n of shots.slice(0, 30)) {
    const url = await synthesize(n.data.dialogue);
    patchCanvasNode(project.canvas_id, n.id, { audio: url });
    addAsset({ tab: 'material', kind: 'audio', name: `配音·镜头${n.data.order}`, url, prompt: n.data.dialogue, source: 'volc-tts', projectId });
    done.push({ node_id: n.id, order: n.data.order, url });
  }
  return { dubbed: done.length, items: done };
}

// ---------- 视频生成（异步任务） ----------
const LOCAL_VIDEO_MS = () => ((process.env.LINGJING_FAST_LOCAL || process.env.QINGLUAN_FAST_LOCAL) ? 50 : 4000);

export async function createVideoTask({ prompt, imageUrl = '', lastImageUrl = '', duration = 5, ratio = '', projectId = '', nodeId = '', name = '', order = 0, model = '', resolution = '' }) {
  if (!prompt?.trim()) throw bad('缺少视频提示词 prompt');
  const project = projectId ? getProject(projectId, { required: false }) : null;
  prompt = applyStyle(prompt.trim(), project?.style);
  // 注入视频硬性禁止项（穿模/下沉/换人/改外观）
  if (!prompt.includes('【视频禁止】')) prompt += `。${VIDEO_NEG}`;
  ratio = ratio || project?.ratio || '16:9';
  duration = clamp(duration, 2, 12);
  const taskId = uid('t');
  // 按模型 ID 路由：veo* → Google Veo 3，其余 → 火山 Seedance（各用各的 API Key）
  const vp = pickVideoProvider(model, { arkEnabled: arkEnabled(), arkModel: model || cfg().modelVideo });
  const provLabel = vp.provider === 'google' ? 'Veo' : vp.provider === 'alibaba' ? '通义万相' : '方舟视频';
  const params = { ratio, duration, imageUrl, lastImageUrl: lastImageUrl || '', name, order, model: vp.model || '', provider: vp.enabled ? vp.provider : 'local', resolution: resolution || '' };

  let provider = 'local';
  let remoteId = '';
  model = vp.model;
  if (vp.enabled) {
    try {
      const r = vp.provider === 'google'
        ? await googleVeoCreate({ prompt, imageUrl, ratio, model: vp.model })
        : vp.provider === 'alibaba'
          ? await dashscopeVideoCreate({ prompt, imageUrl, ratio, model: vp.model })
          : await arkVideoCreate({ prompt, imageUrl, lastImageUrl, ratio, duration, model: vp.model, resolution });
      provider = vp.provider;
      remoteId = r.remoteId;
      model = r.model;
    } catch (e) {
      console.warn(`[pipeline] ${provLabel}任务创建失败：`, e.message);
      // 已接入却失败 → 默认不静默落本地，而是把任务标记失败并暴露真实原因
      // （让用户能看到「模型未开通 / ID 错误 / 无额度」等，而不是误以为生成了真视频）
      if (!localFallbackOn()) {
        q.run(`INSERT INTO tasks (id, kind, status, provider, model, prompt, params, project_id, node_id, error, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
          taskId, 'video', 'failed', vp.provider, model, prompt.slice(0, 1500), JSON.stringify(params), projectId, nodeId, `${provLabel}失败：${e.message}`, now(), now());
        if (nodeId && project?.canvas_id) { try { patchCanvasNode(project.canvas_id, nodeId, { task_id: taskId, task_status: 'failed' }); } catch { /* noop */ } }
        throw bad(`${provLabel}生成失败：${e.message}。请到设置页确认该模型对应的 API Key/模型 ID 已正确配置；如需占位预览可在设置页开启「本地兜底」`);
      }
      params.localError = `${vp.provider}: ${e.message}（已用本地兜底）`;
    }
  }
  q.run(`INSERT INTO tasks (id, kind, status, provider, model, remote_id, prompt, params, project_id, node_id, created_at, updated_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
    taskId, 'video', 'running', provider, model, remoteId, prompt.slice(0, 1500), JSON.stringify(params), projectId, nodeId, now(), now());

  if (nodeId && project?.canvas_id) {
    try { patchCanvasNode(project.canvas_id, nodeId, { task_id: taskId, task_status: 'running' }); } catch { /* noop */ }
  }
  return { taskId, provider, status: 'running' };
}

export async function pollTask(taskId) {
  const t = q.get('SELECT * FROM tasks WHERE id = ?', taskId);
  if (!t) throw notFound('任务不存在');
  if (t.status === 'succeeded' || t.status === 'failed') {
    return { ...t, params: jparse(t.params, {}), result: jparse(t.result, {}) };
  }
  const params = jparse(t.params, {});

  const finish = (status, result = {}, error = '') => {
    q.run('UPDATE tasks SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?',
      status, JSON.stringify(result), error, now(), taskId);
    if (t.node_id && t.project_id) {
      const project = getProject(t.project_id, { required: false });
      if (project?.canvas_id) {
        try {
          patchCanvasNode(project.canvas_id, t.node_id,
            status === 'succeeded' ? { video: result.url, task_status: 'succeeded' } : { task_status: 'failed' });
        } catch { /* 节点可能已删除 */ }
      }
    }
    if (status === 'succeeded' && t.kind === 'video') {
      addAsset({ tab: 'material', kind: 'video', name: params.name || t.prompt.slice(0, 20), url: result.url, poster: params.imageUrl || '', prompt: t.prompt, source: t.provider, projectId: t.project_id });
    }
    return { ...q.get('SELECT * FROM tasks WHERE id = ?', taskId), params, result };
  };

  // 兜底超时：任务跑太久（默认 18 分钟）直接判失败，避免前端无限轮询、工作流"停不下来"
  const VIDEO_TIMEOUT_MS = 18 * 60_000;
  if (t.kind === 'video' && now() - t.created_at > VIDEO_TIMEOUT_MS) {
    return finish('failed', {}, '生成超时（超过 18 分钟未完成，已自动结束）');
  }

  if ((t.provider === 'ark' || t.provider === 'google' || t.provider === 'alibaba') && t.remote_id) {
    try {
      const r = t.provider === 'google'
        ? await googleVeoGet(t.remote_id, { duration: params.duration || 8 })
        : t.provider === 'alibaba'
          ? await dashscopeTaskGet(t.remote_id, { kind: 'video', duration: params.duration || 5 })
          : await arkVideoGet(t.remote_id, { duration: params.duration || 5 });
      if (r.status === 'succeeded') return finish('succeeded', { url: r.url });
      if (r.status === 'failed') return finish('failed', {}, r.error || '生成失败');
      return { ...t, params, result: {}, status: r.status };
    } catch (e) {
      // 查询接口连续报错也不再卡死：记录但保持 running，由超时兜底
      console.warn(`[pollTask] ${t.provider === 'google' ? 'Veo' : t.provider === 'alibaba' ? '通义万相' : '方舟'}查询失败：`, e.message);
      return { ...t, params, result: {}, status: 'running', error: e.message };
    }
  }

  // 本地模拟：到时间后产出 SMIL 动画 SVG
  if (now() - t.created_at >= LOCAL_VIDEO_MS()) {
    const url = saveSVG(localVideoSVG({ prompt: t.prompt, name: params.name, ratio: params.ratio, duration: params.duration, order: params.order }));
    return finish('succeeded', { url });
  }
  return { ...t, params, result: {}, status: 'running' };
}
