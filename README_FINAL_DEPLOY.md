# LingMirror AI v1.0 LTS 商用冻结版 — Final Deploy Guide

## 1. What this project is

LingMirror AI / 灵镜 AI is a commercial frozen LTS platform for overseas users to create AI video production packages, product ads, AI copy, business promotional film scripts, e-commerce material plans, knowledge-base answers, poster concepts, 3D asset briefs, Memory Anchors, AI Director QC records and Project Memory Snapshots.

This is not an MVP and not a future-upgrade placeholder. v1.0 LTS keeps the final commercial boundary: email auth, real Google OAuth when configured, wallet ledger, PayPal link payment plus administrator manual paid_balance top-up, Volcengine Ark or authorized model gateway routing, fallback logging, project creation, insufficient-balance pause and top-up resume.

## 2. Deployment

Target architecture:

- Ubuntu 22.04 / 24.04
- Node.js 20+
- SQLite
- Nginx serves `public/`
- Node listens only on `127.0.0.1:3001`
- Nginx proxies `/api/` to `http://127.0.0.1:3001/api/`

Command:

```bash
sudo APP_DIR=/var/www/lingmirror DOMAIN=lingmirror.com.cn bash scripts/bootstrap-production.sh
```

The script installs Node 20 when needed, installs `sqlite3 nginx rsync`, syncs the project to `/var/www/lingmirror`, preserves existing `.env`, `data`, `storage` and logs, generates first-deploy secrets, runs migrations and preflight, installs systemd and Nginx, starts the service and checks `/health`.

## 3. Configure `.env`

Copy `.env.example` to `.env` on the server and edit only server-side values. Never place API keys in `public/`, HTML, frontend JS, README or Git.

Required production items:

```bash
ADMIN_PASSWORD=replace-with-strong-admin-password
JWT_SECRET=replace-with-random-secret
VOLCENGINE_ARK_API_KEY=your-server-side-key-if-using-volcengine
GOOGLE_CLIENT_ID=your-google-client-id-if-using-google-login
GOOGLE_CLIENT_SECRET=your-google-client-secret-if-using-google-login
```

## 4. Generate JWT_SECRET

```bash
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
```

## 5. Generate ADMIN_PASSWORD

```bash
node -e "console.log(require('crypto').randomBytes(18).toString('base64url'))"
```

## 6. PayPal links and payment flow

v1.0 LTS uses PayPal links plus manual administrator review. It does not use automatic PayPal capture or automatic crediting.

Recharge links:

- $10: `https://www.paypal.com/ncp/payment/LECBVJR2JVUZL`
- $30: `https://www.paypal.com/ncp/payment/FBXGEAF8T6AL6`
- $100: `https://www.paypal.com/ncp/payment/FRTV6K6M7P9EC`
- $300: `https://www.paypal.com/ncp/payment/N3FU3KFL4PWM4`

User instruction shown on `wallet.html` and `pricing.html`:

> After payment, please send your PayPal payment screenshot and registered email to zhishiliu057@gmail.com. We will manually add paid credits to your wallet.

中文说明：付款后，请把 PayPal 付款截图和注册邮箱发送到 zhishiliu057@gmail.com，管理员审核后会人工补充 paid_balance。

## 7. Manual top-up after payment

1. User pays through one of the PayPal links.
2. User emails PayPal screenshot and registered email to `zhishiliu057@gmail.com`.
3. Admin opens `/admin.html`.
4. Admin enters `ADMIN_PASSWORD`.
5. Admin searches the registered email.
6. Admin enters user ID, amount and optional note.
7. Admin clicks “Add paid_balance”.
8. The backend writes a wallet transaction with `type=credit`, `bucket=paid`, `provider=paypal_manual`, default description `PayPal manual top-up`.
9. The backend automatically changes that user’s `paused_insufficient_balance` projects back to `pending`.

## 8. Google Console configuration

Application type: `Web application`

Authorized JavaScript origins:

- `https://lingmirror.com.cn`
- `https://www.lingmirror.com.cn`

Authorized redirect URIs:

- `https://lingmirror.com.cn/api/auth/google/callback`
- `https://www.lingmirror.com.cn/api/auth/google/callback`

Optional local development redirect:

- `http://localhost:3001/api/auth/google/callback`

`.env`:

```bash
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALLBACK_URL=https://lingmirror.com.cn/api/auth/google/callback
```

If `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is missing, `/api/auth/google/start` returns `google_oauth_not_configured`, and the frontend displays: “Google login is being configured, please use email login first.” Google scope is only `openid email profile`.

## 9. Volcengine Ark configuration

`.env`:

```bash
AI_PROVIDER=volcengine
ENABLE_REAL_API=true
VOLCENGINE_ARK_API_KEY=your-key
VOLCENGINE_ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_ENABLE_TEXT=true
VOLCENGINE_ENABLE_IMAGE=true
VOLCENGINE_ENABLE_VISION=true
VOLCENGINE_ENABLE_EMBEDDING=true
VOLCENGINE_ENABLE_VIDEO=false
DEFAULT_TEXT_MODEL=doubao-seed-2-0-lite
CHEAP_TEXT_MODEL=doubao-seed-2-0-mini
STRONG_TEXT_MODEL=doubao-seed-2-0-pro
CODE_MODEL=doubao-seed-2-0-code
EMBEDDING_MODEL=doubao-embedding
VISION_MODEL=doubao-seed-vision
VIDEO_MODEL_FAST=doubao-seedance-2-0-fast-260128
VIDEO_MODEL_QUALITY=doubao-seedance-2-0-260128
```

Text-oriented modules call real text models first when the key is configured. If the real provider is missing or fails, the backend falls back to `mockProvider` and records `fallback_used=true` in `api_usage_logs`.

## 10. NewAPI / OneAPI / self-hosted gateway

Only connect legally authorized API keys owned by you. Do not use illegal shared pools, stolen accounts, or quota abuse.

```bash
MODEL_GATEWAY_ENABLED=true
MODEL_GATEWAY_BASE_URL=https://your-gateway.example.com/v1
MODEL_GATEWAY_API_KEY=your-authorized-key
MODEL_GATEWAY_DEFAULT_TEXT_MODEL=
MODEL_GATEWAY_CHEAP_TEXT_MODEL=
MODEL_GATEWAY_STRONG_TEXT_MODEL=
MODEL_GATEWAY_CODE_MODEL=
MODEL_GATEWAY_VISION_MODEL=
MODEL_GATEWAY_EMBEDDING_MODEL=
```

Call order:

1. Gateway when `MODEL_GATEWAY_ENABLED=true` and gateway credentials exist.
2. Volcengine Ark when gateway fails or is disabled.
3. `mockProvider` fallback when real providers fail or are not configured.

Every call records provider, model, gateway_used, fallback_used, token estimates, estimated_cost, actual_cost, user_charge, profit, profit_margin and error_message.

## 11. Why video is disabled by default

`VOLCENGINE_ENABLE_VIDEO=false` prevents unpaid or free users from burning expensive real video credits. The current default creates scripts, shot plans, Visual Bible, Memory Anchor, mock preview frame and project snapshot only. Pages explicitly show: “Video API not enabled yet. Current version generates scripts, shot plans, memory and mock preview only.”

## 12. How to enable real video

Set all required server-side gates:

```bash
ENABLE_REAL_API=true
VOLCENGINE_ARK_API_KEY=your-key
VOLCENGINE_ENABLE_VIDEO=true
VIDEO_MODEL_FAST=doubao-seedance-2-0-fast-260128
VIDEO_MODEL_QUALITY=doubao-seedance-2-0-260128
```

Real video must only run after paid_balance, platform budget, user daily limit, model ID and project ownership checks. Free bonus credits are not for real video burning.

## 13. Logs

- API usage: `/admin.html` or `api_usage_logs` table.
- Admin actions: `admin_audit_logs` table.
- Systemd logs: `journalctl -u lingmirror -n 200 --no-pager`.
- Nginx logs: `/var/log/nginx/`.

Secrets are read from `.env` and must not be printed as full keys.

## 14. Smoke test

```bash
npm run migrate
NODE_ENV=production npm run preflight
npm run start
BASE_URL=http://127.0.0.1:3001 ADMIN_PASSWORD=your-admin-password bash scripts/smoke-test.sh
```

## 15. Package release

```bash
bash scripts/package-release.sh
```

Outputs:

- `release/lingmirror-ai.tar.gz`
- `release/lingmirror-ai.zip`

The package excludes `.env`, `node_modules`, `data`, generated media folders and logs.

## 16. Real functions

- Email register/login.
- Real Google OAuth when configured.
- Wallet auto-creation and transaction ledger.
- Admin manual paid_balance top-up.
- Project insufficient-balance pause and top-up resume.
- Authorized gateway / Volcengine text routing.
- Admin visibility for users, wallets, transactions, projects, paused projects, API logs, provider, model, fallback_used, costs, profits, memory snapshots, memory anchors and generation jobs.

## 17. Fallback/mock functions

When real provider settings are absent or fail, AI modules use `mockProvider` fallback and record `fallback_used=true`. With `VOLCENGINE_ENABLE_VIDEO=false`, video output is a script, shot plan, Visual Bible, Memory Anchor, mock preview frame and project snapshot, not a real generated video success.

## 18. Credits legal statement

LingMirror Credits are service credits only. They are not a virtual currency, cannot be withdrawn, cannot be transferred, cannot be traded and cannot be redeemed for cash.

## 19. Frozen maintenance policy

LingMirror AI v1.0 LTS 商用冻结版 is the final feature release. Future work is limited to bug fixes, key replacement, price/text edits and server maintenance. No new feature upgrade roadmap is planned.
