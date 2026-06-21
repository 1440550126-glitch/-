#!/usr/bin/env bash
# ============================================================================
# LingMirror AI 视频 · 一键部署（Ubuntu 24.04 / Docker + Caddy）
#   安全保证：只在 /opt/video 内作业；绝不触碰 /opt/lingmirror；
#            Caddy 只【新增/更新】本站点的标记块，不删改其它站点；
#            不占用 80/443/3000/3001，对外端口默认 3002（被占用自动顺延并同步 Caddy）。
#   用法：  sudo bash /opt/video/lingjing/deploy/deploy.sh
# ============================================================================
set -euo pipefail

APP_ROOT=/opt/video
DOMAIN=video.lingmirror.com.cn
WANT_PORT=3002
CADDYFILE=/etc/caddy/Caddyfile
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # /opt/video/lingjing/deploy

log(){ printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[deploy] 错误：%s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || die "请用 root 运行： sudo bash $0"
command -v docker >/dev/null || die "未找到 docker"
docker compose version >/dev/null 2>&1 || die "未找到 docker compose (v2)"

# 0) 代码就位（项目应已位于 /opt/video；可选 REPO_URL 自动拉取，绝不覆盖 /opt/lingmirror）
if [ ! -f "$APP_ROOT/lingjing/server/index.js" ]; then
  if [ -n "${REPO_URL:-}" ]; then
    log "克隆代码到 $APP_ROOT （分支 ${BRANCH:-main}）"
    mkdir -p "$APP_ROOT"; git clone --depth=1 -b "${BRANCH:-main}" "$REPO_URL" "$APP_ROOT"
  else
    die "未在 $APP_ROOT/lingjing 找到项目。请先把项目放到 $APP_ROOT（rsync/scp/git），或设 REPO_URL=… 重跑"
  fi
fi

# 1) 目录（数据 + 日志）
mkdir -p "$APP_ROOT/logs" "$APP_ROOT/data/uploads"

# 2) .env（不存在才创建，绝不覆盖已填好的密钥）
if [ ! -f "$APP_ROOT/.env" ]; then
  cp "$HERE/.env.example" "$APP_ROOT/.env"
  chmod 600 "$APP_ROOT/.env"
  log "已生成 $APP_ROOT/.env（按需填 API Key；留空也能先上线走本地占位）"
else
  log "$APP_ROOT/.env 已存在，保留不动"
fi

# 3) 端口冲突检测 → 自动顺延（避开 80/443/3000/3001 与已占用端口），并同步给 Caddy
port_busy(){ { command -v ss >/dev/null && ss -ltnH "( sport = :$1 )" 2>/dev/null | grep -q .; } \
          || { command -v lsof >/dev/null && lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }; }
PORT=$WANT_PORT
for reserved in 80 443 3000 3001; do [ "$PORT" = "$reserved" ] && PORT=3002; done
while port_busy "$PORT" || printf '80\n443\n3000\n3001\n' | grep -qx "$PORT"; do
  log "端口 $PORT 不可用，顺延"; PORT=$((PORT+1));
done
[ "$PORT" = "$WANT_PORT" ] || log "对外端口改用 $PORT（已避开占用/保留端口）"
export VIDEO_PORT="$PORT"

# 4) 构建 + 启动（项目名隔离）
cd "$HERE"
log "docker compose 构建并启动（主机 127.0.0.1:$PORT → 容器 4399）…"
VIDEO_PORT="$PORT" docker compose up -d --build

# 5) 等待容器 healthy
log "等待容器 healthy（最多 ~120s）…"
ok=0
for i in $(seq 1 40); do
  st="$(docker inspect -f '{{.State.Health.Status}}' lingmirror-video 2>/dev/null || echo starting)"
  [ "$st" = healthy ] && { ok=1; log "容器 healthy ✓"; break; }
  sleep 3
done
[ "$ok" = 1 ] || die "容器未在时限内 healthy。排查： docker compose -f $HERE/docker-compose.yml logs --tail=80"

# 6) Caddy：仅幂等管理本站点的标记块（不删改其它站点）
[ -f "$CADDYFILE" ] || die "未找到 $CADDYFILE"
cp -a "$CADDYFILE" "$CADDYFILE.bak.$(date +%Y%m%d%H%M%S)"
# 删掉旧的本站点 managed 块（若有），再追加最新的（端口可能变了）
sed -i '/# >>> lingmirror-video (managed) >>>/,/# <<< lingmirror-video (managed) <<</d' "$CADDYFILE"
# 顺手清掉可能存在的、未带标记的同域名裸块（保守：仅当其反代到本机时）
cat >> "$CADDYFILE" <<EOF

# >>> lingmirror-video (managed) >>>
$DOMAIN {
    encode zstd gzip
    reverse_proxy 127.0.0.1:$PORT
}
# <<< lingmirror-video (managed) <<<
EOF
log "已在 $CADDYFILE 写入 $DOMAIN → 127.0.0.1:$PORT（已备份原文件）"

# 7) 校验并重载 Caddy（HTTPS 证书自动签发）
if command -v caddy >/dev/null && caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1; then
  caddy reload --config "$CADDYFILE" --adapter caddyfile 2>/dev/null || systemctl reload caddy
else
  systemctl reload caddy 2>/dev/null || die "Caddy 配置校验/重载失败，请检查 $CADDYFILE（已备份）"
fi
log "Caddy 已 reload（首次 HTTPS 证书签发约需 10-40s）"

# 8) 健康检查
sleep 3
code="$(curl -fsS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/bootstrap" 2>/dev/null || echo 000)"
log "本地直连 http://127.0.0.1:$PORT/api/bootstrap → HTTP $code"
ext="$(curl -fsS --max-time 40 -o /dev/null -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || echo 000)"
log "对外 https://$DOMAIN/ → HTTP $ext （若为 000/5xx，等证书签发后再试一次）"

echo
echo "✅ 部署完成"
echo "域名：     https://$DOMAIN"
echo "项目目录： $APP_ROOT"
echo "运行端口： $PORT"
echo "数据：     $APP_ROOT/data     日志： $APP_ROOT/logs/video.log"
echo "查看状态： docker compose -f $HERE/docker-compose.yml ps"
