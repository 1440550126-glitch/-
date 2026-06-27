// 远程控制 Mac · 中继核心（内存态，单实例够用；集群化后换 Redis/消息队列）
//
// 角色：
//   - Agent（跑在 Mac 上的 mac-agent/agent.mjs）：长轮询拉取指令、回传结果，定时心跳。
//   - Controller（手机/电脑浏览器里的控制台 web/remote.html）：下发指令、看结果、订阅 SSE。
// 支持「多台 Mac」：每台 agent 用稳定的 deviceId 注册，中继按设备路由指令与流式通道。
// 中继不持久化指令（远程控制天然是瞬时的），只在内存里排队 + 短期保留结果。
import crypto from 'node:crypto';
import { now, uid } from './util.js';

const TOKEN = (process.env.REMOTE_TOKEN || '').trim();
const ONLINE_TTL = 40_000;        // 超过这个时间没心跳就算离线
const RESULT_TTL = 5 * 60_000;    // 结果保留 5 分钟供轮询兜底
const DEVICE_TTL = 10 * 60_000;   // 离线超过这个时间的设备从列表里清掉
const MAX_QUEUE = 50;             // 单设备待执行指令上限（防积压）

export const remoteEnabled = () => !!TOKEN;
export function remoteTokenWeak() { return remoteEnabled() && TOKEN.length < 16; }

// 常量时间比较，避免计时攻击
export function checkToken(t) {
  if (!TOKEN || !t) return false;
  const a = Buffer.from(String(t));
  const b = Buffer.from(TOKEN);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

// 从请求里取 remote token：头 X-Remote-Token / Authorization Bearer / ?token= / body.token
export function remoteToken(ctx) {
  return (
    ctx.req.headers['x-remote-token'] ||
    (ctx.req.headers.authorization || '').replace(/^Bearer\s+/i, '') ||
    ctx.query?.get?.('token') ||
    ctx.body?.token ||
    ''
  ).toString().trim();
}

// ---- 内存态 ----
const devices = new Map();         // deviceId -> { id, host, user, os, caps, lastSeen, queue, pollWaiters, ws }
const results = new Map();         // cmdId -> { id, device, ok, data, error, at }
const resultWaiters = new Map();   // cmdId -> [{ resolve, timer }]
const controllers = new Set();     // 控制台 SSE 客户端

const isOnline = (d) => !!d && now() - d.lastSeen < ONLINE_TTL;

function getDevice(id, create = false) {
  let d = devices.get(id);
  if (!d && create) {
    d = { id, host: '', user: '', os: '', caps: [], lastSeen: 0, queue: [], pollWaiters: [], ws: null };
    devices.set(id, d);
  }
  return d;
}

function deviceView(d) {
  return {
    device: d.id,
    host: d.host || null,
    user: d.user || null,
    os: d.os || null,
    caps: d.caps,
    online: isOnline(d),
    stream: isOnline(d) && !!d.ws,
    last_seen: d.lastSeen || null,
    queued: d.queue.length
  };
}

export function listDevices() {
  // 顺手清理早就离线的设备
  for (const [id, d] of devices) {
    if (!isOnline(d) && now() - d.lastSeen > DEVICE_TTL && !d.ws) devices.delete(id);
  }
  return [...devices.values()].map(deviceView).sort((a, b) => Number(b.online) - Number(a.online));
}

// 解析目标设备：显式指定优先；否则取唯一在线设备（单 Mac 场景免选）
function resolveDevice(deviceId) {
  if (deviceId) return getDevice(deviceId);
  const onlineOnes = [...devices.values()].filter(isOnline);
  return onlineOnes.length === 1 ? onlineOnes[0] : null;
}

// ---- Agent 侧 ----
export function agentHello(info = {}) {
  const id = String(info.device || info.host || 'default').slice(0, 64);
  const d = getDevice(id, true);
  const was = isOnline(d);
  d.host = String(info.host || '').slice(0, 60);
  d.user = String(info.user || '').slice(0, 40);
  d.os = String(info.os || '').slice(0, 60);
  d.caps = Array.isArray(info.caps) ? info.caps.map((c) => String(c).slice(0, 24)).slice(0, 40) : [];
  d.lastSeen = now();
  if (!was) broadcastDevices();
  return deviceView(d);
}

export function agentPoll(deviceId, waitMs = 25_000) {
  const d = getDevice(deviceId, true);
  d.lastSeen = now();
  if (d.queue.length) return Promise.resolve(d.queue.shift());
  return new Promise((resolve) => {
    const waiter = { resolve: null, timer: null };
    waiter.timer = setTimeout(() => {
      const i = d.pollWaiters.indexOf(waiter);
      if (i >= 0) d.pollWaiters.splice(i, 1);
      resolve(null);
    }, Math.min(Math.max(waitMs, 1000), 50_000));
    waiter.resolve = (cmd) => { clearTimeout(waiter.timer); resolve(cmd); };
    d.pollWaiters.push(waiter);
  });
}

export function agentResult(id, payload = {}) {
  const result = {
    id,
    device: payload.device || null,
    ok: payload.ok !== false,
    data: payload.data ?? null,
    error: payload.error || null,
    at: now()
  };
  results.set(id, result);
  const waiters = resultWaiters.get(id);
  if (waiters) {
    for (const w of waiters) { clearTimeout(w.timer); w.resolve(result); }
    resultWaiters.delete(id);
  }
  broadcast('result', result);   // 截图等大字段也走 SSE，省一次轮询
  if (payload.device) { const d = getDevice(payload.device); if (d) d.lastSeen = now(); }
  sweepResults();
  return result;
}

// ---- Controller 侧 ----
export function enqueueCommand(deviceId, action, args = {}) {
  const d = resolveDevice(deviceId);
  if (!d || !isOnline(d)) throw new Error('目标 Mac 未连接');
  if (d.queue.length >= MAX_QUEUE) throw new Error('指令积压过多，请稍后再试');
  const cmd = { id: uid('cmd_', 12), device: d.id, action: String(action), args: args || {}, at: now() };
  const waiter = d.pollWaiters.shift();
  if (waiter) waiter.resolve(cmd);     // 有 agent 在等 → 直接投递
  else d.queue.push(cmd);              // 否则排队，等下次 poll
  return cmd.id;
}

export function waitResult(id, waitMs = 30_000) {
  const existing = results.get(id);
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve) => {
    const waiter = { resolve: null, timer: null };
    waiter.timer = setTimeout(() => {
      const arr = resultWaiters.get(id);
      if (arr) {
        const i = arr.indexOf(waiter);
        if (i >= 0) arr.splice(i, 1);
        if (!arr.length) resultWaiters.delete(id);
      }
      resolve(null);
    }, Math.min(Math.max(waitMs, 1000), 60_000));
    waiter.resolve = (r) => { clearTimeout(waiter.timer); resolve(r); };
    if (!resultWaiters.has(id)) resultWaiters.set(id, []);
    resultWaiters.get(id).push(waiter);
  });
}

// ---- 控制台 SSE ----
export function addController(client) {
  controllers.add(client);
  client.onUnsub = () => controllers.delete(client);
  client.send('devices', { devices: listDevices() });
}
function broadcast(event, data) {
  for (const c of controllers) c.send(event, data);
}
function broadcastDevices() {
  broadcast('devices', { devices: listDevices() });
}

// ---- 流式通道（WebSocket）：鼠标实时控制，按设备路由 ----
export function attachAgentStream(deviceId, conn) {
  const d = getDevice(deviceId, true);
  if (d.ws && d.ws !== conn) d.ws.close();
  d.ws = conn;
  d.lastSeen = now();
  conn.onmessage = () => { d.lastSeen = now(); };               // agent 心跳/回执
  conn.onclose = () => { if (d.ws === conn) { d.ws = null; broadcastDevices(); } };
  broadcastDevices();
}

export function attachControllerStream(conn, deviceId) {
  conn.onmessage = (raw) => {
    const d = resolveDevice(deviceId);
    if (d && d.ws) d.ws.send(raw);                              // 透传给目标 agent
  };
  conn.onclose = () => { /* 无状态，自动清理 */ };
}

function sweepResults() {
  if (results.size < 200) {
    const cutoff = now() - RESULT_TTL;
    for (const [id, r] of results) if (r.at < cutoff) results.delete(id);
    return;
  }
  results.clear();   // 兜底防泄漏
}
