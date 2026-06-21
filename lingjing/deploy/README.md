# LingMirror AI 视频 · 部署包（video.lingmirror.com.cn）

把本项目放到香港服务器的 `/opt/video`，然后一条命令完成 Docker + Caddy + HTTPS 上线。
**与 `/opt/lingmirror` 完全独立**，不动其它站点，不占用 `80/443/3000/3001`，对外端口 `3002`。

## 一键部署（推荐）

```bash
# 1) 把项目放到 /opt/video（任选其一）
sudo rsync -a ./ /opt/video/            # 本地已有代码：rsync/scp 上去
#   或：sudo REPO_URL=<你的git地址> BRANCH=main bash -c 'git clone --depth=1 -b "$BRANCH" "$REPO_URL" /opt/video'

# 2) 跑部署脚本（构建镜像→起容器→等 healthy→写 Caddy→reload→健康检查）
sudo bash /opt/video/lingjing/deploy/deploy.sh

# 3) 填 API Key（可选，留空先走本地占位也能开站）后重启容器使其生效
sudo nano /opt/video/.env
sudo docker compose -f /opt/video/lingjing/deploy/docker-compose.yml restart
```

完成后访问 **https://video.lingmirror.com.cn**（首次 HTTPS 证书自动签发约需 10-40s）。

## 这套部署做了什么
- **端口**：容器内 4399，对外 `127.0.0.1:3002`（仅本机，外网只经 Caddy）。3002 被占用会自动顺延并同步改 Caddy。
- **Caddy**：向 `/etc/caddy/Caddyfile` 追加带标记的 `video.lingmirror.com.cn { reverse_proxy 127.0.0.1:3002 }` 块（幂等，可重复跑），**先备份原文件、绝不删改其它站点**，随后 `caddy reload`。
- **数据持久化**：`/opt/video/data`（SQLite + 上传/生成文件）。**日志**：`/opt/video/logs/video.log`。
- **健康检查**：容器 `HEALTHCHECK` 打 `/api/bootstrap`；`docker compose ps` 显示 `healthy`。
- **环境变量**：所有 Key 走 `/opt/video/.env`（见 `.env.example`），不写死在代码。

## 常用命令
```bash
cd /opt/video/lingjing/deploy
docker compose ps                 # 应为 healthy
docker compose logs -f --tail=100 # 实时日志（或 tail -f /opt/video/logs/video.log）
docker compose restart            # 改 .env 后重启
docker compose up -d --build      # 更新代码后重建
```

## 非 Docker 备选（systemd）
见 `video.service` 顶部注释：`systemctl enable --now lingmirror-video`（端口直接 3002，Caddy 同样反代 3002）。

## 账号互通 / 钱包 / 计费（预留接口）
- **账号互通（共用登录）**：`.env` 的 `LINGMIRROR_SSO_*` —— 登录身份走主站（PayPal/Google/GitHub/邮箱）。
- **钱包【不互通】（视频站独立）**：`VIDEO_WALLET_*`、`VIDEO_BILLING_*`、本站独立 `PAYPAL_*` —— 本站自有余额与账单，
  与主站钱包**分开**，按秒 / 按模型 / 按 GPU / 会员订阅独立计费。
当前版本先把 **AI 视频生成内核** 上线；SSO 登录与独立钱包/计费为后续接入项（接口已留位）。
