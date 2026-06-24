# 部署（video.lingmirror.com.cn）

部署包在 `lingjing/deploy/`，目标香港服务器 Ubuntu 24.04，与 `/opt/lingmirror` 完全隔离、不占 80/443/3000/3001，对外端口 **3002**。

## 一键
代码放 `/opt/video` → `sudo bash /opt/video/lingjing/deploy/deploy.sh`。脚本：建目录→生成 `.env`(不覆盖)→端口冲突自动顺延→`docker compose up -d --build`→等 healthy→向 Caddyfile **追加带标记的** video 块(先备份、只管自身块)→`caddy reload`→健康检查→打印 `✅ 部署完成`。

## 文件
- `Dockerfile`：node:22-slim + ffmpeg，跑 `lingjing/server/index.js`，HEALTHCHECK 打 `/api/bootstrap`。
- `docker-compose.yml`：`127.0.0.1:3002→容器4399`，数据/日志卷，env_file=/opt/video/.env。
- `video.service`：systemd 非 Docker 备选。
- `.env.example`：所有 Key 走环境变量；预留 SSO/**独立钱包**(VIDEO_WALLET_*，**钱包不与主站互通**)/计费/OAuth。
- `CICD.md` + `.github/workflows/deploy-video.yml`：推送即部署（GitHub 跑机 SSH 进服务器跑 deploy.sh，私钥放 Secret）。

## 沙箱限制
Claude Code 沙箱**无网络到香港服务器**，不能代跑；deploy.sh 逻辑已在沙箱演练验证（3002 起、/api/bootstrap 200、Caddy 幂等不动其它站）。

## 账号/钱包
账号互通(SSO 共用登录)，**钱包不互通**(视频站独立余额/计费)。密钥只以服务器文件存、env 用路径引用，永不入库/对话。
