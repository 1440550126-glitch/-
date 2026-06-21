# PROGRESS — 灵阵 / AI句灵

> 每次会话先读本文件，再 `git log --oneline -10`，再跑一次冒烟确认从可用状态开始。
> 一次只做一项，做完（验证 + 截图）再开下一项。完成后更新本文件。

## Done（已交付，分支 claude/gracious-ride-p4z988）
- 灵阵独立站 `/lingzhen`：登录、团队广场/12智能体/8团队、作战室 SSE 直播、运行历史
- 知识库 RAG、对外 API、定时触发器、批量运行、团队记忆、出站 Webhook（飞书自动识别格式）
- 智能体工作室、草稿箱、团队项目空间活动流、新手首跑引导、结果公开分享
- 引擎：DoD 验收标准 + 验收官逐条核验 + 不达标自动返工；成员自检；RACI/工时；失败重试升级；交付含执行摘要/风险
- 商业化：包月订阅、Key 加密落库、会员到期提醒、用量看板
- 大模型：`.env` 自动加载；纯 BYOK + 省心模式（平台 Key）混合；BYOK 7 家可选
- 定价两档：自带Key版 ¥39 / 省心版 ¥99（平台模型仅省心版可用，已强制）
- 引入并初始化 Anthropic 长时运行 Agent Harness
- 修复定价改两档导致的 smoke 回归：`scripts/smoke.mjs` 两处过期断言（会员方案 3→2、订单 ¥9.9→自带Key版¥39）→ `npm run smoke` 168/0 全绿（证据 `screenshots/smoke-result.txt`，evaluator 复跑确认 PASS）
- 回归验证 lingzhen-loads + byok-two-tier → test-results.json 全绿。lingzhen：/lingzhen 带与不带尾斜杠均 app.js HTTP 200、SPA 启动（证据截图带 URL 标签 + lingzhen-loads-result.txt）；byok：两档强制差异化（byok-two-tier-result.txt）。evaluator 独立复核 PASS——其间逮到一次「两张截图字节相同」的弱证据、已重拍修正。
- 整站回归走查 lingzhen-regression：13 个主要页面逐页加载，关键选择器在场 + 0 JS 错误（screenshots/regression-result.txt + reg-01..13-*.png）。evaluator 抽看 5 页确认渲染正常、互异 → PASS。

- 部署套件 deploy/：DEPLOY.md 手册 + bootstrap.sh 一键脚本 + systemd 单元 + Caddy/nginx 反代（含 SSE 关缓冲）+ deploy.sh 更新脚本。已验证：脚本语法、生产模式启动无安全告警、/api/health 正常。
- 品牌改名：用户可见「灵阵」→「SoloCompany OS」（前端全量 + 飞书通知消息 + 关键词），副标题改「单人公司 · AI 团队」。内部目录/路由 lingzhen 与 /lingzhen 保留不动。check 59/59、smoke 168/0、登录页截图确认。
- 换 Logo：去掉 🛰 表情包，改为 lingzhen/logo.svg（渐变圆角 + 白色中枢-成员节点网络），用于 favicon/顶栏/登录/欢迎横幅。截图确认 img 加载渲染正常。团队/智能体头像仍用 emoji 头像系统（非品牌 logo，未动）。
- 新建团队默认头像 🛰 → 🤖（前端建队页/卡片/详情兜底 + 后端 POST /api/teams 默认）。smoke 168/0、建队页截图确认。

## In progress
- （空）

## Next（候选，未承诺）
- 价格后台可配（管理后台改价不改代码）
- 参照 harness 把后端「验收官/迭代」再打磨一版
- 注：季/年卡已随两档重构移除，「只包月」诉求实际已满足

## Notes
- 零依赖红线、CSP 无内联、密钥不提交——见 CLAUDE.md。
- 出网白名单受限：外部大模型可能不可直连，用本地 mock 验证接线。
- 验证四步：`npm run check` → `npm run smoke` → 一次性 `.mjs` 端到端 → Playwright 截图存 `screenshots/`。
- 教训：改 `server/lib/catalog.js` 定价/方案后，务必跑 `npm run smoke`——里面有 member_plans 数量与订单金额的硬断言。
