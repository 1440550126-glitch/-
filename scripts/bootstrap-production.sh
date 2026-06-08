#!/usr/bin/env bash
set -euo pipefail
APP_DIR=${APP_DIR:-/var/www/lingmirror}
DOMAIN=${DOMAIN:-lingmirror.com.cn}
SRC_DIR=$(cd "$(dirname "$0")/.." && pwd)
if ! command -v node >/dev/null || [ "$(node -p 'Number(process.versions.node.split(`.`)[0])')" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
apt-get update
apt-get install -y sqlite3 nginx rsync curl
mkdir -p "$APP_DIR" "$APP_DIR/data" "$APP_DIR/storage/videos" "$APP_DIR/storage/frames" "$APP_DIR/storage/uploads" "$APP_DIR/storage/renders" "$APP_DIR/storage/logs"
rsync -a --delete --exclude='.git' --exclude='.env' --exclude='node_modules' --exclude='data' --exclude='release' --exclude='storage/videos/*' --exclude='storage/frames/*' --exclude='storage/uploads/*' --exclude='storage/renders/*' --exclude='storage/logs/*' "$SRC_DIR/" "$APP_DIR/"
cd "$APP_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
  JWT=$(node -e "console.log(require('crypto').randomBytes(48).toString('hex'))")
  ADMIN=$(node -e "console.log(require('crypto').randomBytes(18).toString('base64url'))")
  sed -i "s#^JWT_SECRET=.*#JWT_SECRET=$JWT#" .env
  sed -i "s#^ADMIN_PASSWORD=.*#ADMIN_PASSWORD=$ADMIN#" .env
  sed -i "s#^BASE_URL=.*#BASE_URL=https://$DOMAIN#" .env
  sed -i "s#^GOOGLE_CALLBACK_URL=.*#GOOGLE_CALLBACK_URL=https://$DOMAIN/api/auth/google/callback#" .env
  echo "Generated ADMIN_PASSWORD: $ADMIN"
fi
npm install --omit=dev
npm run migrate
NODE_ENV=production npm run preflight
cat >/etc/systemd/system/lingmirror.service <<SERVICE
[Unit]
Description=LingMirror AI v1.0 LTS
After=network.target
[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5
User=www-data
Group=www-data
[Install]
WantedBy=multi-user.target
SERVICE
chown -R www-data:www-data "$APP_DIR/data" "$APP_DIR/storage"
cat >/etc/nginx/sites-available/lingmirror <<NGINX
server {
  listen 80;
  server_name $DOMAIN www.$DOMAIN;
  root $APP_DIR/public;
  index index.html;
  location /api/ { proxy_pass http://127.0.0.1:3001/api/; proxy_http_version 1.1; proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr; proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto \$scheme; }
  location /health { proxy_pass http://127.0.0.1:3001/health; }
  location / { try_files \$uri \$uri/ /index.html; }
}
NGINX
ln -sf /etc/nginx/sites-available/lingmirror /etc/nginx/sites-enabled/lingmirror
nginx -t
systemctl daemon-reload
systemctl enable lingmirror
systemctl restart lingmirror
systemctl reload nginx
sleep 2
curl -fsS http://127.0.0.1:3001/health | grep -q OK
echo "LingMirror deployed to $APP_DIR for $DOMAIN"
