# 灵境AI 架构

零依赖 Node 22+（`node:sqlite` / 原生 `fetch` / `http`），无 npm 依赖。入口 `lingjing/server/index.js`，默认端口 4399（`LINGJING_PORT`）。前端是无构建的原生 ESM SPA（`lingjing/web/`）。

## 目录
- `server/index.js` — http 服务：`/api/*` 走 [providers](providers.md) 路由，其余服务 `web/` 静态 + `/uploads/`。
- `server/lib/` — 核心：
  - `pipeline.js` — 创作流水线：剧本→解析→分镜→出图→出片；锁定档案、对齐、[consistency](consistency.md) 全在这。
  - `ark.js` — 火山方舟客户端 + `cfg()`/`arkChat`/`arkImage`/`arkVideoCreate`；chat 按模型路由（千问走 DashScope）。
  - `providers.js` — OpenAI/Google/阿里/Vidu/可灵 客户端 + 按模型 ID 路由 + 时长/多图能力判定。见 [providers](providers.md)。
  - `wiki.js` — 运行时知识库，见 [llm-wiki](llm-wiki.md)。
  - `tools.js` — Agent 工具注册表 `TOOLS`（也是 MCP 的工具源）。
  - `workflow.js` — 一键托管工作流引擎（剧本→…→导出，步骤化、可取消）。
  - `expressions.js`/`styles.js`/`qc.js`/`tts.js`/`export.js`/`db.js`。
- `mcp/server.mjs` — MCP 服务器（stdio），代理 `/api/agent/v1/tools`；另有 HTTP MCP `/api/agent/v1/mcp`。
- `scripts/smoke.mjs` — 218 条端到端冒烟测试。

## 数据
SQLite（`var/lingjing.sqlite`，env 可改）。表：projects/assets/canvases/tasks/usage_logs/agent_logs/workflows/qc_records/settings/wiki_pages。`schema.sql` 每次启动 `CREATE TABLE IF NOT EXISTS`，轻量迁移用 `ALTER TABLE … ADD COLUMN`（db.js）。

## 接入面
1. REST `/api/*`（前端用）。2. Agent HTTP `/api/agent/v1/*`（带 token）。3. MCP（stdio + HTTP）。三者共用 `TOOLS`。
