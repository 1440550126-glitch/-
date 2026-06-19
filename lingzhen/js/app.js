// 灵阵 · AI 团队（独立站）：登录 → 团队广场/模板 → 派单 → 作战室实时直播 → 历史 → 建队。
// 对接 AI句灵 服务端现有 /api/agents·/api/teams·/api/runs 接口；无大模型 Key 时后端走本地引擎，零成本可跑通。
import { GET, POST, PUT, PATCH, DEL, sse, getToken, setToken } from './api.js';

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
const isMemberNow = () => (state.me?.member_until || 0) > Date.now();
const yuan = (fen) => '¥' + (fen / 100).toFixed(2).replace(/\.00$/, '');

// ---------------- 弹窗 / 转化 ----------------
function closeModal() { document.querySelector('.lz-mask')?.remove(); }
function modal(...content) {
  closeModal();
  const mask = h('div', { class: 'lz-mask', onclick: (e) => { if (e.target === mask) closeModal(); } },
    h('div', { class: 'lz-modal' }, h('button', { class: 'lz-modal-x', onclick: closeModal }, '✕'), ...content));
  document.body.append(mask);
  requestAnimationFrame(() => mask.classList.add('show'));
  return mask;
}
function upgradeModal(msg) {
  modal(h('div', { class: 'lz-up' },
    h('div', { class: 'lz-up-i' }, '👑'),
    h('h3', {}, '今天的免费额度用完了'),
    h('p', {}, msg || '免费每天可体验 8 次。订阅会员并自带大模型 Key，即可用自己的模型不限量跑。'),
    h('div', { class: 'lz-up-rows' },
      h('div', {}, h('b', {}, '8 → ∞'), h('small', {}, '自带 Key 不限量')),
      h('div', {}, h('b', {}, '自带模型'), h('small', {}, '任意 OpenAI 兼容')),
      h('div', {}, h('b', {}, '¥39 起'), h('small', {}, '按月订阅'))),
    h('button', { class: 'lz-btn block xl', onclick: () => { closeModal(); nav('#/pricing'); } }, '查看订阅方案'),
    h('button', { class: 'lz-btn ghost block', onclick: closeModal }, '明天再来')));
}
// 配额耗尽 → 转化弹窗；其余错误 → toast
function handleErr(e) {
  if (e?.extra?.quota_exceeded || e?.extra?.need_member) upgradeModal(e.message);
  else toast(e?.message || '出错了，稍后再试', 'warn');
}

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
const toolMeta = (id) => (state.meta?.tools || []).find((t) => t.id === id);
const toolName = (id) => toolMeta(id)?.name || id;
const toolIcon = (id) => toolMeta(id)?.icon || '🔧';

// 示例任务：消灭"空白输入框"，也用于新手一键体验
const SAMPLE_TASKS = {
  '内容创作小组': '围绕「下班后的城市露营」写一篇小红书种草文案，并给 3 个标题',
  '市场调研参谋部': '分析「年轻人为什么爱喝手冲咖啡」，给出 3 个洞察和 1 个机会点',
  '产品冲刺组': '为「帮上班族高效午休的小程序」列出 MVP 功能清单与优先级',
  '流水线写作台': '写一篇 500 字短文：《如果城市可以静音一小时》',
  '吵架群': '就「周报到底有没有用」吵一架，正反方各来三轮',
  '杠精辩论赛': '辩论「AI 会不会让人变懒」，正反方各打三回合并给裁判结论',
  '赛博算命馆': '给「测试工程师 · 林」算一卦今天的工作运势',
  '唐诗文学创作组': '以「深夜便利店」为题作一首五言绝句，并附简短赏析'
};
function sampleTask(team) {
  if (SAMPLE_TASKS[team?.name]) return SAMPLE_TASKS[team.name];
  const g = (team?.goal || '').trim();
  return g ? `围绕「${g}」给我一份可直接用的产出` : '用你们的专业能力，帮我策划一场周末城市市集';
}

// ---------------- 公共 UI 片段 ----------------
const NAV = [
  { label: '团队广场', hash: '#/', match: ['', 'team', 'run', 'batch'] },
  { label: '智能体', hash: '#/agents', match: ['agents', 'agent'] },
  { label: '知识库', hash: '#/kb', match: ['kb'] },
  { label: '触发器', hash: '#/triggers', match: ['triggers'] },
  { label: '历史', hash: '#/history', match: ['history'] },
  { label: '用量', hash: '#/usage', match: ['usage'] },
  { label: '＋ 建队', hash: '#/new', match: ['new', 'edit'], primary: true }
];
const sectionOf = () => (location.hash || '#/').replace(/^#\/?/, '').split('/')[0];
function header() {
  const m = state.me, sec = sectionOf();
  return h('header', { class: 'lz-top' },
    h('div', { class: 'lz-brand', onclick: () => nav('#/') },
      h('span', { class: 'lz-logo' }, '🛰'),
      h('div', {}, h('b', {}, '灵阵'), h('small', {}, 'AI 团队 · 对标扣子'))),
    h('nav', { class: 'lz-nav' }, NAV.map((it) =>
      h('a', { class: it.primary ? 'primary' : (it.match.includes(sec) ? 'on' : ''), onclick: () => nav(it.hash) }, it.label))),
    h('div', { class: 'lz-user' },
      state.meta ? (state.meta.byok
        ? h('a', { class: 'lz-quota vip', title: '自带模型 Key · 不限量', onclick: () => nav('#/llm') }, '🔑 ∞')
        : h('a', { class: 'lz-quota' + (isMemberNow() ? ' vip' : ''), title: isMemberNow() ? '会员 · 查看权益' : '今日剩余运行次数 · 点击升级', onclick: () => nav('#/pricing') },
            (isMemberNow() ? '👑 ' : '⚡ ') + `${state.meta.quota.left}/${state.meta.quota.limit}`)) : null,
      h('a', { class: 'lz-me', title: '个人中心', onclick: () => nav('#/me') }, (isMemberNow() ? '👑 ' : '👤 '), m?.nickname || '我'),
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
  document.title = '灵阵 · AI 团队';
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

    // 新手首跑：一键派单一支示例团队，直达作战室看它们"真的在干活"
    let welcome = null;
    if (!localStorage.getItem('lz_seen_intro') && teams.templates.length) {
      const demo = teams.templates[0];
      const demoBtn = h('button', { class: 'lz-btn xl' }, '🚀 一键跑通一支团队');
      demoBtn.addEventListener('click', async () => {
        demoBtn.disabled = true; demoBtn.textContent = '正在召集「' + demo.name + '」…';
        try {
          const { run_id } = await POST(`/api/teams/${demo.id}/run`, { task: sampleTask(demo) });
          localStorage.setItem('lz_seen_intro', '1');
          nav(`#/run/${run_id}`);
        } catch (e) { handleErr(e); demoBtn.disabled = false; demoBtn.textContent = '🚀 一键跑通一支团队'; }
      });
      welcome = h('div', { class: 'lz-welcome' },
        h('button', { class: 'lz-welcome-x', title: '关闭', onclick: () => { localStorage.setItem('lz_seen_intro', '1'); welcome.remove(); } }, '✕'),
        h('div', { class: 'lz-welcome-i' }, '🛰'),
        h('h2', {}, '欢迎来到灵阵'),
        h('p', {}, '一句话，调动一支会分工的专业 AI 团队替你干活。要不要现在就看一支团队跑起来？'),
        demoBtn,
        h('div', { class: 'lz-welcome-steps' }, h('span', {}, '① 选团队'), h('span', {}, '② 下达任务'), h('span', {}, '③ 作战室看协作交付')));
    }

    mount(shell(
      welcome,
      welcome ? null : h('section', { class: 'lz-intro' },
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
    const [{ team, members }, runsData] = await Promise.all([
      GET(`/api/teams/${id}`),
      GET('/api/runs').catch(() => ({ items: [] }))
    ]);
    const teamRuns = (runsData.items || []).filter((r) => String(r.team_id) === String(id)).slice(0, 6);
    const recentRow = (r) => {
      const [label, cls] = STATUS[r.status] || ['—', ''];
      return h('div', { class: 'lz-run-row', onclick: () => nav(`#/run/${r.id}`) },
        h('div', { class: 'lz-run-task', style: { flex: '1' } }, r.task),
        h('div', { class: 'lz-run-side' },
          h('span', { class: 'lz-st ' + cls }, label),
          h('small', {}, `${r.step_count} 步 · ${r.by_llm ? '大模型' : '本地'} · ${fmtTime(r.started_at)}`)));
    };

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
      runBox(team),
      teamRuns.length ? h('div', { class: 'lz-team-runs' },
        h('div', { class: 'lz-runs-head' },
          h('div', { class: 'lz-sec-t', style: { margin: '0' } }, `本团队最近运行（${teamRuns.length}）`),
          h('a', { class: 'lz-link', onclick: () => nav('#/history') }, '全部历史 →')),
        h('div', { class: 'lz-runs' }, teamRuns.map(recentRow))) : null,
      actions,
      team.mine && !team.is_template ? apiPanel(team) : null,
      team.mine && !team.is_template ? webhookPanel(team) : null,
      team.mine && !team.is_template ? memoryPanel(team) : null));
  } catch (e) { mount(shell(empty('团队不存在或无权访问', e.message))); }
}

// 派单：单次 / 批量（一个任务模板套用多条输入，逐条排队执行）
function runBox(team) {
  const id = team.id;
  let mode = 'single';
  const box = h('div', { class: 'lz-run-box' });
  const ta = h('textarea', { class: 'lz-ta', rows: 4, placeholder: '描述要这支团队完成什么，例如：围绕「年轻人露营」写一篇小红书种草文案，并给3个标题。' });
  const tplTa = h('textarea', { class: 'lz-ta', rows: 3, placeholder: '任务模板，用 {{input}} 代表每条输入。例：为「{{input}}」写一句小红书标题。' });
  const itemsTa = h('textarea', { class: 'lz-ta', rows: 5, placeholder: '每行一条输入（最多 10 条）：\n露营\n飞盘\n骑行' });
  function draw() {
    box.innerHTML = '';
    box.append(
      h('div', { class: 'lz-sec-t' }, '给这支团队下达任务'),
      h('p', { class: 'lz-hint', style: { margin: '0 0 10px' } }, '派单后团队自动协作产出 → 验收官把关 → 不达标就继续改进，直到通过验收才停下；可在下方配置完成后通知飞书。'),
      h('div', { class: 'lz-mode-tabs' },
        h('button', { class: 'lz-mode' + (mode === 'single' ? ' on' : ''), onclick: () => { if (mode !== 'single') { mode = 'single'; draw(); } } }, '单次派单'),
        h('button', { class: 'lz-mode' + (mode === 'batch' ? ' on' : ''), onclick: () => { if (mode !== 'batch') { mode = 'batch'; draw(); } } }, '批量派单')));
    if (mode === 'single') {
      const runBtn = h('button', { class: 'lz-btn block xl' }, '🚀 派单运行');
      runBtn.addEventListener('click', async () => {
        const task = ta.value.trim();
        if (!task) { ta.focus(); toast('先描述一下任务', 'warn'); return; }
        runBtn.disabled = true; runBtn.textContent = '正在创建运行…';
        try { const { run_id } = await POST(`/api/teams/${id}/run`, { task }); nav(`#/run/${run_id}`); }
        catch (e) { handleErr(e); runBtn.disabled = false; runBtn.textContent = '🚀 派单运行'; }
      });
      const sample = sampleTask(team);
      const chip = h('button', { class: 'lz-chip-btn', onclick: () => { ta.value = sample; ta.focus(); } }, '✨ 试试：' + sample);
      box.append(ta, h('div', { class: 'lz-samples-row' }, chip), runBtn);
    } else {
      const batchBtn = h('button', { class: 'lz-btn block xl' }, '🚀 批量派单');
      batchBtn.addEventListener('click', async () => {
        const task = tplTa.value.trim();
        const items = itemsTa.value.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 10);
        if (!task) { toast('先写任务模板', 'warn'); return; }
        if (!items.length) { toast('至少给一条输入', 'warn'); return; }
        batchBtn.disabled = true; batchBtn.textContent = '正在创建…';
        try { const { batch_id } = await POST(`/api/teams/${id}/batch`, { task, items }); nav(`#/batch/${batch_id}`); }
        catch (e) { handleErr(e); batchBtn.disabled = false; batchBtn.textContent = '🚀 批量派单'; }
      });
      box.append(
        h('p', { class: 'lz-hint' }, '一个任务模板套用多条输入，逐条排队执行，结果汇总到一张表。'),
        h('label', { class: 'lz-form-lbl' }, '任务模板'), tplTa,
        h('label', { class: 'lz-form-lbl' }, '输入列表（每行一条，最多 10 条）'), itemsTa, batchBtn);
    }
  }
  draw();
  return box;
}

// 出站 Webhook：运行完成后把结果 POST 给外部地址（可对接微信/飞书机器人、自动化平台）
function webhookPanel(team) {
  const box = h('div', { class: 'lz-api' });
  function draw(url) {
    box.innerHTML = '';
    box.append(
      h('div', { class: 'lz-sec-t' }, '🔔 完成通知 / 出站 Webhook'),
      h('p', { class: 'lz-api-desc' }, '任务完成（通过验收）后自动推送结果到这个地址。粘贴飞书自定义机器人 webhook 即按飞书格式发送通知（机器人安全设置加关键词「灵阵」即可放行）；其它地址按通用 JSON 推送，可对接企业微信、n8n 等。'));
    const urlIn = h('input', { class: 'lz-in', placeholder: 'https://open.feishu.cn/open-apis/bot/v2/hook/…', value: url || '' });
    const saveBtn = h('button', { class: 'lz-btn sm' }, url ? '更新' : '保存');
    saveBtn.addEventListener('click', async () => {
      const v = urlIn.value.trim();
      if (!v) { toast('填一个回调地址', 'warn'); return; }
      saveBtn.disabled = true;
      try { const r = await PUT(`/api/teams/${team.id}/webhook`, { url: v }); toast('已保存'); draw(r.webhook_url); }
      catch (e) { toast(e.message, 'warn'); saveBtn.disabled = false; }
    });
    box.append(h('div', { class: 'lz-row' }, urlIn, saveBtn));
    if (url) box.append(h('div', { class: 'lz-api-actions', style: { marginTop: '10px' } },
      h('span', { class: 'lz-tag pub' }, '● 已开启'),
      h('button', { class: 'lz-btn ghost danger sm', onclick: async () => {
        if (!confirm('移除 Webhook？')) return;
        try { await DEL(`/api/teams/${team.id}/webhook`); toast('已移除'); draw(''); } catch (e) { toast(e.message, 'warn'); }
      } }, '移除')));
  }
  draw(team.webhook_url || '');
  return box;
}

// 团队记忆：长期键值记忆，任务里用 {{键名}} 引用，运行时自动填充
function memoryPanel(team) {
  const box = h('div', { class: 'lz-api' });
  async function load() {
    box.innerHTML = '';
    box.append(
      h('div', { class: 'lz-sec-t' }, '🧠 团队记忆'),
      h('p', { class: 'lz-api-desc' }, '沉淀团队的长期记忆（品牌名、语气、受众…）。在任务里用 {{键名}} 引用，运行时自动填充——把流程一次配置、反复复用。最多 50 条。'));
    let items = [];
    try { items = (await GET(`/api/teams/${team.id}/memory`)).items; } catch (e) { /* ignore */ }
    const list = h('div', { class: 'lz-mem-list' });
    if (!items.length) list.append(h('p', { class: 'lz-hint' }, '还没有记忆条目，下面加一条试试。'));
    for (const it of items) list.append(h('div', { class: 'lz-mem-row' },
      h('code', { class: 'lz-mem-k' }, '{{' + it.key + '}}'),
      h('span', { class: 'lz-mem-v' }, it.value || '（空）'),
      h('button', { class: 'lz-btn mini ghost danger', onclick: async () => {
        try { await DEL(`/api/teams/${team.id}/memory/${encodeURIComponent(it.key)}`); toast('已删除'); load(); }
        catch (e) { toast(e.message, 'warn'); }
      } }, '删除')));
    const kIn = h('input', { class: 'lz-in', placeholder: '键名（如 品牌名）', maxlength: 60 });
    const vIn = h('input', { class: 'lz-in', placeholder: '值', maxlength: 500 });
    const addBtn = h('button', { class: 'lz-btn sm' }, '＋ 保存');
    addBtn.addEventListener('click', async () => {
      const key = kIn.value.trim();
      if (!key) { toast('填个键名', 'warn'); return; }
      addBtn.disabled = true;
      try { await PUT(`/api/teams/${team.id}/memory`, { key, value: vIn.value.trim() }); toast('已保存'); load(); }
      catch (e) { toast(e.message, 'warn'); addBtn.disabled = false; }
    });
    box.append(list, h('div', { class: 'lz-mem-add' }, kIn, vIn, addBtn));
  }
  load();
  return box;
}

// 对外 API：为自己的团队生成密钥，任意外部系统可凭密钥同步调用（无需登录）
function apiPanel(team) {
  const box = h('div', { class: 'lz-api' });
  async function regen() {
    try { const d = await POST(`/api/teams/${team.id}/api-key`); draw(true, d.api_key); toast('已生成新密钥'); }
    catch (e) { toast(e.message, 'warn'); }
  }
  async function revoke() {
    if (!confirm('吊销后，使用此密钥的所有外部调用都会失效。继续？')) return;
    try { await DEL(`/api/teams/${team.id}/api-key`); toast('已吊销'); draw(false, null); }
    catch (e) { toast(e.message, 'warn'); }
  }
  function draw(hasApi, freshKey) {
    box.innerHTML = '';
    box.append(h('div', { class: 'lz-sec-t' }, '🔌 对外 API'),
      h('p', { class: 'lz-api-desc' }, '生成团队密钥后，任意外部系统可凭密钥同步调用该团队（无需登录），每天 50 次。'));
    if (freshKey) {
      box.append(h('div', { class: 'lz-key-box' },
        h('div', { class: 'lz-key-warn' }, '⚠ 密钥只显示这一次，请立即复制保存：'),
        h('div', { class: 'lz-key-row' }, h('code', { class: 'lz-key' }, freshKey), h('button', { class: 'lz-btn mini', onclick: () => copy(freshKey) }, '复制')),
        h('div', { class: 'lz-curl-t' }, '调用示例'),
        h('pre', { class: 'lz-curl' }, `curl -X POST ${location.origin}/api/public/run \\\n  -H 'Content-Type: application/json' \\\n  -d '{"key":"${freshKey}","task":"你的任务描述"}'`)));
    }
    const row = h('div', { class: 'lz-api-actions' });
    if (hasApi) row.append(h('span', { class: 'lz-tag pub' }, '● API 已开启'),
      h('button', { class: 'lz-btn ghost sm', onclick: regen }, '重新生成'),
      h('button', { class: 'lz-btn ghost danger sm', onclick: revoke }, '吊销'));
    else row.append(h('button', { class: 'lz-btn sm', onclick: regen }, '生成 API 密钥'));
    box.append(row);
  }
  draw(team.has_api, null);
  return box;
}

// ---------------- 作战室：实时直播 ----------------
// 单个协作步骤节点（作战室 + 公开分享页共用）
function stepNode(s) {
  const running = s.status === 'running';
  if (s.phase === 'tool') {
    return h('div', { class: 'lz-step tool' },
      h('div', { class: 'lz-tool-line' }, '🔧 ', h('b', {}, s.agent_name), ' 调用 ', h('code', {}, String(s.title || '').replace('调用工具 · ', '')), running ? h('span', { class: 'lz-dots' }, '…') : null),
      s.tool_result ? h('div', { class: 'lz-tool-out' }, String(s.tool_result).slice(0, 500)) : null);
  }
  const phaseCls = { plan: 'plan', act: 'act', synthesize: 'synth', system: 'sys', review: 'review' }[s.phase] || '';
  const badge = { plan: '编排官拆解', synthesize: '总编整合', system: '系统', review: '验收官' }[s.phase] || '';
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

// 生成分享链接并弹窗
async function shareRun(id) {
  try { const { share_id } = await POST(`/api/runs/${id}/share`); shareModal(`${location.origin}/lingzhen#/s/${share_id}`); }
  catch (e) { handleErr(e); }
}
function shareModal(url) {
  const input = h('input', { class: 'lz-in', value: url, readonly: true, onclick: (e) => e.target.select() });
  modal(h('div', { class: 'lz-up' },
    h('div', { class: 'lz-up-i' }, '🔗'),
    h('h3', {}, '分享这次协作'),
    h('p', {}, '任何人打开链接都能看到这支团队的完整协作过程与交付（只读），并能一键来组建自己的。'),
    h('div', { class: 'lz-key-row' }, input, h('button', { class: 'lz-btn', onclick: () => copy(url) }, '复制')),
    h('a', { class: 'lz-btn ghost block', href: url, target: '_blank', rel: 'noopener' }, '在新标签预览')));
}

// 公开分享页（免登录只读，自带获客 CTA）
function shareTopbar() {
  const go = () => { location.hash = '#/'; };
  return h('header', { class: 'lz-top' },
    h('div', { class: 'lz-brand', onclick: go }, h('span', { class: 'lz-logo' }, '🛰'), h('div', {}, h('b', {}, '灵阵'), h('small', {}, 'AI 团队 · 对标扣子'))),
    h('a', { class: 'lz-btn sm', onclick: go }, '进入灵阵 →'));
}
async function renderShare(shareId) {
  document.title = '灵阵 · 协作分享';
  mount(h('div', { class: 'lz-shell' }, shareTopbar(), h('main', { class: 'lz-main' }, spinner())));
  let data;
  try { data = await GET(`/api/public/share/${encodeURIComponent(shareId)}`); }
  catch (e) { mount(h('div', { class: 'lz-shell' }, shareTopbar(), h('main', { class: 'lz-main' }, empty('分享不存在或已取消', e.message)))); return; }
  const r = data.run;
  const cta = (label) => { const b = h('button', { class: 'lz-btn xl' }, label); b.addEventListener('click', () => { location.hash = '#/'; }); return b; };
  mount(h('div', { class: 'lz-shell' }, shareTopbar(),
    h('main', { class: 'lz-main lz-share' },
      h('div', { class: 'lz-share-hero' },
        h('div', { class: 'lz-share-badge' }, '🛰 灵阵 · AI 团队协作回放'),
        h('h1', {}, r.team_name),
        h('p', { class: 'lz-rh-task' }, '🎯 ' + r.task),
        h('div', { class: 'lz-share-meta' },
          r.by_llm ? h('span', { class: 'lz-chip llm' }, '大模型协作') : h('span', { class: 'lz-chip local' }, '本地引擎'),
          h('span', { class: 'lz-st done' }, '已完成 · ' + r.step_count + ' 步'))),
      cta('✨ 我也要组建一支 AI 团队'),
      h('div', { class: 'lz-tl-t' }, '协作过程'),
      h('div', { class: 'lz-timeline' }, data.steps.map(stepNode)),
      r.result ? h('div', { class: 'lz-result' },
        h('div', { class: 'lz-result-h' }, h('span', {}, '🧩 最终交付'), h('button', { class: 'lz-btn mini ghost', onclick: () => copy(r.result) }, '复制')),
        mdBody(r.result)) : null,
      h('div', { class: 'lz-share-foot' },
        h('p', {}, '这支团队由「灵阵」零代码组建 · 一句话，调动一支会分工的 AI 团队替你干活'),
        cta('🚀 免费试一支团队')))));
}

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

  function renderResult(r) {
    resultBox.innerHTML = '';
    if (r.status === 'done' && r.result) {
      resultBox.append(h('div', { class: 'lz-result' },
        h('div', { class: 'lz-result-h' }, h('span', {}, '🧩 最终交付'),
          h('div', { class: 'lz-result-acts' },
            h('button', { class: 'lz-btn mini ghost', onclick: () => shareRun(r.id) }, '🔗 分享'),
            h('button', { class: 'lz-btn mini ghost', onclick: () => copy(r.result) }, '复制'))),
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

// ---------------- 运行历史 / 草稿箱 ----------------
function runsView(items) {
  if (!items.length) return empty('还没有运行记录', '去团队广场派一个任务吧');
  return h('div', { class: 'lz-runs' }, items.map((r) => {
    const [label, cls] = STATUS[r.status] || ['—', ''];
    return h('div', { class: 'lz-run-row', onclick: () => nav(`#/run/${r.id}`) },
      h('span', { class: 'lz-strat' }, stratIcon(r.strategy) + ' ' + r.team_name),
      h('div', { class: 'lz-run-task' }, r.task),
      h('div', { class: 'lz-run-side' },
        h('span', { class: 'lz-st ' + cls }, label),
        h('small', {}, `${r.step_count} 步 · ${r.by_llm ? '大模型' : '本地'} · ${fmtTime(r.started_at)}`)));
  }));
}
function draftsView(items) {
  if (!items.length) return empty('草稿箱是空的', '让带「📥 文案入草稿箱」工具的成员跑一条任务，产出会落在这里');
  const wrap = h('div', { class: 'lz-drafts' });
  for (const d of items) {
    const card = d.card || {};
    const row = h('div', { class: 'lz-draft' },
      h('div', { class: 'lz-draft-text' }, d.text),
      h('div', { class: 'lz-draft-meta' },
        card.emotion ? h('span', { class: 'lz-src' }, '情绪 · ' + card.emotion) : null,
        card.scene ? h('span', { class: 'lz-src' }, '场景 · ' + card.scene) : null,
        h('small', {}, fmtTime(d.created_at))),
      h('div', { class: 'lz-draft-acts' },
        h('button', { class: 'lz-btn mini', onclick: () => copy(d.text) }, '复制'),
        d.run_id ? h('button', { class: 'lz-btn mini ghost', onclick: () => nav(`#/run/${d.run_id}`) }, '来源运行') : null,
        h('button', { class: 'lz-btn mini ghost danger', onclick: async () => {
          try { await DEL(`/api/agent-drafts/${d.id}`); toast('已删除'); row.remove(); } catch (e) { toast(e.message, 'warn'); }
        } }, '删除')));
    wrap.append(row);
  }
  return wrap;
}
async function renderHistory() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const [runs, drafts] = await Promise.all([GET('/api/runs'), GET('/api/agent-drafts').catch(() => ({ items: [] }))]);
    let tab = location.hash.includes('drafts') ? 'drafts' : 'runs';
    const tabbar = h('div', { class: 'lz-tabs' });
    const body = h('div', {});
    function paint() {
      tabbar.innerHTML = '';
      for (const [k, lbl] of [['runs', '运行历史 ' + runs.items.length], ['drafts', '草稿箱 ' + drafts.items.length]])
        tabbar.append(h('button', { class: 'lz-tab' + (tab === k ? ' on' : ''), onclick: () => { tab = k; paint(); } }, lbl));
      body.innerHTML = '';
      body.append(tab === 'runs' ? runsView(runs.items) : draftsView(drafts.items));
    }
    paint();
    mount(shell(h('div', { class: 'lz-sec-t big' }, '运行记录'), tabbar, body));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 批量运行结果 ----------------
async function renderBatch(batchId) {
  mount(shell(spinner()));
  let data;
  try { data = await GET(`/api/runs/batch/${batchId}`); }
  catch (e) { mount(shell(empty('批量任务不存在', e.message))); return; }
  await loadMeta();

  const wrap = h('div', { class: 'lz-batch' });
  function paint(d) {
    wrap.innerHTML = '';
    const done = d.items.filter((r) => r.status !== 'running').length;
    wrap.append(h('div', { class: 'lz-batch-bar' },
      h('span', {}, `共 ${d.items.length} 条 · 已完成 ${done}/${d.items.length}`),
      d.done ? h('span', { class: 'lz-st done' }, '全部完成') : h('span', { class: 'lz-st run' }, '运行中…')));
    for (const r of d.items) {
      const [label, cls] = STATUS[r.status] || ['—', ''];
      wrap.append(h('div', { class: 'lz-batch-item', onclick: () => nav(`#/run/${r.id}`) },
        h('div', { class: 'lz-batch-h' },
          h('div', { class: 'lz-batch-task' }, r.task),
          h('span', { class: 'lz-st ' + cls }, label)),
        r.result ? h('div', { class: 'lz-batch-res' }, String(r.result).slice(0, 240))
          : (r.status === 'running' ? h('div', { class: 'lz-hint' }, '排队 / 运行中…') : null)));
    }
  }
  paint(data);
  mount(shell(
    h('button', { class: 'lz-back', onclick: () => nav('#/history') }, '‹ 运行历史'),
    h('div', { class: 'lz-sec-t big' }, '📦 批量运行'),
    h('p', { class: 'lz-intro' }, '同一团队对多条输入逐条执行，点任意一条进入它的作战室看全过程。'),
    wrap));

  let stop = false;
  window.addEventListener('hashchange', () => { stop = true; }, { once: true });
  while (!data.done && !stop) {
    await new Promise((r) => setTimeout(r, 1300));
    if (stop) break;
    try { data = await GET(`/api/runs/batch/${batchId}`); paint(data); } catch { break; }
  }
}

// ---------------- 建队 / 编辑 ----------------
async function renderBuilder(editId) {
  mount(shell(spinner()));
  try {
    const m = await loadMeta();
    const [agents, kbsData] = await Promise.all([GET('/api/agents'), GET('/api/kb')]);
    const allAgents = [...agents.mine, ...agents.templates];
    const allKbs = [...kbsData.mine, ...kbsData.templates];
    let team = { name: '', avatar: '🛰', goal: '', strategy: 'orchestrate', manager_note: '', member_ids: [], knowledge_ids: [], max_rounds: 3 };
    if (editId) {
      const d = await GET(`/api/teams/${editId}`);
      if (!d.team.mine) { mount(shell(empty('只能编辑自己的团队', '可先「复制为我的」'))); return; }
      team = { name: d.team.name, avatar: d.team.avatar, goal: d.team.goal, strategy: d.team.strategy, manager_note: d.team.manager_note, member_ids: d.members.map((x) => x.id), knowledge_ids: d.team.knowledge_ids || [], max_rounds: d.team.max_rounds };
    }
    const sel = new Set(team.member_ids);
    const kbSel = new Set(team.knowledge_ids);

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

    const kbPicker = allKbs.length
      ? h('div', { class: 'lz-pick-grid' }, allKbs.map((k) => {
        const card = h('button', { class: 'lz-pick' + (kbSel.has(k.id) ? ' on' : ''), onclick: () => {
          if (kbSel.has(k.id)) kbSel.delete(k.id); else kbSel.add(k.id);
          card.classList.toggle('on', kbSel.has(k.id));
        } }, h('span', { class: 'lz-ava' }, '📚'), h('div', {}, h('b', {}, k.name), h('small', {}, `${k.chunk_count || 0} 块` + (k.is_template ? ' · 示例' : ''))));
        return card;
      }))
      : h('p', { class: 'lz-hint' }, '还没有知识库，可先到「知识库」创建，再回来挂载（可选）。');

    const save = h('button', { class: 'lz-btn block xl' }, editId ? '保存修改' : '创建团队');
    save.addEventListener('click', async () => {
      const body = { name: fName.value.trim(), avatar: fAva.value.trim() || '🛰', goal: fGoal.value.trim(), strategy: team.strategy, manager_note: fNote.value.trim(), member_ids: [...sel], knowledge_ids: [...kbSel], max_rounds: Number(fRounds.value) || 3 };
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
        h('p', { class: 'lz-hint' }, '没有合适的成员？', h('a', { class: 'lz-link', onclick: () => nav('#/agent/new') }, '去智能体工作室造一个 →')),
        h('label', {}, '挂载知识库（可选 · 供调研类成员 RAG 检索）'), kbPicker,
        h('label', {}, '编排官指令（可选）'), fNote,
        h('label', {}, ['每位成员最大工具轮数（1-', String(m.limits.max_rounds), '）']), fRounds,
        save)));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 知识库（RAG） ----------------
async function renderKB() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const { mine, templates } = await GET('/api/kb');
    const nameIn = h('input', { class: 'lz-in', placeholder: '知识库名称（如：产品资料）', maxlength: 30 });
    const descIn = h('input', { class: 'lz-in', placeholder: '简介（可选）', maxlength: 200 });
    const createBtn = h('button', { class: 'lz-btn' }, '＋ 新建');
    createBtn.addEventListener('click', async () => {
      const name = nameIn.value.trim();
      if (!name) { toast('给知识库起个名字', 'warn'); return; }
      createBtn.disabled = true;
      try { const { kb } = await POST('/api/kb', { name, description: descIn.value.trim() }); toast('已创建'); nav(`#/kb/${kb.id}`); }
      catch (e) { toast(e.message, 'warn'); createBtn.disabled = false; }
    });
    const card = (k) => h('article', { class: 'lz-card', onclick: () => nav(`#/kb/${k.id}`) },
      h('div', { class: 'lz-card-h' }, h('span', { class: 'lz-ava lg' }, '📚'),
        h('div', { class: 'lz-card-ti' }, h('b', {}, k.name), h('span', { class: 'lz-strat' }, `${k.chunk_count || 0} 块 · ${k.doc_count || 0} 文档`)),
        k.is_template ? h('span', { class: 'lz-tag tpl' }, '示例') : null),
      k.description ? h('p', { class: 'lz-card-goal' }, k.description) : null);
    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '📚 知识库'),
      h('p', { class: 'lz-intro' }, '粘贴资料建库，调研类成员在运行时会自动 RAG 检索它（零依赖关键词检索，中文 bigram 倒排）。'),
      h('div', { class: 'lz-kb-new' }, h('div', { class: 'lz-sec-t' }, '新建知识库'), h('div', { class: 'lz-row' }, nameIn, createBtn), descIn),
      h('div', { class: 'lz-sec-t' }, `我的（${mine.length}）`),
      mine.length ? h('div', { class: 'lz-grid' }, mine.map(card)) : empty('还没有知识库', '建一个，粘贴资料，团队成员就能检索它'),
      templates.length ? h('div', { class: 'lz-sec-t' }, '内置示例') : null,
      templates.length ? h('div', { class: 'lz-grid' }, templates.map(card)) : null));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

async function renderKBDetail(id) {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const data = await GET(`/api/kb/${id}`);
    const kb = data.kb;

    const qIn = h('input', { class: 'lz-in', placeholder: '输入要检索的内容，看 RAG 命中效果' });
    const searchBtn = h('button', { class: 'lz-btn' }, '检索');
    const hits = h('div', { class: 'lz-hits' });
    async function doSearch() {
      const query = qIn.value.trim(); if (!query) return;
      searchBtn.disabled = true;
      try {
        const r = await POST(`/api/kb/${id}/search`, { query });
        hits.innerHTML = '';
        if (!r.hits.length) hits.append(h('p', { class: 'lz-hint' }, '没有命中，换个说法试试。'));
        else for (const hh of r.hits) hits.append(h('div', { class: 'lz-hit' },
          h('div', { class: 'lz-hit-h' }, h('small', {}, '📄 ' + hh.source), h('span', { class: 'lz-score' }, '得分 ' + hh.score)),
          h('div', { class: 'lz-hit-t' }, hh.text)));
      } catch (e) { toast(e.message, 'warn'); }
      searchBtn.disabled = false;
    }
    searchBtn.addEventListener('click', doSearch);
    qIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

    let addBox = null;
    if (kb.mine) {
      const srcIn = h('input', { class: 'lz-in', placeholder: '来源名（如：产品定位.md）', maxlength: 60 });
      const txtIn = h('textarea', { class: 'lz-ta', rows: 5, placeholder: '粘贴文本，自动切块入库（支持中英文）' });
      const addBtn = h('button', { class: 'lz-btn' }, '入库');
      addBtn.addEventListener('click', async () => {
        const text = txtIn.value.trim(); if (!text) { toast('粘贴一些文本', 'warn'); return; }
        addBtn.disabled = true;
        try { const r = await POST(`/api/kb/${id}/docs`, { text, source: srcIn.value.trim() || '文档' }); toast(`已入库 ${r.added} 块`); renderKBDetail(id); }
        catch (e) { toast(e.message, 'warn'); addBtn.disabled = false; }
      });
      addBox = h('div', { class: 'lz-kb-new' }, h('div', { class: 'lz-sec-t' }, '添加文档'), srcIn, txtIn, addBtn);
    }
    const delBtn = kb.mine ? h('button', { class: 'lz-btn ghost danger sm', onclick: async () => {
      if (!confirm('删除这个知识库及其全部内容？')) return;
      try { await DEL(`/api/kb/${id}`); toast('已删除'); nav('#/kb'); } catch (e) { toast(e.message, 'warn'); }
    } }, '🗑 删除知识库') : null;

    mount(shell(
      h('button', { class: 'lz-back', onclick: () => nav('#/kb') }, '‹ 知识库'),
      h('div', { class: 'lz-team-hero' }, h('span', { class: 'lz-ava xl' }, '📚'),
        h('div', { class: 'lz-team-meta' }, h('h1', {}, kb.name),
          h('p', { class: 'lz-goal' }, `${kb.chunk_count || 0} 块 · ${kb.doc_count || 0} 文档` + (kb.mine ? '' : ' · 内置示例（只读）')),
          kb.description ? h('p', { class: 'lz-note' }, kb.description) : null)),
      h('div', { class: 'lz-run-box' }, h('div', { class: 'lz-sec-t' }, '🔎 检索测试'), h('div', { class: 'lz-row' }, qIn, searchBtn), hits),
      addBox,
      data.sources.length ? h('div', { class: 'lz-sec-t' }, '来源') : null,
      data.sources.length ? h('div', { class: 'lz-srcs' }, data.sources.map((s) => h('span', { class: 'lz-src' }, `📄 ${s.source} · ${s.chunks} 块`))) : null,
      data.sample.length ? h('div', { class: 'lz-sec-t' }, '内容预览') : null,
      data.sample.length ? h('div', { class: 'lz-samples' }, data.sample.map((c) => h('div', { class: 'lz-sample' }, h('small', {}, c.source + ' #' + c.idx), h('div', {}, c.text)))) : null,
      delBtn));
  } catch (e) { mount(shell(empty('知识库不存在或无权访问', e.message))); }
}

// ---------------- 定时触发器 ----------------
async function renderTriggers() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const [{ items, limits }, teamsData] = await Promise.all([GET('/api/triggers'), GET('/api/teams')]);
    const myTeams = teamsData.mine;

    const teamSel = h('select', { class: 'lz-in' },
      ...(myTeams.length
        ? myTeams.map((t) => h('option', { value: t.id }, t.name))
        : [h('option', {}, '（暂无我的团队）')]));
    const nameIn = h('input', { class: 'lz-in', placeholder: '任务名（可留空，自动生成）', maxlength: 30 });
    const taskIn = h('textarea', { class: 'lz-ta', rows: 3, placeholder: '自动执行的任务内容（500 字以内）' });

    let kind = 'daily';
    const kindRow = h('div', { class: 'lz-trg-kinds' });
    const hourIn = h('input', { class: 'lz-in tiny', type: 'number', min: 0, max: 23, value: 9 });
    const minIn = h('input', { class: 'lz-in tiny', type: 'number', min: 0, max: 59, value: 0 });
    const intIn = h('input', { class: 'lz-in tiny', type: 'number', min: limits.min_interval_min, max: 1440, value: limits.min_interval_min });
    const dailyBox = h('div', { class: 'lz-trg-time' },
      h('span', {}, '每天 '), hourIn, h('span', {}, ' 时 '), minIn, h('span', {}, ' 分'));
    const intBox = h('div', { class: 'lz-trg-time', hidden: true },
      h('span', {}, '每 '), intIn, h('span', {}, ` 分钟（最少 ${limits.min_interval_min} 分）`));

    function drawKinds() {
      kindRow.innerHTML = '';
      for (const [k, lbl] of [['daily', '每天定时'], ['interval', '按间隔']]) {
        kindRow.append(h('button', {
          class: 'lz-strat-opt' + (kind === k ? ' on' : ''),
          onclick: () => { kind = k; drawKinds(); dailyBox.hidden = k !== 'daily'; intBox.hidden = k !== 'interval'; }
        }, lbl));
      }
    }
    drawKinds();

    const addBtn = h('button', { class: 'lz-btn' }, '＋ 创建触发器');
    addBtn.addEventListener('click', async () => {
      if (!myTeams.length) { toast('先创建一个团队再来设触发器', 'warn'); return; }
      const task = taskIn.value.trim();
      if (!task) { toast('描述要自动执行的任务', 'warn'); return; }
      addBtn.disabled = true;
      try {
        await POST('/api/triggers', {
          team_id: Number(teamSel.value), name: nameIn.value.trim() || undefined, task,
          schedule_kind: kind, at_hour: Number(hourIn.value) || 9,
          at_minute: Number(minIn.value) || 0, interval_min: Number(intIn.value) || limits.min_interval_min
        });
        toast('触发器已创建'); renderTriggers();
      } catch (e) { toast(e.message, 'warn'); addBtn.disabled = false; }
    });

    const fmtSched = (t) =>
      t.schedule_kind === 'daily'
        ? `每天 ${String(t.at_hour).padStart(2, '0')}:${String(t.at_minute).padStart(2, '0')}`
        : `每 ${t.interval_min} 分钟`;

    const listEl = h('div', { class: 'lz-trg-list' });
    if (!items.length) {
      listEl.append(empty('还没有定时触发器', '创建一个，让 AI 团队按计划自动工作'));
    } else {
      for (const t of items) {
        const tgRow = h('div', { class: 'lz-trg-row' });
        const togBtn = h('button', { class: 'lz-toggle' + (t.enabled ? ' on' : '') }, t.enabled ? '启用中' : '已停用');
        togBtn.addEventListener('click', async () => {
          togBtn.disabled = true;
          try {
            const res = await PATCH(`/api/triggers/${t.id}`, { enabled: !t.enabled });
            t.enabled = res.trigger.enabled;
            togBtn.className = 'lz-toggle' + (t.enabled ? ' on' : '');
            togBtn.textContent = t.enabled ? '启用中' : '已停用';
            toast(t.enabled ? '已启用' : '已停用');
          } catch (e) { toast(e.message, 'warn'); }
          togBtn.disabled = false;
        });
        const runNowBtn = h('button', { class: 'lz-btn ghost sm' }, '▶ 立即运行');
        runNowBtn.addEventListener('click', async () => {
          runNowBtn.disabled = true;
          try {
            const { run_id } = await POST(`/api/triggers/${t.id}/run-now`);
            toast('已触发！'); setTimeout(() => nav(`#/run/${run_id}`), 500);
          } catch (e) { handleErr(e); runNowBtn.disabled = false; }
        });
        const delBtn = h('button', { class: 'lz-btn ghost danger sm' }, '删除');
        delBtn.addEventListener('click', async () => {
          if (!confirm('删除这个触发器？')) return;
          try { await DEL(`/api/triggers/${t.id}`); toast('已删除'); tgRow.remove(); }
          catch (e) { toast(e.message, 'warn'); }
        });
        tgRow.append(
          h('div', { class: 'lz-trg-info' },
            h('div', { class: 'lz-trg-name' }, t.name, h('span', { class: 'lz-tag tpl' }, t.team_name)),
            h('div', { class: 'lz-trg-meta' },
              fmtSched(t) +
              (t.next_run_at ? ' · 下次 ' + fmtTime(t.next_run_at) : '') +
              (t.run_count ? ` · 已跑 ${t.run_count} 次` : '')),
            h('div', { class: 'lz-trg-task' }, t.task),
            t.last_run_id ? h('a', { class: 'lz-link', onclick: () => nav(`#/run/${t.last_run_id}`) }, '查看最近一次运行') : null),
          h('div', { class: 'lz-trg-acts' }, togBtn, runNowBtn, delBtn));
        listEl.append(tgRow);
      }
    }

    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '⏰ 定时触发器'),
      h('p', { class: 'lz-intro' }, `让 AI 团队按计划自动执行任务，结果存入运行历史。最多同时启用 ${limits.max_triggers} 个。`),
      myTeams.length
        ? h('div', { class: 'lz-kb-new' },
            h('div', { class: 'lz-sec-t' }, '新建触发器'),
            h('label', { class: 'lz-form-lbl' }, '团队'), teamSel,
            h('label', { class: 'lz-form-lbl' }, '任务名（可选）'), nameIn,
            h('label', { class: 'lz-form-lbl' }, '任务内容'), taskIn,
            h('label', { class: 'lz-form-lbl' }, '执行计划'), kindRow, dailyBox, intBox,
            addBtn)
        : h('div', { class: 'lz-note' }, '💡 需要先有「我的团队」才能创建触发器。',
            h('a', { class: 'lz-link', onclick: () => nav('#/new') }, ' 去建队 →')),
      h('div', { class: 'lz-sec-t' }, `我的触发器（${items.length}）`),
      listEl));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 用量看板 ----------------
async function renderUsage() {
  mount(shell(spinner()));
  try {
    const u = await GET('/api/agents/usage');
    const fmtYuan = (micro) => micro ? `¥${(micro / 1e6).toFixed(4)}` : '¥0';
    const pctBar = (used, limit, col) => {
      const pct = Math.min(100, Math.round((used / Math.max(1, limit)) * 100));
      return h('div', { class: 'lz-bar' },
        h('div', { class: 'lz-bar-fill', style: { width: pct + '%', background: col || 'var(--acc)' } }));
    };
    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '📊 用量看板'),
      h('p', { class: 'lz-intro' }, u.byok
        ? '已接入你自己的大模型 Key 🔑 · 用自己的额度跑，会员不限量。'
        : u.member
          ? '会员账号 · 在「模型设置」填上自己的大模型 Key 即可不限量。'
          : `体验账号，每天最多运行 ${u.quota.run.limit} 次，外部 API 每天 ${u.quota.api.limit} 次。`),
      h('div', { class: 'lz-usg-grid' },
        h('div', { class: 'lz-usg-card' },
          h('div', { class: 'lz-usg-label' }, '今日运行'),
          h('div', { class: 'lz-usg-val' }, String(u.runs.today), h('span', {}, u.quota.run.limit >= 1e6 ? ' / ∞' : ` / ${u.quota.run.limit}`)),
          pctBar(u.runs.today, u.quota.run.limit, 'var(--acc)'),
          h('div', { class: 'lz-usg-sub' }, u.quota.run.limit >= 1e6 ? '自带 Key · 不限量' : `累计已用额度 ${u.quota.run.used} 次`)),
        h('div', { class: 'lz-usg-card' },
          h('div', { class: 'lz-usg-label' }, '历史总运行'),
          h('div', { class: 'lz-usg-val', style: { color: 'var(--acc2)' } }, String(u.runs.total)),
          h('div', { class: 'lz-usg-sub' }, `成功 ${u.runs.done} 次 · 失败 ${u.runs.failed} 次`)),
        h('div', { class: 'lz-usg-card' },
          h('div', { class: 'lz-usg-label' }, '今日花费'),
          h('div', { class: 'lz-usg-val', style: { color: 'var(--ok)' } }, fmtYuan(u.cost.today_micro)),
          h('div', { class: 'lz-usg-sub' }, `累计总花费 ${fmtYuan(u.cost.total_micro)}`)),
        h('div', { class: 'lz-usg-card' },
          h('div', { class: 'lz-usg-label' }, '对外 API（今日）'),
          h('div', { class: 'lz-usg-val' }, String(u.quota.api.used), h('span', {}, ` / ${u.quota.api.limit}`)),
          pctBar(u.quota.api.used, u.quota.api.limit, 'var(--acc2)'),
          h('div', { class: 'lz-usg-sub' }, '公开 API 调用次数')),
        h('div', { class: 'lz-usg-card' },
          h('div', { class: 'lz-usg-label' }, '我的资产'),
          h('div', { class: 'lz-usg-assets' },
            h('div', {}, h('div', { class: 'lz-usg-n' }, String(u.assets.teams)), h('small', {}, '团队')),
            h('div', {}, h('div', { class: 'lz-usg-n' }, String(u.assets.agents)), h('small', {}, '智能体')),
            h('div', {}, h('div', { class: 'lz-usg-n' }, String(u.assets.kbs)), h('small', {}, '知识库'))))),
      u.byok
        ? h('div', { class: 'lz-member-ok' }, '🔑 已接入你自己的大模型 Key · 任务用你自己的模型与额度跑，会员不限量。')
        : u.member
          ? h('div', { class: 'lz-upsell', onclick: () => nav('#/llm') },
              h('div', {}, h('b', {}, '🔑 填上你的大模型 Key，立即不限量'), h('small', {}, '豆包 / DeepSeek / 通义… 用自己的额度跑')),
              h('button', { class: 'lz-btn' }, '去设置 →'))
          : h('div', { class: 'lz-upsell', onclick: () => nav('#/pricing') },
              h('div', {}, h('b', {}, '👑 订阅会员 + 自带 Key 不限量'), h('small', {}, '包月解锁平台 · 模型用你自己的 Key')),
              h('button', { class: 'lz-btn' }, '查看订阅 →'))));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 会员 / 定价 ----------------
async function renderPricing() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const cat = await GET('/api/shop/catalog');
    const member = isMemberNow();
    const until = state.me?.member_until ? new Date(state.me.member_until) : null;

    async function buy(plan, btn) {
      btn.disabled = true; btn.textContent = '开通中…';
      try {
        const { order } = await POST('/api/shop/orders', { kind: 'member', item_id: plan.id });
        await POST(`/api/shop/orders/${order.id}/pay`);
        state.meta = null;
        try { state.me = await GET('/api/me'); } catch { /* ignore */ }
        await loadMeta();
        toast('开通成功，欢迎成为会员 👑');
        renderPricing();
      } catch (e) { handleErr(e); btn.disabled = false; btn.textContent = member ? '续费' : '立即开通'; }
    }
    const planCard = (p) => {
      const btn = h('button', { class: 'lz-btn block' + (p.tag ? ' xl' : '') }, member ? '续费' : '立即开通');
      btn.addEventListener('click', () => buy(p, btn));
      return h('div', { class: 'lz-plan' + (p.tag ? ' hot' : '') },
        p.tag ? h('span', { class: 'lz-plan-tag' }, p.tag) : null,
        h('div', { class: 'lz-plan-name' }, p.name.replace('句灵会员 · ', '')),
        h('div', { class: 'lz-plan-price' }, yuan(p.price_fen), h('small', {}, ` / ${p.months} 个月`)),
        h('div', { class: 'lz-plan-blurb' }, p.blurb), btn);
    };
    const cmp = (label, free, vip) => h('div', { class: 'lz-cmp-row' },
      h('span', {}, label), h('span', { class: 'lz-cmp-free' }, free), h('span', { class: 'lz-cmp-vip' }, vip));

    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '👑 订阅 · 包月解锁全力的 AI 团队'),
      member
        ? h('div', { class: 'lz-member-ok' }, `你已订阅 · 有效期至 ${until.getFullYear()}-${until.getMonth() + 1}-${until.getDate()}。`, h('a', { class: 'lz-link', onclick: () => nav('#/llm') }, '去填自己的大模型 Key，不限量跑 →'))
        : h('p', { class: 'lz-intro' }, '本产品按月订阅：包月解锁平台全部能力，模型用你自己的 Key（任意 OpenAI 兼容：豆包 / DeepSeek / 通义…），成本透明、会员不限量。当前为沙盒支付，开通即时生效。'),
      h('div', { class: 'lz-cmp' },
        h('div', { class: 'lz-cmp-head' }, h('span', {}, '能力'), h('span', {}, '免费体验'), h('span', { class: 'lz-cmp-vip' }, '包月订阅')),
        cmp('每日团队运行', '8 次', '自带 Key 不限量'),
        cmp('自带大模型 Key（BYOK）', '—', '✓ 任意 OpenAI 兼容'),
        cmp('高级模型协作 + 验收官迭代', '本地引擎', '✓ 你的模型全力跑'),
        cmp('批量 / 定时 / 知识库 / API / Webhook', '✓', '✓'),
        cmp('结果分享 / 团队记忆 / 草稿箱', '✓', '✓')),
      h('div', { class: 'lz-plans' }, cat.member_plans.map(planCard)),
      h('div', { class: 'lz-upsell', onclick: () => nav('#/llm') },
        h('div', {}, h('b', {}, '🔑 订阅后自带大模型 Key'), h('small', {}, '豆包 / DeepSeek / 通义 / OpenAI… 任选，用自己的模型与额度，不限量跑')),
        h('button', { class: 'lz-btn' }, '去设置 →')),
      h('div', { class: 'lz-sec-t' }, '开通后还一并获得'),
      h('ul', { class: 'lz-benefits' }, (cat.member_benefits || []).map((b) => h('li', {}, b))),
      h('p', { class: 'lz-hint' }, cat.fair_play || '沙盒支付环境，正式上线将接入微信支付 / 支付宝 / Apple 内购。')));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 智能体工作室（把风格/话术封装成可复用的 AI 分身） ----------------
async function renderAgents() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const { mine, templates } = await GET('/api/agents');
    const card = (a) => h('article', { class: 'lz-card', onclick: () => nav(`#/agent/${a.id}`) },
      h('div', { class: 'lz-card-h' },
        h('span', { class: 'lz-ava lg' }, a.avatar || '🤖'),
        h('div', { class: 'lz-card-ti' }, h('b', {}, a.name), h('span', { class: 'lz-strat' }, a.role || '通用智能体')),
        a.is_template ? h('span', { class: 'lz-tag tpl' }, '模板') : (a.tier === 'premium' ? h('span', { class: 'lz-tag pub' }, '高级') : null)),
      a.persona ? h('p', { class: 'lz-card-goal' }, a.persona) : null,
      (a.tools || []).length ? h('div', { class: 'lz-tools' }, a.tools.slice(0, 6).map((t) => h('span', { class: 'lz-tool' }, toolIcon(t) + ' ' + toolName(t)))) : null);
    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '🤖 智能体工作室'),
      h('p', { class: 'lz-intro' }, '把你的风格、话术、专业经验封装成一个 AI 分身——设定人设与可用工具，存为可复用的「技能包」，随时编入任意团队。'),
      h('button', { class: 'lz-btn', onclick: () => nav('#/agent/new') }, '＋ 新建智能体'),
      h('div', { class: 'lz-sec-t' }, `我的智能体（${mine.length}）`),
      mine.length ? h('div', { class: 'lz-grid' }, mine.map(card)) : empty('还没有自定义智能体', '从下方模板复制一个，或点上方新建'),
      h('div', { class: 'lz-sec-t' }, '内置模板'),
      h('div', { class: 'lz-grid' }, templates.map(card))));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

async function renderAgentEdit(id) {
  mount(shell(spinner()));
  try {
    const m = await loadMeta();
    const isNew = id === 'new';
    let a = { name: '', avatar: '🤖', role: '', persona: '', tier: 'default', tools: [], temperature: 0.7, mine: true, is_template: false };
    if (!isNew) a = (await GET(`/api/agents/${id}`)).agent;
    const readOnly = !isNew && !a.mine;

    const fName = h('input', { class: 'lz-in', value: a.name, placeholder: '智能体名（如：小红书爆款写手）', maxlength: 24 });
    const fAva = h('input', { class: 'lz-in tiny', value: a.avatar, maxlength: 8 });
    const fRole = h('input', { class: 'lz-in', value: a.role || '', placeholder: '一句话角色（如：资深种草文案）', maxlength: 60 });
    const fPersona = h('textarea', { class: 'lz-ta', rows: 6, placeholder: '人设 / 风格 / 话术：它是谁、擅长什么、用什么语气、有哪些偏好与禁忌。写得越具体，分身越像你。' });
    fPersona.value = a.persona || '';
    const fTemp = h('input', { class: 'lz-in tiny', type: 'number', min: 0, max: 1.5, step: 0.1, value: a.temperature });
    if (readOnly) for (const el of [fName, fAva, fRole, fPersona, fTemp]) el.setAttribute('disabled', '');

    let tier = a.tier === 'premium' ? 'premium' : 'default';
    const tierWrap = h('div', { class: 'lz-mode-tabs', style: { maxWidth: '320px' } });
    function drawTier() {
      tierWrap.innerHTML = '';
      for (const [k, lbl] of [['default', '标准模型'], ['premium', '高级模型']])
        tierWrap.append(h('button', { class: 'lz-mode' + (tier === k ? ' on' : ''), onclick: () => { if (readOnly) return; tier = k; drawTier(); } }, lbl));
    }
    drawTier();

    const toolSel = new Set(a.tools || []);
    const toolGrid = h('div', { class: 'lz-pick-grid' }, m.tools.map((t) => {
      const cardEl = h('button', { class: 'lz-pick' + (toolSel.has(t.id) ? ' on' : ''), onclick: () => {
        if (readOnly) return;
        if (toolSel.has(t.id)) toolSel.delete(t.id); else toolSel.add(t.id);
        cardEl.classList.toggle('on', toolSel.has(t.id));
      } }, h('span', { class: 'lz-ava' }, t.icon || '🔧'), h('div', {}, h('b', {}, t.name), h('small', {}, t.desc)));
      return cardEl;
    }));

    const actions = h('div', { class: 'lz-team-actions' });
    if (readOnly) {
      actions.append(h('button', { class: 'lz-btn xl', onclick: async () => {
        try { const { agent } = await POST(`/api/agents/${id}/clone`); toast('已复制为我的'); nav(`#/agent/${agent.id}`); }
        catch (e) { toast(e.message, 'warn'); }
      } }, '⎘ 复制为我的，再编辑'));
    } else {
      const save = h('button', { class: 'lz-btn xl' }, isNew ? '创建智能体' : '保存修改');
      save.addEventListener('click', async () => {
        const body = { name: fName.value.trim(), avatar: fAva.value.trim() || '🤖', role: fRole.value.trim(), persona: fPersona.value.trim(), tier, tools: [...toolSel], temperature: Number(fTemp.value) || 0.7 };
        if (!body.name) { toast('给智能体起个名字', 'warn'); return; }
        save.disabled = true;
        try { const { agent } = isNew ? await POST('/api/agents', body) : await PATCH(`/api/agents/${id}`, body); toast(isNew ? '已创建' : '已保存'); nav(`#/agent/${agent.id}`); }
        catch (e) { toast(e.message, 'warn'); save.disabled = false; }
      });
      actions.append(save);
      if (!isNew) actions.append(h('button', { class: 'lz-btn ghost danger', onclick: async () => {
        if (!confirm('删除这个智能体？已编入团队的引用会失效。')) return;
        try { await DEL(`/api/agents/${id}`); toast('已删除'); nav('#/agents'); } catch (e) { toast(e.message, 'warn'); }
      } }, '🗑 删除'));
    }

    mount(shell(
      h('button', { class: 'lz-back', onclick: () => nav('#/agents') }, '‹ 智能体'),
      h('div', { class: 'lz-sec-t big' }, isNew ? '新建智能体' : (readOnly ? '智能体（内置模板 · 只读）' : '编辑智能体')),
      readOnly ? h('div', { class: 'lz-note' }, '内置模板不可直接修改，「复制为我的」后即可自由编辑人设与工具。') : null,
      h('div', { class: 'lz-form' },
        h('label', {}, '名称 / 头像'),
        h('div', { class: 'lz-row' }, fName, fAva),
        h('label', {}, '角色'), fRole,
        h('label', {}, '人设 / 风格 / 话术'), fPersona,
        h('label', {}, '模型档位'), tierWrap,
        h('label', {}, ['可用工具（已选 ', String(toolSel.size), '）']), toolGrid,
        h('label', {}, '发挥度 temperature（0 严谨 ~ 1.5 发散）'), fTemp,
        actions)));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 个人中心 ----------------
async function renderMe() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    state.me = await GET('/api/me');
    const me = state.me, member = isMemberNow(), isGuest = me.is_guest;
    const until = me.member_until ? new Date(me.member_until) : null;

    const nickIn = h('input', { class: 'lz-in', value: me.nickname || '', maxlength: 12, placeholder: '昵称（2-12 字）' });
    const saveNick = h('button', { class: 'lz-btn sm' }, '保存');
    saveNick.addEventListener('click', async () => {
      saveNick.disabled = true;
      try { state.me = await PATCH('/api/me', { nickname: nickIn.value.trim() }); toast('已保存'); renderMe(); }
      catch (e) { toast(e.message, 'warn'); saveNick.disabled = false; }
    });

    let bindBox = null;
    if (isGuest) {
      const uIn = h('input', { class: 'lz-in', placeholder: '用户名（3-20 位字母/数字/下划线）', autocomplete: 'username' });
      const pIn = h('input', { class: 'lz-in', type: 'password', placeholder: '设置密码（至少 6 位）', autocomplete: 'new-password' });
      const bindBtn = h('button', { class: 'lz-btn xl' }, '绑定，保住我的团队与会员');
      bindBtn.addEventListener('click', async () => {
        bindBtn.disabled = true;
        try { state.me = await POST('/api/me/bind', { username: uIn.value.trim(), password: pIn.value }); toast('已升级为正式账号 🎉'); renderMe(); }
        catch (e) { toast(e.message, 'warn'); bindBtn.disabled = false; }
      });
      bindBox = h('div', { class: 'lz-kb-new' },
        h('div', { class: 'lz-sec-t' }, '🔐 绑定正式账号'),
        h('p', { class: 'lz-api-desc' }, '你现在是游客账号，只靠这台设备保存。设置用户名密码后即可换设备登录，团队 / 运行记录 / 会员都不会丢。'),
        h('div', { class: 'lz-form-col' }, uIn, pIn), bindBtn);
    }

    mount(shell(
      h('div', { class: 'lz-sec-t big' }, '👤 个人中心'),
      h('section', { class: 'lz-team-hero' },
        h('span', { class: 'lz-ava xl' }, '👤'),
        h('div', { class: 'lz-team-meta' },
          h('h1', {}, me.nickname || '我'),
          h('div', { class: 'lz-me-tags' },
            isGuest ? h('span', { class: 'lz-tag' }, '游客账号') : h('span', { class: 'lz-tag pub' }, '正式账号 · @' + me.username),
            member ? h('span', { class: 'lz-tag vip' }, '👑 会员') : h('span', { class: 'lz-tag' }, '免费版')))),
      member
        ? h('div', { class: 'lz-member-ok' }, `👑 会员有效期至 ${until.getFullYear()}-${until.getMonth() + 1}-${until.getDate()} · `, h('a', { class: 'lz-link', onclick: () => nav('#/pricing') }, '续费'))
        : h('div', { class: 'lz-upsell', onclick: () => nav('#/pricing') },
            h('div', {}, h('b', {}, '👑 订阅会员，自带 Key 不限量跑'), h('small', {}, '包月解锁平台，模型用你自己的 Key')),
            h('button', { class: 'lz-btn' }, '查看订阅 →')),
      h('div', { class: 'lz-upsell', onclick: () => nav('#/llm') },
        h('div', {}, h('b', {}, state.meta?.byok ? '🔑 已接入你的大模型 Key' : '🔑 模型设置 · 自带大模型 Key'),
          h('small', {}, state.meta?.byok ? '任务正用你自己的模型跑 · 会员不限量' : '填自己的 Key（豆包/DeepSeek/通义…），用自己的模型与额度')),
        h('button', { class: 'lz-btn' }, state.meta?.byok ? '管理 →' : '去设置 →')),
      h('div', { class: 'lz-kb-new' }, h('div', { class: 'lz-sec-t' }, '昵称'), h('div', { class: 'lz-row' }, nickIn, saveNick)),
      bindBox,
      h('div', { class: 'lz-me-actions' }, h('button', { class: 'lz-btn ghost', onclick: logout }, '退出登录'))));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 模型设置（自带大模型 Key · BYOK） ----------------
async function renderLLM() {
  mount(shell(spinner()));
  try {
    await loadMeta();
    const { providers, config } = await GET('/api/me/llm');
    let pid = config?.provider || 'doubao';
    const prov = (id) => providers.find((p) => p.id === id) || providers[0];

    const baseIn = h('input', { class: 'lz-in', placeholder: '接口地址 base_url（OpenAI 兼容 /chat/completions 的前缀）' });
    const keyIn = h('input', { class: 'lz-in', type: 'password', placeholder: config ? '如不修改可留空（沿用已保存的 Key）' : '你的 API Key（只存服务端，绝不下发前端）', autocomplete: 'off' });
    const defIn = h('input', { class: 'lz-in', placeholder: '默认模型名（高频调用，选便宜的）' });
    const premIn = h('input', { class: 'lz-in', placeholder: '高级模型名（整合/验收等质量关键步骤）' });
    const hint = h('p', { class: 'lz-hint' });

    function fillProvider(p) {
      baseIn.value = p.base_url || '';
      defIn.value = p.models.default || '';
      premIn.value = p.models.premium || '';
      hint.innerHTML = '';
      hint.append('💡 ' + p.recommend + ' · ' + p.key_hint + ' ');
      if (p.apply) hint.append(h('a', { class: 'lz-link', href: p.apply, target: '_blank', rel: 'noopener' }, '去申请 Key →'));
    }
    const picker = h('div', { class: 'lz-prov-grid' }, providers.map((p) =>
      h('button', { class: 'lz-prov' + (pid === p.id ? ' on' : ''), 'data-id': p.id, onclick: () => {
        pid = p.id; for (const b of picker.children) b.classList.toggle('on', b.dataset.id === p.id); fillProvider(p);
      } }, h('span', { class: 'lz-prov-emoji' }, p.emoji), h('div', {}, h('b', {}, p.name), h('small', {}, p.vendor)))));

    fillProvider(prov(pid));
    if (config) { baseIn.value = config.base_url; defIn.value = config.model_default; premIn.value = config.model_premium; }  // 已配置则回填实际值

    const testBtn = h('button', { class: 'lz-btn ghost' }, '测试连通');
    const saveBtn = h('button', { class: 'lz-btn xl' }, config ? '更新配置' : '保存并启用');
    async function doSave(silent) {
      const body = { provider: pid, base_url: baseIn.value.trim(), model_default: defIn.value.trim(), model_premium: premIn.value.trim() };
      if (keyIn.value.trim()) body.api_key = keyIn.value.trim();
      await PUT('/api/me/llm', body);
      state.meta = null; await loadMeta();
      if (!silent) { toast('已保存，之后的任务将用你自己的模型 🔑'); renderLLM(); }
    }
    saveBtn.addEventListener('click', async () => {
      if (!baseIn.value.trim() || !defIn.value.trim()) { toast('填好接口地址与默认模型名', 'warn'); return; }
      if (!config && !keyIn.value.trim()) { toast('填入你的 API Key', 'warn'); return; }
      saveBtn.disabled = true;
      try { await doSave(false); } catch (e) { toast(e.message, 'warn'); saveBtn.disabled = false; }
    });
    testBtn.addEventListener('click', async () => {
      testBtn.disabled = true; testBtn.textContent = '测试中…';
      try {
        if (baseIn.value.trim() && (keyIn.value.trim() || config)) await doSave(true);  // 先存再测
        const r = await POST('/api/me/llm/test');
        toast('✓ 连通成功：' + (r.model || '') + ' 回复「' + (r.sample || '') + '」');
      } catch (e) { toast(e.message, 'warn'); }
      testBtn.disabled = false; testBtn.textContent = '测试连通';
    });
    const clearBtn = config ? h('button', { class: 'lz-btn ghost danger sm', onclick: async () => {
      if (!confirm('清除你的模型 Key？之后任务将回落到本地引擎。')) return;
      try { await DEL('/api/me/llm'); state.meta = null; await loadMeta(); toast('已清除'); renderLLM(); } catch (e) { toast(e.message, 'warn'); }
    } }, '清除配置') : null;

    mount(shell(
      h('button', { class: 'lz-back', onclick: () => nav('#/me') }, '‹ 个人中心'),
      h('div', { class: 'lz-sec-t big' }, '🔑 模型设置 · 自带大模型 Key'),
      config
        ? h('div', { class: 'lz-member-ok' }, `已接入：${prov(config.provider).name} · ${config.model_default}。你的任务正用自己的模型跑，会员可不限量。`)
        : h('p', { class: 'lz-intro' }, '订阅后自带任意大模型 Key（OpenAI 兼容即可），任务就用你自己的模型与额度跑——成本透明、会员不限量。Key 只存服务端、绝不下发前端。'),
      h('div', { class: 'lz-sec-t' }, '① 选择模型提供方'),
      picker,
      h('div', { class: 'lz-form' },
        h('div', { class: 'lz-sec-t' }, '② 填写你的配置'),
        h('label', {}, '接口地址 base_url'), baseIn,
        h('label', {}, 'API Key'), keyIn,
        h('label', {}, '默认模型 / 高级模型'),
        h('div', { class: 'lz-row' }, defIn, premIn),
        hint,
        h('div', { class: 'lz-row' }, testBtn, saveBtn),
        clearBtn)));
  } catch (e) { mount(shell(empty('加载失败', e.message))); }
}

// ---------------- 路由 ----------------
const TITLES = { '': '团队广场', agents: '智能体工作室', agent: '智能体', kb: '知识库', triggers: '定时触发器', history: '运行记录', usage: '用量看板', pricing: '会员', me: '个人中心', llm: '模型设置', new: '组建团队', edit: '编辑团队', team: '团队', run: '作战室', batch: '批量运行' };
function route() {
  const hash = location.hash || '#/';
  if (hash.startsWith('#/s/')) return renderShare(hash.slice(4));   // 公开分享：免登录
  if (!state.me) { renderLogin(); return; }
  const [path, p1] = hash.replace(/^#\//, '').split('/');
  document.title = '灵阵 · ' + (TITLES[path] ?? 'AI 团队');
  if (path === 'agents') return renderAgents();
  if (path === 'agent' && p1) return renderAgentEdit(p1);
  if (path === 'team' && p1) return renderTeam(p1);
  if (path === 'run' && p1) return renderRun(p1);
  if (path === 'batch' && p1) return renderBatch(p1);
  if (path === 'history') return renderHistory();
  if (path === 'new') return renderBuilder(null);
  if (path === 'edit' && p1) return renderBuilder(p1);
  if (path === 'kb' && p1) return renderKBDetail(p1);
  if (path === 'kb') return renderKB();
  if (path === 'triggers') return renderTriggers();
  if (path === 'usage') return renderUsage();
  if (path === 'pricing') return renderPricing();
  if (path === 'me') return renderMe();
  if (path === 'llm') return renderLLM();
  return renderHome();
}

async function boot() {
  if (getToken()) { try { state.me = await GET('/api/me'); } catch { setToken(''); } }
  window.addEventListener('hashchange', route);
  route();
}
boot();
