# 更新日志

遵循语义化版本。日期为本地时间。

## 0.2.0

在 0.1.0「本地 7×24 永久记忆 AI 伙伴」基础上，大幅扩展接入面、自动化与体验，
全程零第三方依赖、全链路冒烟测试通过。

### 接入与工具
- **MCP 客户端**：以 stdio JSON-RPC 接入任意 Model Context Protocol 服务，自动把其
  工具注册进 Mnemo（provider 安全别名，原生 function-calling 亦可用）；支持 **MCP 资源**
  列出/读取。`mnemo mcp add/list/test`。
- **Google Gemini 后端**（原生 API：文本/流式/视觉/向量/函数调用）。
- 新工具：`web_search`（DuckDuckGo，零 Key）、`http_request`（任意 REST）、
  `edit_file`（精准替换）、`calc`（AST 安全计算）、`forget`（自纠记忆）、`notify`（推送）。

### 记忆（核心）
- **知识摄入 / RAG**：`mnemo ingest <文件|目录|URL>` 切块入库，相关时自动召回；
  不污染"懂你"画像；`memory import/export`（JSON/Markdown）。
- **会话滚动摘要**：长会话自动压缩保持连贯（`session summarize`，守护进程每日刷新）。
- **每日日记**：`mnemo diary` 把当天对话沉淀为长期叙事记忆。
- **画像直编**：`mnemo profile show/get/set`；扩展高精度抽取（生日/居住地/目标/家人）。
- 记忆/会话管理：按 `kind/tag/source` 过滤、按来源批量遗忘。

### 7×24 与自动化
- **逐字流式输出**（Anthropic/OpenAI SSE；工具步骤不回显 JSON）。
- **通知推送**：desktop / webhook / **email(SMTP)** / stdout 兜底，提醒与任务结果触达。
- **文件监视**：路径变化即触发任务（`mnemo watch`）。
- **剧本 playbook**：命名多步例程，按序共享上下文执行。
- **任务执行历史**、`daemon --status/--stop`、防重复启动。
- **HTTP 重试**（指数退避，瞬时错误/5xx/429）。
- **用量与成本观测** + **每日 token 预算护栏**；可配 `pricing` 计费。

### 体验
- **可切换人格**（内置 程序员/教练/研究员）。
- **`mnemo status`** 一屏总览；**`mnemo init`** 初始化向导。
- 交互对话斜杠命令：`/tools /usage /reminders /persona /ingest …`；`chat --session/--resume`。
- `run --json` 脚本友好输出。
- Web 服务新增 `/api/status /api/usage /api/sessions` 与侧栏用量。
- 新增内置技能：`research`、`learn-about-me`、`triage-code`。

### 修复（两轮自动评审，共 21 条）
- 不把环境注入的密钥落盘；Opus 默认温度规避 400；tar 解包路径校验；
  提醒/调度时间越界处理；transcribe/插件/技能 路径穿越；市场签名强制校验与插件二次确认；
  Web/语音尊重 confirm_danger；原生工具步数耗尽补总结；离线 remember JSON 序列化；
  定价最长前缀匹配；Ollama 模型存在性校验；MCP 原生命名清洗；正文 JSON 不被误执行 等。

## 0.1.0

- 本地终端 7×24 运行；三层永久记忆 + 进化画像；接入任意大模型（文本工具协议 +
  可选原生 function-calling）；技能（含自我进化）/插件/市场；多 Agent；多模态/语音；
  向量语义检索 + LSH ANN；记忆巩固/遗忘；定时提醒；容器沙箱；加密同步；本地 Web GUI。
