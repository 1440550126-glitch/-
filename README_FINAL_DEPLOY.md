# LingMirror AI 最终可落地部署说明

这是 LingMirror AI / 灵镜 AI 的可部署 Node.js 后端 + 静态前端版本。生产目标：Nginx 对外提供 `public/`，`/api/` 反代到只监听 `127.0.0.1:3001` 的 Node API。

## 1. 服务器准备

推荐 Ubuntu 22.04/24.04：

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm sqlite3 nginx rsync ca-certificates
```

## 2. 一键部署到 `/var/www/lingmirror`

在项目根目录执行：

```bash
sudo APP_DIR=/var/www/lingmirror DOMAIN=lingmirror.com.cn bash scripts/bootstrap-production.sh
```

脚本会：

- 安装 Node/npm/sqlite3/nginx/rsync
- 同步项目到 `/var/www/lingmirror`
- 首次部署自动生成 `.env`、`JWT_SECRET`、`ADMIN_PASSWORD`
- 执行 `npm install --omit=dev`
- 执行 `npm run migrate`
- 安装 systemd 服务 `lingmirror`
- 安装 Nginx 配置并反代 `/api/`
- 检查 `http://127.0.0.1:3001/health`

## 3. 手动部署

```bash
sudo mkdir -p /var/www/lingmirror
sudo rsync -a --delete --exclude='.git' --exclude='node_modules' ./ /var/www/lingmirror/
cd /var/www/lingmirror
cp .env.example .env
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"   # 填 JWT_SECRET
node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))" # 填 ADMIN_PASSWORD
npm install --omit=dev
npm run migrate
npm run preflight
npm run start
```

## 4. 真实 API 开关

`.env` 中：

```env
ENABLE_REAL_API=true
VOLCENGINE_ENABLE_TEXT=true
VOLCENGINE_ENABLE_VISION=true
VOLCENGINE_ENABLE_EMBEDDING=true
VOLCENGINE_ENABLE_VIDEO=false
VOLCENGINE_ARK_API_KEY=只放服务器.env里
```

上线顺序：

1. 先让 `VOLCENGINE_ENABLE_TEXT=true`，测试 Copy Lab 和 Product Ads 文本。
2. 再测试剧本分析、Visual Bible、Memory Anchor 摘要。
3. paid_balance、预算和成本日志确认无误后，才打开 `VOLCENGINE_ENABLE_VIDEO=true`。
4. 视频真实调用会先做 paid balance、预算、provider balance、Seedance payload 校验和 frozen balance。

## 5. 健康检查与烟测

启动后执行：

```bash
curl http://127.0.0.1:3001/health
BASE_URL=http://127.0.0.1:3001 bash scripts/smoke-test.sh
```

## 6. 打包交付

```bash
bash scripts/package-release.sh
```

输出：

```text
release/lingmirror-ai.tar.gz
release/lingmirror-ai.zip
```

## 7. Nginx / systemd

模板已放在：

```text
ops/nginx/lingmirror.conf
ops/systemd/lingmirror.service
```

生产部署后：

```bash
sudo systemctl status lingmirror
sudo journalctl -u lingmirror -n 100 --no-pager
sudo nginx -t
```

## 8. 安全

- `.env` 已被 `.gitignore` 排除。
- 不要把 `VOLCENGINE_ARK_API_KEY`、`PAYPAL_CLIENT_SECRET`、`GOOGLE_CLIENT_SECRET`、`ALIPAY_PRIVATE_KEY`、`JWT_SECRET`、`ADMIN_PASSWORD` 写入前端或 Git。
- 日志只允许打码显示密钥。
- 免费用户不能直接烧真实视频；真实视频任务优先检查 `paid_balance`。
