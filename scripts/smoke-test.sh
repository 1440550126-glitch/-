#!/usr/bin/env bash
set -euo pipefail
BASE_URL=${BASE_URL:-http://127.0.0.1:3001}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-}
if [ -f .env ]; then set -a; . ./.env; set +a; fi
ADMIN_PASSWORD=${ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
j(){ node -e "const o=JSON.parse(require('fs').readFileSync(0,'utf8')); console.log($1)"; }
req(){ curl -fsS "$@"; }
echo "1 health"; req "$BASE_URL/health" | grep -q OK
EMAIL="smoke$(date +%s%N)@example.com"; PASS="Smoke12345"
echo "2 register"; REG=$(req -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" "$BASE_URL/api/auth/register"); ! echo "$REG" | grep -q password_hash
TOKEN=$(echo "$REG" | j 'o.token')
echo "3 login"; LOGIN=$(req -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" "$BASE_URL/api/auth/login"); ! echo "$LOGIN" | grep -q password_hash
echo "4 wallet"; req -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/wallet" | tee "$TMP/wallet.json" | grep -q current_balance
echo "5 wallet page/paypal"; req "$BASE_URL/wallet.html" | grep -q 'PayPal payment screenshot'; req "$BASE_URL/api/config" | grep -q LECBVJR2JVUZL
echo "6 ai modules"; for m in copy-lab product-ads business-promo; do req -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"prompt":"smoke product for overseas ecommerce"}' "$BASE_URL/api/ai/$m" | grep -q fallback_used; done
echo "7 create insufficient project"; PROJ=$(req -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"title":"Smoke video","duration_seconds":60,"prompt":"test"}' "$BASE_URL/api/projects"); echo "$PROJ" | grep -q paused_insufficient_balance; PID=$(echo "$PROJ" | j 'o.project.id')
echo "8 access isolation"; REG2=$(req -H 'Content-Type: application/json' -d "{\"email\":\"other$EMAIL\",\"password\":\"$PASS\"}" "$BASE_URL/api/auth/register"); TOK2=$(echo "$REG2" | j 'o.token'); HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOK2" "$BASE_URL/api/projects/$PID"); [ "$HTTP" = "404" ] || { echo "isolation failed: $HTTP"; exit 1; }
echo "9 google not configured"; curl -s "$BASE_URL/api/auth/google/start" | grep -q google_oauth_not_configured
echo "10 provider fallback"; req -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"prompt":"fallback check"}' "$BASE_URL/api/ai/copy-lab" | grep -q '"fallback_used":true'
echo "11 video disabled notice"; echo "$PROJ" | grep -q 'Video API not enabled yet'
echo "12 admin credit resume"; if [ -z "${ADMIN_PASSWORD:-}" ]; then echo "ADMIN_PASSWORD missing for smoke"; exit 1; fi; USER_ID=$(echo "$REG" | j 'o.user.id'); CREDIT=$(req -H "X-Admin-Password: $ADMIN_PASSWORD" -H 'Content-Type: application/json' -d '{"amount":10,"description":"PayPal manual top-up"}' "$BASE_URL/api/admin/users/$USER_ID/credit"); echo "$CREDIT" | grep -q resumed_projects; req -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/projects/$PID" | grep -q '"status":"pending"'
echo "Smoke test OK"
