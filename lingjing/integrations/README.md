# 把【音乐站 / 任意外部应用】接到灵境AI 共享知识库

`knowledge-client.js` 是个零依赖客户端，让外部应用（如 `lingmirror-site` 里的音乐站）经灵境AI 的
**HTTP MCP** 读写同一份 **LLM Wiki** 知识库，按 `domain` 分区——音乐站默认 `domain='music'`，
和视频站（`domain='video'`）共库但**不串味**。

## 3 步接入（在音乐站后端）

1. **拿 Token**：打开视频站 `https://video.lingmirror.com.cn` → 设置页 → 复制 **Agent Token**。
2. **配环境变量**（音乐站后端）：
   ```bash
   KNOWLEDGE_BASE_URL=https://video.lingmirror.com.cn
   KNOWLEDGE_TOKEN=<上一步的 Agent Token>
   ```
3. **拷贝 `knowledge-client.js` 到音乐站**，然后：
   ```js
   import { knowledge } from './knowledge-client.js';
   const kb = knowledge();                 // 默认 domain='music'

   // 写入：把歌曲/专辑/风格沉淀进知识库
   await kb.ingest({ title: '专辑·夜航', content: '赛博朋克、合成器、未来都市夜景', source: 'music-app' });

   // 查询：出歌/写文案前查风格、品牌、已有作品
   const r = await kb.query('夜航 是什么风格');   // → { answer, pages, hits }

   // 列索引 / 审计
   await kb.page({ list: true });
   await kb.audit();
   ```

## 为什么这样接（而不是直连 REST）
- 走 **MCP + Bearer Token**（`/api/agent/v1/mcp`）是**鉴权**通道，跨站安全；视频站的 `/api/wiki/*` REST 是本机无鉴权，不适合跨站暴露。
- HTTP MCP 是**无状态**的：每次 POST 一条 `tools/call` 即可，无需 initialize 握手。
- **只在服务端用**：Token 别下发到浏览器。需要前端用就让音乐站后端做一层代理。

## 跨站调用注意
- 音乐站后端 → 视频站，是服务器到服务器的 HTTPS，无 CORS 问题。
- 两站不同机/不同域都没关系，只要音乐站后端能访问 `video.lingmirror.com.cn`。

## 可用工具（domain 自动带上）
| 方法 | 对应 MCP 工具 | 作用 |
|---|---|---|
| `kb.query(q, opts)` | `wiki_query` | 关键词命中 +（视频站配了大模型时）综合并标注来源 |
| `kb.ingest(page)` | `wiki_ingest` | upsert 一页（自动摘要+交叉引用） |
| `kb.page(opts)` | `wiki_page` | 读整页 / `{list:true}` 列索引 |
| `kb.audit(opts)` | `wiki_audit` | 孤立页/过期页/域分布 |
