# 远程控制 Mac

让手机/电脑浏览器控制一台 Mac。属于 **AI句灵**（仓库根 `server/`）的附加能力，与社交 App 解耦，单独鉴权。

## 形态
中继架构，Mac 主动连出 → 穿透 NAT：
```
浏览器 /remote.html ──下发指令──▶ 中继(/api/remote) ◀──长轮询──  mac-agent/agent.mjs (跑在 Mac)
                    ◀──结果/截图(SSE)──             ──回传结果──▶
```

## 关键文件
- `server/lib/remote.js` — 中继核心（**纯内存**态）：单 agent + 指令队列 + 长轮询挂起 + 结果短存(5min) + 控制台 SSE 集合 + 流式 WS（`agentWS`/`streamers`）。token 用 `timingSafeEqual` 常量时间比对。
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
- **置灰**：控制台从 `/status` 的 `actions[].needs` 收集 `gated` 集合，agent 上报的 `caps` 不含则置灰；带 `data-needs` 的元素（如摄像头按钮）直接隐藏。
- **危险动作**：关机/重启需 agent 端 `REMOTE_ALLOW_POWER=1`，执行命令需 `REMOTE_ALLOW_SHELL=1`，默认关。控制台按 agent 上报的 `caps` 置灰。
- **macOS 授权**：锁屏/输入/截屏要在「隐私与安全性 → 辅助功能 / 屏幕录制」给 node 授权，否则失败。
- **注入防护**：agent 端 `say`/`open`/`shell` 用 execFile 数组参数；osascript 字符串字面量走 `osaStr()` 转义。

## 测试
`npm run remote:smoke`（`scripts/remote-smoke.mjs`，23 项：鉴权/上下线/指令往返/亮度·鼠标·快捷指令·摄像头/轮询兜底/SSE/WS 流式中继）。零依赖，自起服务端 + 假 agent（含 WebSocket 客户端验证握手与转发）。
