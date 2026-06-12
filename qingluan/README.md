# 青鸾 · AI 短剧创作工坊

> 比云雀飞得更高 —— 一个**完全开放**的小云雀（剪映 xyq.jianying.com）式 AI 短剧创作平台：
> 剧本 → 分镜 → 节点画布 → 图像 → 视频全流程，火山方舟（豆包 / Seedream / Seedance）驱动，
> 并把**全部创作能力以 MCP + OpenAPI 开放给任意 Agent**。

## 一键运行（零依赖）

只需要 Node.js ≥ 22.5，不需要 `npm install`：

```bash
npm run studio          # 在仓库根目录执行
# 🎬 工作台      http://localhost:4399
# 🤖 Agent API   http://localhost:4399/api/agent/v1/openapi.json
```

**不配置任何 Key 也能完整体验**：本地规则引擎兜底全流程（模板剧本、规则解析、生成式 SVG 占位图、
SMIL 动画占位视频），界面会明确标注「本地生成」。配置火山方舟 Key 后自动切换为真实大模型。

```bash
npm run studio:dev      # 开发模式（文件变更自动重启）
npm run studio:smoke    # 57 项全链路冒烟测试（API + Agent + MCP stdio/HTTP）
```

## 和小云雀比，好在哪

| | 小云雀（剪映） | 青鸾 |
|---|---|---|
| 创作流程 | 剧本 → 资产 → 画布 → 成片 | 一样齐全（AI 生剧本 / 粘贴剧本 / 自由画布） |
| 分集视频 | 按集管理分镜与生成 | 同款分集面板（每集分镜/首帧/视频完成度、本集一键生成、AI 续写新一集），Agent 侧有 add_episode 工具 |
| 风格库 | 预设风格分类选择 | 同款风格库（电影感/真人/2D/3D ×30 预设 + 自定义提示词），**风格自动注入所有生图/生视频提示词** |
| Agent 接入 | 会员专属 Skill（`npx @pippit-dev/cli`，闭源） | **MCP + OpenAPI + 内置 Agent 三通道，全开放免费** |
| 模型 | 平台内置，不可换 | 方舟全家桶**模型 ID 随便换**（Seedance 2.0 出了改个 ID 就用） |
| 成本 | 积分/会员，黑盒 | **每次调用记账**，按官网单价本地估算，看板透明 |
| 数据 | 云端 | 本机 SQLite + 文件，想搬就搬 |
| 水印 | 跟会员走 | 自己说了算（`watermark` 开关） |
| 兜底 | 无 Key 不可用 | 本地引擎全流程可演示，断网/超额自动兜底 |

## 创作流程

1. **首页**：三个入口——「AI 生剧本」（故事构想 + 类型 + 集数 + 风格库 + 画幅）、「粘贴 / 上传剧本」、「自由画布」。
2. **项目工作台**（`/#/project/:id`）：左侧剧本编辑（自动保存）+ AI 重写；右侧分集面板（每集
   分镜/首帧/视频完成度、本集一键生成、「新增一集」AI 续写）/ 分镜表 / 角色卡 / 场景道具卡 /
   项目内 Agent 对话。点「解析分镜」自动拆出分集、角色、场景、道具、镜头，并搭好节点画布。
   剧本里写「第 N 集」即可分集（AI 多集生成会自动带标记），角色与场景跨集复用。
3. **节点画布**（`/#/canvas/:id`）：小云雀式深色无限画布——平移缩放、节点拖拽、端口连线
   （角色/场景/道具 → 分镜）、属性面板改提示词/台词/时长、逐节点生成图与视频、「一键生成」批量出全部素材。
   快捷键：滚轮缩放、`F` 适配全部、`Delete` 删除选中、`⌘/Ctrl+S` 立即保存。
4. **资产库**：素材 / 角色 / 画布三个 tab；上传本地图片视频、AI 生图、搜索、重命名、复制地址。
   所有生成产物自动入库（方舟返回的 URL 有有效期，青鸾会自动下载落盘）。

## 火山方舟接入

1. 到[方舟控制台](https://console.volcengine.com/ark)开通模型并创建 **API Key**
   （「API Key 管理」里创建的 UUID 形态 Key；`AKLT` 开头的 AccessKey 不能用，设置页会帮你拦截）。
2. 打开青鸾「设置」页粘贴 Key（或配置 `.env` 的 `ARK_API_KEY`），点「测试连接」。
3. 默认模型（设置页 / `.env` 均可改，参考[方舟文档](https://www.volcengine.com/docs/82379)）：

| 用途 | 默认模型 ID | 接口 |
|---|---|---|
| 剧本 / 解析 / Agent | `doubao-seed-1-6-250615` | `POST /chat/completions`（OpenAI 兼容，function calling） |
| 图像（角色/场景/首帧） | `doubao-seedream-4-0-250828` | `POST /images/generations` |
| 视频（分镜出片） | `doubao-seedance-1-0-pro-250528` | `POST /contents/generations/tasks`（异步任务轮询） |

成本看板按设置页单价本地估算（对话按 token、图按张、视频按秒），请按你实际开通的价格调整。

## 把青鸾接给 Agent（三种方式）

工作台「Agent 接入」页有可复制的现成命令与 Token。19 个开放工具覆盖全部能力：
`studio_overview / create_project / update_project / generate_script / add_episode / write_script / parse_script /
list_styles / get_canvas / update_node / generate_image / generate_video / generate_storyboard_media /
get_task / list_assets / import_asset / list_projects / get_project / get_usage_stats`。

### ① MCP（推荐，零依赖 stdio 服务器）

```bash
# Claude Code（先启动青鸾服务）
claude mcp add qingluan \
  --env QINGLUAN_BASE=http://localhost:4399 \
  --env QINGLUAN_TOKEN=<设置页的 Agent Token> \
  -- node /绝对路径/qingluan/mcp/server.mjs
```

Cursor / Cherry Studio 等通用 MCP 客户端：

```json
{
  "mcpServers": {
    "qingluan": {
      "command": "node",
      "args": ["/绝对路径/qingluan/mcp/server.mjs"],
      "env": { "QINGLUAN_BASE": "http://localhost:4399", "QINGLUAN_TOKEN": "<Token>" }
    }
  }
}
```

**远程/云端个人助理（OpenClaw、Hermes Agent、`claude mcp add --transport http` 等）**
用 HTTP 版 MCP，不需要在助理所在机器起进程，URL + Token 即接入：

```json
{
  "mcpServers": {
    "qingluan": {
      "url": "http://<青鸾地址>:4399/api/agent/v1/mcp",
      "headers": { "Authorization": "Bearer <Token>" }
    }
  }
}
```

（实现为 MCP Streamable HTTP 传输的无状态精简版：POST 单条/批量 JSON-RPC，通知返回 202。）

接入后直接对 Agent 说：*「用青鸾创建一个都市逆袭短剧，写好剧本解析分镜，把图和视频都生成出来」*。

### ② HTTP API（任意语言）

```bash
curl -X POST http://localhost:4399/api/agent/v1/tools/generate_script \
  -H "Authorization: Bearer <Token>" -H "Content-Type: application/json" \
  -d '{"idea":"外卖小哥捡到一张黑卡","genre":"都市逆袭"}'
```

- 端点：`POST /api/agent/v1/tools/{工具名}`，统一返回 `{ok, data:{result}}`；MCP HTTP 端点 `POST /api/agent/v1/mcp`
- 发现：`GET /api/agent/v1/tools`（工具 schema）、`GET /api/agent/v1/openapi.json`（OpenAPI 3.1，免鉴权）
- 审计：`GET /api/agent/v1/logs`；Token 在设置页可一键重置

### ③ 内置创作 Agent

每个项目工作台与「Agent 接入」页自带对话框：配置方舟 Key 后为**大模型函数调用循环**
（与 MCP 同一套工具）；未配置时为本地意图规则，演示主流程同样可走通。

## 架构

```
qingluan/
├ server/            Node 22 零依赖服务端（node:sqlite / fetch / http）
│  ├ lib/ark.js      方舟客户端（chat + images + video 任务，结果自动落盘）
│  ├ lib/local.js    本地引擎（模板剧本/规则解析/生成式 SVG/SMIL 动画视频）
│  ├ lib/pipeline.js 创作流水线（剧本→分镜→画布→图像→视频，方舟失败自动兜底）
│  ├ lib/tools.js    Agent 工具注册表（MCP / HTTP / 内置 Agent 三方共用）
│  ├ lib/styles.js   风格库（30 预设 ×4 分类，注入生图/生视频提示词）
│  └ routes/         REST：工作台 / AI / Agent API（Bearer Token + CORS）
├ web/               原生 ES Modules 前端（零构建）
│  └ js/flow/        手写节点图引擎（平移/缩放/拖拽/连线/选择）
├ mcp/server.mjs     MCP stdio 服务器（零依赖 JSON-RPC）
└ scripts/smoke.mjs  57 项冒烟测试
```

数据存仓库 `var/`（已 gitignore）：`qingluan.sqlite` + `qingluan-uploads/`。
与主应用「AI句灵」互不影响，可同时运行（端口 3000 / 4399）。

## FAQ

- **方舟接口报错？** 设置页「测试连接」看具体报错；确认模型已在控制台开通、Key 未过期。
  模型 ID 以[官方文档](https://www.volcengine.com/docs/82379)为准，随时可在设置页替换。
- **视频一直转圈？** 方舟 Seedance 任务一般 1-3 分钟；画布每 3 秒轮询自动回填。本地模式数秒完成。
- **Token 泄露了？** 「Agent 接入」页或设置页一键重置，旧 Token 立即失效。
- **想公网部署？** 反代到 4399 即可；Agent API 自带 Token 鉴权与 CORS，工作台本身无登录，
  公网部署请放到内网或加一层 BasicAuth。
