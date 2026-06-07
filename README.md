# LingMirror AI / 灵镜 AI

LingMirror AI is an **AI Video Production Engine with Memory** for creators, sellers, small businesses, teams and developers.

Core flow: register or Google login → wallet creation → PayPal/Alipay recharge or PayPal subscription credits → project creation → cost estimate → wallet freeze/settle → Volcengine Ark API or safe fallback → Memory Anchor frame extraction and visual analysis → AI Director QC → capped rerun → Project Memory Snapshot → pause/resume after recharge → delivery.

## Run locally

```bash
npm install
cp .env.example .env
npm run migrate
npm run start
curl http://127.0.0.1:3001/health
```

The default host is `127.0.0.1` and port `3001`, suitable for Nginx reverse proxying `/api/` while Nginx serves `public/`.

## Environment

All secrets must stay in `.env`, never in `public/`, HTML, logs or Git. `.env` is ignored by Git.

Generate secrets:

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))" # JWT_SECRET
node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))" # ADMIN_PASSWORD
```

Set Volcengine:

```env
ENABLE_REAL_API=true
VOLCENGINE_ENABLE_TEXT=true
VOLCENGINE_ENABLE_VISION=true
VOLCENGINE_ENABLE_EMBEDDING=true
VOLCENGINE_ENABLE_VIDEO=false # set true only after paid balance and budget tests
VOLCENGINE_ARK_API_KEY=your_server_only_key
```

Switch to fallback/mock by setting `ENABLE_REAL_API=false` or disabling the relevant `VOLCENGINE_ENABLE_*` flag.

## API smoke tests

```bash
curl http://127.0.0.1:3001/health
curl -X POST http://127.0.0.1:3001/api/auth/register -H 'Content-Type: application/json' -d '{"email":"demo@example.com","password":"pass1234"}'
```

Use the returned token as `Authorization: Bearer TOKEN` for wallet, business and project routes.

## Deployment to /var/www/lingmirror

```bash
sudo mkdir -p /var/www/lingmirror
sudo rsync -a --delete ./ /var/www/lingmirror/
cd /var/www/lingmirror
npm install --omit=dev
npm run migrate
npm run start
```

Nginx example:

```nginx
server {
  server_name lingmirror.com.cn;
  root /var/www/lingmirror/public;
  location / { try_files $uri $uri/ /index.html; }
  location /storage/ { alias /var/www/lingmirror/storage/; }
  location /api/ { proxy_pass http://127.0.0.1:3001/api/; proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; }
}
```

## Commercial readiness notes

- Real text tasks are routed through `modelRouter → providerBalanceService → apiBudgetService → walletService → billingService → volcengineProvider → usageLogService → profitService`.
- Real video tasks require `VOLCENGINE_ENABLE_VIDEO=true`, paid balance, provider/budget checks, duration/ratio/resolution validation and capped retry logic.
- Mock fallback is non-empty and records `fallback_used`, so failed real APIs do not crash projects or leak keys.
- Memory Anchor, AI Director QC and Project Memory Snapshot are implemented as database tables, services, project queue flow and front-end project detail panels.
