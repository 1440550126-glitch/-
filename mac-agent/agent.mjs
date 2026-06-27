#!/usr/bin/env node
// 远程控制 Mac · Agent（跑在你的 Mac 上）
//
// 它主动连出中继服务器（所以 Mac 在 NAT/家庭网络后面也能被控），长轮询拉指令、回传结果。
// 零依赖：只用 Node 内置 fetch / child_process。需要 Node ≥ 18（建议 20+）。
//
// 跑起来：
//   REMOTE_SERVER=https://你的服务器  REMOTE_TOKEN=和服务端一样的口令  node mac-agent/agent.mjs
// 开机自启见 mac-agent/README.md（launchd）。
//
// 安全默认：
//   - 关机/重启需要  REMOTE_ALLOW_POWER=1
//   - 执行任意命令需要 REMOTE_ALLOW_SHELL=1
//   两者默认关闭。其余动作（锁屏/音量/播放/截屏/打开/朗读/通知/输入/剪贴板）默认开。
import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const pexec = promisify(execFile);

const SERVER = (process.env.REMOTE_SERVER || 'http://localhost:3000').replace(/\/+$/, '');
const TOKEN = (process.env.REMOTE_TOKEN || '').trim();
const ALLOW_POWER = process.env.REMOTE_ALLOW_POWER === '1';
const ALLOW_SHELL = process.env.REMOTE_ALLOW_SHELL === '1';
const SHOT_MAX_W = Number(process.env.REMOTE_SHOT_WIDTH) || 1400;

if (!TOKEN) {
  console.error('✗ 缺少 REMOTE_TOKEN（必须和服务端 .env 里的一致）');
  process.exit(1);
}
if (process.platform !== 'darwin') {
  console.warn('⚠ 当前不是 macOS，多数动作会失败；仅供调试。');
}

const HEADERS = { 'Content-Type': 'application/json', 'X-Remote-Token': TOKEN };

// 稳定的设备 ID（多台 Mac 用同一中继时区分），优先 env，否则持久化一个
const ID_FILE = path.join(os.homedir(), '.jvling-macagent-id');
function resolveDeviceId() {
  if (process.env.REMOTE_DEVICE_ID) return process.env.REMOTE_DEVICE_ID.slice(0, 64);
  try { const s = fs.readFileSync(ID_FILE, 'utf8').trim(); if (s) return s; } catch { /* 首次 */ }
  const id = (os.hostname().split('.')[0] || 'mac') + '-' + crypto.randomBytes(3).toString('hex');
  try { fs.writeFileSync(ID_FILE, id); } catch { /* 只读 home 也无妨，下次再生成 */ }
  return id;
}
const DEVICE = resolveDeviceId();

// 启动时探测可选的命令行工具是否可用（影响能力上报，让控制台置灰不可用动作）
let CAP_IMAGESNAP = false;
async function probeCaps() {
  CAP_IMAGESNAP = await has('imagesnap');
}
async function has(bin) {
  try { await pexec('which', [bin], { timeout: 3000 }); return true; } catch { return false; }
}

const UNLOCK_PW = process.env.REMOTE_UNLOCK_PASSWORD || '';
function caps() {
  const c = ['lock', 'sleep', 'volume', 'brightness', 'media', 'screenshot', 'mouse', 'open', 'shortcut', 'say', 'notify', 'type', 'clipboard', 'files'];
  if (CAP_IMAGESNAP) c.push('camera');
  if (UNLOCK_PW) c.push('unlock');
  if (ALLOW_POWER) c.push('restart', 'shutdown');
  if (ALLOW_SHELL) c.push('shell');
  return c;
}

// AppleScript 字符串字面量转义
const osaStr = (s) => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/[\r\n]+/g, ' ');
// 跑一段 AppleScript
const osa = (script) => pexec('osascript', ['-e', script], { timeout: 15000 });
// 跑一段 JXA（JavaScript for Automation），用于走 CoreGraphics 控制鼠标
const jxa = (script) => pexec('osascript', ['-l', 'JavaScript', '-e', script], { timeout: 8000 });

// ---- 动作实现 ----
const actions = {
  async lock() {
    // Ctrl+Cmd+Q = 立即锁屏
    await osa('tell application "System Events" to keystroke "q" using {control down, command down}');
    return '已锁屏';
  },
  async sleep() {
    await pexec('pmset', ['sleepnow'], { timeout: 8000 });
    return '已进入睡眠';
  },
  async unlock() {
    // 密码只存在 Mac 端环境变量里，永不经过网络/中继
    if (!UNLOCK_PW) throw new Error('未配置解锁密码（agent 端设 REMOTE_UNLOCK_PASSWORD=）');
    await pexec('caffeinate', ['-u', '-t', '2'], { timeout: 5000 }).catch(() => {});  // 唤醒屏幕
    await new Promise((r) => setTimeout(r, 700));
    await osa('tell application "System Events" to key code 123').catch(() => {});     // 抖一下唤起登录框
    await new Promise((r) => setTimeout(r, 300));
    await osa(`tell application "System Events" to keystroke "${osaStr(UNLOCK_PW)}"`);
    await osa('tell application "System Events" to key code 36');                       // 回车
    return '已尝试解锁';
  },
  async restart() {
    if (!ALLOW_POWER) throw new Error('重启被禁用（agent 需 REMOTE_ALLOW_POWER=1）');
    await osa('tell application "System Events" to restart');
    return '正在重启';
  },
  async shutdown() {
    if (!ALLOW_POWER) throw new Error('关机被禁用（agent 需 REMOTE_ALLOW_POWER=1）');
    await osa('tell application "System Events" to shut down');
    return '正在关机';
  },
  async volume(args = {}) {
    if (args.mute !== undefined) {
      await osa(`set volume output muted ${args.mute ? 'true' : 'false'}`);
    }
    let level = args.level;
    if (args.delta !== undefined) {
      const cur = await actions._getVolume();
      level = Math.max(0, Math.min(100, cur + Number(args.delta)));
    }
    if (level !== undefined) {
      level = Math.max(0, Math.min(100, Math.round(Number(level))));
      await osa(`set volume output volume ${level}`);
    }
    const out = await actions._getVolume();
    const muted = (await osa('output muted of (get volume settings)')).stdout.trim() === 'true';
    return { level: out, muted };
  },
  async _getVolume() {
    const { stdout } = await osa('output volume of (get volume settings)');
    return Number(stdout.trim()) || 0;
  },
  async media(args = {}) {
    const cmd = String(args.cmd || 'playpause');
    const verb = { playpause: 'playpause', play: 'play', pause: 'pause', next: 'next track', prev: 'previous track', previous: 'previous track' }[cmd];
    if (!verb) throw new Error('未知播放指令');
    // 优先 Spotify（在运行的话），否则 Music
    const app = await actions._mediaApp();
    await osa(`tell application "${app}" to ${verb}`);
    return `${app}: ${cmd}`;
  },
  async _mediaApp() {
    try {
      const { stdout } = await osa('tell application "System Events" to (name of processes) contains "Spotify"');
      if (stdout.trim() === 'true') return 'Spotify';
    } catch { /* ignore */ }
    return 'Music';
  },
  async brightness(args = {}) {
    // 用屏幕亮度媒体键（key code 144=调亮 / 145=调暗），无需第三方工具
    const dir = String(args.cmd || 'up') === 'down' ? 145 : 144;
    const steps = Math.max(1, Math.min(10, Number(args.steps) || 1));
    for (let i = 0; i < steps; i++) await osa(`tell application "System Events" to key code ${dir}`);
    return `亮度 ${dir === 145 ? '-' : '+'}${steps}`;
  },
  async mouse(args = {}) {
    const dx = Number(args.dx) || 0;
    const dy = Number(args.dy) || 0;
    const click = ['left', 'right', 'double'].includes(args.click) ? args.click : null;
    if (!dx && !dy && !click) throw new Error('鼠标动作为空');
    const btn = click === 'right' ? 1 : 0;          // kCGMouseButtonLeft=0 / Right=1
    const down = btn ? 3 : 1, up = btn ? 4 : 2;     // right/left MouseDown/Up
    const lines = [
      "ObjC.import('CoreGraphics');",
      'var src = $.CGEventCreate(null);',
      'var loc = $.CGEventGetLocation(src);',
      `var pt = { x: loc.x + (${dx}), y: loc.y + (${dy}) };`
    ];
    if (dx || dy) lines.push('$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 5, pt, 0));'); // 5=mouseMoved
    if (click) {
      lines.push(`$.CGEventPost(0, $.CGEventCreateMouseEvent(null, ${down}, pt, ${btn}));`);
      lines.push(`$.CGEventPost(0, $.CGEventCreateMouseEvent(null, ${up}, pt, ${btn}));`);
      if (click === 'double') {
        lines.push(`$.CGEventPost(0, $.CGEventCreateMouseEvent(null, ${down}, pt, ${btn}));`);
        lines.push(`$.CGEventPost(0, $.CGEventCreateMouseEvent(null, ${up}, pt, ${btn}));`);
      }
    }
    lines.push("'ok';");
    await jxa(lines.join('\n'));
    return click ? `点击:${click}` : `移动 ${dx},${dy}`;
  },
  async shortcut(args = {}) {
    if (args.list) {
      const { stdout } = await pexec('shortcuts', ['list'], { timeout: 8000, maxBuffer: 1024 * 1024 });
      return { shortcuts: stdout.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 300) };
    }
    const name = String(args.name || '').trim();
    if (!name) throw new Error('缺少快捷指令名称');
    await pexec('shortcuts', ['run', name], { timeout: 60000 });
    return `已运行快捷指令：${name}`;
  },
  async camera(args = {}) {
    if (!CAP_IMAGESNAP) throw new Error('需要 imagesnap：brew install imagesnap');
    const cap = path.join(os.tmpdir(), 'jvling-cam.jpg');
    const small = path.join(os.tmpdir(), 'jvling-cam-s.jpg');
    const warm = Math.max(0, Math.min(3, Number(args.warmup) || 1));
    await pexec('imagesnap', ['-w', String(warm), cap], { timeout: 15000 });
    let out = cap;
    try { await pexec('sips', ['-Z', '1000', '-s', 'format', 'jpeg', '-s', 'formatOptions', '70', cap, '--out', small]); out = small; }
    catch { /* 用原图 */ }
    const b64 = fs.readFileSync(out).toString('base64');
    try { fs.unlinkSync(cap); fs.unlinkSync(small); } catch { /* ignore */ }
    return { image: `data:image/jpeg;base64,${b64}` };
  },
  async screenshot() {
    const raw = path.join(os.tmpdir(), 'jvling-shot.png');
    const jpg = path.join(os.tmpdir(), 'jvling-shot.jpg');
    await pexec('screencapture', ['-x', '-C', raw], { timeout: 15000 });
    // 用 sips 压成 jpeg 并限制宽度，避免回传体积过大
    try {
      await pexec('sips', ['-Z', String(SHOT_MAX_W), '-s', 'format', 'jpeg', '-s', 'formatOptions', '70', raw, '--out', jpg], { timeout: 15000 });
    } catch {
      fs.copyFileSync(raw, jpg);
    }
    const b64 = fs.readFileSync(jpg).toString('base64');
    try { fs.unlinkSync(raw); fs.unlinkSync(jpg); } catch { /* ignore */ }
    return { image: `data:image/jpeg;base64,${b64}`, w: SHOT_MAX_W };
  },
  async open(args = {}) {
    const target = String(args.target || '').trim();
    if (!target) throw new Error('缺少打开目标');
    if (/^https?:\/\//i.test(target)) {
      await pexec('open', [target], { timeout: 8000 });
      return `已打开链接 ${target}`;
    }
    await pexec('open', ['-a', target], { timeout: 8000 });
    return `已打开应用 ${target}`;
  },
  async say(args = {}) {
    const text = String(args.text || '').slice(0, 500);
    if (!text) throw new Error('没有要朗读的文字');
    await pexec('say', [text], { timeout: 30000 });
    return '已朗读';
  },
  async notify(args = {}) {
    const text = osaStr(String(args.text || '').slice(0, 300));
    const title = osaStr(String(args.title || '远程控制').slice(0, 60));
    await osa(`display notification "${text}" with title "${title}"`);
    return '已发送通知';
  },
  async type(args = {}) {
    const text = osaStr(String(args.text || '').slice(0, 500));
    if (!text) throw new Error('没有要输入的文字');
    await osa(`tell application "System Events" to keystroke "${text}"`);
    return '已输入';
  },
  async clipboard(args = {}) {
    if (args.set !== undefined) {
      await new Promise((resolve, reject) => {
        const p = execFile('pbcopy', [], (e) => (e ? reject(e) : resolve()));
        p.stdin.end(String(args.set));
      });
      return { set: true };
    }
    const { stdout } = await pexec('pbpaste', [], { timeout: 5000, maxBuffer: 1024 * 1024 });
    return { text: stdout };
  },
  async recv_file(args = {}) {
    const tid = String(args.tid || '');
    if (!tid) throw new Error('缺少传输 id');
    const name = String(args.name || 'file').replace(/[/\\]/g, '_');
    const dest = path.join(os.homedir(), 'Downloads', name);
    const r = await fetch(`${SERVER}/api/remote/agent/transfer/${tid}`, { headers: { 'X-Remote-Token': TOKEN } });
    if (!r.ok) throw new Error(`下载失败 ${r.status}`);
    const buf = Buffer.from(await r.arrayBuffer());
    fs.writeFileSync(dest, buf);
    return { saved: dest, size: buf.length };
  },
  async send_file(args = {}) {
    let p = String(args.path || '').trim();
    if (!p) throw new Error('缺少文件路径');
    if (p === '~' || p.startsWith('~/')) p = path.join(os.homedir(), p.slice(1));
    if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) throw new Error('文件不存在');
    const name = path.basename(p);
    const buf = fs.readFileSync(p);
    const r = await fetch(`${SERVER}/api/remote/agent/upload?device=${encodeURIComponent(DEVICE)}&name=${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: { 'X-Remote-Token': TOKEN, 'Content-Type': 'application/octet-stream' },
      body: buf
    });
    if (!r.ok) throw new Error(`上传失败 ${r.status}`);
    const j = await r.json();
    return { transfer: j.data.id, name, size: buf.length };
  },
  async shell(args = {}) {
    if (!ALLOW_SHELL) throw new Error('执行命令被禁用（agent 需 REMOTE_ALLOW_SHELL=1）');
    const cmd = String(args.cmd || '');
    if (!cmd) throw new Error('空命令');
    const { stdout, stderr } = await pexec('/bin/sh', ['-c', cmd], { timeout: 60000, maxBuffer: 4 * 1024 * 1024 });
    return { stdout, stderr };
  }
};

async function runCommand(cmd) {
  const fn = actions[cmd.action];
  if (!fn || cmd.action.startsWith('_')) return { ok: false, error: `不支持的动作: ${cmd.action}` };
  try {
    const data = await fn(cmd.args || {});
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e.message || String(e) };
  }
}

async function post(p, body) {
  const r = await fetch(`${SERVER}${p}`, { method: 'POST', headers: HEADERS, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} -> ${r.status}`);
  return r.json();
}

async function hello() {
  return post('/api/remote/agent/hello', {
    device: DEVICE,
    host: os.hostname().split('.')[0],
    user: os.userInfo().username,
    os: `macOS ${os.release()}`,
    caps: caps()
  });
}

// ===== 流式鼠标控制（WebSocket）=====
// 关键：开一个常驻的 osascript JXA 进程接收移动指令，避免每次 spawn 的 ~50ms 开销，
// 这样触控板才丝滑。进程挂了会自动重建；环境无 WebSocket（Node<21）则整段跳过。
let streamProc = null;
function ensureStreamProc() {
  if (streamProc && !streamProc.killed) return streamProc;
  const p = spawn('osascript', ['-i', '-l', 'JavaScript'], { stdio: ['pipe', 'ignore', 'ignore'] });
  // 预定义辅助函数：L()取光标位置 / MV相对移动 / CK点击 / SC滚动（CoreGraphics CGEvent）
  const pre = [
    "ObjC.import('CoreGraphics')",
    'function L(){var e=$.CGEventCreate(null);return $.CGEventGetLocation(e)}',
    'function MV(x,y){var p=L();$.CGEventPost(0,$.CGEventCreateMouseEvent(null,5,{x:p.x+x,y:p.y+y},0))}',
    'function CK(b){var p=L();$.CGEventPost(0,$.CGEventCreateMouseEvent(null,b?3:1,p,b));$.CGEventPost(0,$.CGEventCreateMouseEvent(null,b?4:2,p,b))}',
    'function SC(y){$.CGEventPost(0,$.CGEventCreateScrollWheelEvent(null,0,1,y))}'
  ];
  try { p.stdin.write(pre.join('\n') + '\n'); } catch { /* ignore */ }
  p.on('exit', () => { if (streamProc === p) streamProc = null; });
  p.on('error', () => { if (streamProc === p) streamProc = null; });
  streamProc = p;
  return p;
}
function feedJXA(line) {
  try { ensureStreamProc().stdin.write(line + '\n'); } catch { streamProc = null; }
}

let accDX = 0, accDY = 0, flushTimer = null;
function flushMove() {
  flushTimer = null;
  if (!accDX && !accDY) return;
  const x = Math.round(accDX), y = Math.round(accDY);
  accDX = 0; accDY = 0;
  feedJXA(`MV(${x},${y})`);
}
function handleStream(raw) {
  let m; try { m = JSON.parse(raw); } catch { return; }
  switch (m.t) {
    case 'm': accDX += Number(m.dx) || 0; accDY += Number(m.dy) || 0; if (!flushTimer) flushTimer = setTimeout(flushMove, 16); break;
    case 'c': feedJXA(`CK(${m.b ? 1 : 0})`); break;
    case 'd': feedJXA('CK(0);CK(0)'); break;
    case 's': feedJXA(`SC(${Math.round(Number(m.dy) || 0)})`); break;
    // 'k' 心跳：忽略
  }
}

function connectStream() {
  if (typeof WebSocket === 'undefined') { console.log('   流式: 当前 Node 无内置 WebSocket（需 ≥21），仅离散鼠标可用'); return; }
  const url = SERVER.replace(/^http/, 'ws') + '/api/remote/agent/ws?token=' + encodeURIComponent(TOKEN) + '&device=' + encodeURIComponent(DEVICE);
  let ws;
  try { ws = new WebSocket(url); } catch { setTimeout(connectStream, 3000); return; }
  let ka = null;
  ws.addEventListener('open', () => {
    console.log('   流式通道已连接（触控板可用）');
    ka = setInterval(() => { try { if (ws.readyState === 1) ws.send('{"t":"k"}'); } catch { /* ignore */ } }, 20000);
  });
  ws.addEventListener('message', (ev) => handleStream(typeof ev.data === 'string' ? ev.data : ''));
  ws.addEventListener('error', () => {});
  ws.addEventListener('close', () => { if (ka) clearInterval(ka); if (!stop) setTimeout(connectStream, 3000); });
}

let stop = false;
async function loop() {
  let backoff = 1000;
  await probeCaps();
  console.log(`   能力:   ${caps().join(' / ')}`);
  await heartbeatSafe();
  setInterval(heartbeatSafe, 20_000);   // 周期心跳，掉线也能自动恢复在线状态
  connectStream();                      // 开流式触控板通道

  while (!stop) {
    try {
      const r = await fetch(`${SERVER}/api/remote/agent/poll?wait=25000&device=${encodeURIComponent(DEVICE)}`, { headers: HEADERS });
      if (!r.ok) throw new Error(`poll ${r.status}`);
      const { data } = await r.json();
      backoff = 1000;
      const cmd = data?.command;
      if (!cmd) continue;
      console.log(`▶ ${cmd.action}`, cmd.args && Object.keys(cmd.args).length ? cmd.args : '');
      const result = await runCommand(cmd);
      await post('/api/remote/agent/result', { id: cmd.id, device: DEVICE, ...result });
      console.log(result.ok ? `  ✓ ${cmd.action}` : `  ✗ ${cmd.action}: ${result.error}`);
    } catch (e) {
      console.error('· 连接中断，重试中…', e.message);
      await new Promise((res) => setTimeout(res, backoff));
      backoff = Math.min(backoff * 2, 15000);
    }
  }
}

async function heartbeatSafe() {
  try { await hello(); } catch { /* 等下次 */ }
}

process.on('SIGINT', () => { stop = true; console.log('\nbye~'); process.exit(0); });
process.on('SIGTERM', () => { stop = true; process.exit(0); });

console.log(`🖥  mac-agent 启动`);
console.log(`   设备:   ${DEVICE}`);
console.log(`   服务器: ${SERVER}`);
console.log(`   关机重启: ${ALLOW_POWER ? '开' : '关'}  ·  执行命令: ${ALLOW_SHELL ? '开' : '关'}`);
loop();
