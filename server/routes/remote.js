// 远程控制 Mac · 接口层
//
//   Agent（Mac）侧（带 REMOTE_TOKEN）:
//     POST /api/remote/agent/hello    注册 / 心跳，上报主机信息与能力
//     GET  /api/remote/agent/poll     长轮询拉取下一条指令
//     POST /api/remote/agent/result   回传指令执行结果（截图等大字段在这里）
//   Controller（手机/电脑浏览器）侧（带 REMOTE_TOKEN）:
//     GET  /api/remote/status         Mac 是否在线 / 能力 / 可用动作清单
//     POST /api/remote/command        下发一条指令，返回 { id }
//     GET  /api/remote/result/:id     长轮询取结果（SSE 之外的兜底）
//     GET  /api/remote/events         SSE：agent 上下线 + 指令结果实时推送
//
// 鉴权：统一用 REMOTE_TOKEN（环境变量）。未配置 = 功能关闭（503），默认安全。
import { GET, POST, openSSE, ApiError } from '../lib/httpx.js';
import * as remote from '../lib/remote.js';

// 控制台可下发的动作白名单（也用于驱动 UI）。是否真正可执行取决于 agent 端能力开关。
export const REMOTE_ACTIONS = [
  { action: 'lock', label: '锁屏', group: 'power' },
  { action: 'sleep', label: '睡眠', group: 'power' },
  { action: 'restart', label: '重启', group: 'power', danger: true, needs: 'power' },
  { action: 'shutdown', label: '关机', group: 'power', danger: true, needs: 'power' },
  { action: 'volume', label: '音量', group: 'media' },   // args: { level?:0-100, mute?:bool, delta?:±N }
  { action: 'brightness', label: '亮度', group: 'media' }, // args: { cmd:'up'|'down', steps?:1-10 }
  { action: 'media', label: '播放控制', group: 'media' }, // args: { cmd:'playpause'|'next'|'prev' }
  { action: 'screenshot', label: '截屏', group: 'view' },
  { action: 'camera', label: '摄像头', group: 'view', needs: 'camera' }, // 需 imagesnap
  { action: 'mouse', label: '鼠标', group: 'input' },     // args: { dx?,dy?, click?:'left'|'right'|'double' }
  { action: 'open', label: '打开', group: 'app' },        // args: { target:'https://..'|'AppName' }
  { action: 'shortcut', label: '快捷指令', group: 'app' },// args: { name } 或 { list:true }
  { action: 'say', label: '朗读', group: 'app' },         // args: { text }
  { action: 'notify', label: '通知', group: 'app' },      // args: { text, title? }
  { action: 'type', label: '输入文字', group: 'input' },  // args: { text }
  { action: 'clipboard', label: '剪贴板', group: 'input' },// args: { set?:string }（不传=读取）
  { action: 'shell', label: '执行命令', group: 'shell', danger: true, needs: 'shell' } // args: { cmd }
];
const ACTION_SET = new Set(REMOTE_ACTIONS.map((a) => a.action));

function ensureEnabled() {
  if (!remote.remoteEnabled()) {
    throw new ApiError(503, '远程控制未启用：请在服务端 .env 设置 REMOTE_TOKEN 后重启');
  }
}
function auth(ctx) {
  ensureEnabled();
  if (!remote.checkToken(remote.remoteToken(ctx))) throw new ApiError(401, '令牌无效');
}

// ===== Agent 侧 =====
POST('/api/remote/agent/hello', async (ctx) => {
  auth(ctx);
  return remote.agentHello(ctx.body || {});
});

GET('/api/remote/agent/poll', async (ctx) => {
  auth(ctx);
  const wait = Math.min(Number(ctx.query.get('wait')) || 25000, 50000);
  const cmd = await remote.agentPoll(wait);
  return cmd ? { command: cmd } : { command: null };
});

POST('/api/remote/agent/result', async (ctx) => {
  auth(ctx);
  const { id, ...payload } = ctx.body || {};
  if (!id) throw new ApiError(400, '缺少指令 id');
  return remote.agentResult(id, payload);
}, { maxBody: 16 * 1024 * 1024 });   // 截图 base64 可能较大

// ===== Controller 侧 =====
GET('/api/remote/status', async (ctx) => {
  auth(ctx);
  return { ...remote.agentStatus(), actions: REMOTE_ACTIONS };
});

POST('/api/remote/command', async (ctx) => {
  auth(ctx);
  const action = String(ctx.body?.action || '');
  if (!ACTION_SET.has(action)) throw new ApiError(400, '未知动作');
  let id;
  try { id = remote.enqueueCommand(action, ctx.body?.args || {}); }
  catch (e) { throw new ApiError(409, e.message); }
  // 顺手等一小会儿，能在同一请求里返回结果就直接给（截图/剪贴板等读取型很方便）
  const wait = Math.min(Number(ctx.body?.wait) || 0, 60000);
  if (wait > 0) {
    const result = await remote.waitResult(id, wait);
    return { id, result };
  }
  return { id };
});

GET('/api/remote/result/:id', async (ctx) => {
  auth(ctx);
  const wait = Math.min(Number(ctx.query.get('wait')) || 1, 60000);
  const result = await remote.waitResult(ctx.params.id, wait);
  return { result: result || null };
});

GET('/api/remote/events', async (ctx) => {
  auth(ctx);
  const client = openSSE(ctx.req, ctx.res);
  remote.addController(client);
});
