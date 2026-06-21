# 推送即部署（GitHub Actions → 你的服务器）

这是「**自动部署上线、你不用敲命令**」的正路：GitHub 跑机 SSH 进你的香港服务器执行 `deploy.sh`。
我（沙箱）连不到你的服务器，但 GitHub 跑机可以；私钥只放 GitHub Secret，**绝不进代码/对话**。

## 一次性设置（约 3 分钟，只做一次）

### 1) 在服务器准备好部署账号（建议非 root，配免密 sudo 给部署脚本）
```bash
# 用现有用户即可。给它对 deploy.sh 所需命令的免密 sudo：
echo 'deploy ALL=(root) NOPASSWD: /usr/bin/bash /opt/video/lingjing/deploy/deploy.sh' | sudo tee /etc/sudoers.d/video-deploy
sudo chmod 440 /etc/sudoers.d/video-deploy
sudo mkdir -p /opt/video && sudo chown deploy:deploy /opt/video
```
（把 `deploy` 换成你的实际用户名。）

### 2) 生成一把【新的】部署专用密钥（不要用对话里泄露过的那把）
```bash
# 在服务器或本地：
ssh-keygen -t ed25519 -C "video-deploy" -f ~/.ssh/video_deploy -N ""
# 把【公钥】加到服务器部署账号：
cat ~/.ssh/video_deploy.pub >> ~deploy/.ssh/authorized_keys   # 或对应用户的 authorized_keys
```

### 3) 在 GitHub 仓库 → Settings → Secrets and variables → Actions 添加 4 个 Secret
| Secret | 值 |
|---|---|
| `DEPLOY_HOST` | 你服务器公网 IP 或主机名 |
| `DEPLOY_USER` | 部署账号（如 `deploy`） |
| `DEPLOY_SSH_KEY` | 上面【私钥】`~/.ssh/video_deploy` 的全部内容（**只贴这里，别贴对话**） |
| `DEPLOY_PORT` | SSH 端口（默认 22 可不填） |

### 4) 确保服务器防火墙放行 GitHub Actions 出口 IP 的 SSH（22），并已装 Docker/Caddy（你已装）

## 触发部署（两种，都不用你敲服务器命令）
- **自动**：往 `main` 推任何 `lingjing/**` 改动 → 自动部署。
- **手动**：GitHub 仓库 → Actions → “Deploy video.lingmirror.com.cn” → **Run workflow** 按钮。

跑完在 Actions 日志里能看到 `deploy.sh` 打印的 `✅ 部署完成 / 端口 / Healthy`，随后访问 https://video.lingmirror.com.cn 。

## 安全
- 私钥只在 GitHub Secret + 跑机内存临时文件，跑完即删；`.gitignore`/`.dockerignore` 已禁止任何 `*.pem/*.key/id_rsa*` 入库。
- rsync `--exclude .env/data/logs`：**不覆盖**服务器上的 `.env` 与数据/日志。
- `deploy.sh` 只在 `/opt/video` 作业，Caddy 只增改自己的标记块，**不动 `/opt/lingmirror` 与其它站点**。
