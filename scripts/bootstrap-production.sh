#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/var/www/lingmirror}"
SERVICE_USER="${SERVICE_USER:-www-data}"
DOMAIN="${DOMAIN:-lingmirror.com.cn}"
PORT="${PORT:-3001}"
HOST="${HOST:-127.0.0.1}"
NODE_MAJOR="${NODE_MAJOR:-20}"

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root: sudo APP_DIR=$APP_DIR DOMAIN=$DOMAIN bash scripts/bootstrap-production.sh" >&2
  exit 1
fi

need_node_install=0
if ! command -v node >/dev/null 2>&1; then
  need_node_install=1
else
  current_major="$(node -p 'Number(process.versions.node.split(".")[0])')"
  if [[ "$current_major" -lt 18 ]]; then need_node_install=1; fi
fi

apt-get update
apt-get install -y curl ca-certificates gnupg sqlite3 nginx rsync
if [[ "$need_node_install" -eq 1 ]]; then
  echo "Installing Node.js $NODE_MAJOR.x from NodeSource because Node >=18 is required."
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
fi
apt-get install -y nodejs
node -e 'const major=Number(process.versions.node.split(".")[0]); if (major < 18) { console.error(`Node >=18 required, got ${process.version}`); process.exit(1); }'

mkdir -p "$APP_DIR" "$APP_DIR/data" "$APP_DIR/storage/videos" "$APP_DIR/storage/frames" "$APP_DIR/storage/uploads" "$APP_DIR/storage/renders" "$APP_DIR/storage/logs"
# Do not delete production .env, data, storage, logs, or packaged release files during redeploy.
rsync -a --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.env' \
  --exclude='data' \
  --exclude='storage/videos/*' \
  --exclude='storage/frames/*' \
  --exclude='storage/uploads/*' \
  --exclude='storage/renders/*' \
  --exclude='storage/logs/*' \
  --exclude='release/*.tar.gz' \
  --exclude='release/*.zip' \
  ./ "$APP_DIR/"
cd "$APP_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  JWT_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
  ADMIN_PASSWORD=$(node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))")
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" .env
  sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" .env
  sed -i "s|^HOST=.*|HOST=$HOST|" .env
  sed -i "s|^PORT=.*|PORT=$PORT|" .env
  sed -i "s|^BASE_URL=.*|BASE_URL=https://$DOMAIN|" .env
  # Generated production env starts in safe fallback mode. Add VOLCENGINE_ARK_API_KEY and set ENABLE_REAL_API=true after smoke tests.
  sed -i "s|^ENABLE_REAL_API=.*|ENABLE_REAL_API=false|" .env
  sed -i "s|^VOLCENGINE_ENABLE_VIDEO=.*|VOLCENGINE_ENABLE_VIDEO=false|" .env
  echo "Generated .env. Save ADMIN_PASSWORD now: $ADMIN_PASSWORD"
else
  echo "Keeping existing $APP_DIR/.env (not overwritten)."
fi

npm install --omit=dev
npm run migrate
NODE_ENV=production npm run preflight
chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

sed "s|/var/www/lingmirror|$APP_DIR|g; s|lingmirror.com.cn|$DOMAIN|g" ops/nginx/lingmirror.conf > /etc/nginx/sites-available/lingmirror.conf
ln -sf /etc/nginx/sites-available/lingmirror.conf /etc/nginx/sites-enabled/lingmirror.conf
sed "s|/var/www/lingmirror|$APP_DIR|g; s|www-data|$SERVICE_USER|g" ops/systemd/lingmirror.service > /etc/systemd/system/lingmirror.service
systemctl daemon-reload
systemctl enable lingmirror
systemctl restart lingmirror
sleep 2
systemctl --no-pager --full status lingmirror || true
nginx -t
systemctl reload nginx
curl -fsS "http://$HOST:$PORT/health"
echo "LingMirror deployed. Configure DNS for $DOMAIN and TLS with certbot if needed."
echo "If deployment fails, run: sudo APP_DIR=$APP_DIR bash scripts/doctor-server.sh"
