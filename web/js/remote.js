// 远程控制 Mac · 控制台前端（零依赖原生 ESM）
// token 存在 localStorage（个人自托管工具，权衡可接受；公网部署请配 HTTPS）。
const $ = (id) => document.getElementById(id);
const TOKEN_KEY = 'remote_token';

let token = '';
let es = null;
let volTimer = null;

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
  return api('/api/remote/command', { method: 'POST', body: { action, args, wait } });
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

// ---- 状态 / SSE ----
function setStatus(s) {
  const dot = $('dot');
  dot.className = 'dot ' + (s.online ? 'on' : 'off');
  $('host').textContent = s.online ? ` · ${s.host || 'Mac'}（${s.user || ''} · ${s.os || ''}）` : ' · Mac 未连接';
  // agent 不支持的危险动作置灰
  const caps = new Set(s.caps || []);
  document.querySelectorAll('button[data-act]').forEach((b) => {
    const a = b.dataset.act;
    if (['restart', 'shutdown', 'shell'].includes(a)) b.disabled = !s.online || (s.caps && !caps.has(a));
    else b.disabled = !s.online;
  });
  $('shellRun').disabled = !s.online || (s.caps && !caps.has('shell'));
}

function connectSSE() {
  if (es) es.close();
  es = new EventSource(`/api/remote/events?token=${encodeURIComponent(token)}`);
  es.addEventListener('agent', (e) => setStatus(JSON.parse(e.data)));
  es.addEventListener('result', (e) => {
    const r = JSON.parse(e.data);
    // 截图结果直接显示
    if (r.ok && r.data && r.data.image) {
      $('shot').src = r.data.image;
      $('shot').style.display = 'block';
    }
    if (r.ok && r.data && typeof r.data.text === 'string') log(`剪贴板：${r.data.text.slice(0, 200)}`);
    if (r.ok && r.data && r.data.stdout !== undefined) log(`输出：${(r.data.stdout || r.data.stderr || '(空)').slice(0, 500)}`);
    if (r.ok && r.data && r.data.level !== undefined) { $('vol').value = r.data.level; $('volval').textContent = r.data.level; }
  });
  es.onerror = () => { /* EventSource 会自动重连 */ };
}

async function refreshStatus() {
  try { setStatus(await api('/api/remote/status')); }
  catch (e) { if (e.message.includes('令牌') || e.message.includes('401')) gate(); }
}

// ---- 界面切换 ----
function gate(msg) {
  $('panel').classList.add('hidden');
  $('gate').classList.remove('hidden');
  if (msg) $('gateMsg').textContent = msg;
  if (es) { es.close(); es = null; }
}
function enterPanel() {
  $('gate').classList.add('hidden');
  $('panel').classList.remove('hidden');
  connectSSE();
  refreshStatus();
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
}

bind();
const saved = localStorage.getItem(TOKEN_KEY);
if (saved) { token = saved; enterPanel(); }
