#!/usr/bin/env bash
# 在你的服务器上一键部署 Agent（Docker + Caddy + 真实验证）。
# 用法：git clone 到 /opt/agent 后 ——  cd /opt/agent && sudo bash deploy/agent-up.sh
# 幂等：可重复执行；不碰 80/443/3000/3001/3002，不动其它站点。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
DOMAIN="agent.lingmirror.com.cn"; PORT=3003; CADDYFILE="/etc/caddy/Caddyfile"
say(){ printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
die(){ printf '\n\033[1;31m✗ %s\033[0m\n' "$1"; exit 1; }

[ "$(id -u)" = 0 ] || die "请用 sudo 运行：sudo bash deploy/agent-up.sh"
command -v docker >/dev/null || die "未找到 docker"
docker compose version >/dev/null 2>&1 || die "未找到 docker compose v2"

say "1/6 准备持久化目录"
mkdir -p "$ROOT/data" "$ROOT/logs"

say "2/6 .env（密钥只落本机，不入镜像/仓库）"
if [ ! -f "$ROOT/.env" ]; then
  read -rp  "管理员用户名 [admin]: " ADMU </dev/tty; ADMU=${ADMU:-admin}
  read -rsp "管理员密码（必填）: " ADMP </dev/tty; echo
  [ -n "$ADMP" ] || die "管理员密码不能为空"
  read -rp  "大模型 API Key（留空 = 纯 BYOK，用户各自带）: " LKEY </dev/tty
  if [ -n "$LKEY" ]; then
    read -rp "base_url [https://ark.cn-beijing.volces.com/api/v3]: " LURL </dev/tty
    LURL=${LURL:-https://ark.cn-beijing.volces.com/api/v3}
    read -rp "默认模型 [doubao-seed-1-6-flash-250615]: " LMOD </dev/tty
    LMOD=${LMOD:-doubao-seed-1-6-flash-250615}
  fi
  SECRET=$(openssl rand -hex 32 2>/dev/null || tr -dc 'a-f0-9' </dev/urandom | head -c 64)
  {
    echo "PORT=$PORT"; echo "NODE_ENV=production"; echo "APP_SECRET=$SECRET"
    echo "ADMIN_USERNAME=$ADMU"; echo "ADMIN_PASSWORD=$ADMP"
    if [ -n "$LKEY" ]; then
      echo "LLM_PROVIDER=doubao"; echo "LLM_BASE_URL=$LURL"; echo "LLM_API_KEY=$LKEY"
      echo "LLM_MODEL_DEFAULT=$LMOD"; echo "LLM_MODEL_PREMIUM=$LMOD"
    fi
  } > "$ROOT/.env"
  chmod 600 "$ROOT/.env"; echo "已生成 .env（含随机 APP_SECRET）"
else
  echo ".env 已存在 → 沿用（改了就重跑本脚本或 docker compose up -d）"
fi

say "3/6 构建并启动容器"
docker compose up -d --build

say "4/6 等待容器 healthy"
for _ in $(seq 1 30); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' agent 2>/dev/null || echo x)" = healthy ] && break; sleep 2
done
[ "$(docker inspect -f '{{.State.Health.Status}}' agent 2>/dev/null || echo x)" = healthy ] \
  || { docker compose logs --tail=50; die "容器未变 healthy（看上面日志）"; }
docker compose ps

say "5/6 本机健康检查（127.0.0.1:$PORT）"
curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null \
  && echo "✓ /api/health = 200" || die "本机健康检查失败"

say "6/6 Caddy 反代 + 自动 HTTPS"
if grep -q "$DOMAIN" "$CADDYFILE" 2>/dev/null; then
  echo "Caddyfile 已含 $DOMAIN → 跳过追加（不重复改）"
else
  printf '\n%s\n' "$(cat "$ROOT/deploy/caddy-agent.conf")" >> "$CADDYFILE"
  echo "已把反代块追加到 $CADDYFILE"
fi
systemctl reload caddy 2>/dev/null || caddy reload --config "$CADDYFILE" 2>/dev/null || echo "⚠ 请手动 reload caddy"
sleep 4
CODE=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN" || echo 000)

echo
if printf '%s' "$CODE" | grep -qE '^(200|301|302)$'; then
  printf '\033[1;32m✅ Agent 部署成功\n  域名: https://%s  →  HTTP %s\n  目录: %s\n  端口: %s（仅本机）\n  Docker: healthy\n\033[0m' "$DOMAIN" "$CODE" "$ROOT" "$PORT"
else
  printf '\033[1;33m容器与本机健康检查已通过，但 https://%s 暂时是 HTTP %s。\n常见原因：DNS 未指向本机 / 证书正在签发。1~2 分钟后再： curl -I https://%s\n如仍不行：sudo caddy validate --config %s ；并确认该域名 A 记录指向本服务器。\033[0m\n' "$DOMAIN" "$CODE" "$DOMAIN" "$CADDYFILE"
fi
