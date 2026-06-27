#!/usr/bin/env node
// 远程控制 Mac · 命令行遥控器（不用网页，零依赖，任何有 Node 的机器/手机 Termux 都能跑）
//
// 配置（任选其一）：
//   1) 环境变量：REMOTE_SERVER=https://你的服务器  REMOTE_TOKEN=口令  [REMOTE_DEVICE=设备名]
//   2) 配置文件 ~/.jvling-remote.json : { "server": "...", "token": "...", "device": "" }
//   3) 命令行：--server <url> --token <口令> --device <名>
//
// 用法示例：
//   node remote-ctl.mjs devices                 # 列出在线的 Mac
//   node remote-ctl.mjs lock                     # 锁屏
//   node remote-ctl.mjs unlock                   # 解锁（需 agent 配了密码）
//   node remote-ctl.mjs vol 30 | vol +10 | mute  # 音量
//   node remote-ctl.mjs bright up 2              # 亮度调亮 2 档
//   node remote-ctl.mjs play | pause | next | prev
//   node remote-ctl.mjs shot [out.jpg]           # 截屏存文件
//   node remote-ctl.mjs cam [out.jpg]            # 摄像头拍照
//   node remote-ctl.mjs open https://b.com | open Safari
//   node remote-ctl.mjs say 你好 | notify 该喝水了 | type 一段文字
//   node remote-ctl.mjs clip | clip 写入剪贴板的内容
//   node remote-ctl.mjs run 回家模式 | shortcuts   # 跑/列快捷指令
//   node remote-ctl.mjs mouse 50 -20 | click [right|double]
//   node remote-ctl.mjs shell "ls ~/Desktop"     # 需 agent 开 REMOTE_ALLOW_SHELL
//   node remote-ctl.mjs send ./a.png             # 上传文件到 Mac 的「下载」夹
//   node remote-ctl.mjs get ~/Desktop/a.png [out] # 从 Mac 取回文件
//   加 --device <名> 控制指定 Mac（多台时；不加则自动选唯一在线那台）
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// ---- 配置 ----
const argv = process.argv.slice(2);
const flags = {};
const rest = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith('--')) flags[argv[i].slice(2)] = argv[++i];
  else rest.push(argv[i]);
}
let cfg = {};
try { cfg = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.jvling-remote.json'), 'utf8')); } catch { /* 可选 */ }
const SERVER = (flags.server || process.env.REMOTE_SERVER || cfg.server || 'http://localhost:3000').replace(/\/+$/, '');
const TOKEN = flags.token || process.env.REMOTE_TOKEN || cfg.token || '';
const DEVICE = flags.device || process.env.REMOTE_DEVICE || cfg.device || '';

if (!TOKEN) { console.error('✗ 缺少 REMOTE_TOKEN（环境变量 / ~/.jvling-remote.json / --token）'); process.exit(1); }

const [action, ...a] = rest;
if (!action) { printHelp(); process.exit(0); }

const H = { 'Content-Type': 'application/json', 'X-Remote-Token': TOKEN };

async function api(method, p, body) {
  const r = await fetch(`${SERVER}${p}`, { method, headers: H, body: body ? JSON.stringify(body) : undefined });
  const j = await r.json().catch(() => ({ ok: false, error: `HTTP ${r.status}` }));
  if (!j.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j.data;
}
// 下发一条指令并等结果（默认等 30s，读取型够用）
async function cmd(act, args = {}, wait = 30000) {
  const { id, result } = await api('POST', '/api/remote/command', { device: DEVICE, action: act, args, wait });
  if (wait && result && !result.ok) throw new Error(result.error);
  return result || { id };
}
const saveImage = (dataUrl, file) => {
  const b64 = String(dataUrl).replace(/^data:image\/\w+;base64,/, '');
  fs.writeFileSync(file, Buffer.from(b64, 'base64'));
  return file;
};
const num = (v, d = 0) => (v === undefined ? d : Number(v));

try {
  switch (action) {
    case 'devices': {
      const { devices } = await api('GET', '/api/remote/status');
      if (!devices.length) { console.log('（没有设备连接）'); break; }
      for (const d of devices) console.log(`${d.online ? '🟢' : '⚪️'} ${d.device}  ${d.host || ''} ${d.online ? `· 能力 ${d.caps.length} 项${d.stream ? ' · 触控板' : ''}` : '（离线）'}`);
      break;
    }
    case 'lock': case 'unlock': case 'sleep': case 'restart': case 'shutdown':
      await cmd(action, {}, 8000); console.log(`✓ ${action}`); break;
    case 'vol': case 'volume': {
      const v = a[0] || '';
      if (v === '') { console.log(JSON.stringify((await cmd('volume', {})).data)); break; }
      if (v.startsWith('+') || v.startsWith('-')) await cmd('volume', { delta: Number(v) });
      else await cmd('volume', { level: Number(v) });
      console.log(`✓ 音量 ${v}`); break;
    }
    case 'mute': await cmd('volume', { mute: true }); console.log('✓ 静音'); break;
    case 'unmute': await cmd('volume', { mute: false }); console.log('✓ 取消静音'); break;
    case 'bright': case 'brightness':
      await cmd('brightness', { cmd: a[0] === 'down' ? 'down' : 'up', steps: num(a[1], 1) }); console.log(`✓ 亮度 ${a[0] || 'up'}`); break;
    case 'play': case 'pause': case 'playpause': case 'next': case 'prev': case 'previous':
      await cmd('media', { cmd: action === 'play' || action === 'pause' ? 'playpause' : action }); console.log(`✓ ${action}`); break;
    case 'shot': case 'screenshot': {
      const r = await cmd('screenshot', {}, 25000);
      const f = a[0] || `shot-${Date.now()}.jpg`;
      console.log(`✓ 截屏已存 ${saveImage(r.data.image, f)}`); break;
    }
    case 'cam': case 'camera': {
      const r = await cmd('camera', {}, 25000);
      const f = a[0] || `cam-${Date.now()}.jpg`;
      console.log(`✓ 拍照已存 ${saveImage(r.data.image, f)}`); break;
    }
    case 'open': await cmd('open', { target: a.join(' ') }); console.log(`✓ 打开 ${a.join(' ')}`); break;
    case 'say': await cmd('say', { text: a.join(' ') }); console.log('✓ 已朗读'); break;
    case 'notify': await cmd('notify', { text: a.join(' ') }); console.log('✓ 已通知'); break;
    case 'type': await cmd('type', { text: a.join(' ') }); console.log('✓ 已输入'); break;
    case 'clip': case 'clipboard': {
      if (a.length) { await cmd('clipboard', { set: a.join(' ') }); console.log('✓ 已写入剪贴板'); }
      else { const r = await cmd('clipboard', {}, 8000); console.log(r.data.text ?? ''); }
      break;
    }
    case 'run': case 'shortcut': await cmd('shortcut', { name: a.join(' ') }); console.log(`✓ 已运行 ${a.join(' ')}`); break;
    case 'shortcuts': { const r = await cmd('shortcut', { list: true }, 8000); console.log((r.data.shortcuts || []).join('\n')); break; }
    case 'mouse': await cmd('mouse', { dx: num(a[0]), dy: num(a[1]) }); console.log(`✓ 鼠标 ${a[0] || 0},${a[1] || 0}`); break;
    case 'click': await cmd('mouse', { click: ['right', 'double'].includes(a[0]) ? a[0] : 'left' }); console.log(`✓ ${a[0] || 'left'} 点击`); break;
    case 'shell': { const r = await cmd('shell', { cmd: a.join(' ') }, 60000); process.stdout.write((r.data.stdout || '') + (r.data.stderr || '')); break; }
    case 'send': {
      const file = a[0]; if (!file) throw new Error('用法：send <本地文件>');
      if (!DEVICE) console.error('提示：多台 Mac 时建议加 --device');
      const buf = fs.readFileSync(file);
      const name = path.basename(file);
      const r = await fetch(`${SERVER}/api/remote/transfer/up?device=${encodeURIComponent(DEVICE)}&name=${encodeURIComponent(name)}`, { method: 'POST', headers: { 'X-Remote-Token': TOKEN, 'Content-Type': 'application/octet-stream' }, body: buf });
      const j = await r.json(); if (!j.ok) throw new Error(j.error);
      const res = await api('GET', `/api/remote/result/${j.data.id}?wait=120000`);
      console.log(res.result?.ok ? `✓ 已传到 Mac：${res.result.data?.saved}` : `✗ ${res.result?.error || '超时'}`);
      break;
    }
    case 'get': {
      const p = a[0]; if (!p) throw new Error('用法：get <Mac上的文件路径> [本地输出名]');
      const r = await cmd('send_file', { path: p }, 120000);
      const tid = r.data?.transfer; if (!tid) throw new Error('未取得文件');
      const dl = await fetch(`${SERVER}/api/remote/file/${tid}`, { headers: { 'X-Remote-Token': TOKEN } });
      if (!dl.ok) throw new Error(`下载失败 ${dl.status}`);
      const out = a[1] || r.data.name || path.basename(p);
      fs.writeFileSync(out, Buffer.from(await dl.arrayBuffer()));
      console.log(`✓ 已取回 ${out}`); break;
    }
    default: console.error(`未知动作：${action}`); printHelp(); process.exit(1);
  }
} catch (e) {
  console.error(`✗ ${e.message}`);
  process.exit(1);
}

function printHelp() {
  console.log(`远程控制 Mac · 命令行遥控器
配置：REMOTE_SERVER / REMOTE_TOKEN[ / REMOTE_DEVICE]（或 ~/.jvling-remote.json，或 --server/--token/--device）

  devices                      列出在线的 Mac
  lock | unlock | sleep | restart | shutdown
  vol <0-100|+N|-N> | mute | unmute
  bright up|down [档数]
  play | pause | next | prev
  shot [文件] | cam [文件]      截屏 / 摄像头拍照存文件
  open <网址|应用名>
  say <文字> | notify <文字> | type <文字>
  clip [文字]                  读/写剪贴板
  run <快捷指令名> | shortcuts
  mouse <dx> <dy> | click [right|double]
  shell "<命令>"               需 agent 开 REMOTE_ALLOW_SHELL
  send <本地文件> | get <Mac路径> [输出名]
  多台 Mac 加 --device <名>（不加则自动选唯一在线那台）`);
}
