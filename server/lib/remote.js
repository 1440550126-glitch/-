// 远程控制 Mac · 中继核心（内存态，单实例够用；集群化后换 Redis/消息队列）
//
// 角色：
//   - Agent（跑在 Mac 上的 mac-agent/agent.mjs）：长轮询拉取指令、回传结果，定时心跳。
//   - Controller（手机/电脑浏览器里的控制台 web/remote.html）：下发指令、看结果、订阅 SSE。
// 中继不持久化指令（远程控制天然是瞬时的），只在内存里排队 + 短期保留结果。
import crypto from 'node:crypto';
import { now, uid } from './util.js';

const TOKEN = (process.env.REMOTE_TOKEN || '').trim();
const ONLINE_TTL = 40_000;        // 超过这个时间没心跳就算离线
const RESULT_TTL = 5 * 60_000;    // 结果保留 5 分钟供轮询兜底
const MAX_QUEUE = 50;             // 待执行指令上限（防积压）

export const remoteEnabled = () => !!TOKEN;

// 弱 token 警告（仅提示，不阻断）
export function remoteTokenWeak() {
  return remoteEnabled() && TOKEN.length < 16;
}

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
const state = {
  agent: null,                 // { host, user, os, caps:[], lastSeen }
  queue: [],                   // 待下发指令 [{ id, action, args, at }]
  pollWaiters: [],             // agent 长轮询挂起的 resolve [{ resolve, timer }]
  results: new Map(),          // id -> { id, ok, data, error, at }
  resultWaiters: new Map(),    // id -> [{ resolve, timer }]
  controllers: new Set()       // SSE 客户端
};

export function agentOnline() {
  return !!state.agent && now() - state.agent.lastSeen < ONLINE_TTL;
}

export function agentStatus() {
  const online = agentOnline();
  return {
    online,
    host: state.agent?.host || null,
    user: state.agent?.user || null,
    os: state.agent?.os || null,
    caps: state.agent?.caps || [],
    last_seen: state.agent?.lastSeen || null,
    queued: state.queue.length
  };
}

// ---- Agent 侧 ----
export function agentHello(info = {}) {
  const wasOnline = agentOnline();
  state.agent = {
    host: String(info.host || '').slice(0, 60),
    user: String(info.user || '').slice(0, 40),
    os: String(info.os || '').slice(0, 60),
    caps: Array.isArray(info.caps) ? info.caps.map((c) => String(c).slice(0, 24)).slice(0, 40) : [],
    lastSeen: now()
  };
  if (!wasOnline) broadcast('agent', agentStatus());
  return agentStatus();
}

// agent 长轮询：有指令立刻返回，否则挂起到 waitMs 后返回 null
export function agentPoll(waitMs = 25_000) {
  if (state.agent) state.agent.lastSeen = now();
  if (state.queue.length) return Promise.resolve(state.queue.shift());
  return new Promise((resolve) => {
    const waiter = { resolve: null, timer: null };
    waiter.timer = setTimeout(() => {
      const i = state.pollWaiters.indexOf(waiter);
      if (i >= 0) state.pollWaiters.splice(i, 1);
      resolve(null);
    }, Math.min(Math.max(waitMs, 1000), 50_000));
    waiter.resolve = (cmd) => { clearTimeout(waiter.timer); resolve(cmd); };
    state.pollWaiters.push(waiter);
  });
}

export function agentResult(id, payload = {}) {
  const result = {
    id,
    ok: payload.ok !== false,
    data: payload.data ?? null,
    error: payload.error || null,
    at: now()
  };
  state.results.set(id, result);
  const waiters = state.resultWaiters.get(id);
  if (waiters) {
    for (const w of waiters) { clearTimeout(w.timer); w.resolve(result); }
    state.resultWaiters.delete(id);
  }
  // 结果广播给控制台（截图等大字段也走 SSE，省一次轮询）
  broadcast('result', result);
  sweepResults();
  if (state.agent) state.agent.lastSeen = now();
  return result;
}

// ---- Controller 侧 ----
export function enqueueCommand(action, args = {}) {
  if (!agentOnline()) throw new Error('Mac 未连接（agent 离线）');
  if (state.queue.length >= MAX_QUEUE) throw new Error('指令积压过多，请稍后再试');
  const cmd = { id: uid('cmd_', 12), action: String(action), args: args || {}, at: now() };
  const waiter = state.pollWaiters.shift();
  if (waiter) waiter.resolve(cmd);     // 有 agent 在等 → 直接投递
  else state.queue.push(cmd);          // 否则排队，等下次 poll
  return cmd.id;
}

export function waitResult(id, waitMs = 30_000) {
  const existing = state.results.get(id);
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve) => {
    const waiter = { resolve: null, timer: null };
    waiter.timer = setTimeout(() => {
      const arr = state.resultWaiters.get(id);
      if (arr) {
        const i = arr.indexOf(waiter);
        if (i >= 0) arr.splice(i, 1);
        if (!arr.length) state.resultWaiters.delete(id);
      }
      resolve(null);
    }, Math.min(Math.max(waitMs, 1000), 60_000));
    waiter.resolve = (r) => { clearTimeout(waiter.timer); resolve(r); };
    if (!state.resultWaiters.has(id)) state.resultWaiters.set(id, []);
    state.resultWaiters.get(id).push(waiter);
  });
}

// ---- 控制台 SSE ----
export function addController(client) {
  state.controllers.add(client);
  client.onUnsub = () => state.controllers.delete(client);
  client.send('agent', agentStatus());
}
function broadcast(event, data) {
  for (const c of state.controllers) c.send(event, data);
}

function sweepResults() {
  if (state.results.size < 200) {
    const cutoff = now() - RESULT_TTL;
    for (const [id, r] of state.results) if (r.at < cutoff) state.results.delete(id);
    return;
  }
  state.results.clear();   // 兜底防泄漏
}
