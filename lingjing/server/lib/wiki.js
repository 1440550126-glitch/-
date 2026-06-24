// 灵境AI · LLM Wiki 引擎（Karpathy 范式：摄入 Ingest / 查询 Query / 审计 Audit）
// 一套自维护的结构化知识库，按 domain 分区（video/music/agent/global），可被 App 工作流、Agent、
// 以及外部应用（如音乐站）经由 MCP 共享同一份知识。零依赖：node:sqlite + 关键词检索 + 可选 LLM 综合。
import { q } from './db.js';
import { uid, now, jparse } from './util.js';
import { llmEnabled, arkChat } from './ark.js';
import { bad } from './httpx.js';

const DOMAINS = new Set(['video', 'music', 'agent', 'global']);
const norm = (s) => String(s || '').trim();
const dom = (d) => (DOMAINS.has(d) ? d : 'global');
const tokenize = (s) => norm(s).split(/[\s,，。、;；:：!！?？/|\\()（）【】"'`]+/).filter((t) => t.length >= 1).slice(0, 16);
const autoSummary = (content) => norm(content).replace(/\s+/g, ' ').slice(0, 140);

/** 交叉引用：内容里提到的同域其它页标题 */
function crossRefs(domain, namespace, title, content) {
  const others = q.all('SELECT title FROM wiki_pages WHERE domain = ? AND namespace = ? AND title <> ?', domain, namespace, title);
  const c = String(content || '');
  return others.filter((o) => o.title.length >= 2 && c.includes(o.title)).map((o) => o.title).slice(0, 24);
}

/** 摄入/更新一张 Wiki 页（按 domain+namespace+title upsert）：自动摘要 + 自动交叉引用 */
export function wikiIngest({ domain = 'global', namespace = '', title, content = '', summary = '', source = '', refs = null } = {}) {
  title = norm(title);
  if (!title) throw bad('缺少页面标题 title');
  domain = dom(domain);
  namespace = norm(namespace);
  content = String(content || '').slice(0, 20000);
  summary = norm(summary) || autoSummary(content);
  const autoRefs = Array.isArray(refs) ? refs : crossRefs(domain, namespace, title, content);
  const existing = q.get('SELECT id FROM wiki_pages WHERE domain = ? AND namespace = ? AND title = ?', domain, namespace, title);
  if (existing) {
    q.run('UPDATE wiki_pages SET summary = ?, content = ?, refs = ?, source = ?, updated_at = ? WHERE id = ?',
      summary, content, JSON.stringify(autoRefs), source, now(), existing.id);
    return wikiPage({ id: existing.id });
  }
  const id = uid('wk');
  q.run('INSERT INTO wiki_pages (id, domain, namespace, title, summary, content, refs, source, updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, domain, namespace, title, summary, content, JSON.stringify(autoRefs), source, now());
  return wikiPage({ id });
}

/** 批量摄入（解析后把角色/场景/道具一次性建页） */
export function wikiIngestMany(pages = []) {
  let n = 0;
  for (const p of pages) { try { wikiIngest(p); n++; } catch { /* 跳过坏页 */ } }
  return n;
}

/** 读取整页（id 优先，否则按 domain+namespace+title） */
export function wikiPage({ id = '', domain = 'global', namespace = '', title = '' } = {}) {
  const row = id
    ? q.get('SELECT * FROM wiki_pages WHERE id = ?', id)
    : q.get('SELECT * FROM wiki_pages WHERE domain = ? AND namespace = ? AND title = ?', dom(domain), norm(namespace), norm(title));
  return row ? { ...row, refs: jparse(row.refs, []) } : null;
}

/** 列出页（索引）：可按 domain / namespace 过滤 */
export function wikiList({ domain = '', namespace = '' } = {}) {
  const cols = 'id, domain, namespace, title, summary, source, updated_at';
  if (domain && namespace) return q.all(`SELECT ${cols} FROM wiki_pages WHERE domain = ? AND namespace = ? ORDER BY updated_at DESC`, dom(domain), norm(namespace));
  if (domain) return q.all(`SELECT ${cols} FROM wiki_pages WHERE domain = ? ORDER BY updated_at DESC`, dom(domain));
  return q.all(`SELECT ${cols} FROM wiki_pages ORDER BY updated_at DESC LIMIT 500`);
}

/** 查询：关键词命中页 +（可选）LLM 综合并标注来源 */
export async function wikiQuery({ query, domain = '', namespace = '', limit = 6, synthesize = true } = {}) {
  const tokens = tokenize(query);
  if (!tokens.length) throw bad('缺少查询 query');
  const scope = []; const args = [];
  if (domain) { scope.push('domain = ?'); args.push(dom(domain)); }
  if (namespace) { scope.push('namespace = ?'); args.push(norm(namespace)); }
  const where = scope.length ? 'WHERE ' + scope.join(' AND ') : '';
  const all = q.all(`SELECT id, domain, namespace, title, summary, content, source, updated_at FROM wiki_pages ${where}`, ...args);
  const scored = all.map((p) => {
    const hay = `${p.title} ${p.summary} ${p.content}`;
    let s = 0;
    for (const t of tokens) { if (p.title.includes(t)) s += 3; else if (hay.includes(t)) s += 1; }
    return { p, s };
  }).filter((x) => x.s > 0).sort((a, b) => b.s - a.s).slice(0, clampN(limit));
  const pages = scored.map((x) => ({ id: x.p.id, title: x.p.title, summary: x.p.summary, source: x.p.source, domain: x.p.domain }));
  let answer = '';
  if (synthesize && pages.length && llmEnabled()) {
    try {
      const ctx = scored.map((x) => `## ${x.p.title}\n${String(x.p.content || x.p.summary).slice(0, 1200)}`).join('\n\n');
      const r = await arkChat({
        feature: 'wiki', temperature: 0.2, maxTokens: 700,
        system: '你是知识库助手。只依据下面的 Wiki 页面回答用户问题，简洁准确，并在结论后用【来源：页面标题】标注引用；资料不足就直说缺什么、建议补哪页。',
        prompt: `问题：${query}\n\nWiki 资料：\n${ctx}`
      });
      answer = r.text.trim();
    } catch { /* LLM 不可用则只回命中页 */ }
  }
  return { query, answer, pages, hits: pages.length };
}

/** 审计：孤立页（无人引用）、过期页、域分布、总数 —— LLM Wiki 的 Audit 环节 */
export function wikiAudit({ domain = '', namespace = '' } = {}) {
  const pages = wikiList({ domain, namespace });
  const referenced = new Set();
  for (const p of pages) { const full = wikiPage({ id: p.id }); for (const r of (full?.refs || [])) referenced.add(r); }
  const orphans = pages.filter((p) => !referenced.has(p.title)).map((p) => p.title);
  const STALE_MS = 90 * 24 * 3600 * 1000;
  const stale = pages.filter((p) => now() - p.updated_at > STALE_MS).map((p) => p.title);
  return {
    total: pages.length,
    domains: [...new Set(pages.map((p) => p.domain))],
    orphans: orphans.slice(0, 50),
    stale: stale.slice(0, 50)
  };
}

function clampN(n) { n = Number(n) || 6; return n < 1 ? 1 : n > 20 ? 20 : n; }
