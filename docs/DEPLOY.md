# 生产部署指南

目标环境：一台 2C4G 起步的国内云服务器（已备案域名 + HTTPS）。单进程可支撑早期量级（SQLite WAL + SSE，数千日活无压力）。

## 1. 上线前必做清单

- [ ] `.env` 设置强密码 `ADMIN_PASSWORD`（启动日志若警告默认密码，必须处理）
- [ ] `.env` 设置固定 `APP_SECRET`（32+ 随机字符；不设则用首启自动生成并持久化的值）
- [ ] `NODE_ENV=production`（启用启动自检警告）
- [ ] 配置大模型：方舟控制台创建 **API Key**（注意不是 AKLT 开头的 AccessKey），`node scripts/llm-test.mjs` 自检通过
- [ ] 跑一遍 `npm run smoke`（86 项全过再发布）
- [ ] 域名 ICP 备案号填入 `server/index.js` 的 bootstrap compliance（或做成 env）
- [ ] 《用户协议》《隐私政策》内容请法务复核（`web/js/pages/settings.js` 内 DOCS）
- [ ] 管理后台开启「AI 机审」（已配置大模型时）
- [ ] 接入云厂商文本反垃圾 API（接入点：`server/lib/moderation.js` 的 `gateContent`/`aiModeratePost`）

## 2. systemd 守护

```ini
# /etc/systemd/system/jvling.service
[Unit]
Description=AI Jvling
After=network.target

[Service]
Type=simple
User=jvling
WorkingDirectory=/opt/jvling
EnvironmentFile=/opt/jvling/.env
Environment=NODE_ENV=production PORT=3000
ExecStart=/usr/bin/node --disable-warning=ExperimentalWarning server/index.js
Restart=always
RestartSec=3
# SQLite 数据目录可写
ReadWritePaths=/opt/jvling/var

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now jvling
journalctl -u jvling -f        # 看日志
```

## 3. Nginx 反代（HTTPS + SSE）

```nginx
server {
  listen 443 ssl http2;
  server_name app.example.com;
  ssl_certificate     /etc/ssl/jvling/fullchain.pem;
  ssl_certificate_key /etc/ssl/jvling/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    # SSE 必需：关缓冲、长超时
    proxy_buffering off;
    proxy_read_timeout 1h;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
  }
}
server { listen 80; server_name app.example.com; return 301 https://$host$request_uri; }
```

## 4. 数据备份

SQLite 单文件备份（WAL 模式下用 sqlite3 在线备份，凌晨 cron）：

```bash
# /etc/cron.d/jvling-backup   （每天 04:30）
30 4 * * * jvling sqlite3 /opt/jvling/var/jvling.sqlite ".backup /opt/jvling/backup/jvling-$(date +\%F).sqlite" && find /opt/jvling/backup -mtime +14 -delete
```

## 5. 升级流程

```bash
cd /opt/jvling && git pull
npm run check && npm run smoke     # 全绿才继续
sudo systemctl restart jvling      # 进行中的桌游对局会被标记结束（启动恢复逻辑）
```

> 重启会中断进行中的对局（内存权威状态）。低峰期操作；后续迁 Redis 后可平滑。

## 6. 扩容路径（按量级触发）

| 信号 | 动作 |
|---|---|
| 日活 > 1 万 / 写入争用 | 按 docs/DATABASE.md 迁 PostgreSQL；限流与房间态迁 Redis |
| SSE 连接 > 5k | 多实例 + Redis Pub/Sub 替换 `lib/hub.js` |
| 动画生成成本上升 | 后台调低免费配额 / 提高暖场预算阈值 |
| 内容量上涨 | 云厂商机审全量前置，人工只处理 review 队列 |

## 7. 支付接入位

`server/routes/shop.js` 的 `POST /api/shop/orders/:id/pay` 即回调骨架：把"沙盒直接置 paid"替换为微信/支付宝验签 + 查单，**履约逻辑（会员/皮肤/额度入账）无需改动**。iOS 包内购买走 Apple IAP：客户端拿到票据后调服务端验单接口，复用同一履约函数。
