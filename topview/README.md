# 爆款工厂 · AI 电商带货视频

> 对标 [TopView.ai](https://www.topview.ai/) 的**电商带货广告**生成工具，独立小应用：
> **商品链接 / 商品信息 → AI 广告脚本 → 出图 / 出片 → 配音 → 多语言字幕**，
> 火山方舟（豆包 / Seedream / Seedance）或任意 OpenAI 兼容端点驱动，
> 全部能力以 **MCP + OpenAPI** 开放给任意 Agent。**不配 Key 也能用本地引擎跑通全流程。**

## 一键运行（零依赖）

只需要 **Node.js ≥ 22.5**（内置 `node:sqlite` / `fetch`），不需要 `npm install`：

```bash
npm run topview            # 在仓库根目录执行
# 🛍  工作台      http://localhost:4499
# 🤖 Agent API   http://localhost:4499/api/agent/v1/openapi.json

npm run topview:smoke      # 32 项全链路冒烟（商品解析 + API + Agent + MCP stdio/HTTP）
npm run topview:dev        # 开发模式（文件变更自动重启）
```

**默认本地引擎模式**：不配置任何模型 Key，所有能力（脚本/出图/出片/翻译）自动落到本地规则引擎，
产出生成式 SVG 占位图与 SMIL 动画占位片，界面明确标注「本地生成」，成本为 0。
配置火山方舟 Key 后自动切换为真实大模型与图像/视频生成。

## 对标 TopView 的功能

| TopView 能力 | 本应用 |
|---|---|
| **URL → 视频**（商品页→广告片） | ✅ `product_to_video`：抓取公开 OG/JSON-LD（标题/主图/价格/卖点）→ 广告分镜 |
| **AI UGC / 数字人口播** | ✅ `kind=ugc` + 口播套路（测评/痛点-方案/开箱/口播/卖点），数字人剪影占位 + 浏览器朗读 |
| **广告脚本生成** | ✅ 5 种套路 × 钩子→痛点→卖点→信任→促单，LLM 生成 / 本地规则兜底 |
| **AI 配音 Voiceover** | ✅ 浏览器语音合成朗读口播（零成本），放映室按分镜时长同步 |
| **视频翻译 / 多语言本地化** | ✅ `localize_project`：字幕/口播翻译 + 分语言 SRT（对标 29 语言，已内置 15 种） |
| **画面 / 商品图** | ✅ Seedream / gpt-image-1 出图；本地出商品卡占位图 |
| **图生视频** | ✅ Seedance 异步任务（`get_task` 轮询）；本地出 SMIL 占位片 |
| **OpenAPI / 多模型** | ✅ OpenAPI 3.1 + MCP（stdio/HTTP）+ 15 个开放工具，**免费开放** |

> 路线图（下一步，见仓库 `docs/TOPVIEW-BENCHMARK.md`）：接真实数字人/对口型（火山 OmniHuman / 阿里 EMO / HeyGen）、
> 声音克隆、商品摄影 / 虚拟试穿 / 换角色 / 放大 / 运动控制等图像视频编辑原语。

## 创作流程

1. **首页创作框**：① 贴商品链接（或②手填标题/品牌/价格/卖点）→ 选脚本套路、形态（广告片 / 数字人口播）、
   画幅、语言、单镜时长 → 「一键成片」生成广告分镜脚本。
2. **项目页**：查看分镜（钩子/痛点/卖点/信任/促单 + 屏幕字幕 + 口播 + 画面提示）；
   「生成画面+视频」逐镜出图出片；「放映室」按分镜连播（字幕 + 浏览器口播）；
   「重写脚本」换套路；「多语言本地化」选目标语言生成分语言 SRT，一键导出。
3. **Agent**：所有能力同时以 MCP / HTTP / OpenAPI 暴露（见「设置」页的 Token 与接入命令）。

## 模型接入（可选）

到[火山方舟控制台](https://console.volcengine.com/ark)的「API Key 管理」创建 **UUID 形态** 的 Key
（`AKLT` 开头的 AccessKey 不能用），在「设置」页粘贴或配置 `.env` 的 `ARK_API_KEY`：

| 用途 | 默认模型 ID | 接口 |
|---|---|---|
| 脚本 / 翻译 | `doubao-seed-1-6-250615` | `POST /chat/completions`（OpenAI 兼容） |
| 图像 | `doubao-seedream-4-0-250828` | `POST /images/generations` |
| 视频 | `doubao-seedance-1-0-pro-250528` | `POST /contents/generations/tasks`（异步轮询） |

也可配 `OPENAI_API_KEY`，把图像模型设为 `gpt-image-1` 走 OpenAI 出图。成本按设置页单价本地估算。

## 接给 Agent（MCP）

```bash
# Claude Code（先启动服务）
claude mcp add topview \
  --env TOPVIEW_TOKEN=<设置页的 Agent Token> \
  -- node /绝对路径/topview/mcp/server.mjs
```

远端助理用 HTTP 版 MCP：`{ "url": "http://<地址>:4499/api/agent/v1/mcp", "headers": { "Authorization": "Bearer <Token>" } }`。

**15 个开放工具**：`studio_overview · list_tones_styles · list_projects · get_project · scrape_product ·
create_ad · product_to_video · generate_ugc_script · generate_media · get_task · generate_dubbing ·
localize_project · export_srt · list_assets · get_usage_stats`。

## 技术架构

```
topview/
├ server/
│  ├ index.js            零依赖 HTTP 服务（node:sqlite / fetch / http）
│  ├ schema.sql          projects / assets / tasks / localizations / usage_logs / agent_logs
│  ├ lib/
│  │  ├ commerce.js      商品页解析（公开 OG/JSON-LD，parseProductHtml 纯函数）
│  │  ├ adscript.js      广告脚本引擎（套路库 + 风格库 + LLM/本地兜底）
│  │  ├ i18n.js          多语言翻译 + 分语言 SRT
│  │  ├ pipeline.js      商品→脚本→画面/视频→配音→本地化→导出
│  │  ├ llm.js           模型客户端（对话/图/视频 + 记账 + 落盘）
│  │  ├ local.js         本地兜底（商品卡 SVG / SMIL 占位片）
│  │  └ tools.js         Agent 工具注册表（HTTP + MCP 共用）
│  └ routes/             studio（Web REST）+ agent（Agent API / MCP-HTTP / OpenAPI）
├ web/                   工作台 H5（原生 ES Module，零构建）
├ mcp/server.mjs         MCP stdio 服务器
└ scripts/smoke.mjs      32 项冒烟测试
```

## 合规提示

- 商品抓取**仅读取公开页面**的 OG/JSON-LD，不做登录态抓取、不绕过反爬；抓不到时回退手填。
- 引入真实**数字人/对口型**能力时需补「肖像授权 + 深度合成显著标识」。
- AI 生成内容已带「本地生成 / 预览」标识；商用投放请遵守各平台广告规范与《生成式 AI 服务管理办法》。
