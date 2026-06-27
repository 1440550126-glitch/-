# 远程控制 Mac

让手机/电脑浏览器控制**多台** Mac。属于 **AI句灵**（仓库根 `server/`）的附加能力，与社交 App 解耦，单独鉴权。

## 形态
中继架构，Mac 主动连出 → 穿透 NAT：
```
浏览器 /remote.html ──下发指令──▶ 中继(/api/remote) ◀──长轮询──  mac-agent/agent.mjs (跑在 Mac)
                    ◀──结果/截图(SSE)──             ──回传结果──▶
```

## 关键文件
- `server/lib/remote.js` — 中继核心（**纯内存**态）：`devices` Map（每台 Mac 一份：queue/pollWaiters/ws）+ 全局结果短存(5min) + 控制台 SSE。token 用 `timingSafeEqual` 常量时间比对。多设备：agent 用稳定 `deviceId` 注册，命令带 `device` 路由；只有一台在线时可省略（`resolveDevice`），多台在线不指定则 409。
- `server/lib/transfer.js` — 文件中转**落盘**临时存储（`var/remote-tmp/`，TTL 10min，单文件上限 `REMOTE_MAX_FILE` 默认 500MB）。
- `server/routes/remote-files.js` — 文件传输裸流接口（不走 handleApi 的 JSON 缓冲），在 `index.js` 里先于 handleApi 拦截。浏览器↔服务器↔agent 四个端点，取走即删。
- `server/routes/remote.js` — 接口 + 动作白名单 `REMOTE_ACTIONS`。agent 侧 `hello/poll/result`，控制台侧 `status/command/result/:id/events(SSE)`。
- `server/lib/ws.js` — **零依赖手写 WebSocket 服务端**（握手 + 帧编解码，只支持文本/ping/pong/close，客户端帧解掩码）。Node 只内置 WS 客户端，没有服务端。
- `server/routes/remote-ws.js` — `attachRemoteWs(server)` 挂 `server.on('upgrade')`：`/api/remote/agent/ws`（Mac）与 `/api/remote/stream`（浏览器）。token 走 `?token=`，控制台消息原样透传给 agentWS（fire-and-forget，不进队列）。
- `mac-agent/agent.mjs` — Mac 上的执行端，零依赖，靠 `osascript`/`screencapture`/`sips`/`pmset`/`pbcopy`/`shortcuts` 等实现动作。鼠标走 JXA（`osascript -l JavaScript` + CoreGraphics CGEvent），亮度用屏幕亮度媒体键（key code 144/145），摄像头需 `imagesnap`（启动时 `probeCaps()` 探测，没有就不上报 camera 能力）。
- `web/remote.html` + `web/js/remote.js` — 移动优先控制台（CSP 要求 JS 外置）。

## 约定 / 坑
- **鉴权**：统一 `REMOTE_TOKEN` 环境变量，未配置 = 功能关闭(503)。三处（服务端/agent/浏览器）用同一口令。SSE 取不到自定义头 → token 走 `?token=`。
- **body 上限**：截图 base64 会超默认 128KB，故 `httpx.js` 支持 `route opts.maxBody`，`/agent/result` 设 16MB。
- **限流**：`/api/remote/` 的写请求单独计桶 `rc`（300/min）。鼠标离散方向键/点击走这条。
- **触控板（流式）**：丝滑实时拖动走 WebSocket（`/api/remote/stream`→中继→`agent/ws`），不占 REST、不进队列、不计限流。agent 端开**常驻 osascript JXA 进程**（`osascript -i -l JavaScript`，预定义 `MV/CK/SC`）接收移动，避免每次 spawn 的 ~50ms；浏览器端移动 16ms 批量、双指=滚动、轻点=左键。消息格式短键：`{t:'m',dx,dy}`/`{t:'c',b}`/`{t:'d'}`/`{t:'s',dy}`/`{t:'k'}`。需 agent 的 Node ≥21（内置 WebSocket），否则降级为方向键。`status.stream` 表示通道是否在线，控制台据此点亮触控板。
- **置灰**：控制台从 `/status` 的 `actions[].needs` 收集 `gated` 集合，agent 上报的 `caps` 不含则置灰；带 `data-needs` 的元素（摄像头/解锁/文件卡片）直接隐藏。
- **远程解锁**：密码只存 agent 端 `REMOTE_UNLOCK_PASSWORD`，**永不上网**；控制台只发 `unlock` 信号，agent 本地 `caffeinate` 唤醒 + System Events 输入密码 + 回车。对 FileVault 预引导无效。
- **文件传输**：浏览器→Mac 走 `transfer/up`（落盘→enqueue `recv_file`→agent GET 取走）；Mac→浏览器走命令 `send_file`（agent POST `agent/upload`→回 transfer id→浏览器 GET `file/:id` blob 下载）。agent 端用 readFile/writeFile 全量读（v1，受 500MB 上限约束）。
- **危险动作**：关机/重启需 agent 端 `REMOTE_ALLOW_POWER=1`，执行命令需 `REMOTE_ALLOW_SHELL=1`，默认关。控制台按 agent 上报的 `caps` 置灰。
- **macOS 授权**：锁屏/输入/截屏要在「隐私与安全性 → 辅助功能 / 屏幕录制」给 node 授权，否则失败。
- **注入防护**：agent 端 `say`/`open`/`shell` 用 execFile 数组参数；osascript 字符串字面量走 `osaStr()` 转义。

## 测试
`npm run remote:smoke`（`scripts/remote-smoke.mjs`，34 项：鉴权/多设备上下线与路由/指令往返/新增动作/文件传输/轮询兜底/SSE/WS 流式与设备隔离）。零依赖，自起服务端 + 双假 agent（含 WebSocket 客户端验证握手、转发、设备隔离）。
