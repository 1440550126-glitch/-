# 部署手册 — AI句灵 / 灵阵（jvling）

零依赖 Node 22 服务端，**无构建步骤**：拉代码 → 配 `.env` → systemd 跑起来 → 反代加 HTTPS。
数据库是单文件 SQLite（`var/jvling.sqlite`，首次启动自动建表）。

整套大约 10 分钟。下面以 Ubuntu/Debian + systemd 为例；`<尖括号>` 是你要替换的值。

---

## 快速：一键脚本（Ubuntu/Debian）
```bash
sudo mkdir -p /opt/jvling && sudo chown $USER /opt/jvling
git clone <你的仓库地址> /opt/jvling && cd /opt/jvling
git checkout claude/gracious-ride-p4z988      # 或先合并到 main 再部署 main
sudo bash deploy/bootstrap.sh                 # 答：管理员账号/密码、可选平台大模型 Key
```
脚本会装 Node 22（如缺）、建运行用户、生成 `.env`（含随机 APP_SECRET）、装 systemd 服务、起服务、健康检查。
**做完只剩反代+HTTPS 一步**（见下方第 4 步，Caddy 最省事）。想手动逐步来就看下面完整流程。

---

## 0. 前置
- 一台 Linux 服务器（1C1G 起步够用），有 sudo。
- 一个域名，A 记录指向服务器 IP（用 HTTPS 强烈建议）。
- **Node ≥ 22.5**（本项目用内置 `node:sqlite`，必须 22.5+）。检查：`node -v`。
  没有就装：
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
  ```

## 1. 取代码
```bash
sudo mkdir -p /opt/jvling && sudo chown $USER /opt/jvling
git clone <你的仓库地址> /opt/jvling
cd /opt/jvling
# 若还在功能分支，先切过去（或先在 GitHub 合并到 main 再部署 main）
git checkout claude/gracious-ride-p4z988
npm run check    # 语法自检：应输出「✅ … 语法全部通过」
```

## 2. 配 `.env`（关键）
```bash
cp .env.example .env
nano .env
```
**生产至少改这几项**（其余留空即可，详见 `.env.example` 注释）：
```ini
PORT=3000
NODE_ENV=production
APP_SECRET=<一串随机长字符串，例如 openssl rand -hex 32>
ADMIN_USERNAME=<管理员账号>
ADMIN_PASSWORD=<强密码，务必改掉默认值>
```
**大模型（二选一经营模式）**：
- 想让订阅用户「省心模式」开箱即用 → 填平台公共 Key（成本你担、按额度封顶）：
  ```ini
  LLM_PROVIDER=doubao
  LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
  LLM_API_KEY=<你的方舟 API Key>
  LLM_MODEL_DEFAULT=doubao-seed-1-6-flash-250615
  LLM_MODEL_PREMIUM=doubao-seed-1-6-250615
  ```
  配好后跑 `node scripts/llm-test.mjs` 一键连通自检（401/404/429 都有人话提示）。
- 想纯 BYOK（平台不出模型钱，用户各填各的 Key）→ 上面留空即可。

> `.env` 已在 `.gitignore` 里，永不进仓库；密钥只在服务端、不下发前端、自带 Key 加密落库。

## 3. 起服务（systemd）
```bash
sudo useradd --system --no-create-home jvling 2>/dev/null || true
sudo chown -R jvling:jvling /opt/jvling
sudo cp deploy/jvling.service /etc/systemd/system/jvling.service
# 按需改 service 里的 User / WorkingDirectory / node 路径（which node）
sudo systemctl daemon-reload
sudo systemctl enable --now jvling
systemctl status jvling --no-pager        # 看到 active (running)
curl -fsS http://localhost:3000/api/health # {"status":"ok",...}
```

## 4. 反代 + HTTPS（二选一）

### A. Caddy（最省事，自动签发/续期 HTTPS，推荐）
```bash
# 安装 Caddy 见 https://caddyserver.com/docs/install
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/your-domain.com/<你的域名>/' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### B. Nginx + certbot
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/jvling
sudo sed -i 's/your-domain.com/<你的域名>/' /etc/nginx/sites-available/jvling
sudo ln -s /etc/nginx/sites-available/jvling /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d <你的域名>      # 签发 HTTPS
```
> ⚠ 反代**必须关掉缓冲**（两份配置都已设好）：作战室是 SSE 实时直播，开了 `proxy_buffering` 会卡住不出字。

## 5. 验收
- 打开 `https://<你的域名>/lingzhen` → 灵阵独立站登录页（不是白屏）。
- 游客一键进入 → 选团队 → 派单 → 作战室能实时刷出协作步骤（SSE 通了）。
- 管理后台 `https://<你的域名>/admin`，用 `.env` 里的管理员账号登录。

## 6. 更新 / 回滚
```bash
cd /opt/jvling && bash deploy/deploy.sh     # 拉新代码 → 语法检查 → 重启 → 健康检查
# 回滚：git checkout <上个好用的 commit> && sudo systemctl restart jvling
```

## 7. 备份（就一个文件）
```bash
# SQLite 在线备份（WAL 模式，热备安全）
sqlite3 /opt/jvling/var/jvling.sqlite ".backup '/root/jvling-$(date +%F).bak'"
# 建议加 cron 每日跑一次 + 异地保存
```

## 备注
- `cwc-long-running-agents/`、`.claude/`、`screenshots/`、`scripts/` 是开发/质量用，**生产不依赖**，留着无害。
- 出网：若启用平台大模型，确保服务器能访问对应模型域名（如 `ark.cn-beijing.volces.com`）。
- 端口：服务只监听 `3000`，对外只暴露 80/443 给反代；防火墙别直接开 3000。
