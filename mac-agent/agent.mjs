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
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';

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

function caps() {
  const c = ['lock', 'sleep', 'volume', 'media', 'screenshot', 'open', 'say', 'notify', 'type', 'clipboard'];
  if (ALLOW_POWER) c.push('restart', 'shutdown');
  if (ALLOW_SHELL) c.push('shell');
  return c;
}

// AppleScript 字符串字面量转义
const osaStr = (s) => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/[\r\n]+/g, ' ');
// 跑一段 AppleScript
const osa = (script) => pexec('osascript', ['-e', script], { timeout: 15000 });

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
    host: os.hostname(),
    user: os.userInfo().username,
    os: `macOS ${os.release()}`,
    caps: caps()
  });
}

let stop = false;
async function loop() {
  let backoff = 1000;
  await heartbeatSafe();
  setInterval(heartbeatSafe, 20_000);   // 周期心跳，掉线也能自动恢复在线状态

  while (!stop) {
    try {
      const r = await fetch(`${SERVER}/api/remote/agent/poll?wait=25000`, { headers: HEADERS });
      if (!r.ok) throw new Error(`poll ${r.status}`);
      const { data } = await r.json();
      backoff = 1000;
      const cmd = data?.command;
      if (!cmd) continue;
      console.log(`▶ ${cmd.action}`, cmd.args && Object.keys(cmd.args).length ? cmd.args : '');
      const result = await runCommand(cmd);
      await post('/api/remote/agent/result', { id: cmd.id, ...result });
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
console.log(`   服务器: ${SERVER}`);
console.log(`   能力:   ${caps().join(' / ')}`);
console.log(`   关机重启: ${ALLOW_POWER ? '开' : '关'}  ·  执行命令: ${ALLOW_SHELL ? '开' : '关'}`);
loop();
