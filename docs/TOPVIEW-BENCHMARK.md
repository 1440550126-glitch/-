# TopView.ai 全功能对标 & 灵境AI 实现路线图

> 目标：把 [TopView.ai](https://www.topview.ai/) 的**所有功能**逐项拆开，对照仓库里
> [`lingjing/`（灵境AI · 短剧创作工坊）](../lingjing/README.md) 已有的能力，标出缺口，并给出
> **对齐现有架构**（零依赖 Node + 无 Key 本地兜底 + Provider 抽象 + Agent 工具 + 冒烟测试）的
> 落地路线图。本轮只产出本文档，不动功能代码。

---

## 0. 定位差异（先看这个）

| | TopView.ai | 灵境AI（现仓库） |
|---|---|---|
| 定位 | **电商带货 / 营销广告** AI 视频 Agent | **影视短剧 / 长片** AI 创作工坊 |
| 输入起点 | 商品链接 / 商品图 / 卖点 → 广告片 | 一句话创意 / 剧本 → 成片 |
| 招牌能力 | URL→视频、AI UGC 数字人口播、多语言本地化 | 剧本→分镜→画布→出图→出片、主体一致性、爆款复刻 |
| 交付物 | TikTok/Reels/Meta 竖版广告、口播种草 | 横/竖屏短剧、分集连播、电影长片 |
| 开放性 | OpenAPI（一个 API 调所有模型），会员闭源 Skill | **MCP + OpenAPI + 内置 Agent 三通道全开放免费** |

**一句话结论**：灵境AI 已经把 TopView 的「**内容创作链路**」覆盖了大半（脚本→分镜→图→视频→配音→字幕→导出
+ 一致性 + 风格库 + 多模型 + Agent）。真正缺的是 TopView 赖以成名的「**电商带货广告层**」——
把商品变成广告片、数字人口播、和面向全球投放的多语言本地化，外加一批图像/视频**编辑原语**。

---

## 1. TopView.ai 全功能清单

按官网与第三方评测整理（来源见文末）。✅=灵境AI已有 · ⚠️=部分/可复用 · ❌=缺失。

### 1.1 AI 图像
| 功能 | 说明 | 灵境AI |
|---|---|---|
| 文生图 Text to Image | 提示词出图 | ✅ `generate_image`（Seedream/GPT Image/通义万相） |
| 图像编辑 Image Edit | 指令改图（带参考图） | ⚠️ 底层已具备（`openaiImage` 走 `images/edits`，Seedream 支持参考图），未做成独立工具 |
| 局部重绘 Inpaint | 框选区域重画 | ❌ |
| 换角色 Character Swap | 替换画面中人物 | ⚠️ 一致性引擎有「锁脸/换装」思路，无一键换角色 |
| 图像放大 Upscale | 超分辨率 | ❌ |
| 虚拟试穿 Virtual Try-on | 人物穿上指定服饰 | ❌ |
| 商品摄影 Product Photography | 产品图放进打光精修场景 | ❌ |

### 1.2 AI 视频
| 功能 | 说明 | 灵境AI |
|---|---|---|
| 图生视频 Image to Video | 首帧驱动成片 | ✅ `generate_video`（首帧自动引用一致性定妆图） |
| 文生视频 Text to Video | 纯文本出片 | ✅ |
| Omni Reference（Seedance 2.0） | 多主体参考一致 | ✅ `omni_reference_video`（Vidu 全能参考 + Seedance） |
| 首尾帧 / 一镜到底 | 首帧+尾帧自然过渡 | ✅ 创作框 `last_image_url` |
| 视频换角色 Video Character Swap | 替换片中人物 | ❌ |
| 视频放大 Video Upscale | 视频超分 | ❌ |
| 运动控制 Motion Control | 指定镜头/主体运动 | ⚠️ 提示词层面可写，无参数化控制 |
| **URL→视频 URL to Video** | 商品页（亚马逊/Shopify/速卖通…）→广告片 | ❌ **TopView 招牌** |

### 1.3 AI 数字人
| 功能 | 说明 | 灵境AI |
|---|---|---|
| AI 数字人（Avatar 4） | 真人形象口播，全身动作随语音 | ❌ |
| 商品数字人 Product Avatar | 数字人手持产品讲解 | ❌ |
| 自定义数字人 Design My Avatar | 上传/生成专属形象 | ⚠️ 有角色定妆图体系，可作形象来源 |
| 视频对口型 Video Lip-Sync | 任意人像跟随语音对口型 | ❌ |

### 1.4 AI 音频
| 功能 | 说明 | 灵境AI |
|---|---|---|
| AI 配音 Voiceover | 脚本→多语种自然语音 | ✅ `generate_dubbing`（火山 TTS，浏览器朗读兜底） |
| 即时声音克隆 Instant Voice Clone | 克隆参考音色，跨片统一品牌音 | ❌ |

### 1.5 上层产品 / 工作流
| 功能 | 说明 | 灵境AI |
|---|---|---|
| AI UGC 广告 | 数字人测评/种草，钩子/痛点-方案/开箱套路 | ❌（出片能力有，无 UGC 产品形态与脚本套路） |
| 无脸视频自动量产 | TikTok/Reels/Shorts 脚本+画面+配音一条龙 | ⚠️ 出片链路齐全，无「无脸口播」预设与批量投放格式 |
| **视频翻译 / 本地化** | 配音+字幕翻成 29 种语言 | ❌（配音/字幕都是单语） |
| 爆款分析 Agent V2 | 千万爆款库 + 多参考指令规划 | ⚠️ `remake_viral` 解析钩子/节奏/情绪曲线；内置 Agent v2 会先规划再调度（无爆款库） |
| AI 剪辑 | 改脚本/字幕/分镜/配音/格式不重出整片 | ✅ 项目工作台 + 画布逐节点编辑 + 任务中心重试/强制重出 |
| 脚本生成 | 商品链接/提示词→广告脚本 | ⚠️ `generate_script`/`remake_viral` 偏剧情，无「广告脚本」体裁 |
| OpenAPI | 一个 API 调所有视频/图像模型 | ✅ 已有 OpenAPI 3.1 + MCP（stdio/HTTP）+ 30+ 工具，且免费开放 |

---

## 2. 缺口汇总（要补的就这些）

按「招牌缺口」与「完整缺口」分两批，对应建设优先级。

**P1 · 招牌缺口（最能代表 TopView，建议先做）**
1. **商品 URL/信息 → 广告短片**（电商一键成片）
2. **AI UGC / 数字人口播模式**（口播测评 + 对口型）
3. **视频本地化**（多语言翻译 + 重新配音 + 分语言字幕）

**P2 · 完整缺口（图像/视频编辑原语）**
4. 商品摄影 Product Photography
5. 虚拟试穿 Virtual Try-on
6. 换角色 / 视频换角色 Character Swap
7. 图像/视频放大 Upscale
8. 运动控制 Motion Control
9. 局部重绘 Inpaint
10. 即时声音克隆 Voice Clone

---

## 3. 实现路线图（对齐现有架构）

落点文件均为现仓库真实文件。新增 Agent 工具一旦写进 `lingjing/server/lib/tools.js` 的 `TOOLS`
数组，即**自动**同时出现在 MCP（`mcp/server.mjs`）、HTTP（`/api/agent/v1`）、内置 Agent 三个通道，
并被 `/api/agent/v1/openapi.json` 暴露——这是现有设计，无需额外接线。

### 总原则（每个功能都遵守）
- **Provider 抽象**：仿 `providers.js` 的 `pickImageProvider/pickVideoProvider`，每个新能力都给
  「真实 Provider（需 Key）+ 本地兜底引擎（`lib/local.js`，无 Key 可演示）」两条路。
- **零依赖**：只用 Node ≥22.5 内置 `fetch/FormData/Blob/node:sqlite`；不新增 npm 依赖。
- **记账**：所有外部调用走 `logUsage(...)` 进 `usage_logs`，成本看板透明。
- **资产落盘**：外部返回 URL 一律 `downloadToUploads` 落本地（方舟/各家 URL 有时效）。
- **冒烟**：每个新工具在 `lingjing/scripts/smoke.mjs` 增链路用例（无 Key 走本地兜底也要绿）。

---

### P1-1　商品 URL/信息 → 广告短片
**产品形态**：首页万能创作框新增「**电商带货**」模式：贴商品链接或手填（标题/卖点/图片/价格）→
解析卖点 → 生成广告脚本（钩子→卖点→促单 CTA）→ 复用现有解析/画布/出图/出片/配音链路成片。

**落点**
- 新建 `lingjing/server/lib/commerce.js`：
  - `scrapeProduct(url)`：零依赖 `fetch` 取 HTML + 正则/`<meta og:*>`/JSON-LD 抽 标题/主图/价格/要点；
    取不到就回退到「手填商品信息」。**不做登录态抓取**，只取公开页 OG 数据，避免合规风险。
  - `productToScript(product, {tone, lang, duration})`：LLM（`ark.js`）生成广告脚本，
    本地兜底用规则模板（钩子句库 + 卖点排列 + CTA）。
- `pipeline.js` 复用：`createProject(kind:'ad')` → `parseScript` → 画布 → `generateImage`/`createVideoTask` → `generateDubbing`。
- 数据模型：`projects` 表加 `kind TEXT DEFAULT 'drama'`（`drama|ad|ugc`）与 `product TEXT`（JSON：链接/卖点/图）。
- 路由：`routes/studio.js` 加 `POST /api/studio/commerce/parse` 与 `.../commerce/script`。
- UI：`web/js/pages/home.js` 创作框加「电商带货」tab + 链接输入框。

**Agent 工具（新增）**：`scrape_product`、`product_to_video`（一步到位：URL→项目+脚本+分镜）。

**验收**：贴一个商品页（或手填）→ 30 秒内得到带卖点的竖版广告脚本与分镜；无 Key 时本地模板出占位片。

---

### P1-2　AI UGC / 数字人口播
**产品形态**：新增「**UGC 口播**」模式——选/传一个数字人形象 → 生成口播脚本（测评/痛点-方案/开箱）→
TTS 配音 → **对口型**驱动形象说话 → 竖版成片。`商品数字人` = 形象 + 手持产品图参考。

**落点**
- `providers.js` 增 `avatarProviderOf` + `pickAvatarProvider`，候选真实 Provider：
  火山 **OmniHuman**、阿里 **EMO**、HeyGen、D-ID（任选其一接入，URL+Key 形态）。
  本地兜底：用现有 SVG/SMIL 引擎画「会动的口播占位形象 + 字幕条」（`lib/local.js`）。
- 新建 `lingjing/server/lib/avatar.js`：`createLipsyncTask({imageUrl, audioUrl})` + `pollTask` 接入既有任务表
  （`tasks.kind` 增 `'avatar'`）。
- 脚本套路库：`lib/styles.js` 旁新增 `ad-scripts.js`（hook / testimonial / problem-solution / unboxing 模板）。

**Agent 工具（新增）**：`generate_ugc_script`、`generate_avatar_video`（形象+脚本→口播片）。

**验收**：选形象 + 一句卖点 → 出 15s 竖版口播；无 Key 走本地口播占位 + 系统朗读。

---

### P1-3　视频本地化（多语言）
**产品形态**：项目工作台「本地化」按钮：选目标语言（对标 TopView 的 29 种）→ 翻译台词/字幕 →
重新 TTS 配音 → 生成**分语言 SRT** → 放映室可切语言。

**落点**
- `lib/export.js` 已能生成 SRT（按分镜时长排时间轴），扩成 `buildSrt(shots, {lang})` 多语言版本。
- 新建 `lib/i18n.js`：`translateShots(shots, targetLang)`（LLM 翻译，保留时间轴/角色名占位；
  本地兜底走「不翻译 + 标注待译」或内置常用词表）。
- 复用 `generateDubbing` 按目标语言重配音（`tts.js` 传 language/voice 参数）。
- 数据：每集/每语言的配音与字幕作为 `assets` 入库（`name` 带语言后缀）。

**Agent 工具（新增）**：`localize_project`（project_id + langs[] → 各语言字幕+配音）。

**验收**：一个中文项目一键产出英/日/西 三语 SRT + 配音；无 Key 时字幕透传并标注「待翻译」。

---

### P2 · 编辑原语（第二批，逐个独立工具，复用 Provider 抽象）

| 功能 | 落点 / Provider | 新增 Agent 工具 | 本地兜底 |
|---|---|---|---|
| 商品摄影 Product Photography | `commerce.js`；Seedream 参考图 / `gpt-image-1` edits（已通） | `product_photo` | 规则合成：产品图 + 渐变打光背景 SVG |
| 虚拟试穿 Virtual Try-on | Seedream/通义万相 参考图编辑 | `virtual_tryon` | 占位：人像+服饰拼贴标注 |
| 换角色 Character Swap（图/视频） | 参考图编辑 / 视频重绘 Provider | `character_swap` | 占位说明 + 一致性引擎换装路径 |
| 放大 Upscale（图/视频） | Real-ESRGAN 类 Provider；本地 ffmpeg `scale` | `upscale` | 有 ffmpeg 时本地放大，否则原样返回 |
| 运动控制 Motion Control | Seedance/Vidu 运动参数（`movement_amplitude` 已在 Vidu 用到） | 扩 `generate_video` 加 `motion` 参数 | 提示词注入运动描述 |
| 局部重绘 Inpaint | `gpt-image-1` edits + mask / Seedream | `inpaint` | 占位：标注重绘区域 |
| 声音克隆 Voice Clone | 火山声音复刻 / MiniMax / 本地 CosyVoice | `clone_voice` + `generate_dubbing` 传 voice_id | 兜底用既有预设音色 |

> 说明：`gpt-image-1` 的 `images/edits` 多部分表单**已在 `providers.js:openaiImage` 实现**，
> 商品摄影/试穿/Inpaint 可直接复用这条已验证的通路，工作量主要在「构造 mask/参考图 + 包一层工具」。

---

## 4. 不做 / 已具备（避免重复造轮子）
- **OpenAPI / 多模型 / Agent 三通道**：已有且更开放，无需照搬 TopView 闭源 Skill。
- **AI 剪辑 / 任务重试 / 回收站 / 成本看板**：已有，TopView 的「编辑工作流」灵境AI 用画布+任务中心覆盖。
- **水印**：灵境AI `watermark` 开关自控，不跟会员走。
- **合规**：AI 生成内容标识、深度合成备案、未成年人保护见 [COMPLIANCE.md](COMPLIANCE.md)；
  **数字人/换脸**新增能力需补「肖像授权 + 深度合成显著标识」，路线图实现时同步加。
- **爆款库（千万视频）**：版权与数据成本高，暂以 `remake_viral`（贴参考解析）替代，不抓取建库。

---

## 5. 附录

### 5.1 现有 Agent 工具（32 个，`tools.js`）
`studio_overview · list_projects · create_project · get_project · update_project · list_styles ·
write_script · generate_script · remake_viral · add_episode · parse_script · list_assets ·
import_asset · generate_image · generate_expressions · generate_video · generate_dubbing ·
get_task · get_canvas · update_node · check_consistency · get_character_profile · list_entities ·
list_expressions · omni_reference_script · storyboard_sheet · omni_reference_video ·
annotate_entities · generate_storyboard_media · run_workflow · get_workflow · get_usage_stats`

路线图将再新增约 11 个：`scrape_product · product_to_video · generate_ugc_script ·
generate_avatar_video · localize_project · product_photo · virtual_tryon · character_swap ·
upscale · inpaint · clone_voice`。

### 5.2 Provider 矩阵（现状）
| 能力 | 火山方舟 | OpenAI | Google | 阿里通义万相 | Vidu | 本地兜底 |
|---|---|---|---|---|---|---|
| 对话/脚本 | ✅ doubao-seed | — | — | — | — | ✅ 规则引擎 |
| 图像 | ✅ Seedream 4.0 | ✅ gpt-image-1 | — | ✅ wanx/qwen-image | — | ✅ SVG 占位 |
| 视频 | ✅ Seedance | — | ✅ Veo 3 | ✅ wanx i2v/t2v | ✅ 全能参考 | ✅ SMIL 占位 |
| 配音 | ✅ 语音合成 | — | — | — | — | ✅ 浏览器朗读 |
| 数字人/对口型 | 🔲 OmniHuman（待接） | — | — | 🔲 EMO（待接） | — | 🔲 占位（待做） |

### 5.3 资料来源
- 官网：[topview.ai](https://www.topview.ai/) · [AI UGC](https://www.topview.ai/ai-ugc) ·
  [Product Avatar](https://www.topview.ai/ai-avatar/product-avatar) ·
  [AI Video Generator](https://www.topview.ai/ai-video-generator) · [OpenAPI](https://www.topview.ai/openapi)
- 评测：[vidmetoo](https://www.vidmetoo.com/topview-ai-review/) · [toolify](https://www.toolify.ai/tool/topview-ai) ·
  [aiapps](https://www.aiapps.com/items/topview/) · [futuretools](https://futuretools.io/tools/topview-ai)

### 5.4 对照实现进度
- [x] TopView 全功能盘点 + 灵境AI 对照（本文档）
- [ ] P1-1 商品 URL→广告短片
- [ ] P1-2 AI UGC / 数字人口播
- [ ] P1-3 视频本地化（多语言）
- [ ] P2 编辑原语（商品摄影/试穿/换角色/放大/运动控制/Inpaint/声音克隆）
