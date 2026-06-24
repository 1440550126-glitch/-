// LingMirror 知识库客户端 —— 给【音乐站 / 任意外部应用】用。
// 经灵境AI 的 HTTP MCP（POST /api/agent/v1/mcp，Bearer Token，无状态）读写共享知识库（LLM Wiki）。
// 与视频站共用同一份知识、按 domain 分区不串味（音乐站默认 domain='music'）。
// 零依赖：原生 fetch（Node 18+ / 服务端）。务必在【服务端】用，别把 Token 暴露给浏览器。
//
// 配置（环境变量，二选一传参或环境变量）：
//   KNOWLEDGE_BASE_URL   灵境AI 地址，默认 https://video.lingmirror.com.cn
//   KNOWLEDGE_TOKEN      灵境AI「设置页」里的 Agent Token（Bearer）
//
// 用法（ESM）：
//   import { knowledge } from './knowledge-client.js';
//   const kb = knowledge();                                   // 默认 domain='music'
//   await kb.ingest({ title: '专辑·夜航', content: '赛博朋克氛围，合成器…', source: 'music-app' });
//   const r = await kb.query('夜航 是什么风格');               // { query, answer, pages:[...], hits }
//   const idx = await kb.page({ list: true });                 // 列出 music 域全部页（索引）
//   const audit = await kb.audit();                            // 孤立页/过期页/域分布
// CommonJS：const { knowledge } = await import('./knowledge-client.js');

const DEFAULT_BASE = 'https://video.lingmirror.com.cn';

export function knowledge({ baseUrl, token, domain = 'music', namespace = '', timeoutMs = 30000 } = {}) {
  baseUrl = String(baseUrl || process.env.KNOWLEDGE_BASE_URL || DEFAULT_BASE).replace(/\/+$/, '');
  token = token || process.env.KNOWLEDGE_TOKEN || '';
  if (!token) throw new Error('缺少 KNOWLEDGE_TOKEN（灵境AI 设置页的 Agent Token）');

  async function call(name, args) {
    let res;
    try {
      res = await fetch(`${baseUrl}/api/agent/v1/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } }),
        signal: AbortSignal.timeout(timeoutMs)
      });
    } catch (e) { throw new Error(`连接知识库失败：${e.message}`); }
    if (res.status === 401) throw new Error('知识库鉴权失败：Token 不对（检查 KNOWLEDGE_TOKEN）');
    const data = await res.json().catch(() => ({}));
    if (data?.error) throw new Error(`知识库错误：${data.error.message}`);
    const text = data?.result?.content?.[0]?.text;
    if (data?.result?.isError) throw new Error(text || '知识库工具执行失败');
    try { return JSON.parse(text); } catch { return text; }
  }

  return {
    /** 查询知识库，返回 { query, answer, pages:[{id,title,summary,source}], hits } */
    query: (query, opts = {}) => call('wiki_query', { query, domain: opts.domain ?? domain, namespace: opts.namespace ?? namespace, limit: opts.limit }),
    /** 摄入/更新一页（自动 upsert + 摘要 + 交叉引用）。page: { title, content, summary?, source? } */
    ingest: (page) => call('wiki_ingest', { domain, namespace, ...page }),
    /** 读整页（{id} 或 {title}）或列索引（{list:true}） */
    page: (opts = {}) => call('wiki_page', { domain, namespace, ...opts }),
    /** 审计：孤立页/过期页/域分布/总数 */
    audit: (opts = {}) => call('wiki_audit', { domain: opts.domain ?? domain, namespace: opts.namespace ?? namespace }),
    /** 直接调任意工具（高级） */
    raw: call
  };
}

export default knowledge;
