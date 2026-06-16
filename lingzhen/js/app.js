// 灵阵 · AI 团队（独立站）：登录 → 团队广场/模板 → 派单 → 作战室实时直播 → 历史 → 建队。
// 对接 AI句灵 服务端现有 /api/agents·/api/teams·/api/runs 接口；无大模型 Key 时后端走本地引擎，零成本可跑通。
import { GET, POST, PATCH, DEL, sse, getToken, setToken } from './api.js';

// ---------------- DOM 小工具 ----------------
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'value') el.value = v;
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
const $app = () => document.getElementById('app');
function mount(node) { const a = $app(); a.innerHTML = ''; a.append(node); window.scrollTo(0, 0); }
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function toast(msg, kind) {
  const t = h('div', { class: 'lz-toast' + (kind ? ' ' + kind : '') }, msg);
  document.body.append(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2200);
}
const nav = (hash) => { location.hash = hash; };
function fmtTime(ts) {
  if (!ts) return '';
  const d = new Date(ts), p = (n) => (n < 10 ? '0' + n : n);
  return `${d.getMonth() + 1}-${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function copy(text) { navigator.clipboard?.writeText(text).then(() => toast('已复制'), () => toast('复制失败', 'warn')); }

// ---------------- 极简 Markdown 渲染（结果为 Markdown） ----------------
function mdInline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdHtml(md) {
  const lines = String(md || '').replace(/\r/g, '').split('\n');
  let out = '', list = null, code = false, codeBuf = '';
  const closeList = () => { if (list) { out += `</${list}>`; list = null; } };
  for (const raw of lines) {
    const line = raw;
    if (/^```/.test(line)) {
      if (code) { out += `<pre><code>${esc(codeBuf)}</code></pre>`; code = false; codeBuf = ''; }
      else { closeList(); code = true; codeBuf = ''; }
      continue;
    }
    if (code) { codeBuf += line + '\n'; continue; }
    if (!line.trim()) { closeList(); continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) { closeList(); out += `<h${m[1].length}>${mdInline(m[2])}</h${m[1].length}>`; }
    else if (/^(-{3,}|\*{3,})$/.test(line.trim())) { closeList(); out += '<hr>'; }
    else if ((m = line.match(/^\s*>\s?(.*)$/))) { closeList(); out += `<blockquote>${mdInline(m[1])}</blockquote>`; }
    else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { if (list !== 'ul') { closeList(); out += '<ul>'; list = 'ul'; } out += `<li>${mdInline(m[1])}</li>`; }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) { if (list !== 'ol') { closeList(); out += '<ol>'; list = 'ol'; } out += `<li>${mdInline(m[1])}</li>`; }
    else { closeList(); out += `<p>${mdInline(line)}</p>`; }
  }
  if (code) out += `<pre><code>${esc(codeBuf)}</code></pre>`;
  closeList();
  return out;
}
const mdBody = (md) => h('div', { class: 'lz-md', html: mdHtml(md) });

// ---------------- 状态 / 策略 ----------------
const state = { me: null, meta: null, strat: {} };
const STATUS = { running: ['运行中', 'run'], done: ['已完成', 'done'], failed: ['失败', 'fail'], stopped: ['已停止', 'stop'] };
async function loadMeta() { if (!state.meta) { state.meta = await GET('/api/agents/meta'); for (const s of state.meta.strategies) state.strat[s.id] = s; } return state.meta; }
const stratIcon = (id) => (state.strat[id]?.icon) || '🛰';
const stratName = (id) => (state.strat[id]?.name) || id;

// ---------------- 公共 UI 片段 ----------------
function header() {
  const m = state.me;
  return h('header', { class: 'lz-top' },
    h('div', { class: 'lz-brand', onclick: () => nav('#/') },
      h('span', { class: 'lz-logo' }, '🛰'),
      h('div', {}, h('b', {}, '灵阵'), h('small', {}, 'AI 团队 · 对标扣子'))),
    h('nav', { class: 'lz-nav' },
      h('a', { onclick: () => nav('#/') }, '团队广场'),
      h('a', { onclick: () => nav('#/history') }, '运行历史'),
      h('a', { class: 'primary', onclick: () => nav('#/new') }, '＋ 建队')),
    h('div', { class: 'lz-user' },
      state.meta ? h('span', { class: 'lz-quota', title: '今日剩余运行次数' }, `⚡ ${state.meta.quota.left}/${state.meta.quota.limit}`) : null,
      h('span', { class: 'lz-me' }, (m?.avatar ? '' : '👤'), m?.nickname || '我'),
      h('a', { class: 'lz-out', onclick: logout }, '退出')));
}
function shell(...content) { return h('div', { class: 'lz-shell' }, header(), h('main', { class: 'lz-main' }, ...content)); }
const spinner = () => h('div', { class: 'lz-spin' }, h('div', { class: 'lz-spin-d' }), '加载中…');
const empty = (title, sub) => h('div', { class: 'lz-empty' }, h('div', { class: 'lz-empty-i' }, '🫥'), h('b', {}, title), sub ? h('p', {}, sub) : null);

function teamCard(t, opts = {}) {
  return h('article', { class: 'lz-card', onclick: () => nav(`#/team/${t.id}`) },
    h('div', { class: 'lz-card-h' },
      h('span', { class: 'lz-ava lg' }, t.avatar || '🛰'),
      h('div', { class: 'lz-card-ti' },
        h('b', {}, t.name),
        h('span', { class: 'lz-strat' }, stratIcon(t.strategy) + ' ' + stratName(t.strategy))),
      t.is_template ? h('span', { class: 'lz-tag tpl' }, '模板') : (t.published ? h('span', { class: 'lz-tag pub' }, '广场') : null)),
    t.goal ? h('p', { class: 'lz-card-goal' }, t.goal) : null,
    h('div', { class: 'lz-members' },
      (t.members || []).slice(0, 6).map((mb) => h('span', { class: 'lz-ava sm', title: mb.name + ' · ' + (mb.role || '') }, mb.avatar)),
      h('small', { class: 'lz-mcount' }, `${(t.members || []).length} 名成员` + (opts.owner ? ` · 跑过 ${t.run_count || 0} 次` : ''))));
}

// ---------------- 登录 ----------------
function renderLogin() {
  let mode = 'guest';
  const box = h('div', { class: 'lz-auth-box' });
  function draw() {
    box.innerHTML = '';
    const u = h('input', { class: 'lz-in', placeholder: '用户名（3-20 位字母/数字）', autocomplete: 'username' });
    const p = h('input', { class: 'lz-in', type: 'password', placeholder: '密码（至少 6 位）', autocomplete: 'current-password' });
    const nick = h('input', { class: 'lz-in', placeholder: '昵称（2-12 字，可留空）' });
    const tabs = h('div', { class: 'lz-auth-tabs' },
      ['guest', '游客体验', 'login', '登录', 'register', '注册'].reduce((acc, _, i, arr) => {
        if (i % 2) return acc;
        const key = arr[i], label = arr[i + 1];
        acc.push(h('button', { class: 'lz-auth-tab' + (mode === key ? ' on' : ''), onclick: () => { mode = key; draw(); } }, label));
        return acc;
      }, []));
    const submit = h('button', { class: 'lz-btn block xl', onclick: () => go() }, mode === 'guest' ? '👤 一键进入，立即体验' : (mode === 'login' ? '登录' : '注册并进入'));
    async function go() {
      submit.disabled = true;
      try {
        let data;
        if (mode === 'guest') {
          let dev = localStorage.getItem('lz_device') || '';
          data = await POST('/api/auth/guest', { device_id: dev });
          if (data.device_id) localStorage.setItem('lz_device', data.device_id);
        } else if (mode === 'login') {
          data = await POST('/api/auth/login', { username: u.value.trim(), password: p.value });
        } else {
          data = await POST('/api/auth/register', { username: u.value.trim(), password: p.value, nickname: nick.value.trim() || undefined });
        }
        setToken(data.token); state.me = data.user; state.meta = null;
        toast('欢迎来到灵阵 🛰');
        if (!location.hash || location.hash === '#/login') location.hash = '#/';
        route();
      } catch (e) { toast(e.message, 'warn'); submit.disabled = false; }
    }
    box.append(tabs);
    if (mode !== 'guest') { box.append(u, p); if (mode === 'register') box.append(nick); }
    else box.append(h('p', { class: 'lz-auth-hint' }, '无需注册，一键生成体验账号即可调度你的第一支 AI 团队。'));
    box.append(submit);
  }
  draw();
  mount(h('div', { class: 'lz-auth' },
    h('div', { class: 'lz-auth-hero' },
      h('div', { class: 'lz-logo xl' }, '🛰'),
      h('h1', {}, '灵阵 · AI 团队'),
      h('p', { class: 'lz-tagline' }, '一句话，调动一支会分工的专业 AI 团队替你干活。'),
      h('div', { class: 'lz-hero-feats' },
        h('span', {}, '拆解→分派→整合'), h('span', {}, '作战室实时直播'), h('span', {}, '12 智能体 · 8 团队模板'), h('span', {}, '无 Key 也能零成本跑通'))),
    box));
}
function logout() { setToken(''); state.me = null; state.meta = null; toast('已退出'); location.hash = ''; renderLogin(); }

// ---------------- 首页：团队广场 / 模板 / 我的 ----------------
async function renderHome() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const [teams, gallery] = await Promise.all([GET('/api/teams'), GET('/api/teams/gallery').catch(() => ({ items: [] }))]);
    let tab = location.hash.split('?t=')[1] || 'templates';
    const tabbar = h('div', { class: 'lz-tabs' });
    const grid = h('div', { class: 'lz-grid' });
    const tabsDef = [['templates', '开箱模板 ' + teams.templates.length], ['mine', '我的团队 ' + teams.mine.length], ['gallery', '团队广场 ' + gallery.items.length]];
    function paint() {
      tabbar.innerHTML = '';
      for (const [k, label] of tabsDef) tabbar.append(h('button', { class: 'lz-tab' + (tab === k ? ' on' : ''), onclick: () => { tab = k; paint(); } }, label));
      grid.innerHTML = '';
      const list = tab === 'templates' ? teams.templates : tab === 'mine' ? teams.mine : gallery.items;
      if (!list.length) { grid.append(tab === 'mine' ? empty('还没有自己的团队', '从「开箱模板」复制一个，或点右上角「建队」') : empty('暂时空空如也')); return; }
      for (const t of list) grid.append(teamCard(t, { owner: tab === 'mine' }));
    }
    paint();
    mount(shell(
      h('section', { class: 'lz-intro' },
        h('h2', {}, '把任务交给一支会分工的 AI 团队'),
        h('p', {}, '选一个团队 → 下达任务 → 在作战室看它们拆解、分派、调工具、整合交付。')),
      tabbar, grid));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 团队详情 + 派单 ----------------
async function renderTeam(id) {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const { team, members } = await GET(`/api/teams/${id}`);
    const ta = h('textarea', { class: 'lz-ta', rows: 4, placeholder: '描述要这支团队完成什么，例如：围绕「年轻人露营」写一篇小红书种草文案，并给3个标题。' });
    const runBtn = h('button', { class: 'lz-btn block xl' }, '🚀 派单运行');
    runBtn.addEventListener('click', async () => {
      const task = ta.value.trim();
      if (!task) { ta.focus(); toast('先描述一下任务', 'warn'); return; }
      runBtn.disabled = true; runBtn.textContent = '正在创建运行…';
      try { const { run_id } = await POST(`/api/teams/${id}/run`, { task }); nav(`#/run/${run_id}`); }
      catch (e) { toast(e.message, 'warn'); runBtn.disabled = false; runBtn.textContent = '🚀 派单运行'; }
    });

    const actions = h('div', { class: 'lz-team-actions' });
    if (team.is_template || !team.mine) {
      actions.append(h('button', { class: 'lz-btn ghost', onclick: async () => {
        try { const { team: nt } = await POST(`/api/teams/${id}/clone`); toast('已复制为我的团队'); nav(`#/edit/${nt.id}`); }
        catch (e) { toast(e.message, 'warn'); }
      } }, '⎘ 复制为我的'));
    }
    if (team.mine) {
      actions.append(h('button', { class: 'lz-btn ghost', onclick: () => nav(`#/edit/${id}`) }, '✎ 编辑'));
      actions.append(h('button', { class: 'lz-btn ghost danger', onclick: async () => {
        if (!confirm('确认删除这个团队？')) return;
        try { await DEL(`/api/teams/${id}`); toast('已删除'); nav('#/'); } catch (e) { toast(e.message, 'warn'); }
      } }, '🗑 删除'));
    }

    mount(shell(
      h('button', { class: 'lz-back', onclick: () => nav('#/') }, '‹ 返回'),
      h('section', { class: 'lz-team-hero' },
        h('span', { class: 'lz-ava xl' }, team.avatar || '🛰'),
        h('div', { class: 'lz-team-meta' },
          h('h1', {}, team.name),
          h('div', { class: 'lz-strat-row' },
            h('span', { class: 'lz-strat big' }, stratIcon(team.strategy) + ' ' + stratName(team.strategy)),
            state.strat[team.strategy] ? h('small', {}, state.strat[team.strategy].tagline) : null),
          team.goal ? h('p', { class: 'lz-goal' }, '🎯 ' + team.goal) : null)),
      team.manager_note ? h('div', { class: 'lz-note' }, '🧭 编排官指令：' + team.manager_note) : null,
      h('div', { class: 'lz-sec-t' }, `团队成员（${members.length}）`),
      h('div', { class: 'lz-roster' }, members.map((mb) => h('div', { class: 'lz-mem' },
        h('span', { class: 'lz-ava' }, mb.avatar),
        h('div', {}, h('b', {}, mb.name), h('small', {}, mb.role || ''),
          (mb.tools || []).length ? h('div', { class: 'lz-tools' }, (mb.tools || []).map((tl) => h('span', { class: 'lz-tool' }, '🔧 ' + tl))) : null)))),
      (team.knowledge || []).length ? h('div', { class: 'lz-kb' }, '📚 挂载知识库：' + team.knowledge.map((k) => k.name).join('、')) : null,
      h('div', { class: 'lz-run-box' }, h('div', { class: 'lz-sec-t' }, '给这支团队下达任务'), ta, runBtn),
      actions));
  } catch (e) { mount(shell(empty('团队不存在或无权访问', e.message))); }
}

// ---------------- 作战室：实时直播 ----------------
async function renderRun(id) {
  mount(shell(spinner()));
  let init;
  try { init = await GET(`/api/runs/${id}`); } catch (e) { mount(shell(empty('运行不存在', e.message))); return; }

  const head = h('div', { class: 'lz-run-head' });
  const timeline = h('div', { class: 'lz-timeline' });
  const resultBox = h('div', {});
  const stopBtn = h('button', { class: 'lz-btn ghost danger sm', hidden: true }, '⏹ 停止');
  stopBtn.addEventListener('click', async () => { try { await POST(`/api/runs/${id}/stop`); toast('已请求停止'); } catch (e) { toast(e.message, 'warn'); } });

  function renderHead(r) {
    const [label, cls] = STATUS[r.status] || ['—', ''];
    head.innerHTML = '';
    head.append(
      h('div', { class: 'lz-rh-top' },
        h('span', { class: 'lz-strat' }, stratIcon(r.strategy) + ' ' + r.team_name),
        h('span', { class: 'lz-st ' + cls }, label),
        r.by_llm ? h('span', { class: 'lz-chip llm' }, '大模型协作') : h('span', { class: 'lz-chip local' }, '本地引擎'),
        stopBtn),
      h('div', { class: 'lz-rh-task' }, '🎯 ' + r.task));
  }

  const stepsById = new Map();
  function paintTimeline() {
    timeline.innerHTML = '';
    for (const s of [...stepsById.values()].sort((a, b) => a.idx - b.idx)) timeline.append(stepNode(s));
  }
  function stepNode(s) {
    const running = s.status === 'running';
    if (s.phase === 'tool') {
      return h('div', { class: 'lz-step tool' },
        h('div', { class: 'lz-tool-line' }, '🔧 ', h('b', {}, s.agent_name), ' 调用 ', h('code', {}, String(s.title || '').replace('调用工具 · ', '')), running ? h('span', { class: 'lz-dots' }, '…') : null),
        s.tool_result ? h('div', { class: 'lz-tool-out' }, String(s.tool_result).slice(0, 500)) : null);
    }
    const phaseCls = { plan: 'plan', act: 'act', synthesize: 'synth', system: 'sys' }[s.phase] || '';
    const badge = { plan: '编排官拆解', synthesize: '总编整合', system: '系统' }[s.phase] || '';
    return h('div', { class: 'lz-step ' + phaseCls + (running ? ' running' : '') },
      h('div', { class: 'lz-step-h' },
        h('span', { class: 'lz-ava' }, s.agent_avatar || '🛰'),
        h('div', { style: { flex: '1' } },
          h('div', { class: 'lz-step-name' }, s.agent_name, badge ? h('span', { class: 'lz-phase-b' }, badge) : null,
            running ? h('span', { class: 'lz-work' }, '工作中', h('span', { class: 'lz-dots' }, '…')) : null),
          s.title && s.phase !== 'synthesize' ? h('div', { class: 'lz-step-ti' }, s.title) : null)),
      s.output ? (s.phase === 'synthesize' ? h('div', { class: 'lz-tip' }, '↓ 最终交付见下方') : h('div', { class: 'lz-step-out' }, mdBody(s.output)))
        : (running ? null : h('div', { class: 'lz-step-out muted' }, '（无输出）')));
  }

  function renderResult(r) {
    resultBox.innerHTML = '';
    if (r.status === 'done' && r.result) {
      resultBox.append(h('div', { class: 'lz-result' },
        h('div', { class: 'lz-result-h' }, h('span', {}, '🧩 最终交付'), h('button', { class: 'lz-btn mini ghost', onclick: () => copy(r.result) }, '复制')),
        mdBody(r.result),
        h('div', { class: 'lz-result-meta' }, `${r.step_count} 步 · ${r.by_llm ? '大模型协作' : '本地引擎'}${r.token_total ? ' · 约 ' + r.token_total + ' tokens' : ''}`),
        h('button', { class: 'lz-btn block', onclick: () => nav(`#/team/${r.team_id}`) }, '↻ 再派一个任务')));
    } else if (r.status === 'failed') {
      resultBox.append(h('div', { class: 'lz-result fail' }, '运行失败：' + (r.error || '未知错误'),
        h('button', { class: 'lz-btn block ghost', onclick: () => nav(`#/team/${r.team_id}`) }, '返回团队')));
    } else if (r.status === 'stopped') {
      resultBox.append(h('div', { class: 'lz-result' }, '已停止。', h('button', { class: 'lz-btn block ghost', onclick: () => nav(`#/team/${r.team_id}`) }, '返回团队')));
    }
  }

  mount(shell(
    h('button', { class: 'lz-back', onclick: () => nav('#/history') }, '‹ 运行历史'),
    h('div', { class: 'lz-sec-t big' }, '🛰 作战室'),
    head, h('div', { class: 'lz-tl-t' }, '协作过程'), timeline, resultBox));

  for (const s of init.steps) stepsById.set(s.id, s);
  renderHead(init.run); paintTimeline();

  let es = null;
  function finish(r) { stopBtn.hidden = true; renderHead(r); renderResult(r); }
  if (init.run.status !== 'running') { finish(init.run); return; }

  stopBtn.hidden = false;
  es = sse(`/api/runs/${id}/events`, {
    step: (s) => { stepsById.set(s.id, s); paintTimeline(); if (s.status === 'running') timeline.lastChild?.scrollIntoView?.({ block: 'nearest' }); },
    done: async () => { es?.close(); try { const full = await GET(`/api/runs/${id}`); for (const s of full.steps) stepsById.set(s.id, s); paintTimeline(); finish(full.run); } catch { /* ignore */ } },
    error: (e) => { es?.close(); toast(e.error || '运行失败', 'warn'); GET(`/api/runs/${id}`).then((full) => finish(full.run)).catch(() => {}); }
  });
  window.addEventListener('hashchange', () => es?.close(), { once: true });
}

// ---------------- 运行历史 ----------------
async function renderHistory() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const { items } = await GET('/api/runs');
    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '运行历史'),
      items.length ? h('div', { class: 'lz-runs' }, items.map((r) => {
        const [label, cls] = STATUS[r.status] || ['—', ''];
        return h('div', { class: 'lz-run-row', onclick: () => nav(`#/run/${r.id}`) },
          h('span', { class: 'lz-strat' }, stratIcon(r.strategy) + ' ' + r.team_name),
          h('div', { class: 'lz-run-task' }, r.task),
          h('div', { class: 'lz-run-side' },
            h('span', { class: 'lz-st ' + cls }, label),
            h('small', {}, `${r.step_count} 步 · ${r.by_llm ? '大模型' : '本地'} · ${fmtTime(r.started_at)}`)));
      })) : empty('还没有运行记录', '去团队广场派一个任务吧')));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 建队 / 编辑 ----------------
async function renderBuilder(editId) {
  mount(shell(spinner()));
  try {
    const m = await loadMeta();
    const agents = await GET('/api/agents');
    const allAgents = [...agents.mine, ...agents.templates];
    let team = { name: '', avatar: '🛰', goal: '', strategy: 'orchestrate', manager_note: '', member_ids: [], max_rounds: 3 };
    if (editId) {
      const d = await GET(`/api/teams/${editId}`);
      if (!d.team.mine) { mount(shell(empty('只能编辑自己的团队', '可先「复制为我的」'))); return; }
      team = { name: d.team.name, avatar: d.team.avatar, goal: d.team.goal, strategy: d.team.strategy, manager_note: d.team.manager_note, member_ids: d.members.map((x) => x.id), max_rounds: d.team.max_rounds };
    }
    const sel = new Set(team.member_ids);

    const fName = h('input', { class: 'lz-in', value: team.name, placeholder: '团队名（如：内容创作小组）', maxlength: 24 });
    const fAva = h('input', { class: 'lz-in tiny', value: team.avatar, maxlength: 8 });
    const fGoal = h('textarea', { class: 'lz-ta', rows: 2, placeholder: '团队使命：这支队伍要达成什么' }); fGoal.value = team.goal || '';
    const fNote = h('textarea', { class: 'lz-ta', rows: 2, placeholder: '编排官指令（可选）：风格 / 边界 / 偏好' }); fNote.value = team.manager_note || '';
    const fRounds = h('input', { class: 'lz-in tiny', type: 'number', min: 1, max: m.limits.max_rounds, value: team.max_rounds });

    const stratWrap = h('div', { class: 'lz-strat-pick' }, m.strategies.map((s) =>
      h('button', { class: 'lz-strat-opt' + (team.strategy === s.id ? ' on' : ''), onclick: () => { team.strategy = s.id; for (const b of stratWrap.children) b.classList.toggle('on', b.dataset.k === s.id); }, 'data-k': s.id },
        h('b', {}, s.icon + ' ' + s.name), h('small', {}, s.blurb))));

    const roster = h('div', { class: 'lz-pick-grid' }, allAgents.map((a) => {
      const card = h('button', { class: 'lz-pick' + (sel.has(a.id) ? ' on' : ''), onclick: () => {
        if (sel.has(a.id)) sel.delete(a.id);
        else { if (sel.size >= m.limits.max_members) { toast(`最多 ${m.limits.max_members} 名成员`, 'warn'); return; } sel.add(a.id); }
        card.classList.toggle('on', sel.has(a.id));
        cnt.textContent = `已选 ${sel.size} / ${m.limits.max_members}`;
      } }, h('span', { class: 'lz-ava' }, a.avatar), h('div', {}, h('b', {}, a.name), h('small', {}, a.role || '')));
      return card;
    }));
    const cnt = h('small', { class: 'lz-pick-cnt' }, `已选 ${sel.size} / ${m.limits.max_members}`);

    const save = h('button', { class: 'lz-btn block xl' }, editId ? '保存修改' : '创建团队');
    save.addEventListener('click', async () => {
      const body = { name: fName.value.trim(), avatar: fAva.value.trim() || '🛰', goal: fGoal.value.trim(), strategy: team.strategy, manager_note: fNote.value.trim(), member_ids: [...sel], max_rounds: Number(fRounds.value) || 3 };
      if (!body.name) { toast('给团队起个名字', 'warn'); return; }
      if (!body.member_ids.length) { toast('至少选 1 名成员', 'warn'); return; }
      save.disabled = true;
      try {
        const { team: nt } = editId ? await PATCH(`/api/teams/${editId}`, body) : await POST('/api/teams', body);
        toast(editId ? '已保存' : '团队已创建'); nav(`#/team/${nt.id}`);
      } catch (e) { toast(e.message, 'warn'); save.disabled = false; }
    });

    mount(shell(
      h('button', { class: 'lz-back', onclick: () => history.back() }, '‹ 返回'),
      h('div', { class: 'lz-sec-t big' }, editId ? '编辑团队' : '组建一支 AI 团队'),
      h('div', { class: 'lz-form' },
        h('label', {}, '团队名 / 头像'),
        h('div', { class: 'lz-row' }, fName, fAva),
        h('label', {}, '团队使命'), fGoal,
        h('label', {}, '编排策略'), stratWrap,
        h('label', {}, ['选择成员 ', cnt]), roster,
        h('label', {}, '编排官指令（可选）'), fNote,
        h('label', {}, ['每位成员最大工具轮数（1-', String(m.limits.max_rounds), '）']), fRounds,
        save)));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 路由 ----------------
function route() {
  if (!state.me) { renderLogin(); return; }
  const hash = location.hash || '#/';
  const [path, p1] = hash.replace(/^#\//, '').split('/');
  if (path === 'team' && p1) return renderTeam(p1);
  if (path === 'run' && p1) return renderRun(p1);
  if (path === 'history') return renderHistory();
  if (path === 'new') return renderBuilder(null);
  if (path === 'edit' && p1) return renderBuilder(p1);
  return renderHome();
}

async function boot() {
  if (getToken()) { try { state.me = await GET('/api/me'); } catch { setToken(''); } }
  window.addEventListener('hashchange', route);
  route();
}
boot();
