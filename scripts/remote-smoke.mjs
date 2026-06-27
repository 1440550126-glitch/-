// 远程控制 Mac · 中继冒烟测试
// 起一个服务端（带 REMOTE_TOKEN），用 fetch 同时扮演「Mac agent」和「浏览器控制台」，
// 验证：鉴权 / 上线状态 / 指令下发→agent拉取→回传→控制台拿到结果 / SSE 推送 / 离线拒发。
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3211;
const BASE = `http://localhost:${PORT}`;
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

const server = spawn('node', ['--disable-warning=ExperimentalWarning', path.join(__dirname, '..', 'server', 'index.js')], {
  env: { ...process.env, PORT: String(PORT), DB_PATH: DB, WARMUP_AUTOSTART: '0', LLM_PROVIDER: 'none', REMOTE_TOKEN: TOKEN },
  stdio: ['ignore', 'pipe', 'inherit']
});
server.stdout.on('data', () => {});

// 极简「Mac agent」：心跳 + 持续长轮询拉指令、把指令回显成结果
function fakeAgent() {
  let stop = false;
  const H = { 'Content-Type': 'application/json', 'X-Remote-Token': TOKEN };
  const hello = () => fetch(`${BASE}/api/remote/agent/hello`, { method: 'POST', headers: H, body: JSON.stringify({ host: 'FakeMac', user: 'tester', os: 'macOS test', caps: ['lock', 'volume', 'screenshot', 'shell'] }) });
  (async () => {
    await hello();
    while (!stop) {
      try {
        const r = await fetch(`${BASE}/api/remote/agent/poll?wait=3000`, { headers: H });
        const { data } = await r.json();
        const cmd = data?.command;
        if (!cmd) continue;
        let result = { id: cmd.id, ok: true, data: `did:${cmd.action}` };
        if (cmd.action === 'screenshot') result.data = { image: 'data:image/jpeg;base64,AAAA' };
        if (cmd.action === 'volume') result.data = { level: cmd.args.level ?? 50, muted: false };
        await fetch(`${BASE}/api/remote/agent/result`, { method: 'POST', headers: H, body: JSON.stringify(result) });
      } catch { await new Promise((r) => setTimeout(r, 200)); }
    }
  })();
  return { stop: () => { stop = true; } };
}

let agent = null;
try {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(BASE + '/api/health'); if (r.ok) break; } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 250));
  }

  console.log('\n== 鉴权 ==');
  const noToken = await api('GET', '/api/remote/status');
  ok('无令牌被拒(401)', noToken.status === 401, JSON.stringify(noToken));
  const badToken = await api('GET', '/api/remote/status', { token: 'wrong' });
  ok('错误令牌被拒(401)', badToken.status === 401);

  console.log('\n== 离线态 ==');
  const offline = await api('GET', '/api/remote/status', { token: TOKEN });
  ok('正确令牌可查状态', offline.ok && Array.isArray(offline.data.actions));
  ok('agent 离线', offline.data.online === false);
  const rejected = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock' } });
  ok('离线时下发被拒(409)', rejected.status === 409, JSON.stringify(rejected));

  console.log('\n== 上线 ==');
  agent = fakeAgent();
  let online = false;
  for (let i = 0; i < 30; i++) {
    const s = await api('GET', '/api/remote/status', { token: TOKEN });
    if (s.data.online) { online = true; ok('agent 上线 + 上报主机', s.data.host === 'FakeMac'); break; }
    await new Promise((r) => setTimeout(r, 200));
  }
  ok('检测到 agent 在线', online);

  console.log('\n== 指令往返 ==');
  const lock = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock', wait: 5000 } });
  ok('锁屏指令回传结果', lock.ok && lock.data.result?.ok && lock.data.result.data === 'did:lock', JSON.stringify(lock));
  const shot = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'screenshot', wait: 5000 } });
  ok('截屏返回图片', shot.data.result?.data?.image?.startsWith('data:image/'), JSON.stringify(shot).slice(0, 120));
  const vol = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'volume', args: { level: 33 }, wait: 5000 } });
  ok('音量返回 level', vol.data.result?.data?.level === 33);
  const unknown = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: '__nope__' } });
  ok('未知动作被拒(400)', unknown.status === 400);

  console.log('\n== 结果轮询兜底 ==');
  const queued = await api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock' } });
  ok('下发返回 id', !!queued.data.id);
  const polled = await api('GET', `/api/remote/result/${queued.data.id}?wait=5000`, { token: TOKEN });
  ok('按 id 轮询拿到结果', polled.data.result?.ok === true, JSON.stringify(polled));

  console.log('\n== SSE 推送 ==');
  const ctrl = new AbortController();
  const sseDone = (async () => {
    const res = await fetch(`${BASE}/api/remote/events?token=${TOKEN}`, { signal: ctrl.signal });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    let gotResult = false;
    const t = setTimeout(() => ctrl.abort(), 6000);
    // 触发一条指令，应当通过 SSE 收到 result
    setTimeout(() => api('POST', '/api/remote/command', { token: TOKEN, body: { action: 'lock' } }), 300);
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        if (/event: result/.test(buf)) { gotResult = true; break; }
      }
    } catch { /* aborted */ }
    clearTimeout(t); ctrl.abort();
    return gotResult;
  })();
  ok('SSE 收到 result 事件', await sseDone);

} catch (e) {
  console.error(e);
  failed++;
} finally {
  agent?.stop();
  server.kill('SIGTERM');
}

console.log(`\n${failed ? '❌' : '✅'} 远程控制冒烟：${passed} 通过 / ${failed} 失败`);
process.exit(failed ? 1 : 0);
