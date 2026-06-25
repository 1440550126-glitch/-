// 灵阵 · 知识库（RAG）：零依赖关键词检索。
// 中文用 bigram + 单字，拉丁用词，倒排式打分；数据量上来后可平滑替换为向量库。
import { q } from '../lib/db.js';
import { now, estimateTokens } from '../lib/util.js';

// 分词：拉丁词(≥2) + 中文 bigram + 中文单字
export function terms(s) {
  const out = [];
  const str = String(s || '').toLowerCase();
  for (const m of str.matchAll(/[a-z0-9]{2,}/g)) out.push(m[0]);
  for (const run of (str.match(/[一-鿿]+/g) || [])) {
    for (let i = 0; i < run.length; i++) {
      out.push(run[i]);
      if (i + 1 < run.length) out.push(run.slice(i, i + 2));
    }
  }
  return out;
}

const weight = (t) => (t.length >= 2 && /[一-鿿]/.test(t) ? 2 : 1); // 中文 bigram 更有区分度

// 把长文切成 ~maxLen 字的块（优先在句子/段落边界切）
export function chunkText(text, maxLen = 320) {
  const clean = String(text || '').replace(/\r\n/g, '\n').trim();
  if (!clean) return [];
  const parts = clean.split(/\n{2,}|(?<=[。！？!?\n])/).map((s) => s.trim()).filter(Boolean);
  const chunks = [];
  let buf = '';
  for (const p of parts) {
    if ((buf + p).length > maxLen && buf) { chunks.push(buf.trim()); buf = ''; }
    if (p.length > maxLen) {                 // 超长句硬切
      for (let i = 0; i < p.length; i += maxLen) chunks.push(p.slice(i, i + maxLen).trim());
    } else {
      buf += p;
    }
  }
  if (buf.trim()) chunks.push(buf.trim());
  return chunks.filter(Boolean);
}

// 向知识库写入一篇文档：切块入库并刷新计数
export function addDoc(kbId, source, text) {
  const chunks = chunkText(text);
  if (!chunks.length) return { added: 0 };
  const base = q.get('SELECT COALESCE(MAX(idx), -1) m FROM knowledge_chunks WHERE kb_id = ?', kbId)?.m ?? -1;
  chunks.forEach((c, i) => {
    q.run('INSERT INTO knowledge_chunks (kb_id, source, idx, text, tokens, created_at) VALUES (?,?,?,?,?,?)',
      kbId, source || '未命名文档', base + 1 + i, c, estimateTokens(c), now());
  });
  q.run(
    `UPDATE knowledge_bases SET chunk_count = (SELECT COUNT(*) FROM knowledge_chunks WHERE kb_id = ?),
       doc_count = (SELECT COUNT(DISTINCT source) FROM knowledge_chunks WHERE kb_id = ?), updated_at = ?
     WHERE id = ?`,
    kbId, kbId, now(), kbId
  );
  return { added: chunks.length };
}

// 在若干知识库里检索与 query 最相关的若干块
export function searchKnowledge(kbIds, query, topK = 4) {
  const ids = (kbIds || []).map(Number).filter(Boolean);
  if (!ids.length || !String(query || '').trim()) return [];
  const qTerms = [...new Set(terms(query))];
  if (!qTerms.length) return [];
  const placeholders = ids.map(() => '?').join(',');
  const rows = q.all(`SELECT id, kb_id, source, idx, text FROM knowledge_chunks WHERE kb_id IN (${placeholders})`, ...ids);
  const scored = [];
  for (const r of rows) {
    const counts = new Map();
    for (const t of terms(r.text)) counts.set(t, (counts.get(t) || 0) + 1);
    let score = 0, hit = 0;
    for (const t of qTerms) {
      const c = counts.get(t);
      if (c) { score += Math.min(c, 3) * weight(t); hit++; }
    }
    if (score > 0) {
      // 轻度长度归一，避免长块通吃；命中词种类多的加成
      score = (score * (1 + hit / qTerms.length)) / Math.sqrt(Math.max(20, r.text.length));
      scored.push({ id: r.id, source: r.source, idx: r.idx, text: r.text, score: Number(score.toFixed(4)) });
    }
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}
