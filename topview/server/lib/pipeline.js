// 爆款工厂 · 创作管线：商品→广告脚本→画面/视频→配音→本地化→导出，串起所有能力。
// 本地引擎同步出占位结果；配了模型后图像/视频走真实生成（视频异步，由 getTask 轮询推进）。
import { q } from './db.js';
import { uid, now, jparse, clamp } from './util.js';
import { bad, notFound } from './httpx.js';
import { genImage, genVideoCreate, genVideoGet, imageEnabled, videoEnabled } from './llm.js';
import { localFrameSVG, localClipSVG, saveSVG } from './local.js';
import { scrapeProduct, normalizeProduct } from './commerce.js';
import { buildAdScript, resolveStyle, TONE_IDS } from './adscript.js';
import { translateShots, buildSrt, langName } from './i18n.js';

const RATIOS = ['9:16', '16:9', '1:1', '4:5'];

// ---------- 项目 ----------
export function createProject(a = {}) {
  const id = uid('p');
  const t = now();
  const product = normalizeProduct(a.product || {});
  q.run(
    `INSERT INTO projects (id,title,kind,tone,product,lang,style,ratio,duration,storyboard,status,created_at,updated_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
    id, String(a.title || product.title || '未命名广告').slice(0, 120),
    a.kind === 'ugc' ? 'ugc' : 'ad',
    TONE_IDS.includes(a.tone) ? a.tone : 'ugc',
    JSON.stringify(product), String(a.lang || 'zh').slice(0, 6), String(a.style || '').slice(0, 200),
    RATIOS.includes(a.ratio) ? a.ratio : '9:16', clamp(a.duration || 6, 3, 12),
    '{}', 'draft', t, t
  );
  return getProject(id);
}
export function getProject(id) {
  const p = q.get('SELECT * FROM projects WHERE id = ? AND deleted_at = 0', id);
  if (!p) throw notFound('项目不存在');
  return p;
}
export function touchProject(id, fields = {}) {
  const keys = Object.keys(fields);
  if (!keys.length) return;
  q.run(`UPDATE projects SET ${keys.map((k) => `${k} = ?`).join(', ')}, updated_at = ? WHERE id = ?`,
    ...keys.map((k) => fields[k]), now(), id);
}
export function projectOut(p) {
  const localizations = q.all('SELECT lang, by_llm, created_at FROM localizations WHERE project_id = ?', p.id);
  return {
    id: p.id, title: p.title, kind: p.kind, tone: p.tone, lang: p.lang, style: p.style,
    ratio: p.ratio, duration: p.duration, status: p.status, cover: p.cover,
    product: jparse(p.product, {}), storyboard: jparse(p.storyboard, {}),
    localizations: localizations.map((l) => ({ lang: l.lang, name: langName(l.lang), by_llm: !!l.by_llm })),
    created_at: p.created_at, updated_at: p.updated_at
  };
}
export function listProjects() {
  return q.all('SELECT id,title,kind,tone,ratio,status,cover,updated_at FROM projects WHERE deleted_at = 0 ORDER BY updated_at DESC LIMIT 100');
}

export function addAsset({ kind = 'image', name = '', url = '', prompt = '', lang = '', source = 'local', project_id = '' }) {
  const id = uid('a');
  q.run('INSERT INTO assets (id,kind,name,url,prompt,lang,source,project_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, kind, name.slice(0, 80), url, prompt.slice(0, 300), lang, source, project_id, now());
  return { id, kind, name, url, source, project_id };
}

// ---------- 商品 → 广告脚本 ----------
/** 解析商品页（仅公开信息）。返回归一化商品信息。 */
export async function parseProduct(url) {
  return normalizeProduct(await scrapeProduct(url));
}

/** 商品（url 或手填）→ 新项目 + 广告分镜脚本。 */
export async function productToAd(a = {}) {
  let product = normalizeProduct(a.product || {});
  if (a.url && !product.title) product = await parseProduct(a.url);
  else if (a.url) product.url = a.url;
  if (!product.title) throw bad('缺少商品信息：请提供商品页链接或至少填写商品标题');
  const proj = createProject({
    title: a.title || product.title, kind: a.kind, tone: a.tone, product,
    lang: a.lang || 'zh', style: a.style, ratio: a.ratio, duration: a.duration
  });
  const { storyboard, byLLM } = await buildAdScript(product, {
    tone: proj.tone, lang: proj.lang, ratio: proj.ratio, duration: proj.duration, style: proj.style
  });
  touchProject(proj.id, { storyboard: JSON.stringify(storyboard), status: 'scripted' });
  return { project: projectOut(getProject(proj.id)), by_llm: byLLM };
}

// ---------- 任务 ----------
function createTask({ kind, project_id = '', shot_key = '', provider = 'local', model = '', prompt = '', params = {} }) {
  const id = uid('t'); const t = now();
  q.run('INSERT INTO tasks (id,kind,status,provider,model,prompt,params,project_id,shot_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
    id, kind, 'queued', provider, model, prompt.slice(0, 300), JSON.stringify(params), project_id, shot_key, t, t);
  return id;
}
function finishTask(id, { status, url = '', error = '', remote_id = '' }) {
  q.run('UPDATE tasks SET status=?, result=?, error=?, remote_id=?, updated_at=? WHERE id=?',
    status, url ? JSON.stringify({ url }) : '', error, remote_id, now(), id);
}
function taskOut(t) {
  return { id: t.id, kind: t.kind, status: t.status, provider: t.provider, shot_key: t.shot_key, project_id: t.project_id, result: jparse(t.result, null), error: t.error };
}

/** 写回某个分镜的产物地址（image/video/audio），并在全部视频就绪时把项目标记 done */
function setShotMedia(projectId, shotKey, field, url) {
  const p = getProject(projectId);
  const sb = jparse(p.storyboard, { shots: [] });
  const shot = (sb.shots || []).find((s) => s.key === shotKey);
  if (shot) shot[field] = url;
  const allVideo = (sb.shots || []).length && sb.shots.every((s) => s.video);
  if (field === 'image' && !p.cover) touchProject(projectId, { cover: url });
  touchProject(projectId, { storyboard: JSON.stringify(sb), ...(allVideo ? { status: 'done' } : {}) });
}

const visualPrompt = (p, shot) => `${resolveStyle(p.style)}，${shot.visual || shot.onscreen}${p.kind === 'ugc' ? '，达人手持产品口播，竖屏短视频' : ''}`;

/** 为项目生成全部画面/视频（本地同步；供应商图像同步、视频异步）。返回 {project, tasks, pending} */
export async function generateMedia(projectId, { only = 'all' } = {}) {
  const p = getProject(projectId);
  const sb = jparse(p.storyboard, null);
  if (!sb?.shots?.length) throw bad('请先生成广告脚本（product_to_video / 生成脚本）');
  touchProject(projectId, { status: 'generating' });
  const refs = (jparse(p.product, {}).images || []).slice(0, 2);
  const tasks = []; const pending = [];
  const frameKind = p.kind === 'ugc' ? 'presenter' : 'product';
  const prod = jparse(p.product, {});

  for (const shot of sb.shots) {
    // 画面（首帧/商品图）
    if (only === 'all' || only === 'image') {
      const tid = createTask({ kind: 'image', project_id: projectId, shot_key: shot.key, provider: imageEnabled() ? 'ark' : 'local', prompt: visualPrompt(p, shot) });
      try {
        let url;
        if (imageEnabled()) url = (await genImage({ prompt: visualPrompt(p, shot), ratio: p.ratio, refImages: refs, feature: 'image' })).url;
        else url = saveSVG(localFrameSVG({ onscreen: shot.onscreen, brand: prod.brand, price: prod.price ? `${prod.currency || '¥'}${prod.price}` : '', kind: frameKind, ratio: p.ratio, order: shot.order }));
        addAsset({ kind: 'image', name: `${p.title}-${shot.key}`, url, prompt: shot.visual, source: imageEnabled() ? 'ark' : 'local', project_id: projectId });
        setShotMedia(projectId, shot.key, 'image', url);
        finishTask(tid, { status: 'succeeded', url });
        tasks.push(tid);
      } catch (e) { finishTask(tid, { status: 'failed', error: e.message }); }
    }
    // 视频
    if (only === 'all' || only === 'video') {
      const firstFrame = jparse(getProject(projectId).storyboard, { shots: [] }).shots.find((s) => s.key === shot.key)?.image || '';
      const tid = createTask({ kind: 'video', project_id: projectId, shot_key: shot.key, provider: videoEnabled() ? 'ark' : 'local', prompt: visualPrompt(p, shot) });
      try {
        if (videoEnabled()) {
          const { remoteId, model } = await genVideoCreate({ prompt: visualPrompt(p, shot), imageUrl: firstFrame, ratio: p.ratio, duration: shot.duration });
          q.run('UPDATE tasks SET status=?, remote_id=?, model=?, updated_at=? WHERE id=?', 'running', remoteId, model, now(), tid);
          pending.push(tid);
        } else {
          const url = saveSVG(localClipSVG({ onscreen: shot.onscreen, voiceover: shot.voiceover, brand: prod.brand, kind: frameKind, ratio: p.ratio, duration: shot.duration, order: shot.order }));
          addAsset({ kind: 'video', name: `${p.title}-${shot.key}-clip`, url, prompt: shot.visual, source: 'local', project_id: projectId });
          setShotMedia(projectId, shot.key, 'video', url);
          finishTask(tid, { status: 'succeeded', url });
          tasks.push(tid);
        }
      } catch (e) { finishTask(tid, { status: 'failed', error: e.message }); }
    }
  }
  return { project: projectOut(getProject(projectId)), tasks, pending };
}

/** 查询任务（供应商视频任务在此轮询推进并写回分镜） */
export async function getTask(id) {
  const t = q.get('SELECT * FROM tasks WHERE id = ?', id);
  if (!t) throw notFound('任务不存在');
  if (t.status === 'running' && t.kind === 'video' && t.remote_id) {
    try {
      const params = jparse(t.params, {});
      const r = await genVideoGet(t.remote_id, { duration: params.duration || 5 });
      if (r.status === 'succeeded') {
        addAsset({ kind: 'video', name: `clip-${t.shot_key}`, url: r.url, source: 'ark', project_id: t.project_id });
        setShotMedia(t.project_id, t.shot_key, 'video', r.url);
        finishTask(t.id, { status: 'succeeded', url: r.url });
      } else if (r.status === 'failed') {
        finishTask(t.id, { status: 'failed', error: r.error || '生成失败' });
      }
    } catch (e) { /* 轮询出错下次再试 */ void e; }
    return taskOut(q.get('SELECT * FROM tasks WHERE id = ?', id));
  }
  return taskOut(t);
}

// ---------- 配音（本地：浏览器朗读口播；接 TTS 供应商后产出 mp3） ----------
export function generateDubbing(projectId) {
  const p = getProject(projectId);
  const sb = jparse(p.storyboard, null);
  if (!sb?.shots?.length) throw bad('请先生成广告脚本');
  // 当前标准版用浏览器语音合成（零依赖、零成本）朗读口播；放映室按分镜时长同步播放。
  return {
    mode: 'browser', lang: p.lang,
    note: '标准版用浏览器语音合成朗读口播（零成本）；配置 TTS 供应商后将产出可下载的 mp3 并写回分镜。',
    shots: sb.shots.map((s) => ({ key: s.key, voiceover: s.voiceover, duration: s.duration }))
  };
}

// ---------- 本地化（多语言） ----------
export async function localizeProject(projectId, langs = []) {
  const p = getProject(projectId);
  const sb = jparse(p.storyboard, null);
  if (!sb?.shots?.length) throw bad('请先生成广告脚本');
  const targets = (Array.isArray(langs) ? langs : [langs]).map(String).filter((l) => l && l !== p.lang);
  if (!targets.length) throw bad('请选择至少一种不同于主语言的目标语言');
  const out = [];
  for (const lang of targets.slice(0, 12)) {
    const { shots, byLLM } = await translateShots(sb.shots, lang, { sourceLang: p.lang });
    const srt = buildSrt(sb.shots, shots);
    q.run(`INSERT INTO localizations (id,project_id,lang,shots,srt,by_llm,created_at) VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(project_id,lang) DO UPDATE SET shots=excluded.shots, srt=excluded.srt, by_llm=excluded.by_llm, created_at=excluded.created_at`,
      uid('loc'), projectId, lang, JSON.stringify(shots), srt, byLLM ? 1 : 0, now());
    addAsset({ kind: 'audio', name: `${p.title}-${lang}.srt`, url: '', prompt: 'subtitle', lang, source: byLLM ? 'ark' : 'local', project_id: projectId });
    out.push({ lang, name: langName(lang), by_llm: byLLM, srt_lines: shots.length });
  }
  return { project_id: projectId, localized: out };
}

/** 导出某语言 SRT（默认主语言用分镜原文） */
export function exportSrt(projectId, lang = '') {
  const p = getProject(projectId);
  const sb = jparse(p.storyboard, { shots: [] });
  if (lang && lang !== p.lang) {
    const loc = q.get('SELECT shots FROM localizations WHERE project_id=? AND lang=?', projectId, lang);
    if (!loc) throw notFound(`还没有 ${langName(lang)} 的本地化，请先 localize_project`);
    return { lang, srt: buildSrt(sb.shots, jparse(loc.shots, [])) };
  }
  return { lang: p.lang, srt: buildSrt(sb.shots) };
}

export function usageStats() {
  const row = q.get('SELECT COALESCE(SUM(cost_micro),0) c, COUNT(*) n FROM usage_logs') || {};
  const byFeature = q.all('SELECT feature, COUNT(*) n, COALESCE(SUM(cost_micro),0) c FROM usage_logs GROUP BY feature ORDER BY c DESC');
  return { calls: row.n || 0, cost_micro: row.c || 0, by_feature: byFeature };
}
