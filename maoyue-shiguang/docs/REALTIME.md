# 小程序实时（WebSocket）使用说明

前端通过 `wx.connectSocket` 连后端 `maoyue-server` 的 `/ws`，实现情侣双方**实时同步**。

## 开启步骤

1. 启动后端：`maoyue-server` 里 `npm start`（默认 `:3001`，WS 地址 `ws://localhost:3001/ws`）。
2. 配置前端 `utils/api.js`：
   ```js
   const API_BASE = 'http://localhost:3001/api';   // 或你的 https 域名 + /api
   const WS_BASE  = 'ws://localhost:3001/ws';       // 或 wss://你的域名/ws
   ```
3. 登录拿 token（建立连接的前提）：在某处调用 `require('../../utils/api.js').login()`（内部 `wx.login` → 后端换 openid，存 token）。
4. App 启动时 `app.js` 会自动 `realtime.init(wsUrl())` 连接；未配置或未登录则静默跳过（纯本地原型照常用）。

> 开发者工具：详情 → 本地设置 → 勾选「不校验合法域名…」即可用 `ws://localhost`。  
> 真机：需在小程序后台「开发管理 → 服务器域名」配置 **socket 合法域名**（`wss://你的域名`）。

## 页面里订阅事件

```js
const app = getApp();
// onShow 订阅，onHide/onUnload 取消（返回值即取消函数）
this._off = app.onRealtime('mood.updated', d => { /* d = {mood:{e,t}} */ });
// 取消：this._off();
```

事件名（与后端一致）：`mood.updated`、`note.created`、`vault.updated`、`cat.updated`、`affection.received`、`partner.status`、`chat.message`、`couple.bound/unbound`、`dailyq.answered`、`wish.updated`、`anniv.updated`、`memory.created`。

## 已接入的演示

- **全局**（`app.js`）：收到 `affection.received` → 顶部提示「TA 想你了 / 抱了抱你…」。
- **首页**：`mood.updated` 即时刷新 TA 的心情；`partner.status` 更新 TA 电量/在线。
- **小金库**：`vault.updated` 即时刷新余额与流水。
- **陪伴页**：`note.created` 让 TA 的新纸条立刻出现。

## 与数据层的关系

实时通道已通。要让**所有页面数据**都走后端（而非本地缓存），需把 `utils/store.js` 的读写改成 `api.request(...)`（映射见 `docs/BACKEND-API.md` 第 18 节）。届时收到事件后调用各页 `refresh()` 即可拉到最新服务端数据；当前演示是直接用事件 payload 更新 UI。

## 机制

`utils/realtime.js`：指数退避自动重连、25s 心跳、`on/off` 事件订阅。后端 `/ws` 为零依赖手写实现（握手 + 帧编解码），事件与 SSE 完全一致，二者可并存。
