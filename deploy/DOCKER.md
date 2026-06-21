# 在 LingMirror 香港服务器部署 Agent（/opt/agent · 3003 · Docker · Caddy）

> 我无法远程登录你的服务器，下面是你在服务器上**复制粘贴即可**的步骤。每一步都不碰
> `/opt/lingmirror`、`/opt/video`、`/opt/music`，不占用 80/443/3000/3001/3002。

## 1. 取代码到 /opt/agent
```bash
sudo mkdir -p /opt/agent && sudo chown $USER /opt/agent
git clone <你的仓库地址> /opt/agent && cd /opt/agent
git checkout claude/gracious-ride-p4z988   # 或先合并到 main
mkdir -p data logs                          # SQLite 与日志的持久化目录
```

## 2. 配置 .env（所有 Key 放这里，不写死）
```bash
cp .env.example .env && nano .env
```
至少设置：
```ini
PORT=3003
NODE_ENV=production
APP_SECRET=<openssl rand -hex 32 生成>
ADMIN_USERNAME=<管理员账号>
ADMIN_PASSWORD=<强密码>
# 平台大模型（可选；想让用户免配置直接用就填，否则留空 = 纯 BYOK 用户各自带 Key）
# 任意 OpenAI 兼容端点：火山方舟 / DeepSeek / Qwen / GLM / 百炼 / OpenRouter / Ollama / 自定义
# LLM_PROVIDER=doubao
# LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# LLM_API_KEY=<key>
# LLM_MODEL_DEFAULT=doubao-seed-1-6-flash-250615
# LLM_MODEL_PREMIUM=doubao-seed-1-6-250615
```

## 3. 起容器
```bash
docker compose up -d --build
docker compose ps          # 等到 STATUS 显示 healthy（约 10~20s）
docker compose logs -f     # 看启动日志；也会落到 ./logs/agent.log
curl -fsS http://127.0.0.1:3003/api/health   # {"status":"ok",...}
```

## 4. Caddy 反代 + HTTPS（不动其它站点）
把 `deploy/caddy-agent.conf` 的块追加到你的 Caddyfile，然后重载：
```bash
cat /opt/agent/deploy/caddy-agent.conf | sudo tee -a /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl -I https://agent.lingmirror.com.cn      # 应 200，证书自动签发
```

## 5. 更新 / 回滚
```bash
cd /opt/agent && git pull && docker compose up -d --build   # 更新
docker compose down                                          # 停
# 回滚：git checkout <上个好用的 commit> && docker compose up -d --build
```

## 数据 / 备份 / 日志
- 数据库：`/opt/agent/data/jvling.sqlite`（单文件，热备：`sqlite3 .../jvling.sqlite ".backup '/root/agent-$(date +%F).bak'"`）。
- 日志：`/opt/agent/logs/agent.log` + `docker compose logs`。
- **不需要** PostgreSQL / Redis / MinIO —— 本服务零依赖、用内置 SQLite。

---

## ⚠ 这个服务覆盖了你需求里的哪些（务必先对齐预期）
SoloCompany OS 是**零依赖 Node 22 + SQLite 的多智能体 Agent 平台**，覆盖你列表的一个**子集**：

**已具备**
- Agent 自动执行（多智能体团队：拆解→分派→产出→验收→不达标返工）
- 多模型调用：**OpenAI 兼容**统一接入（平台 Key + 用户 BYOK）——DeepSeek / Qwen / GLM /
  百炼 / 火山方舟 / OpenRouter / Ollama / 自定义 OpenAI API 均可；OpenAI 直连可；
  **Anthropic、Gemini 需用各自的 OpenAI 兼容端点或网关**（非原生多协议路由）
- 任务历史、定时任务调度、出站 Webhook、知识库(RAG)、对外 API（按 team 发 key）、后台管理
- API 网关（`/api/public/run` 同步调用）、密钥加密落库

**尚未具备（你的需求里有、但本代码库没有，别误以为有）**
- 可视化工作流节点编辑器（Node / 条件 / 循环 / 变量 / HTTP / 代码节点 Python·JS·Shell）
- PostgreSQL / Redis / MinIO、文件上传到对象存储、独立任务队列（现为内存内调度）
- Google / GitHub / PayPal OAuth 登录、钱包余额（现为用户名密码 + 游客 + 会员订阅）
- 原生「视频/音乐/图片/数字人」生成工作流（这些是 video./music. 等站点各自的能力，
  本服务只做 Agent 编排与 LLM 调用；要做成「全部经 Agent API 调用」需要再开发对接层）

> 也就是说：**可以现在就部署上线、当 LLM/Agent 编排中枢用**；但要成为你描述的那种
> n8n/Dify 级「可视化工作流引擎 + 多媒体生成中台」，是另一阶段的开发工作量。
