# 运行时知识库（LLM Wiki）

App 内置的自维护知识库，给「创作工作流 / 产品 Agent / 外部音乐站」用。代码 `lingjing/server/lib/wiki.js`，表 `wiki_pages`。范式同 Karpathy LLM Wiki：摄入 / 查询 / 审计。

## 分区
`domain`：`video` / `music` / `agent` / `global`；`namespace`：如项目 id。多 App 共用一库**不串味**（query 按 domain 过滤）。

## 接口
- 函数：`wikiIngest`（按 domain+namespace+title upsert，自动摘要+交叉引用）、`wikiQuery`（关键词命中 +（llmEnabled 时）LLM 综合并标注来源）、`wikiPage`、`wikiList`、`wikiAudit`（孤立页/过期页/域分布）。
- REST：`/api/wiki`（list）、`POST /api/wiki/query`、`POST /api/wiki/ingest`、`/api/wiki/page`、`/api/wiki/audit`。
- Agent/MCP 工具：`wiki_query` / `wiki_ingest` / `wiki_audit` / `wiki_page`（在 `tools.js TOOLS`，经 MCP stdio+HTTP 自动暴露）。

## 怎么"接入所有工作流 + 音乐站一起用"
- **解析后自动摄入**：角色/场景/道具/总览建页（domain=video, namespace=项目id）——见 `pipeline.js ingestStoryboardToWiki`。
- **App 工作流 / 产品 Agent**：调 `wiki_query` 拿画风/品牌/角色设定/模型最佳实践。
- **外部音乐站（独立仓库）**：连同一个 MCP 端点 `/api/agent/v1/mcp`（带 agent token），用 `domain:'music'` 读写——即与视频站共享同一知识库、互不串味。

## 与工程 wiki 的区别
本页讲的是**运行时**知识库（产品用）。仓库 `wiki/` 目录是**工程**知识库（写代码的 Agent 用），范式相同、对象不同。改了本能力记得同步本页。
