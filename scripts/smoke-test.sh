#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:3001}"
EMAIL="smoke-$(date +%s)@example.com"
PASSWORD="pass1234"

echo "[1/7] health"
curl -fsS "$BASE_URL/health" | grep -q OK

echo "[2/7] register"
TOKEN=$(curl -fsS -X POST "$BASE_URL/api/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>console.log(JSON.parse(s).token))')

echo "[3/7] wallet"
curl -fsS "$BASE_URL/api/wallet" -H "Authorization: Bearer $TOKEN" | grep -q current_balance

echo "[4/7] copy lab"
curl -fsS -X POST "$BASE_URL/api/business/copy-lab" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"product":"LingMirror AI","audience":"e-commerce sellers"}' | grep -q 'copy_generation'

echo "[5/7] paypal recharge mock/capture"
ORDER=$(curl -fsS -X POST "$BASE_URL/api/payments/paypal/create-order" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"amount":10}' | node -e 'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>console.log(JSON.parse(s).orderId))')
curl -fsS -X POST "$BASE_URL/api/payments/paypal/capture-order" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d "{\"orderId\":\"$ORDER\"}" | grep -q paid

echo "[6/7] project create"
PROJECT=$(curl -fsS -X POST "$BASE_URL/api/projects" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Smoke 15s","project_type":"video","target_duration_seconds":15,"script_text":"A founder explains LingMirror Memory Anchor continuity.","director_supervision_level":"off"}' \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>console.log(JSON.parse(s).id))')

echo "[7/7] run one shot and verify memory"
curl -fsS -X POST "$BASE_URL/api/projects/$PROJECT/run" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"maxShots":1}' | grep -Eq 'pending|delivered|paused_insufficient_balance'
curl -fsS "$BASE_URL/api/projects/$PROJECT" -H "Authorization: Bearer $TOKEN" | grep -q 'memory_anchors\|anchors'

echo "Smoke test passed: $PROJECT"
