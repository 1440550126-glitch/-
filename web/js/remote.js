// 远程控制 Mac · 控制台前端（零依赖原生 ESM）
// token 存在 localStorage（个人自托管工具，权衡可接受；公网部署请配 HTTPS）。
const $ = (id) => document.getElementById(id);
const TOKEN_KEY = 'remote_token';
const DEVICE_KEY = 'remote_device';

let token = '';
let es = null;
let sws = null;          // 流式触控板 WebSocket
let volTimer = null;
let gated = new Set();   // 需要特定能力才可用的动作（agent 未提供则置灰），由 /status 下发
let streamOK = false;    // agent 流式通道是否在线
let devices = [];        // 当前所有 Mac 设备
let selected = localStorage.getItem(DEVICE_KEY) || null;  // 当前控制的设备 ID
let streamDevice = null; // 流式通道当前指向的设备

// ---- 基础请求 ----
async function api(path, { method = 'GET', body } = {}) {
  const r = await fetch(path, {
    method,
    headers: { 'X-Remote-Token': token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined
  });
  const j = await r.json().catch(() => ({ ok: false, error: '响应解析失败' }));
  if (!j.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j.data;
}

// 下发一条指令；wait>0 时同一请求里等结果回来
function cmd(action, args = {}, wait = 0) {
  return api('/api/remote/command', { method: 'POST', body: { device: selected, action, args, wait } });
}

function log(msg, kind = '') {
  const el = $('log');
  const t = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  const prefix = kind === 'err' ? '✗' : kind === 'ok' ? '✓' : '·';
  el.textContent = `[${t}] ${prefix} ${msg}\n` + el.textContent;
}

async function send(action, args = {}, opts = {}) {
  try {
    const { result } = await cmd(action, args, opts.wait || 0);
    if (opts.wait && result && !result.ok) throw new Error(result.error);
    log(`${action} ${result?.ok ? '完成' : '已下发'}`, 'ok');
    return result;
  } catch (e) {
    log(`${action} 失败：${e.message}`, 'err');
    if (e.message.includes('令牌')) gate();
    return null;
  }
}

// ---- 多设备 ----
function applyDevices(list) {
  devices = list || [];
  // 保持已选；失效则自动挑一个在线的（单 Mac 场景零操作）
  if (!selected || !devices.find((d) => d.device === selected)) {
    const onl = devices.find((d) => d.online);
    selected = onl ? onl.device : (devices[0]?.device || null);
  }
  renderDevicePicker();
  applySelected();
}
function renderDevicePicker() {
  const sel = $('devSel');
  sel.innerHTML = '';
  if (!devices.length) { sel.classList.add('hidden'); return; }
  sel.classList.toggle('hidden', devices.length < 1);
  for (const d of devices) {
    const o = document.createElement('option');
    o.value = d.device;
    o.textContent = `${d.online ? '🟢' : '⚪️'} ${d.host || d.device}`;
    if (d.device === selected) o.selected = true;
    sel.appendChild(o);
  }
  sel.classList.toggle('hidden', devices.length <= 1);   // 只有一台就不显示选择器
}
function applySelected() {
  const d = devices.find((x) => x.device === selected);
  setStatus(d || { online: false, caps: [] });
  if (selected && streamDevice !== selected) connectStreamWS();   // 首次或切换设备时接流式通道
}
function switchDevice(id) {
  if (id === selected) return;
  selected = id;
  localStorage.setItem(DEVICE_KEY, id);
  $('shot').style.display = 'none';
  applySelected();
}

// ---- 状态 / SSE ----
function setStatus(s) {
  const dot = $('dot');
  dot.className = 'dot ' + (s.online ? 'on' : 'off');
  $('host').textContent = s.online ? ` · ${s.host || 'Mac'}（${s.user || ''} · ${s.os || ''}）` : ' · Mac 未连接';
  // 离线全灰；在线时按 agent 能力对受限动作（关机/重启/执行命令/摄像头等）置灰
  const caps = new Set(s.caps || []);
  const off = (act) => !s.online || (gated.has(act) && s.caps && !caps.has(act));
  document.querySelectorAll('button[data-act]').forEach((b) => { b.disabled = off(b.dataset.act); });
  $('shellRun').disabled = off('shell');
  document.querySelectorAll('[data-needs]').forEach((el) => { el.classList.toggle('hidden', s.caps && !caps.has(el.dataset.needs)); });

  // 触控板可用性
  streamOK = !!s.stream;
  const pad = $('pad');
  pad.style.opacity = streamOK ? '1' : '.5';
  pad.style.pointerEvents = streamOK ? 'auto' : 'none';
  $('padBadge').textContent = !s.online ? '' : streamOK ? '● 实时' : '○ 不可用';
  $('padBadge').style.color = streamOK ? 'var(--ok)' : 'var(--mut)';
}

// ---- 流式触控板 ----
function connectStreamWS() {
  if (sws) { try { sws.onclose = null; sws.close(); } catch { /* ignore */ } sws = null; }
  if (!selected) { streamDevice = null; return; }
  streamDevice = selected;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/api/remote/stream?token=${encodeURIComponent(token)}&device=${encodeURIComponent(selected)}`);
  ws.onclose = () => { if (token && sws === ws) setTimeout(connectStreamWS, 3000); };
  ws.onerror = () => {};
  sws = ws;
}
function streamSend(o) { if (sws && sws.readyState === 1) sws.send(JSON.stringify(o)); }

function setupTrackpad() {
  const pad = $('pad');
  const pts = new Map();
  let dist = 0, downAt = 0;
  const SENS = 1.7;
  pad.addEventListener('pointerdown', (e) => {
    pad.setPointerCapture(e.pointerId);
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    dist = 0; downAt = Date.now();
  });
  pad.addEventListener('pointermove', (e) => {
    const p = pts.get(e.pointerId); if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    dist += Math.abs(dx) + Math.abs(dy);
    if (pts.size >= 2) streamSend({ t: 's', dy: Math.round(dy * 0.6) });   // 双指=滚动
    else streamSend({ t: 'm', dx: dx * SENS, dy: dy * SENS });             // 单指=移动
  });
  const up = (e) => {
    const had = pts.has(e.pointerId);
    pts.delete(e.pointerId);
    if (had && pts.size === 0 && dist < 6 && Date.now() - downAt < 300) streamSend({ t: 'c', b: 0 }); // 轻点=左键
  };
  pad.addEventListener('pointerup', up);
  pad.addEventListener('pointercancel', up);
}

function connectSSE() {
  if (es) es.close();
  es = new EventSource(`/api/remote/events?token=${encodeURIComponent(token)}`);
  es.addEventListener('devices', (e) => applyDevices(JSON.parse(e.data).devices));
  es.addEventListener('result', (e) => {
    const r = JSON.parse(e.data);
    if (r.device && selected && r.device !== selected) return;   // 只看当前设备的结果
    // 截图结果直接显示
    if (r.ok && r.data && r.data.image) {
      $('shot').src = r.data.image;
      $('shot').style.display = 'block';
    }
    if (r.ok && r.data && typeof r.data.text === 'string') log(`剪贴板：${r.data.text.slice(0, 200)}`);
    if (r.ok && r.data && r.data.stdout !== undefined) log(`输出：${(r.data.stdout || r.data.stderr || '(空)').slice(0, 500)}`);
    if (r.ok && r.data && r.data.level !== undefined) { $('vol').value = r.data.level; $('volval').textContent = r.data.level; }
    if (r.ok && r.data && Array.isArray(r.data.shortcuts)) renderShortcuts(r.data.shortcuts);
  });
  es.onerror = () => { /* EventSource 会自动重连 */ };
}

async function refreshStatus() {
  try {
    const s = await api('/api/remote/status');
    gated = new Set((s.actions || []).filter((a) => a.needs).map((a) => a.action));
    applyDevices(s.devices);
  } catch (e) { if (e.message.includes('令牌') || e.message.includes('401')) gate(); }
}

// ---- 界面切换 ----
function gate(msg) {
  $('panel').classList.add('hidden');
  $('gate').classList.remove('hidden');
  if (msg) $('gateMsg').textContent = msg;
  if (es) { es.close(); es = null; }
  if (sws) { try { sws.onclose = null; sws.close(); } catch { /* ignore */ } sws = null; }
  streamDevice = null;
}
function enterPanel() {
  $('gate').classList.add('hidden');
  $('panel').classList.remove('hidden');
  connectSSE();
  refreshStatus();   // 内部 applyDevices → applySelected 会接好流式通道
}

// ---- 事件绑定 ----
function bind() {
  $('connect').onclick = async () => {
    const t = $('token').value.trim();
    if (!t) { $('gateMsg').textContent = '请输入 REMOTE_TOKEN'; return; }
    token = t;
    try {
      await api('/api/remote/status');
      if ($('remember').checked) localStorage.setItem(TOKEN_KEY, t);
      enterPanel();
    } catch (e) {
      gate(e.message.includes('未启用') ? '服务端未启用远程控制（.env 设置 REMOTE_TOKEN 后重启）' : '令牌无效，请重试');
    }
  };
  $('token').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('connect').click(); });

  $('logout').onclick = () => { localStorage.removeItem(TOKEN_KEY); token = ''; gate(); };

  $('devSel').onchange = (e) => switchDevice(e.target.value);

  // 通用动作按钮（电源 / 媒体 / 带输入框的打开/朗读/通知/输入）
  document.querySelectorAll('button[data-act]').forEach((b) => {
    b.onclick = () => {
      const act = b.dataset.act;
      if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
      let args = {};
      if (b.dataset.cmd) args.cmd = b.dataset.cmd;
      if (b.dataset.input) {
        const val = $(b.dataset.input).value.trim();
        if (!val) return;
        args[b.dataset.arg] = val;
      }
      send(act, args);
    };
  });

  // 音量滑块（防抖）
  $('vol').addEventListener('input', () => {
    const v = $('vol').value;
    $('volval').textContent = v;
    clearTimeout(volTimer);
    volTimer = setTimeout(() => send('volume', { level: Number(v) }), 180);
  });
  $('mute').onclick = () => send('volume', { mute: true });

  // 截屏：等结果一起回来
  $('snap').onclick = () => send('screenshot', {}, { wait: 20000 });

  // 剪贴板
  $('clipSet').onclick = () => { const v = $('clipText').value; if (v) send('clipboard', { set: v }); };
  $('clipGet').onclick = () => send('clipboard', {}, { wait: 8000 });

  // 执行命令
  $('shellRun').onclick = () => { const v = $('shellCmd').value.trim(); if (v) send('shell', { cmd: v }, { wait: 60000 }); };

  // 鼠标方向键：步长可调
  const step = () => Number($('mouseStep').value) || 50;
  document.querySelectorAll('button[data-mouse]').forEach((b) => {
    b.onclick = () => {
      const d = b.dataset.mouse;
      if (d === 'up') send('mouse', { dy: -step() });
      else if (d === 'down') send('mouse', { dy: step() });
      else if (d === 'left') send('mouse', { dx: -step() });
      else if (d === 'right') send('mouse', { dx: step() });
      else send('mouse', { click: d });   // left / right / double
    };
  });

  // 快捷指令：拉列表 + 运行
  $('scList').onclick = () => send('shortcut', { list: true }, { wait: 8000 });
  $('scRun').onclick = () => { const v = $('scName').value.trim(); if (v) send('shortcut', { name: v }); };

  // 摄像头
  $('cam').onclick = () => send('camera', {}, { wait: 20000 });

  // 文件传输
  $('upBtn').onclick = uploadToMac;
  $('dlBtn').onclick = downloadFromMac;

  setupTrackpad();
}

async function uploadToMac() {
  const f = $('upFile').files[0];
  if (!f) { log('请先选择文件', 'err'); return; }
  if (!selected) { log('请先选择设备', 'err'); return; }
  try {
    log(`上传 ${f.name}（${(f.size / 1024 / 1024).toFixed(1)}MB）…`);
    const r = await fetch(`/api/remote/transfer/up?device=${encodeURIComponent(selected)}&name=${encodeURIComponent(f.name)}`, {
      method: 'POST', headers: { 'X-Remote-Token': token, 'Content-Type': 'application/octet-stream' }, body: f
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    const res = await api(`/api/remote/result/${j.data.id}?wait=120000`);
    const rr = res.result;
    if (rr && rr.ok) log(`已保存到 Mac：${rr.data?.saved || f.name}`, 'ok');
    else log(`Mac 接收失败：${rr?.error || '超时'}`, 'err');
  } catch (e) { log(`上传失败：${e.message}`, 'err'); }
}

async function downloadFromMac() {
  const p = $('dlPath').value.trim();
  if (!p) { log('请输入 Mac 上的文件路径', 'err'); return; }
  const res = await send('send_file', { path: p }, { wait: 120000 });
  if (!res || !res.data?.transfer) return;
  try {
    const r = await fetch(`/api/remote/file/${res.data.transfer}`, { headers: { 'X-Remote-Token': token } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = res.data.name || 'file'; a.click();
    URL.revokeObjectURL(url);
    log(`已取回 ${res.data.name}`, 'ok');
  } catch (e) { log(`取回失败：${e.message}`, 'err'); }
}

function renderShortcuts(names) {
  const dl = $('scNames');
  dl.innerHTML = '';
  for (const n of names) { const o = document.createElement('option'); o.value = n; dl.appendChild(o); }
  log(`快捷指令 ${names.length} 个`);
}

bind();
const saved = localStorage.getItem(TOKEN_KEY);
if (saved) { token = saved; enterPanel(); }
