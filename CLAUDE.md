# CLAUDE.md — 项目向导（AI句灵 / 灵阵）

本仓库已用 **Anthropic「长时运行 Agent Harness」起步项目** 初始化（见 `cwc-long-running-agents/`）。
长时运行约定见 `.claude/CLAUDE.md`；本文件告诉你**这个项目**怎么跑、怎么验证。

## 项目是什么
- **AI句灵**：零依赖 Node 22 服务端（`server/`，用内置 `node:sqlite` / `node:http` / `fetch`，**禁止引入第三方 npm 依赖**）。
- **灵阵（lingzhen/）**：多智能体 AI 团队独立站，原生 ES Modules、无打包；HTML 由 `serveStatic` 加 CSP `script-src 'self'`——**禁止内联 `<script>` / 内联事件**，JS 一律走外部 `type="module"`。
- 数据库 `var/jvling.sqlite`（schema 在 `server/schema.sql`，每次启动幂等执行；新列走 `server/agents/seed.js` 的 `runAgentMigrations`）。
- 大模型：纯 BYOK + 可选平台 Key；解析顺序 用户Key→平台Key→本地引擎（`server/lib/llm.js` 的 `resolveLLM`）。密钥加密落库（`server/lib/secretbox.js`），**永不提交、不下发前端**。

## 怎么跑
```bash
node server/index.js          # 启动；读 .env（server/lib/env.js 自动加载）。默认端口 3000
npm run dev                   # --watch 热重启
```

## 怎么验证（proof before passing）
顺序：**语法 → 冒烟 → 端到端 → 截图**。
```bash
npm run check                 # scripts/check-syntax.mjs：全量 node --check
npm run smoke                 # scripts/smoke.mjs：服务端冒烟
node scripts/llm-test.mjs     # 大模型连通自检（按 .env / 环境变量）
```
- **端到端**：起服务后写一次性 `.mjs` 脚本打 `http://localhost:3000/api/...`（本仓库历来这么做），打印关键断言。
- **前端/视觉**：用 Playwright（`/opt/node22/lib/node_modules/playwright`，浏览器在 `/opt/pw-browsers`）注入 `localStorage.jl_token` 后访问 `#/...` 截图，**截图存到 `screenshots/`**，然后用 Read 工具打开看清楚再判通过。
- 出网受限：本环境只允许白名单域名；`ark.cn-beijing.volces.com` 等可能被拦，用本地 mock OpenAI 兼容端点验证接线（见历史做法）。

## 质量闭环（本仓库已装的 harness）
- 验收清单：`test-results.json`，**每项默认 `passes:false`**（Default-FAIL）。只有在「跑 live + Read 证据（`screenshots/*.png` 或 `*-result.txt`）」后才可改 true——`.claude/hooks/verify-gate.sh` 会拦截无证据的修改。
- 独立验收：交活前可让 `evaluator` 子代理以全新上下文复核（`.claude/agents/evaluator.md`）。
- 交接：每次会话先读 `PROGRESS.md`，做完一项更新它；`Stop` 钩子会自动 checkpoint 提交。
- 操作员控制：`touch AGENT_STOP` 急停；写 `STEER.md` 中途纠偏。

## 红线
- 不加第三方运行时依赖（保持零依赖）。
- 不破坏 CSP（灵阵无内联脚本）。
- 不提交任何密钥 / `.env`。
- 只在 `claude/gracious-ride-p4z988` 等指定分支开发，不擅自推主干。
