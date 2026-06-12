// 青鸾 · 创作流水线：剧本 → 分镜 → 画布 → 图像 → 视频
// 配置了火山方舟 Key 走真实模型；否则自动落到本地规则引擎（结果带 provider 标识）
import { q, getSetting } from './db.js';
import { uid, now, jparse, clamp } from './util.js';
import { arkEnabled, arkChat, arkImage, arkVideoCreate, arkVideoGet, cfg } from './ark.js';
import { localScript, localParse, localImageSVG, localVideoSVG, saveSVG, localNextEpisode } from './local.js';
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
  q.run(
    'INSERT INTO projects (id, title, idea, genre, style, ratio, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
    id, String(title || '未命名短剧').slice(0, 50), String(idea).slice(0, 2000), String(genre).slice(0, 20),
    String(style).slice(0, 300), ratio, now(), now()
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

// ---------- 剧本解析 → 分镜 ----------
const PARSE_SYSTEM = `你是短剧导演兼分镜师。把剧本解析为可拍摄的结构化 JSON，只输出 JSON。schema：
{"title":"剧名","logline":"一句话故事","style":"画面风格描述",
 "episodes":[{"key":"e1","title":"集标题","summary":"本集一句话梗概"}],
 "characters":[{"key":"c1","name":"","role":"主角/反派/配角","desc":"外貌+性格","image_prompt":"用于文生图的人物肖像提示词"}],
 "scenes":[{"key":"s1","name":"","desc":"","image_prompt":"场景空镜提示词"}],
 "props":[{"key":"p1","name":"","desc":"","image_prompt":"道具特写提示词"}],
 "shots":[{"key":"sh1","order":1,"episode":"e1","scene":"s1","characters":["c1"],"shot_type":"远景/全景/中景/近景/特写","camera":"运镜","action":"画面内发生的事","dialogue":"台词(可空)","duration":5,"image_prompt":"该镜头首帧画面的文生图提示词","video_prompt":"该镜头的图生视频动态提示词(动作+运镜)"}]}
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
        shot_type: sh.shot_type, camera: sh.camera, action: sh.action, dialogue: sh.dialogue,
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
  return c ? { ...c, nodes: jparse(c.nodes, []), edges: jparse(c.edges, []), viewport: jparse(c.viewport, null) } : null;
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
export async function generateImage({ prompt, name = '', kind = 'scene', ratio = '', projectId = '', nodeId = '', refImages = [], tab = '' }) {
  if (!prompt?.trim()) throw bad('缺少图片提示词 prompt');
  const project = projectId ? getProject(projectId, { required: false }) : null;
  prompt = applyStyle(prompt.trim(), project?.style);
  ratio = ratio || project?.ratio || '16:9';
  const taskId = uid('t');
  q.run('INSERT INTO tasks (id, kind, status, provider, prompt, params, project_id, node_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
    taskId, 'image', 'running', arkEnabled() ? 'ark' : 'local', prompt.slice(0, 500),
    JSON.stringify({ kind, ratio, name }), projectId, nodeId, now(), now());

  let url = '';
  let provider = 'local';
  try {
    if (arkEnabled()) {
      const r = await arkImage({ prompt, ratio: kind === 'character' ? '3:4' : ratio, refImages, feature: `image:${kind}` });
      url = r.url;
      provider = 'ark';
    } else {
      url = saveSVG(localImageSVG({ prompt, name, kind, ratio, order: 0 }));
    }
  } catch (e) {
    // 方舟失败 → 本地兜底，但记录原始错误
    console.warn('[pipeline] 方舟图片失败，落本地：', e.message);
    url = saveSVG(localImageSVG({ prompt, name, kind, ratio }));
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

// ---------- 视频生成（异步任务） ----------
const LOCAL_VIDEO_MS = () => (process.env.QINGLUAN_FAST_LOCAL ? 50 : 4000);

export async function createVideoTask({ prompt, imageUrl = '', duration = 5, ratio = '', projectId = '', nodeId = '', name = '', order = 0 }) {
  if (!prompt?.trim()) throw bad('缺少视频提示词 prompt');
  const project = projectId ? getProject(projectId, { required: false }) : null;
  prompt = applyStyle(prompt.trim(), project?.style);
  ratio = ratio || project?.ratio || '16:9';
  duration = clamp(duration, 2, 12);
  const taskId = uid('t');
  const params = { ratio, duration, imageUrl, name, order };

  let provider = 'local';
  let remoteId = '';
  let model = '';
  if (arkEnabled()) {
    try {
      const r = await arkVideoCreate({ prompt, imageUrl, ratio, duration });
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
