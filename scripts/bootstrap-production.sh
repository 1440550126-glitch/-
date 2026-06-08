#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/var/www/lingmirror}"
SERVICE_USER="${SERVICE_USER:-www-data}"
DOMAIN="${DOMAIN:-lingmirror.com.cn}"
PORT="${PORT:-3001}"
HOST="${HOST:-127.0.0.1}"

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root: sudo APP_DIR=$APP_DIR DOMAIN=$DOMAIN bash scripts/bootstrap-production.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y nodejs npm sqlite3 nginx rsync ca-certificates
mkdir -p "$APP_DIR"
rsync -a --delete --exclude='.git' --exclude='node_modules' --exclude='data' ./ "$APP_DIR/"
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
  echo "Generated .env. Save ADMIN_PASSWORD now: $ADMIN_PASSWORD"
fi
npm install --omit=dev
npm run migrate
chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"
sed "s|/var/www/lingmirror|$APP_DIR|g; s|lingmirror.com.cn|$DOMAIN|g" ops/nginx/lingmirror.conf > /etc/nginx/sites-available/lingmirror.conf
ln -sf /etc/nginx/sites-available/lingmirror.conf /etc/nginx/sites-enabled/lingmirror.conf
sed "s|/var/www/lingmirror|$APP_DIR|g; s|www-data|$SERVICE_USER|g" ops/systemd/lingmirror.service > /etc/systemd/system/lingmirror.service
systemctl daemon-reload
systemctl enable lingmirror
systemctl restart lingmirror
nginx -t
systemctl reload nginx
curl -fsS "http://$HOST:$PORT/health"
echo "LingMirror deployed. Configure DNS for $DOMAIN and TLS with certbot if needed."
