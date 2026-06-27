// 远程控制 Mac · 中继冒烟测试（多设备 + 指令 + 流式）
// 起服务端（带 REMOTE_TOKEN），用 fetch/WebSocket 扮演多台「Mac agent」和「浏览器控制台」，
// 验证：鉴权 / 多设备上下线与路由 / 指令往返 / 新增动作 / 轮询兜底 / SSE / WS 流式与设备隔离。
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3211;
const BASE = `http://localhost:${PORT}`;
const WSB = `ws://localhost:${PORT}`;
const DB = `/tmp/jvling-remote-smoke-${Date.now()}.sqlite`;
const TOKEN = 'test-remote-token-0123456789abcdef';

let passed = 0, failed = 0;
const ok = (name, cond, extra = '') => {
  if (cond) { passed++; console.log(`  ✅ ${name}`); }
  else { failed++; console.log(`  ❌ ${name} ${extra}`); }
};

async function api(method, url, { token, body } = {}) {
  const res = await fetch(BASE + url, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { 'X-Remote-Token': token } : {}) },
    body: body ? JSON.stringify(body) : undefined
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, ...json };
}
const findDev = (st, id) => (st.data.devices || []).find((d) => d.device === id);
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// 一台假 Mac：HTTP 心跳 + 长轮询拉指令、把指令回显成结果
function fakeAgent(device, capsList) {
  let stop = false;
  const H = { 'Content-Type': 'application/json', 'X-Remote-Token': TOKEN };
  const hello = () => fetch(`${BASE}/api/remote/agent/hello`, { method: 'POST', headers: H, body: JSON.stringify({ device, host: device, user: 'tester', os: 'macOS test', caps: capsList }) });
  (async () => {
    await hello();
    while (!stop) {
      try {
        const r = await fetch(`${BASE}/api/remote/agent/poll?wait=3000&device=${device}`, { headers: H });
        const { data } = await r.json();
        const cmd = data?.command;
        if (!cmd) continue;
        const result = { id: cmd.id, device, ok: true, data: `did:${cmd.action}@${device}` };
        if (cmd.action === 'screenshot' || cmd.action === 'camera') result.data = { image: 'data:image/jpeg;base64,AAAA' };
        if (cmd.action === 'volume') result.data = { level: cmd.args.level ?? 50, muted: false };
        if (cmd.action === 'mouse') result.data = cmd.args.click ? `点击:${cmd.args.click}` : `移动 ${cmd.args.dx || 0},${cmd.args.dy || 0}`;
        if (cmd.action === 'shortcut' && cmd.args.list) result.data = { shortcuts: ['打开灯', '回家模式'] };
        if (cmd.action === 'recv_file') {
          const rr = await fetch(`${BASE}/api/remote/agent/transfer/${cmd.args.tid}`, { headers: H });
          const txt = await rr.text();
          result.data = { saved: `/Users/tester/Downloads/${cmd.args.name}`, got: txt, size: txt.length };
        }
        if (cmd.action === 'send_file') {
          const up = await fetch(`${BASE}/api/remote/agent/upload?device=${device}&name=out.txt`, { method: 'POST', headers: { ...H, 'Content-Type': 'application/octet-stream' }, body: 'world' });
          const uj = await up.json();
          result.data = { transfer: uj.data.id, name: 'out.txt', size: 5 };
        }
        await fetch(`${BASE}/api/remote/agent/result`, { method: 'POST', headers: H, body: JSON.stringify(result) });
      } catch { await delay(200); }
    }
  })();
  return { stop: () => { stop = true; } };
}

async function waitOnline(device, want = true) {
  for (let i = 0; i < 30; i++) {
    const st = await api('GET', '/api/remote/status', { token: TOKEN });
    if (!!findDev(st, device)?.online === want) return true;
    await delay(150);
  }
  return false;
}

const server = spawn('node', ['--disable-warning=ExperimentalWarning', path.join(__dirname, '..', 'server', 'index.js')], {
  env: { ...process.env, PORT: String(PORT), DB_PATH: DB, WARMUP_AUTOSTART: '0', LLM_PROVIDER: 'none', REMOTE_TOKEN: TOKEN },
  stdio: ['ignore', 'pipe', 'inherit']
});
server.stdout.on('data', () => {});

const CAPS = ['lock', 'volume', 'brightness', 'screenshot', 'mouse', 'shortcut', 'camera', 'shell'];
let agentA = null, agentB = null;
try {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(BASE + '/api/health'); if (r.ok) break; } catch { /* retry */ }
    await delay(250);
  }

  console.log('\n== 鉴权 ==');
  ok('无令牌被拒(401)', (await api('GET', '/api/remote/status')).status === 401);
  ok('错误令牌被拒(401)', (await api('GET', '/api/remote/status', { token: 'wrong' })).status === 401);

  console.log('\n== 离线态 ==');
  const offline = await api('GET', '/api/remote/status', { token: TOKEN });
  ok('正确令牌可查状态', offline.ok && Array.isArray(offline.data.devices) && Array.isArray(offline.data.actions));
  ok('设备列表为空', offline.data.devices.length === 0);
  ok('无在线设备时下发被拒(409)', (await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock' } })).status === 409);

  console.log('\n== 单设备上线 ==');
  agentA = fakeAgent('macA', CAPS);
  ok('macA 上线', await waitOnline('macA'));
  const st1 = await api('GET', '/api/remote/status', { token: TOKEN });
  ok('上报主机名', findDev(st1, 'macA')?.host === 'macA');

  console.log('\n== 指令往返（默认路由到唯一在线设备）==');
  const lock = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock', wait: 5000 } });
  ok('锁屏回传结果', lock.data.result?.data === 'did:lock@macA', JSON.stringify(lock));
  const shot = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'screenshot', wait: 5000 } });
  ok('截屏返回图片', shot.data.result?.data?.image?.startsWith('data:image/'));
  const vol = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'volume', args: { level: 33 }, wait: 5000 } });
  ok('音量返回 level', vol.data.result?.data?.level === 33);
  ok('未知动作被拒(400)', (await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: '__nope__' } })).status === 400);

  console.log('\n== 新增动作 ==');
  ok('亮度', (await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'brightness', args: { cmd: 'up' }, wait: 5000 } })).data.result?.data === 'did:brightness@macA');
  ok('鼠标移动', (await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'mouse', args: { dx: 50 }, wait: 5000 } })).data.result?.data === '移动 50,0');
  ok('鼠标点击', (await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'mouse', args: { click: 'left' }, wait: 5000 } })).data.result?.data === '点击:left');
  const scl = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'shortcut', args: { list: true }, wait: 5000 } });
  ok('快捷指令列表', scl.data.result?.data?.shortcuts?.length === 2);
  ok('摄像头返回图片', (await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'camera', wait: 5000 } })).data.result?.data?.image?.startsWith('data:image/'));

  console.log('\n== 多设备 ==');
  agentB = fakeAgent('macB', CAPS);
  ok('macB 上线', await waitOnline('macB'));
  const st2 = await api('GET', '/api/remote/status', { token: TOKEN });
  ok('两台设备都在线', st2.data.devices.filter((d) => d.online).length === 2);
  // 两台都在线时必须显式指定 device，否则歧义被拒
  ok('不指定设备且多台在线 → 拒绝(409)', (await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock' } })).status === 409);
  const toA = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'lock', wait: 5000 } });
  const toB = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macB', action: 'lock', wait: 5000 } });
  ok('指令路由到 macA', toA.data.result?.data === 'did:lock@macA' && toA.data.result?.device === 'macA');
  ok('指令路由到 macB', toB.data.result?.data === 'did:lock@macB' && toB.data.result?.device === 'macB');

  console.log('\n== 文件传输 ==');
  const up = await fetch(`${BASE}/api/remote/transfer/up?device=macA&name=test.txt`, { method: 'POST', headers: { 'X-Remote-Token': TOKEN, 'Content-Type': 'application/octet-stream' }, body: 'hello' });
  const uj = await up.json();
  ok('上传接口返回 id', uj.ok && !!uj.data.id);
  const ur = await api('GET', `/api/remote/result/${uj.data.id}?wait=6000`, { token: TOKEN });
  ok('Mac 收到上传文件内容', ur.data.result?.ok && ur.data.result?.data?.got === 'hello');
  const sf = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'send_file', args: { path: '/x' }, wait: 6000 } });
  const tid = sf.data.result?.data?.transfer;
  ok('下载命令返回 transfer id', !!tid);
  const dl = await fetch(`${BASE}/api/remote/file/${tid}`, { headers: { 'X-Remote-Token': TOKEN } });
  ok('浏览器下载到文件内容', (await dl.text()) === 'world');
  ok('取走后文件清理(再取 404)', (await fetch(`${BASE}/api/remote/file/${tid}`, { headers: { 'X-Remote-Token': TOKEN } })).status === 404);
  ok('文件接口无令牌被拒(401)', (await fetch(`${BASE}/api/remote/file/${tid}`)).status === 401);

  console.log('\n== 结果轮询兜底 ==');
  const queued = await api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'lock' } });
  ok('下发返回 id', !!queued.data.id);
  ok('按 id 轮询拿到结果', (await api('GET', `/api/remote/result/${queued.data.id}?wait=5000`, { token: TOKEN })).data.result?.ok === true);

  console.log('\n== SSE 推送 ==');
  const ctrl = new AbortController();
  const sseGot = (async () => {
    const res = await fetch(`${BASE}/api/remote/events?token=${TOKEN}`, { signal: ctrl.signal });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '', okDevices = false, okResult = false;
    const t = setTimeout(() => ctrl.abort(), 6000);
    setTimeout(() => api('POST', '/api/remote/command', { token: TOKEN, body: { device: 'macA', action: 'lock' } }), 300);
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        if (/event: devices/.test(buf)) okDevices = true;
        if (/event: result/.test(buf)) okResult = true;
        if (okDevices && okResult) break;
      }
    } catch { /* aborted */ }
    clearTimeout(t); ctrl.abort();
    return okDevices && okResult;
  })();
  ok('SSE 收到 devices + result 事件', await sseGot);

  console.log('\n== 流式触控板（WebSocket）+ 设备隔离 ==');
  const agentWS = new WebSocket(`${WSB}/api/remote/agent/ws?token=${TOKEN}&device=macA`);
  await new Promise((res, rej) => { const t = setTimeout(() => rej(new Error('agentWS 超时')), 5000); agentWS.addEventListener('open', () => { clearTimeout(t); res(); }); agentWS.addEventListener('error', () => {}); });
  ok('macA 流式上线(status.stream)', await (async () => { for (let i = 0; i < 20; i++) { const st = await api('GET', '/api/remote/status', { token: TOKEN }); if (findDev(st, 'macA')?.stream) return true; await delay(100); } return false; })());
  ok('错误令牌 WS 被拒', await new Promise((res) => { const b = new WebSocket(`${WSB}/api/remote/stream?token=wrong&device=macA`); b.addEventListener('open', () => res(false)); b.addEventListener('error', () => res(true)); b.addEventListener('close', () => res(true)); setTimeout(() => res(false), 3000); }));

  // 收集 agentWS 收到的消息
  const inbox = [];
  agentWS.addEventListener('message', (ev) => inbox.push(typeof ev.data === 'string' ? ev.data : String(ev.data)));
  // 控制台指向 macA 发移动 → agentWS(macA) 应收到
  const cA = new WebSocket(`${WSB}/api/remote/stream?token=${TOKEN}&device=macA`);
  await new Promise((r) => { cA.addEventListener('open', r); cA.addEventListener('error', r); });
  cA.send(JSON.stringify({ t: 'm', dx: 7, dy: 2 }));
  await delay(400);
  ok('移动经中继送达 macA', inbox.some((m) => { try { const j = JSON.parse(m); return j.t === 'm' && j.dx === 7; } catch { return false; } }));
  // 控制台指向 macB 发移动 → agentWS(macA) 不应收到
  const before = inbox.length;
  const cB = new WebSocket(`${WSB}/api/remote/stream?token=${TOKEN}&device=macB`);
  await new Promise((r) => { cB.addEventListener('open', r); cB.addEventListener('error', r); });
  cB.send(JSON.stringify({ t: 'm', dx: 99, dy: 99 }));
  await delay(400);
  ok('发往 macB 的消息不会串到 macA', inbox.slice(before).every((m) => { try { return JSON.parse(m).dx !== 99; } catch { return true; } }));
  agentWS.close(); cA.close(); cB.close();

} catch (e) {
  console.error(e);
  failed++;
} finally {
  agentA?.stop();
  agentB?.stop();
  server.kill('SIGTERM');
}

console.log(`\n${failed ? '❌' : '✅'} 远程控制冒烟：${passed} 通过 / ${failed} 失败`);
process.exit(failed ? 1 : 0);
