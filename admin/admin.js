// 句灵管理后台：登录 + 9 个管理模块（纯原生，无依赖）
const $ = (s) => document.querySelector(s);
let token = sessionStorage.getItem('jl_admin_token') || '';

function toast(msg) {
  const d = document.createElement('div');
  d.textContent = msg;
  $('#toast').append(d);
  setTimeout(() => d.remove(), 2600);
}

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined
  });
  const json = await res.json().catch(() => ({}));
  if (!json.ok) throw new Error(json.error || '请求失败');
  return json.data;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children.flat(9)) if (c != null) e.append(c.nodeType ? c : String(c));
  return e;
}
const fmtTime = (ts) => ts ? new Date(ts).toLocaleString('zh-CN', { hour12: false }) : '-';

function table(headers, rows) {
  return el('table', {},
    el('thead', {}, el('tr', {}, headers.map((x) => el('th', {}, x)))),
    el('tbody', {}, rows.length ? rows.map((r) => el('tr', {}, r.map((c) => el('td', {}, c)))) : el('tr', {}, el('td', { colspan: String(headers.length), class: 'muted' }, '暂无数据')))
  );
}

// ---- 登录 ----
function renderLogin() {
  const root = $('#root');
  root.innerHTML = '';
  const u = el('input', { placeholder: '管理员用户名', value: 'admin' });
  const p = el('input', { placeholder: '密码', type: 'password' });
  const box = el('div', { class: 'login-box' },
    el('h1', {}, '🔧 句灵管理后台'),
    u, p,
    el('button', {
      class: 'btn', onclick: async () => {
        try {
          const data = await api('POST', '/api/auth/login', { username: u.value.trim(), password: p.value });
          if (data.user.role !== 'admin') { toast('该账号不是管理员'); return; }
          token = data.token;
          sessionStorage.setItem('jl_admin_token', token);
          renderApp();
        } catch (e) { toast(e.message); }
      }
    }, '登录'),
    el('p', { class: 'muted', style: 'margin-top:12px;text-align:center' }, '默认账号见 .env.example / 启动日志')
  );
  p.addEventListener('keydown', (e) => { if (e.key === 'Enter') box.querySelector('.btn').click(); });
  root.append(box);
}

// ---- 主框架 ----
const MODULES = {
  dashboard: ['📊 数据总览', renderDashboard],
  review: ['🛡 审核队列', renderReview],
  reports: ['🚨 举报处理', renderReports],
  posts: ['📝 内容管理', renderPosts],
  users: ['👥 用户管理', renderUsers],
  warmup: ['🤖 AI 暖场', renderWarmup],
  cost: ['💰 AI 成本', renderCost],
  agents: ['🛰 灵阵团队', renderAgentsAdmin],
  rooms: ['🎲 桌游房间', renderRooms],
  shop: ['🛍 皮肤与订单', renderShopOrders],
  words: ['🔞 敏感词', renderWords],
  logs: ['📜 审核日志', renderLogs]
};
let current = 'dashboard';
let main;

function renderApp() {
  const root = $('#root');
  root.innerHTML = '';
  const menu = el('div', { class: 'menu' });
  main = el('main', {});
  for (const [key, [name]] of Object.entries(MODULES)) {
    menu.append(el('button', {
      class: key === current ? 'on' : '',
      onclick: (e) => {
        current = key;
        menu.querySelectorAll('button').forEach((b) => b.classList.remove('on'));
        e.target.classList.add('on');
        load();
      }
    }, name));
  }
  menu.append(el('button', { style: 'margin-top:20px', onclick: () => { token = ''; sessionStorage.clear(); renderLogin(); } }, '↩ 退出登录'));
  root.append(el('div', { class: 'layout' }, el('aside', {}, el('h1', {}, '句灵后台'), menu), main));
  load();
}

async function load() {
  main.innerHTML = '<p class="muted">加载中…</p>';
  try { await MODULES[current][1](); }
  catch (e) { main.innerHTML = ''; main.append(el('p', { class: 'muted' }, '加载失败：' + e.message)); }
}

// ---- 模块们 ----
async function renderDashboard() {
  const s = await api('GET', '/api/admin/stats');
  main.innerHTML = '';
  const stat = (k, v, extra = '') => el('div', { class: 'stat' }, el('div', { class: 'k' }, k), el('div', { class: 'v' }, String(v)), extra ? el('div', { class: 'muted' }, extra) : null);
  main.append(
    el('h2', {}, '📊 数据总览'),
    el('div', { class: 'cards' },
      stat('注册用户', s.users.total, `今日新增 ${s.users.today_new} · 今日活跃 ${s.users.today_active}`),
      stat('会员数', s.users.members, `封禁中 ${s.users.banned}`),
      stat('文案总数', s.content.posts, `今日新增 ${s.content.today_posts}`),
      stat('待审内容', s.content.pending, `未处理举报 ${s.content.open_reports}`),
      stat('累计流水', '¥' + s.revenue.total_yuan, `今日 ¥${s.revenue.today_yuan} · ${s.revenue.paid_orders} 单`),
      stat('AI 成本（今日）', '¥' + s.ai.today_cost_yuan, `累计 ¥${s.ai.total_cost_yuan}`),
      stat('AI 调用（今日）', s.ai.today_calls, `兜底 ${s.ai.today_fallbacks} 次 · ${s.ai.llm_enabled ? '已接大模型' : '本地规则模式'}`),
      stat('AI 暖场', s.warmup.enabled ? '开启' : '已关闭', `今日动作 ${s.warmup.today_actions} 次`),
      stat('桌游对局', s.games.total, `今日 ${s.games.today} 局`)
    ),
    el('p', { class: 'muted' }, '提示：大模型未配置时所有 AI 功能自动走本地规则引擎，成本为 0。配置见 .env.example。')
  );
  try {
    const sys = await api('GET', '/api/admin/settings');
    main.append(el('div', { class: 'row', style: 'margin-top:14px' },
      el('span', {}, 'AI 大模型机审（敏感词之上的第二道防线，需配置大模型）：'),
      el('button', {
        class: 'btn ' + (sys.ai_moderation ? 'warn' : 'ok'),
        onclick: async () => {
          await api('PUT', '/api/admin/settings', { ai_moderation: !sys.ai_moderation });
          toast(sys.ai_moderation ? '已关闭 AI 机审' : '已开启 AI 机审'); load();
        }
      }, sys.ai_moderation ? '关闭机审' : '开启机审'),
      el('span', { class: 'tag ' + (sys.ai_moderation ? 'green' : 'gray') }, sys.ai_moderation ? '运行中' : '未开启')
    ));
  } catch { /* 旧版后端无此接口 */ }
}

async function renderAgentsAdmin() {
  const d = await api('GET', '/api/admin/agents/overview');
  main.innerHTML = '';
  const yuan = (micro) => '¥' + (micro / 1e6).toFixed(4);
  const stat = (k, v, extra = '') => el('div', { class: 'stat' }, el('div', { class: 'k' }, k), el('div', { class: 'v' }, String(v)), extra ? el('div', { class: 'muted' }, extra) : null);
  main.append(
    el('h2', {}, '🛰 灵阵 · AI 团队'),
    el('div', { class: 'cards' },
      stat('累计运行', d.runs.total, `今日 ${d.runs.today} 次`),
      stat('进行中', d.runs.running, `失败 ${d.runs.failed}`),
      stat('已完成', d.runs.done, `大模型参与 ${d.runs.by_llm}`),
      stat('今日成本', yuan(d.cost_today_micro), `预算 ${d.budget_micro ? yuan(d.budget_micro) : '不限'}`),
      stat('用户团队', d.totals.teams, `已发布 ${d.totals.published} · 开 API ${d.totals.api_teams}`),
      stat('用户智能体', d.totals.agents, `知识库 ${d.totals.kbs} · 草稿 ${d.totals.drafts}`),
      stat('定时任务', d.totals.triggers_enabled, `共 ${d.totals.triggers} 个`)
    )
  );
  const budgetInput = el('input', { type: 'number', value: String((d.budget_micro / 1e6) || 0), step: '0.5', style: 'width:110px' });
  main.append(el('div', { class: 'row', style: 'margin-top:14px' },
    el('span', {}, '每日成本预算封顶（元，0=不限；超额后强制走本地引擎，不超支）：'),
    budgetInput,
    el('button', {
      class: 'btn ok', onclick: async () => {
        await api('PUT', '/api/admin/agents/config', { budget_micro: Math.round(Number(budgetInput.value || 0) * 1e6) });
        toast('已更新预算'); load();
      }
    }, '保存'),
    el('span', { class: 'tag green' }, `运行配额：免费 ${d.quota.free} / 会员 ${d.quota.member} 次每日`)
  ));
  main.append(
    el('h2', { style: 'margin-top:22px' }, '最近运行'),
    table(['#', '用户', '团队', '策略', '来源', '状态', '步数', 'tokens', '成本', '时间', '操作'], d.recent.map((r) => [
      String(r.id), r.owner_name || '-', r.team_name, r.strategy,
      el('span', { class: 'tag ' + (r.source === 'trigger' ? 'green' : 'gray') }, r.source === 'trigger' ? '定时' : '手动'),
      el('span', { class: 'tag ' + (r.status === 'done' ? 'green' : r.status === 'failed' ? 'red' : r.status === 'running' ? '' : 'gray') }, r.status),
      String(r.step_count), String(r.token_total), yuan(r.cost_micro), fmtTime(r.started_at),
      r.status === 'running'
        ? el('button', { class: 'btn warn', onclick: async () => { if (!confirm('强制停止该运行？')) return; await api('POST', `/api/admin/agents/runs/${r.id}/stop`); toast('已请求停止'); load(); } }, '停止')
        : ''
    ]))
  );
}

async function renderRooms() {
  const data = await api('GET', '/api/admin/rooms');
  main.innerHTML = '';
  main.append(
    el('h2', {}, '🎲 进行中的房间'),
    table(['房间号', '名称', '玩法', '状态', '人数(真人)', '轮次', '创建时间', '操作'], data.live.map((r) => [
      r.id, r.name, r.game_type === 'werewolf' ? '狼人杀' : '谁是卧底',
      el('span', { class: 'tag ' + (r.status === 'playing' ? 'green' : '') }, r.status === 'playing' ? `游戏中·${r.phase}` : '等待中'),
      `${r.players}(${r.humans})`, String(r.round), fmtTime(r.created_at),
      el('button', { class: 'btn warn', onclick: async () => {
        if (!confirm('确定关闭这个房间？玩家将被请出。')) return;
        await api('POST', `/api/admin/rooms/${r.id}/close`); toast('已关闭'); load();
      } }, '关闭')
    ])),
    el('h2', { style: 'margin-top:22px' }, '最近结束的对局'),
    table(['房间号', '名称', '玩法', '轮次', '胜方', '时间'], data.ended.map((r) => [
      r.id, r.name, r.game_type === 'werewolf' ? '狼人杀' : '谁是卧底', String(r.round), r.winner || '-', fmtTime(r.created_at)
    ]))
  );
}

async function renderReview() {
  const { items } = await api('GET', '/api/admin/posts?status=pending');
  main.innerHTML = '';
  main.append(el('h2', {}, '🛡 人工审核队列（含自伤关怀内容）'),
    table(['ID', '作者', '内容', '时间', '操作'], items.map((p) => [
      String(p.id), p.author?.nickname || '-', p.content, fmtTime(p.created_at),
      el('span', {},
        el('button', { class: 'btn ok', onclick: () => act(p.id, 'approve') }, '通过'),
        el('button', { class: 'btn warn', onclick: () => act(p.id, 'reject') }, '不通过'))
    ])));
  async function act(id, action) {
    await api('POST', `/api/admin/posts/${id}/action`, { action });
    toast('已处理'); load();
  }
}

async function renderReports() {
  const { items } = await api('GET', '/api/admin/reports?status=open');
  main.innerHTML = '';
  main.append(el('h2', {}, '🚨 待处理举报'),
    table(['ID', '类型', '原因', '被举报内容', '时间', '操作'], items.map((r) => [
      String(r.id),
      el('span', { class: 'tag' }, { post: '帖子', comment: '评论', user: '用户', room_message: '房间消息' }[r.target_type] || r.target_type),
      `${r.reason}${r.detail ? '：' + r.detail : ''}`,
      r.snapshot ? `「${r.snapshot.content}」` : el('span', { class: 'muted' }, '内容已不存在'),
      fmtTime(r.created_at),
      el('span', {},
        el('button', { class: 'btn warn', onclick: () => handle(r.id, 'resolve') }, '违规处理'),
        el('button', { class: 'btn ghost', onclick: () => handle(r.id, 'dismiss') }, '无违规'))
    ])));
  async function handle(id, action) {
    await api('POST', `/api/admin/reports/${id}/handle`, { action });
    toast('已处理'); load();
  }
}

async function renderPosts() {
  main.innerHTML = '';
  const sel = el('select', {},
    ['all|全部', 'active|展示中', 'pending|待审', 'removed|已下架', 'rejected|未过审'].map((o) => {
      const [v, n] = o.split('|');
      return el('option', { value: v }, n);
    }));
  const box = el('div', {});
  main.append(el('h2', {}, '📝 内容管理'), el('div', { class: 'row' }, sel), box);
  sel.addEventListener('change', draw);
  async function draw() {
    const { items } = await api('GET', `/api/admin/posts?status=${sel.value}`);
    box.innerHTML = '';
    box.append(table(['ID', '作者', '内容', '状态', '互动', '操作'], items.map((p) => [
      String(p.id),
      el('span', {}, p.author?.nickname || '-', p.is_ai ? el('span', { class: 'tag' }, 'AI') : ''),
      p.content,
      el('span', { class: `tag ${p.status === 'active' ? 'green' : p.status === 'pending' ? '' : 'red'}` }, p.status),
      `❤${p.like_count} 💬${p.comment_count} ▶${p.play_count}`,
      el('span', {},
        p.status === 'active'
          ? el('button', { class: 'btn warn', onclick: () => act(p.id, 'remove') }, '下架')
          : el('button', { class: 'btn ok', onclick: () => act(p.id, 'restore') }, '恢复'))
    ])));
  }
  async function act(id, action) {
    await api('POST', `/api/admin/posts/${id}/action`, { action, reason: '管理员操作' });
    toast('已处理'); draw();
  }
  draw();
}

async function renderUsers() {
  main.innerHTML = '';
  const q = el('input', { placeholder: '搜昵称 / 用户名 / ID' });
  const box = el('div', {});
  main.append(el('h2', {}, '👥 用户管理'),
    el('div', { class: 'row' }, q, el('button', { class: 'btn', onclick: draw }, '搜索')), box);
  async function draw() {
    const { items } = await api('GET', `/api/admin/users?q=${encodeURIComponent(q.value || '')}`);
    box.innerHTML = '';
    box.append(table(['ID', '昵称', '账号', '身份', '状态', '会员/额度', '操作'], items.map((u) => [
      String(u.id),
      el('span', {}, u.nickname, u.is_ai ? el('span', { class: 'tag' }, 'AI 暖场官') : ''),
      u.username || '(游客)',
      u.role === 'admin' ? el('span', { class: 'tag' }, '管理员') : '用户',
      u.status === 'banned'
        ? el('span', { class: 'tag red' }, `封禁至 ${fmtTime(u.banned_until)}`)
        : el('span', { class: `tag ${u.status === 'active' ? 'green' : 'gray'}` }, u.status),
      `${u.member_until > Date.now() ? '会员' : '-'} / ✦${u.credits}`,
      u.role === 'admin' || u.is_ai ? '' : (u.status === 'banned'
        ? el('button', { class: 'btn ok', onclick: async () => { await api('POST', `/api/admin/users/${u.id}/unban`); toast('已解封'); draw(); } }, '解封')
        : el('button', { class: 'btn warn', onclick: async () => {
            const days = prompt('封禁天数？', '7');
            if (!days) return;
            const reason = prompt('封禁原因？', '违反社区规范') || '违反社区规范';
            await api('POST', `/api/admin/users/${u.id}/ban`, { days: Number(days), reason });
            toast('已封禁'); draw();
          } }, '封禁'))
    ])));
  }
  draw();
}

async function renderWarmup() {
  const data = await api('GET', '/api/admin/warmup');
  const c = data.config;
  main.innerHTML = '';
  const fields = [
    ['posts_per_day', '每日发帖条数 (0-30)'], ['max_comments_per_post', '每帖最多 AI 评论 (0-2)'],
    ['comment_delay_min_s', '评论最小延迟(秒)'], ['comment_delay_max_s', '评论最大延迟(秒)'],
    ['like_probability', '点赞概率 (0-1)'], ['lobby_min_m', '大厅提醒最小间隔(分)'],
    ['lobby_max_m', '大厅提醒最大间隔(分)'], ['quiet_start', '夜间降频开始(时)'],
    ['quiet_end', '夜间降频结束(时)'], ['quiet_factor', '夜间频率系数 (0-1)']
  ];
  const inputs = {};
  const grid = el('div', { class: 'field-grid' },
    fields.map(([key, label]) => el('div', {}, el('label', {}, label), inputs[key] = el('input', { value: String(c[key]) }))));
  main.append(
    el('h2', {}, '🤖 AI 暖场配置'),
    el('div', { class: 'row' },
      el('button', { class: `btn ${c.enabled ? 'warn' : 'ok'}`, onclick: async () => {
        await api('PUT', '/api/admin/warmup', { enabled: !c.enabled });
        toast(c.enabled ? '已一键关闭全部 AI 暖场' : '已开启 AI 暖场'); load();
      } }, c.enabled ? '⏸ 一键关闭全部暖场' : '▶ 开启暖场'),
      el('button', { class: 'btn ghost', onclick: async () => { const r = await api('POST', '/api/admin/warmup/trigger', {}); toast(r.message || '已触发'); load(); } }, '手动发一条暖场'),
      el('button', { class: 'btn ghost', onclick: async () => { const r = await api('POST', '/api/admin/warmup/trigger', { action: 'topic' }); toast('今日话题：' + r.topic.title); } }, '重新生成今日话题'),
      el('span', { class: 'tag ' + (c.enabled ? 'green' : 'red') }, c.enabled ? '运行中' : '已关闭')
    ),
    grid,
    el('button', { class: 'btn', onclick: async () => {
      const patch = {};
      for (const [k] of fields) patch[k] = Number(inputs[k].value);
      await api('PUT', '/api/admin/warmup', patch);
      toast('配置已保存');
    } }, '保存配置'),
    el('h2', { style: 'margin-top:22px' }, 'AI 账号'),
    table(['人设键', '昵称', '账号', '人设'], data.accounts.map((a) => [a.key, a.nickname, a.username, a.persona])),
    el('h2', { style: 'margin-top:22px' }, '最近暖场动作'),
    table(['时间', '账号', '动作', '内容'], data.recent.map((r) => [
      fmtTime(r.created_at), r.nickname || r.account_id,
      el('span', { class: 'tag' }, r.action), r.content || `→ ${r.target_id}`
    ]))
  );
}

async function renderCost() {
  const data = await api('GET', '/api/admin/ai-usage?days=7');
  main.innerHTML = '';
  main.append(
    el('h2', {}, `💰 AI 成本统计（${data.llm_enabled ? '大模型已接入' : '本地规则模式，成本为 0'}）`),
    el('h2', { style: 'font-size:14px' }, '近 7 天'),
    table(['日期', '调用次数', '兜底次数', 'Prompt Tokens', 'Completion Tokens', '成本(元)'],
      data.daily.map((d) => [d.day, String(d.calls), String(d.fallbacks), String(d.prompt_tokens), String(d.completion_tokens), d.cost_yuan])),
    el('h2', { style: 'font-size:14px;margin-top:18px' }, '按功能分布'),
    table(['功能', '次数', '成本(元)'], data.by_feature.map((f) => [f.feature, String(f.calls), f.cost_yuan])),
    el('h2', { style: 'font-size:14px;margin-top:18px' }, '最近调用'),
    table(['时间', '功能', '提供方', '模型', 'tokens', '状态'], data.recent.map((r) => [
      fmtTime(r.created_at), r.feature, r.provider, r.model,
      `${r.prompt_tokens}+${r.completion_tokens}`,
      r.ok ? (r.fallback ? el('span', { class: 'tag' }, '本地兜底') : el('span', { class: 'tag green' }, '成功')) : el('span', { class: 'tag red' }, '失败')
    ]))
  );
}

async function renderShopOrders() {
  const [skins, orders] = await Promise.all([api('GET', '/api/admin/skins'), api('GET', '/api/admin/orders')]);
  main.innerHTML = '';
  main.append(
    el('h2', {}, '🛍 皮肤商品（仅外观，可调价/上下架）'),
    table(['ID', '名称', '类型', '稀有度', '价格(分)', '状态', '操作'], skins.items.map((s) => {
      const price = el('input', { value: String(s.price_fen), style: 'width:80px' });
      return [s.id, s.name, s.type, el('span', { class: 'tag' }, s.rarity), price,
        el('span', { class: `tag ${s.enabled ? 'green' : 'gray'}` }, s.enabled ? '上架' : '下架'),
        el('span', {},
          el('button', { class: 'btn ghost', onclick: async () => { await api('POST', `/api/admin/skins/${s.id}/update`, { price_fen: Number(price.value) }); toast('价格已更新'); } }, '改价'),
          el('button', { class: `btn ${s.enabled ? 'warn' : 'ok'}`, onclick: async () => { await api('POST', `/api/admin/skins/${s.id}/update`, { enabled: !s.enabled }); toast('已更新'); load(); } }, s.enabled ? '下架' : '上架'))];
    })),
    el('h2', { style: 'margin-top:22px' }, '🧾 订单'),
    table(['订单号', '用户', '商品', '金额', '状态', '渠道', '时间'], orders.items.map((o) => [
      o.id, o.nickname, o.title, `¥${(o.amount_fen / 100).toFixed(2)}`,
      el('span', { class: `tag ${o.status === 'paid' ? 'green' : 'gray'}` }, o.status), o.channel, fmtTime(o.created_at)
    ]))
  );
}

async function renderWords() {
  const { items } = await api('GET', '/api/admin/sensitive-words');
  main.innerHTML = '';
  const w = el('input', { placeholder: '新敏感词' });
  const cat = el('select', {},
    el('option', { value: 'block' }, 'block 直接拦截'),
    el('option', { value: 'review' }, 'review 转人工'),
    el('option', { value: 'selfharm' }, 'selfharm 关怀+人工'));
  main.append(
    el('h2', {}, '🔞 敏感词库'),
    el('div', { class: 'row' }, w, cat,
      el('button', { class: 'btn', onclick: async () => {
        if (!w.value.trim()) return;
        await api('POST', '/api/admin/sensitive-words', { word: w.value.trim(), category: cat.value });
        toast('已添加，30 秒内生效'); load();
      } }, '添加')),
    table(['词', '级别', '操作'], items.map((it) => [
      it.word,
      el('span', { class: `tag ${it.category === 'block' ? 'red' : it.category === 'selfharm' ? '' : 'gray'}` }, it.category),
      el('button', { class: 'btn ghost', onclick: async () => { await api('POST', '/api/admin/sensitive-words/delete', { word: it.word }); toast('已删除'); load(); } }, '删除')
    ]))
  );
}

async function renderLogs() {
  const { items } = await api('GET', '/api/admin/moderation-logs');
  main.innerHTML = '';
  main.append(el('h2', {}, '📜 审核与操作日志'),
    table(['时间', '操作者', '动作', '对象', '详情'], items.map((l) => [
      fmtTime(l.created_at), l.actor, el('span', { class: 'tag' }, l.action),
      `${l.target_type || ''} #${l.target_id || ''}`, l.detail || ''
    ])));
}

// ---- 启动 ----
if (token) {
  api('GET', '/api/me').then((me) => me.role === 'admin' ? renderApp() : renderLogin()).catch(renderLogin);
} else renderLogin();
