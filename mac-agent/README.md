# 远程控制 Mac · Agent

跑在你 **Mac** 上的小程序。它主动连出中继服务器，所以即便 Mac 在家庭路由 / NAT 后面，
你也能用手机或另一台电脑的浏览器控制它。零依赖，只用 Node 内置能力。

```
手机/电脑浏览器  ──①下发指令──▶  中继服务器(/api/remote)  ◀──②长轮询拉取──  Mac Agent
   /remote.html  ◀──④结果/截图──        (你部署的服务端)      ──③回传结果──▶
   触控板(鼠标)  ══WebSocket 流式══▶   /api/remote/stream → agent/ws  ══▶（低延迟实时）
```

> 触控板走单独的 WebSocket 流式通道（绕开"一指令一往返"），Mac 端用一个常驻的
> JXA 进程接收移动，所以丝滑。需要运行 agent 的 Node ≥ 21（自带 WebSocket）；
> 老版本会自动降级，只保留方向键 + 点击。

## 1. 服务端开启远程控制

在服务端 `.env` 里设置一个**足够长的随机口令**，重启服务：

```bash
REMOTE_TOKEN=$(openssl rand -hex 24)   # 复制这串，agent 和浏览器都要用它
echo "REMOTE_TOKEN=$REMOTE_TOKEN" >> .env
npm start
```

启动日志会打印：`🖥 远程控制 已启用 → http://<服务器>:3000/remote.html`

> 公网部署务必走 **HTTPS**（口令和指令都经由它）。本地/局域网直接用 http 即可。

## 2. 在 Mac 上跑 Agent

把本仓库拷到 Mac（或只拷 `mac-agent/` 目录），需要 Node ≥ 18：

```bash
REMOTE_SERVER=https://你的服务器 REMOTE_TOKEN=上一步的口令 node mac-agent/agent.mjs
# 也可 npm run agent（同目录仓库）
```

**开机自启**（launchd）：

```bash
cd mac-agent
REMOTE_SERVER=https://你的服务器 REMOTE_TOKEN=口令 ./install.sh
```

## 3. 用手机/电脑控制

浏览器打开 `http://<服务器>:3000/remote.html`，输入同一个 `REMOTE_TOKEN` → 连接。
可加到手机主屏当 App 用。

## 支持的动作

| 动作 | 说明 | 默认 |
|---|---|---|
| 锁屏 / 睡眠 | Ctrl+Cmd+Q / 立即睡眠 | ✅ |
| 音量 | 滑块设音量、静音 | ✅ |
| 亮度 | 调亮 / 调暗（屏幕亮度媒体键） | ✅ |
| 播放控制 | 上一首 / 播放暂停 / 下一首（Spotify 优先，否则 Music） | ✅ |
| 截屏 | 截当前屏幕，压缩成 JPEG 回传显示 | ✅ |
| 鼠标 | **触控板**（滑动移动 / 轻点左键 / 双指滚动，WebSocket 实时）+ 方向键 + 左/右/双击 | ✅（触控板需 Node ≥21） |
| 打开 | 打开网址或应用（如 Safari） | ✅ |
| 快捷指令 | 列出并运行「快捷指令」App 里的 Shortcuts | ✅ |
| 朗读 / 通知 | `say` 朗读、`display notification` 推送 | ✅ |
| 输入文字 | 把文字敲到当前焦点处 | ✅ |
| 剪贴板 | 读取 / 写入 Mac 剪贴板 | ✅ |
| 文件传输 | 浏览器传文件到 Mac「下载」夹 / 取回 Mac 上任意路径文件 | ✅ |
| 摄像头 | 拍一张回传显示 | 需 `brew install imagesnap` |
| 解锁 | 唤醒并输入锁屏密码登录 | 需 `REMOTE_UNLOCK_PASSWORD=`（密码只存 Mac 本机） |
| 重启 / 关机 | — | 需 `REMOTE_ALLOW_POWER=1` |
| 执行命令 | 任意 shell 命令 | 需 `REMOTE_ALLOW_SHELL=1` |

### 多台 Mac

每台 Mac 跑一个 agent，连到同一个中继即可；控制台顶部会出现**设备下拉框**切换控制对象。
设备标识默认按主机名自动生成并存到 `~/.jvling-macagent-id`，也可用 `REMOTE_DEVICE_ID` 固定。

### 远程解锁（开机/锁屏密码）

```bash
REMOTE_UNLOCK_PASSWORD='你的登录密码' node mac-agent/agent.mjs
```

密码**只存在 Mac 本机的环境变量里，永不经过网络/中继**——控制台点「解锁」只发一个
`unlock` 信号，由 agent 在本地唤醒屏幕并输入密码。注意：对 FileVault **开机前**的
预引导密码无效（那时系统还没起来），仅适用于已登录后的锁屏 / 睡眠唤醒。

危险动作（关机/重启/执行命令）默认**关闭**，要在 agent 端显式打开：

```bash
REMOTE_ALLOW_POWER=1 REMOTE_ALLOW_SHELL=1 node mac-agent/agent.mjs
```

## macOS 授权

第一次用到锁屏/输入/截屏时，系统会提示授权。请到
**系统设置 → 隐私与安全性** 里给运行 agent 的 `node`（或终端 / launchd）勾选：

- **辅助功能**（Accessibility）—— 锁屏、输入文字、播放控制需要
- **屏幕录制**（Screen Recording）—— 截屏需要

## 安全建议

- `REMOTE_TOKEN` 用 `openssl rand -hex 24` 这种长随机串，别用弱口令。
- 公网部署走 HTTPS；只在可信网络暴露端口。
- 不需要时别开 `REMOTE_ALLOW_SHELL` / `REMOTE_ALLOW_POWER`。
- 想临时停用：`launchctl unload ~/Library/LaunchAgents/com.jvling.macagent.plist`。
