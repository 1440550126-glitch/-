#!/usr/bin/env bash
set -u
APP_DIR="${APP_DIR:-/var/www/lingmirror}"
PORT="${PORT:-3001}"
HOST="${HOST:-127.0.0.1}"

echo "== LingMirror server doctor =="
echo "APP_DIR=$APP_DIR"
echo

echo "[node]"
if command -v node >/dev/null 2>&1; then node -v; else echo "node missing"; fi
if command -v npm >/dev/null 2>&1; then npm -v; else echo "npm missing"; fi
if command -v sqlite3 >/dev/null 2>&1; then sqlite3 --version; else echo "sqlite3 missing"; fi

echo

echo "[files]"
ls -ld "$APP_DIR" "$APP_DIR/backend" "$APP_DIR/public" "$APP_DIR/storage" "$APP_DIR/storage/logs" 2>&1 || true
if [[ -f "$APP_DIR/.env" ]]; then
  echo ".env exists"
  sed -n '1,30p' "$APP_DIR/.env" | sed -E 's/(SECRET|KEY|PASSWORD)=.*/\1=****/g'
else
  echo ".env missing"
fi

echo

echo "[preflight]"
(cd "$APP_DIR" && NODE_ENV=production npm run preflight) 2>&1 || true

echo

echo "[port]"
if command -v ss >/dev/null 2>&1; then ss -ltnp | grep -E ":$PORT\b" || echo "nothing listening on $PORT"; fi

echo

echo "[health]"
curl -v --max-time 5 "http://$HOST:$PORT/health" 2>&1 || true

echo

echo "[systemd]"
systemctl --no-pager --full status lingmirror 2>&1 || true
journalctl -u lingmirror -n 80 --no-pager 2>&1 || true

echo

echo "[nginx]"
nginx -t 2>&1 || true
systemctl --no-pager --full status nginx 2>&1 || true

echo

echo "[common fixes]"
echo "1) Node must be >=18. If not: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash - && sudo apt-get install -y nodejs"
echo "2) Ensure .env has JWT_SECRET, ADMIN_PASSWORD, HOST=127.0.0.1, PORT=3001."
echo "3) Run: cd $APP_DIR && npm install --omit=dev && npm run migrate && NODE_ENV=production npm run preflight"
echo "4) Restart: sudo systemctl restart lingmirror && curl http://127.0.0.1:3001/health"
