// 灵境AI · AIQC 质量管控：生成前后让模型"仔细看图/审提示词"，发现问题→Agent 改正→复检→记录
// 有方舟视觉模型：真·看图审查（解剖/一致性/构图/清晰度/恐怖谷）；无 Key：启发式审查（提示词与参考图完整性）。
import { q, getSetting } from './db.js';
import { uid, now, jparse } from './util.js';
import { llmEnabled, arkChat } from './ark.js';
import { getProject, getCanvas, patchCanvasNode, generateImage } from './pipeline.js';
import { bad, notFound } from './httpx.js';

export const qcEnabled = () => getSetting('qc_enabled', true) !== false;     // 总开关
export const qcAutofix = () => getSetting('qc_autofix', true) !== false;     // 发现问题自动改正
export const qcMinScore = () => Math.round(Number(getSetting('qc_min_score', 75)) || 75); // 放行阈值

const QC_SYSTEM = `你是影视级 AI 画面质检员（AIQC）。仔细观察给你的图片，对照"期望"，逐项排查问题。只输出 JSON：
{"score":0到100,"summary":"一句话结论",
 "issues":[{"type":"anatomy(解剖)|consistency(与角色设定不符)|framing(构图/取景)|clarity(模糊/变形)|uncanny(恐怖谷)|content(内容缺失)","severity":"high|med|low","detail":"具体问题","fix":"应如何修改生成提示词来解决"}]}
重点排查：肢体残缺/多余、上下半身错位或分离、大头怪、头身比失调、五官扭曲、面部恐怖谷、人物被画框不当裁切、与角色应有外貌/性别/服装不符、画面模糊。无问题则 issues 为空、score≥90。`;

/** 对一张图做质检；characterHint=该镜头应出现的人物设定，便于核对一致性 */
export async function qcImage({ imageUrl, expectation = '', characterHint = '' }) {
  if (llmEnabled() && imageUrl && /^(https?:|\/uploads\/)/.test(imageUrl) && !/\.svg$/i.test(imageUrl)) {
    try {
      const r = await arkChat({
        feature: 'qc', system: QC_SYSTEM, json: true, temperature: 0.1, maxTokens: 1500, timeoutMs: 60_000,
        prompt: `期望画面：${expectation || '符合剧本镜头描述'}。${characterHint ? `应出现人物设定：${characterHint}。` : ''}请仔细质检这张图。`,
        images: [imageUrl]
      });
      const j = jparse(String(r.text).replace(/```(json)?/gi, '').replace(/```/g, ''), null);
      if (j && typeof j.score === 'number') {
        return { score: clampScore(j.score), summary: String(j.summary || ''), issues: normIssues(j.issues), byVision: true };
      }
    } catch (e) { console.warn('[qc] 视觉审查失败，转启发式：', e.message); }
  }
  // 启发式兜底：看不到图，就审查"提示词与参考是否到位"（本地占位图直接给出说明）
  return heuristicQC({ imageUrl, expectation });
}

function heuristicQC({ imageUrl, expectation }) {
  const issues = [];
  let score = 88;
  const isLocal = /\.svg$/i.test(imageUrl || '');
  if (isLocal) { issues.push({ type: 'clarity', severity: 'low', detail: '本地占位图，未接入方舟无法视觉审查', fix: '配置方舟 Key 后重生成并由视觉模型质检' }); score = 70; }
  if (!/解剖|肢体|完整|半身|全身|取景|脚部|不被画框|裁断/.test(expectation || '')) {
    issues.push({ type: 'framing', severity: 'low', detail: '提示词缺少明确取景/解剖约束', fix: '补充景别与"人物完整、解剖正确"等约束' });
    score -= 8;
  }
  return { score: clampScore(score), summary: isLocal ? '本地占位图（建议接入方舟后由视觉模型质检）' : '启发式审查通过', issues, byVision: false };
}

const clampScore = (s) => Math.max(0, Math.min(100, Math.round(Number(s) || 0)));
function normIssues(arr) {
  if (!Array.isArray(arr)) return [];
  return arr.slice(0, 8).map((it) => ({
    type: String(it.type || 'content').slice(0, 24),
    severity: ['high', 'med', 'low'].includes(it.severity) ? it.severity : 'med',
    detail: String(it.detail || '').slice(0, 200),
    fix: String(it.fix || '').slice(0, 200)
  }));
}

function logQC({ projectId = '', nodeId = '', stage = 'image', target = '', score = 0, issues = [], action = '', byVision = false }) {
  const id = uid('qc');
  const passed = score >= qcMinScore() && !issues.some((i) => i.severity === 'high') ? 1 : 0;
  q.run(`INSERT INTO qc_records (id, project_id, node_id, stage, target, score, passed, issues, action, by_vision, created_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
    id, projectId, nodeId, stage, String(target).slice(0, 60), score, passed, JSON.stringify(issues), action, byVision ? 1 : 0, now());
  return { id, passed: !!passed };
}

/**
 * 质检某个画布节点的图片；发现问题且开启自动修正时，按 fix 建议增强提示词重生成并复检（最多 1 轮）。
 * @returns {Promise<{score, passed, issues, fixed, byVision, recordId}>}
 */
export async function qcNode(projectId, nodeId, { autofix = qcAutofix(), stage = 'image' } = {}) {
  const project = getProject(projectId);
  if (!project.canvas_id) throw bad('项目还没有画布');
  const c = getCanvas(project.canvas_id);
  const node = c.nodes.find((n) => n.id === nodeId || n.data?.key === nodeId);
  if (!node) throw notFound('节点不存在');
  const img = node.data.image;
  if (!img) throw bad('该节点还没有图片，先生成');

  // 期望与人物设定（核对一致性）
  const charHint = (node.type === 'shot'
    ? c.edges.filter((e) => e.to === node.id).map((e) => c.nodes.find((x) => x.id === e.from)).filter((x) => x?.type === 'character')
    : node.type === 'character' ? [node] : [])
    .map((x) => `${x.data.name}（${x.data.gender || ''}${String(x.data.desc || '').slice(0, 50)}）`).join('、');
  const expectation = node.data.image_prompt || node.data.prompt || node.data.action || node.data.name;

  let qc = await qcImage({ imageUrl: img, expectation, characterHint: charHint });
  let action = '';
  let fixed = false;

  if (autofix && !pass(qc)) {
    // Agent 改正：把 QC 的 fix 建议拼进提示词，强化约束后重生成
    const fixes = qc.issues.map((i) => i.fix).filter(Boolean).join('；');
    const base = node.type === 'shot' ? (node.data.image_prompt || node.data.action) : (node.data.prompt || node.data.name);
    const newPrompt = `${base}。质检修正：${fixes || '修正解剖与构图，确保人物完整、比例正确、五官清晰不变形'}`;
    try {
      await generateImage({
        prompt: newPrompt, name: node.data.name,
        kind: node.type === 'shot' ? 'frame' : node.type, projectId, nodeId: node.id, skipQC: true
      });
      action = `按质检建议重生成：${(fixes || '强化解剖/构图约束').slice(0, 80)}`;
      fixed = true;
      // 复检
      const fresh = getCanvas(project.canvas_id).nodes.find((n) => n.id === node.id);
      qc = await qcImage({ imageUrl: fresh?.data.image || img, expectation, characterHint: charHint });
    } catch (e) { action = `自动修正失败：${e.message.slice(0, 80)}`; }
  }
  const rec = logQC({ projectId, nodeId: node.id, stage, target: node.data.name || node.type, score: qc.score, issues: qc.issues, action, byVision: qc.byVision });
  return { ...qc, passed: pass(qc), fixed, action, recordId: rec.id };
}
const pass = (qc) => qc.score >= qcMinScore() && !qc.issues.some((i) => i.severity === 'high');

/** 视频生成前的把关：先确保首帧图存在且通过 QC（不达标会尝试自动修正首帧），返回是否放行 */
export async function qcBeforeVideo(projectId, nodeId) {
  if (!qcEnabled()) return { passed: true, skipped: true };
  const project = getProject(projectId);
  const c = getCanvas(project.canvas_id);
  const node = c.nodes.find((n) => n.id === nodeId);
  if (!node?.data.image) return { passed: true, skipped: true, reason: '无首帧图，跳过质检' };
  const r = await qcNode(projectId, nodeId, { stage: 'video' });
  return { passed: r.passed, score: r.score, issues: r.issues, fixed: r.fixed, recordId: r.recordId };
}

export function listQC(projectId, { onlyOpen = false } = {}) {
  const rows = q.all('SELECT * FROM qc_records WHERE project_id = ? ORDER BY created_at DESC LIMIT 200', projectId || '');
  const out = rows.map((r) => ({ ...r, issues: jparse(r.issues, []), passed: !!r.passed, by_vision: !!r.by_vision, resolved: !!r.resolved }));
  return onlyOpen ? out.filter((r) => !r.passed && !r.resolved) : out;
}
export function resolveQC(id) {
  q.run('UPDATE qc_records SET resolved = 1 WHERE id = ?', id);
  return { resolved: true };
}
export function qcSummary(projectId) {
  const rows = listQC(projectId);
  const open = rows.filter((r) => !r.passed && !r.resolved);
  const avg = rows.length ? Math.round(rows.reduce((s, r) => s + r.score, 0) / rows.length) : 0;
  return { total: rows.length, open: open.length, avg_score: avg, vision: rows.some((r) => r.by_vision) };
}
