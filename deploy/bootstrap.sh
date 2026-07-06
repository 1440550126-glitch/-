#!/usr/bin/env bash
# 一键在本机部署 jvling（Ubuntu/Debian + systemd）。
# 用法：先 git clone 到 /opt/jvling（或任意目录），cd 进去，然后：
#       sudo bash deploy/bootstrap.sh
# 做完只剩「配反代+HTTPS」一步（见 deploy/DEPLOY.md 第 4 步，Caddy 最省事）。
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SVC=jvling
say(){ printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }

[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行：sudo bash deploy/bootstrap.sh"; exit 1; }

say "1/6 检查 Node ≥ 22.5"
need_node=1
if command -v node >/dev/null; then
  [ "$(node -e 'const[a,b]=process.versions.node.split(".").map(Number);process.stdout.write((a>22||(a===22&&b>=5))?"ok":"no")')" = ok ] && need_node=0
fi
if [ "$need_node" = 1 ]; then
  echo "安装 Node 22…"; curl -fsSL https://deb.nodesource.com/setup_22.x | bash -; apt-get install -y nodejs
fi
node -v

say "2/6 运行用户与目录权限"
id "$SVC" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$SVC"
mkdir -p "$APP_DIR/var"
chown -R "$SVC":"$SVC" "$APP_DIR"

say "3/6 语法自检"
sudo -u "$SVC" bash -c "cd '$APP_DIR' && npm run check"

if [ ! -f "$APP_DIR/.env" ]; then
  say "4/6 生成 .env"
  read -rp  "管理员用户名 [admin]: " ADMU; ADMU=${ADMU:-admin}
  read -rsp "管理员密码（必填）: " ADMP; echo
  [ -n "$ADMP" ] || { echo "管理员密码不能为空"; exit 1; }
  read -rp  "平台大模型 API Key（留空=纯 BYOK，用户各自带 Key）: " LKEY
  SECRET=$(node -e 'console.log(require("crypto").randomBytes(32).toString("hex"))')
  {
    echo "PORT=3000"
    echo "NODE_ENV=production"
    echo "APP_SECRET=$SECRET"
    echo "ADMIN_USERNAME=$ADMU"
    echo "ADMIN_PASSWORD=$ADMP"
    if [ -n "$LKEY" ]; then
      echo "LLM_PROVIDER=doubao"
      echo "LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3"
      echo "LLM_API_KEY=$LKEY"
      echo "LLM_MODEL_DEFAULT=doubao-seed-1-6-flash-250615"
      echo "LLM_MODEL_PREMIUM=doubao-seed-1-6-250615"
    fi
  } > "$APP_DIR/.env"
  chown "$SVC":"$SVC" "$APP_DIR/.env"; chmod 600 "$APP_DIR/.env"
else
  say "4/6 .env 已存在 → 跳过（如需改：编辑 $APP_DIR/.env 后 systemctl restart $SVC）"
fi

say "5/6 安装并启动 systemd 服务"
NODE_BIN=$(command -v node)
sed "s#^ExecStart=.*#ExecStart=$NODE_BIN --disable-warning=ExperimentalWarning server/index.js#; s#^WorkingDirectory=.*#WorkingDirectory=$APP_DIR#" \
    "$APP_DIR/deploy/jvling.service" > /etc/systemd/system/$SVC.service
systemctl daemon-reload
systemctl enable --now "$SVC"
sleep 2
systemctl --no-pager --lines=0 status "$SVC" | head -4 || true

say "6/6 健康检查"
if curl -fsS http://localhost:3000/api/health >/dev/null; then
  echo "✅ 服务已起：本机 http://localhost:3000 正常（/lingzhen 是灵阵独立站，/admin 是后台）"
  echo "▶ 最后一步：配反代 + HTTPS —— 见 deploy/DEPLOY.md 第 4 步（Caddy：两行配置自动签证书）"
else
  echo "❌ 健康检查失败 → journalctl -u $SVC -n 60 --no-pager"; exit 1
fi
