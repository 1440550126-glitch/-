// 灵境AI · 创作流水线：剧本 → 分镜 → 画布 → 图像 → 视频
// 配置了火山方舟 Key 走真实模型；否则自动落到本地规则引擎（结果带 provider 标识）
import { q, getSetting } from './db.js';
import { uid, now, jparse, clamp } from './util.js';
import { arkEnabled, arkChat, arkImage, arkVideoCreate, arkVideoGet, cfg } from './ark.js';
import { localScript, localParse, localImageSVG, localVideoSVG, saveSVG, localNextEpisode, localViralAnalysis } from './local.js';
import { resolveStylePrompt } from './styles.js';
import { bad, notFound } from './httpx.js';

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
const SCRIPT_SYSTEM = `你是资深短剧编剧，擅长强钩子、快节奏、高信息密度的竖屏/横屏短剧。
输出格式要求（严格遵守，便于后续解析）：
1. 第一行《剧名》；
2. 【人物】块：每行"名字（身份）：人设描述"；
3. 【关键道具】块（如有）；
4. 多集时每集以"第 N 集 ｜ 集标题"单独成行开头（单集可省略）；
5. 每场以"第 N 场 ｜ 场景：场景名 ｜ 日/夜 ｜ 内/外"开头；
6. 动作行用中文圆括号（…）单独成行；台词行用"名字：台词"；
7. 每集结尾用"[钩子] …"留下悬念。只输出剧本本体，不要解释。`;

export async function generateScript({ projectId = '', idea = '', genre = '', numScenes = 4, numEpisodes = 1, style = '', title = '' }) {
  let project = projectId ? getProject(projectId) : createProject({ title, idea, genre, style });
  idea = idea || project.idea || project.title;
  genre = genre || project.genre;
  style = style || project.style;

  let script = '';
  let byLLM = false;
  if (arkEnabled()) {
    try {
      const eps = clamp(numEpisodes, 1, 6);
      const r = await arkChat({
        feature: 'script',
        system: SCRIPT_SYSTEM,
        prompt: `请创作一部${genre ? `「${genre}」类型的` : ''}短剧剧本，${eps > 1 ? `共 ${eps} 集，每集 ${clamp(numScenes, 2, 8)} 场，集与集之间用强钩子衔接` : `共 ${clamp(numScenes, 2, 8)} 场`}，每场 3-6 个动作/台词节拍。${style ? `整体影像风格：${resolveStylePrompt(style)}。` : ''}\n核心创意：${idea || '自由发挥一个反转强烈的故事'}`,
        temperature: 0.9,
        maxTokens: eps > 1 ? 6000 : 3000
      });
      script = r.text.trim();
      byLLM = true;
    } catch (e) {
      console.warn('[pipeline] 方舟剧本生成失败，落本地引擎：', e.message);
    }
  }
  if (!script) script = localScript({ idea, genre, numScenes, numEpisodes, title: title || (projectId ? project.title : '') });

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
  if (arkEnabled()) {
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
const PARSE_SYSTEM = `你是短剧导演兼分镜师。把剧本解析为可拍摄的结构化 JSON，只输出 JSON。schema：
{"title":"剧名","logline":"一句话故事","style":"画面风格描述",
 "episodes":[{"key":"e1","title":"集标题","summary":"本集一句话梗概"}],
 "characters":[{"key":"c1","name":"","role":"主角/反派/配角","desc":"外貌+性格","image_prompt":"用于文生图的人物肖像提示词"}],
 "scenes":[{"key":"s1","name":"","desc":"","image_prompt":"场景空镜提示词"}],
 "props":[{"key":"p1","name":"","desc":"","image_prompt":"道具特写提示词"}],
 "shots":[{"key":"sh1","order":1,"episode":"e1","scene":"s1","characters":["c1"],"shot_type":"远景/全景/中景/近景/特写","camera":"运镜","emotion":"主要角色情绪(可空：冷酷/愤怒/狂喜/悲伤/微笑/惊恐/魅惑/羞涩)","action":"画面内发生的事","dialogue":"台词(可空)","duration":5,"image_prompt":"该镜头首帧画面的文生图提示词","video_prompt":"该镜头的图生视频动态提示词(动作+运镜)"}]}
要求：剧本含「第 N 集」标记时按集划分 episodes（否则只有 e1），shots 按集顺序排列且 episode 正确引用；每集分镜 4-10 个；
角色/场景跨集复用同一 key（不要每集重复建）；image_prompt/video_prompt 用中文、具体、含风格词。`;

function normalizeStoryboard(sb) {
  const out = {
    title: String(sb.title || '未命名短剧').slice(0, 50),
    logline: String(sb.logline || '').slice(0, 200),
    style: String(sb.style || '').slice(0, 100),
    episodes: [], characters: [], scenes: [], props: [], shots: []
  };
  const remap = {};
  const epRemap = {};
  (Array.isArray(sb.episodes) ? sb.episodes : []).slice(0, 12).forEach((e, i) => {
    const key = `e${i + 1}`;
    epRemap[e.key || key] = key;
    out.episodes.push({ key, order: i + 1, title: String(e.title || `第 ${i + 1} 集`).slice(0, 30), summary: String(e.summary || '').slice(0, 120) });
  });
  if (!out.episodes.length) out.episodes.push({ key: 'e1', order: 1, title: '第一集', summary: '' });
  (Array.isArray(sb.characters) ? sb.characters : []).slice(0, 8).forEach((c, i) => {
    const key = `c${i + 1}`;
    remap[c.key || key] = key;
    out.characters.push({ key, name: String(c.name || `角色${i + 1}`).slice(0, 20), role: String(c.role || '角色').slice(0, 10), desc: String(c.desc || '').slice(0, 200), image_prompt: String(c.image_prompt || c.name || '').slice(0, 400) });
  });
  (Array.isArray(sb.scenes) ? sb.scenes : []).slice(0, 10).forEach((s, i) => {
    const key = `s${i + 1}`;
    remap[s.key || key] = key;
    out.scenes.push({ key, name: String(s.name || `场景${i + 1}`).slice(0, 20), desc: String(s.desc || '').slice(0, 200), image_prompt: String(s.image_prompt || s.name || '').slice(0, 400) });
  });
  (Array.isArray(sb.props) ? sb.props : []).slice(0, 6).forEach((p, i) => {
    const key = `p${i + 1}`;
    remap[p.key || key] = key;
    out.props.push({ key, name: String(p.name || `道具${i + 1}`).slice(0, 20), desc: String(p.desc || '').slice(0, 200), image_prompt: String(p.image_prompt || p.name || '').slice(0, 400) });
  });
  if (!out.characters.length) out.characters.push({ key: 'c1', name: '主角', role: '主角', desc: '', image_prompt: '电影感人物肖像' });
  if (!out.scenes.length) out.scenes.push({ key: 's1', name: '主场景', desc: '', image_prompt: '电影感场景空镜' });
  const epOrder = new Map(out.episodes.map((e) => [e.key, e.order]));
  const rawShots = (Array.isArray(sb.shots) ? sb.shots : []).slice(0, 48)
    .map((sh, idx) => ({ sh, idx, ep: epOrder.get(epRemap[sh.episode] || 'e1') || 1 }))
    .sort((a, b) => a.ep - b.ep || a.idx - b.idx);   // 按集分组，集内保持原顺序
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
  return out;
}

export async function parseScript({ projectId }) {
  const project = getProject(projectId);
  if (!project.script?.trim()) throw bad('项目还没有剧本，先写剧本或用 AI 生成');
  let sb = null;
  let byLLM = false;
  if (arkEnabled()) {
    try {
      const r = await arkChat({
        feature: 'parse', system: PARSE_SYSTEM, json: true, temperature: 0.4, maxTokens: 6000,
        prompt: `剧本如下，请解析：\n${project.script.slice(0, 12000)}${project.style ? `\n（项目预设风格：${resolveStylePrompt(project.style)}，所有 image_prompt/video_prompt 必须体现该风格）` : ''}`
      });
      sb = normalizeStoryboard(jparse(r.text.replace(/^```(json)?|```$/gm, ''), {}));
      byLLM = true;
    } catch (e) {
      console.warn('[pipeline] 方舟解析失败，落本地引擎：', e.message);
    }
  }
  if (!sb) sb = normalizeStoryboard(localParse(project.script, { style: resolveStylePrompt(project.style) }));

  // 同步画布（已有画布则整体重建结构，保留画布 id）
  const canvasId = ensureCanvas(project, sb);
  touchProject(project.id, {
    storyboard: JSON.stringify(sb), status: 'parsed', canvas_id: canvasId,
    ...(project.title === '未命名短剧' && sb.title ? { title: sb.title } : {}),
    ...(sb.style && !project.style ? { style: sb.style.slice(0, 300) } : {})
  });
  return { project: projectOut(q.get('SELECT * FROM projects WHERE id = ?', project.id)), storyboard: sb, byLLM, canvasId };
}

// ---------- 续写一集 ----------
export async function addEpisode({ projectId, idea = '' }) {
  const project = getProject(projectId);
  if (!project.script?.trim()) throw bad('项目还没有剧本，先写剧本或用 AI 生成');
  const sb = jparse(project.storyboard, null);
  const marks = [...project.script.matchAll(/^第\s*\d+\s*集/gm)];
  const nextOrder = Math.max(marks.length, sb?.episodes?.length || 1) + 1;

  let chunk = '';
  if (arkEnabled()) {
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
export async function generateImage({ prompt, name = '', kind = 'scene', ratio = '', projectId = '', nodeId = '', refImages = [], tab = '', emotion = '' }) {
  if (!prompt?.trim()) throw bad('缺少图片提示词 prompt');
  const project = projectId ? getProject(projectId, { required: false }) : null;
  prompt = applyStyle(prompt.trim(), project?.style);
  ratio = ratio || project?.ratio || '16:9';

  // 画面一致性：分镜首帧自动 ①引用连线角色/场景定妆图（角色优先，情绪联动表情集）
  // ②同集同场景的上一镜首帧作为跨镜参考（无缝衔接） ③注入文本锁定词
  let refs = (refImages || []).filter(Boolean);
  let shotEmotion = '';
  let chainRef = false;
  if (kind === 'frame' && nodeId && project?.canvas_id) {
    try {
      const c = getCanvas(project.canvas_id, { required: false });
      if (c) {
        const incoming = c.edges.filter((e) => e.to === nodeId)
          .map((e) => c.nodes.find((n) => n.id === e.from))
          .filter(Boolean);
        const chars = incoming.filter((n) => n.type === 'character');
        const scenes = incoming.filter((n) => n.type === 'scene');
        const shotNode = c.nodes.find((n) => n.id === nodeId);
        shotEmotion = String(shotNode?.data.emotion || '').trim();
        if (!refs.length) {
          const okUrl = (u) => u && !/\.svg$/i.test(u);
          const charRef = (n) => {
            if (shotEmotion && Array.isArray(n.data.variants)) {
              const v = n.data.variants.find((x) => x.emotion === shotEmotion && okUrl(x.url));
              if (v) return v.url;       // 该情绪的表情定妆照优先
            }
            return okUrl(n.data.image) ? n.data.image : '';
          };
          refs = [...chars.map(charRef), ...scenes.map((n) => (okUrl(n.data.image) ? n.data.image : ''))]
            .filter(Boolean)
            .slice(0, 3);
          // 跨镜参考链：同集同场景的上一镜首帧
          if (shotNode && refs.length < 3) {
            const prev = c.nodes.find((n) => n.type === 'shot'
              && (n.data.episode || 'e1') === (shotNode.data.episode || 'e1')
              && n.data.scene === shotNode.data.scene
              && n.data.order === shotNode.data.order - 1);
            if (prev && okUrl(prev.data.image)) {
              refs.push(prev.data.image);
              chainRef = true;
            }
          }
        }
        const lockChars = chars.slice(0, 3).map((n) => `${n.data.name}（${String(n.data.desc || n.data.prompt || '').slice(0, 50)}）`).filter(Boolean);
        const lockScene = scenes[0] ? `${scenes[0].data.name}（${String(scenes[0].data.desc || '').slice(0, 40)}）` : '';
        if (lockChars.length || lockScene) {
          prompt += `。出场人物：${lockChars.join('、') || '同前'}${shotEmotion ? `，情绪：${shotEmotion}` : ''}${lockScene ? `；场景：${lockScene}` : ''}。严格保持人物五官、发型、服装与场景陈设和参考图完全一致${chainRef ? '，并与上一镜画面无缝衔接' : ''}`;
        }
      }
    } catch { /* 画布可能已删除 */ }
  }
  const seed = project?.seed || 0;

  const taskId = uid('t');
  q.run('INSERT INTO tasks (id, kind, status, provider, prompt, params, project_id, node_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
    taskId, 'image', 'running', arkEnabled() ? 'ark' : 'local', prompt.slice(0, 500),
    JSON.stringify({ kind, ratio, name, ref_images: refs.length, seed, emotion: shotEmotion, chain_ref: chainRef }), projectId, nodeId, now(), now());

  let url = '';
  let provider = 'local';
  try {
    if (arkEnabled()) {
      const r = await arkImage({ prompt, ratio: kind === 'character' ? '3:4' : ratio, refImages: refs, seed, feature: `image:${kind}` });
      url = r.url;
      provider = 'ark';
    } else {
      url = saveSVG(localImageSVG({ prompt, name, kind, ratio, order: 0, emotion }));
    }
  } catch (e) {
    // 方舟失败 → 本地兜底，但记录原始错误
    console.warn('[pipeline] 方舟图片失败，落本地：', e.message);
    url = saveSVG(localImageSVG({ prompt, name, kind, ratio, emotion }));
    q.run('UPDATE tasks SET error = ? WHERE id = ?', `ark: ${e.message}（已用本地兜底）`, taskId);
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
      prompt: `${node.data.prompt || node.data.desc || node.data.name}，表情：${emo}，同一角色、同一造型与五官，仅表情变化，角色表情参考图，纯色背景`,
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
  ratio = ratio || project?.ratio || '16:9';
  duration = clamp(duration, 2, 12);
  const taskId = uid('t');
  const params = { ratio, duration, imageUrl, lastImageUrl: lastImageUrl || '', name, order, model: model || '', resolution: resolution || '' };

  let provider = 'local';
  let remoteId = '';
  if (arkEnabled()) {
    try {
      const r = await arkVideoCreate({ prompt, imageUrl, lastImageUrl, ratio, duration, model, resolution });
      provider = 'ark';
      remoteId = r.remoteId;
      model = r.model;
    } catch (e) {
      console.warn('[pipeline] 方舟视频任务创建失败，落本地：', e.message);
      params.localError = `ark: ${e.message}（已用本地兜底）`;
    }
  }
  q.run(`INSERT INTO tasks (id, kind, status, provider, model, remote_id, prompt, params, project_id, node_id, created_at, updated_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
    taskId, 'video', 'running', provider, model, remoteId, prompt.slice(0, 500), JSON.stringify(params), projectId, nodeId, now(), now());

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

  if (t.provider === 'ark' && t.remote_id) {
    const r = await arkVideoGet(t.remote_id, { duration: params.duration || 5 });
    if (r.status === 'succeeded') return finish('succeeded', { url: r.url });
    if (r.status === 'failed') return finish('failed', {}, r.error || '生成失败');
    return { ...t, params, result: {}, status: r.status };
  }

  // 本地模拟：到时间后产出 SMIL 动画 SVG
  if (now() - t.created_at >= LOCAL_VIDEO_MS()) {
    const url = saveSVG(localVideoSVG({ prompt: t.prompt, name: params.name, ratio: params.ratio, duration: params.duration, order: params.order }));
    return finish('succeeded', { url });
  }
  return { ...t, params, result: {}, status: 'running' };
}
