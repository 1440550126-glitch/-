# 句灵｜让文案活过来

这是一个可直接导入微信开发者工具的微信小程序 MVP。项目采用 **Canvas 2D + Animation Manifest + 本地优先数据层 + 云函数实现**：开发预览时无需后端即可完整体验发布、长按动画、点赞、评论、回复、分享、收藏、热门榜与 AI 暖场；接入正式云开发环境后，可部署 `cloudfunctions/` 内的云函数并把集合名称按 README 的数据库设计创建。

## 一键运行

1. 打开微信开发者工具。
2. 选择“导入项目”，目录选择本仓库根目录。
3. AppID 可先使用测试号或替换 `project.config.json` 中的 `appid`。
4. 编译后进入“句灵广场”，长按任意文案生命卡即可播放 Manifest 驱动的线条动画与时间轴音效。

## 核心代码路径

- `app.js`：初始化云开发与本地种子数据。
- `app.json`：页面、导航栏与 tabBar 配置。
- `utils/aiParser.js`：文案语义、情绪、场景、对象、动作、声音、预览图参数和 Animation Manifest 生成。
- `utils/motionEngine.js`：Canvas 2D 线条动画引擎，包含人物、风、雨、雪、心、海浪、云、猫、光点等绘制与时间轴动作。
- `utils/audioEngine.js`：微信小程序音频引擎，按 timeline 精准触发音效、循环环境音与淡出。
- `utils/moderation.js`：关键词 + 模拟 AI 审核，自伤风险进入审核提示。
- `utils/db.js`：本地优先数据层，完整实现信息流、发布、点赞、评论、回复、分享、收藏、播放计数、热门排序与 AI 暖场。
- `components/living-card/`：文案生命卡组件，负责预览图、长按触发、互动按钮。
- `components/line-animation-canvas/`：Canvas 动画播放器组件，按 Manifest 渲染。
- `components/comment-list/`：评论与回复入口组件。
- `pages/index/`：信息流首页。
- `pages/create/`：发布文案与生成预览页。
- `pages/detail/`：详情页、Manifest 解释与评论区。
- `pages/profile/`：用户主页。
- `pages/hot/`：热门榜。
- `cloudfunctions/`：云开发函数，覆盖解析、预览、Manifest、发布、信息流、点赞、评论、回复、分享、收藏、AI 暖场与审核。
- `assets/sounds/`：音效占位文件；上线时替换为真实 mp3 文件名即可。

## 数据库集合

建议创建以下云开发集合：`posts`、`comments`、`users`、`likes`、`collects`、`follows`、`shares`、`ai_warmup_logs`。

## 产品原则落地

`utils/aiParser.js` 不直接随机生成动画，而是建立“文案语义 → 情绪/场景 → 视觉对象 → 动作 → 声音”的映射。例如文案中出现“雨”，Manifest 会包含 `rain` 元素、`rain_fall_to_stop` 动作与 `rain_soft` 声音；出现“等/原地/站”，会包含 `line_person` 与 `idle_waiting`；出现“心/你”，会包含心跳线与心跳音效。
