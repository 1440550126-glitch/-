// 迷雾庄园·凶夜 专项集成测试：6 真人完整对局（覆盖随机小丑角色与第三方胜利）
// 运行：npm run test:horror  （自起隔离服务、随机空闲端口、测完自关）
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const PORT = Number(process.env.HORROR_PORT) || (3400 + Math.floor(Math.random() * 1500));
const BASE = `http://localhost:${PORT}`;
const DB = `/tmp/jvling-horror-${Date.now()}-${PORT}.sqlite`;
const VALID = ['killer', 'medium', 'guard', 'survivor', 'jester'];
let pass = 0, fail = 0;
const ok = (n, c, x = '') => { if (c) { pass++; console.log('  ✅', n); } else { fail++; console.log('  ❌', n, x); } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, url, { token, body } = {}) {
  const res = await fetch(BASE + url, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: body ? JSON.stringify(body) : undefined });
  return { status: res.status, ...(await res.json().catch(() => ({}))) };
}
function sse(url, token) {
  const events = []; const ctrl = new AbortController();
  (async () => { try {
    const res = await fetch(BASE + url + '?token=' + token, { signal: ctrl.signal });
    const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = '';
    for (;;) { const { done, value } = await reader.read(); if (done) break; buf += dec.decode(value, { stream: true });
      let i; while ((i = buf.indexOf('\n\n')) >= 0) { const c = buf.slice(0, i); buf = buf.slice(i + 2);
        let ev = 'message', d = ''; for (const ln of c.split('\n')) { if (ln.startsWith('event: ')) ev = ln.slice(7); if (ln.startsWith('data: ')) d += ln.slice(6); }
        if (d) { try { events.push({ event: ev, data: JSON.parse(d) }); } catch { /* skip */ } } } }
  } catch { /* aborted */ } })();
  return { events, close: () => ctrl.abort() };
}

const server = spawn('node', ['--disable-warning=ExperimentalWarning', path.join(ROOT, 'server', 'index.js')], {
  env: { ...process.env, PORT: String(PORT), DB_PATH: DB, WARMUP_AUTOSTART: '0', LLM_PROVIDER: 'none' }, stdio: ['ignore', 'ignore', 'inherit']
});
let stream;
try {
  for (let i = 0; i < 40; i++) { try { const r = await fetch(BASE + '/api/health'); if (r.ok) break; } catch { /* retry */ } await sleep(250); }
  console.log('== 迷雾庄园·凶夜（6 真人完整对局） ==');
  const gs = [];
  for (let i = 0; i < 6; i++) gs.push((await api('POST', '/api/auth/guest', { body: {} })).data);
  const host = gs[0];
  const id = (await api('POST', '/api/rooms', { token: host.token, body: { name: '凶夜', game_type: 'horror', max_players: 8, allow_bots: false } })).data.room.id;
  stream = sse(`/api/rooms/${id}/events`, host.token);
  for (const g of gs.slice(1)) await api('POST', `/api/rooms/${id}/join`, { token: g.token });
  for (const g of gs) await api('POST', `/api/rooms/${id}/ready`, { token: g.token, body: { ready: true } });
  ok('6 真人开局', (await api('POST', `/api/rooms/${id}/start`, { token: host.token })).ok);
  await sleep(400);
  const st0 = (await api('GET', `/api/rooms/${id}`, { token: host.token })).data.room;
  ok('满 6 人就座', st0.players.length === 6);
  const roles = [];
  for (const g of gs) roles.push((await api('GET', `/api/rooms/${id}`, { token: g.token })).data.room.my_role);
  ok('身份均合法', roles.every((r) => VALID.includes(r)), roles.join(','));
  ok('身份卡含阵营标签', !!st0.my_role_info?.camp_label);

  let done = false;
  for (let t = 0; t < 500 && !done; t++) {
    for (const g of gs) {
      const r = (await api('GET', `/api/rooms/${id}`, { token: g.token })).data.room;
      if (r.status === 'ended') { done = true; break; }
      const me = r.players.find((x) => x.user_id === g.user.id);
      if (!me?.alive) continue;
      const n = r.my_night;
      try {
        if (r.phase === 'night' && n && !n.acted) {
          if ((n.targets || []).length) await api('POST', `/api/rooms/${id}/action`, { token: g.token, body: { action: n.action, target_seat: n.targets[0].seat } });
          else if (n.can_skip) await api('POST', `/api/rooms/${id}/action`, { token: g.token, body: { action: 'skip' } });
        } else if (r.phase === 'speak' && r.turn_seat === me.seat) {
          await api('POST', `/api/rooms/${id}/speak`, { token: g.token, body: { content: '我没动过' } });
        } else if (r.phase === 'vote' && !me.voted) {
          const tg = r.players.find((x) => x.alive && x.user_id !== g.user.id);
          if (tg) await api('POST', `/api/rooms/${id}/vote`, { token: g.token, body: { target_seat: tg.seat } });
        }
      } catch { /* 状态竞争属正常 */ }
    }
    if (!done) await sleep(250);
  }
  ok('6 人局完整跑完', done);
  await sleep(300);
  const end = [...stream.events].reverse().find((e) => e.event === 'state' && e.data.status === 'ended')?.data;
  ok('胜负方 ∈ {survivor,killer,jester}', ['survivor', 'killer', 'jester'].includes(end?.winner), String(end?.winner));
  ok('揭晓全部 6 人身份且合法', end?.reveal?.length === 6 && end.reveal.every((r) => VALID.includes(r.role)));
  ok('随机灵异事件已触发', stream.events.some((e) => e.event === 'msg' && (e.data.content || '').includes('灵异事件')));
  console.log(`  ℹ 身份组合=[${roles.join(',')}] 胜方=${end?.winner}${roles.includes('jester') ? ' 🃏含小丑' : ''}`);
} catch (e) { console.error('💥', e); fail++; } finally { stream?.close(); server.kill('SIGKILL'); }
console.log(`\n========== 凶夜专项：${pass} 通过 / ${fail} 失败 ==========\n`);
process.exit(fail ? 1 : 0);
