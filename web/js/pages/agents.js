// 灵阵 · AI 团队：首页控制台 / 团队工作台 / 作战室实时直播
import { GET, POST, PATCH, DEL, sse } from '../api.js';
import { h, toast, sheet, confirmSheet, emptyState, spinner, timeAgo } from '../ui.js';
import { nav } from '../router.js';

let META = null;
async function meta() { if (!META) META = await GET('/api/agents/meta'); return META; }
const STRAT_ICON = { orchestrate: '🛰', sequential: '⛓', route: '🔀', debate: '⚖️' };
const stratName = (id) => (META?.strategies?.find((s) => s.id === id)?.name) || id;
const STATUS = {
  running: ['进行中', 'st-run'], done: ['已完成', 'st-done'],
  failed: ['失败', 'st-fail'], stopped: ['已停止', 'st-stop']
};

// 极简 Markdown → DOM（标题/加粗/引用/列表/段落），不走 innerHTML，避免注入
function mdNodes(text) {
  const out = [];
  const lines = String(text || '').split('\n');
  let list = null;
  const flush = () => { if (list) { out.push(list); list = null; } };
  const inline = (s) => {
    const frag = document.createDocumentFragment();
    for (const part of String(s).split(/(\*\*[^*]+\*\*)/g)) {
      if (!part) continue;
      if (/^\*\*[^*]+\*\*$/.test(part)) frag.append(h('strong', {}, part.slice(2, -2)));
      else frag.append(document.createTextNode(part));
    }
    return frag;
  };
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    if (!line.trim()) { flush(); continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) { flush(); out.push(h('h' + Math.min(4, m[1].length + 1), { class: 'md-h' }, inline(m[2]))); }
    else if ((m = line.match(/^>\s?(.*)/))) { flush(); out.push(h('blockquote', { class: 'md-q' }, inline(m[1]))); }
    else if ((m = line.match(/^[-*]\s+(.*)/)) || (m = line.match(/^\d+\.\s+(.*)/))) {
      if (!list) list = h('ul', { class: 'md-ul' });
      list.append(h('li', {}, inline(m[1])));
    } else { flush(); out.push(h('p', { class: 'md-p' }, inline(line))); }
  }
  flush();
  return out;
}

const avaEl = (emoji, cls = '') => h('span', { class: `agent-ava ${cls}` }, emoji || '🤖');
async function copyText(t) {
  try { await navigator.clipboard.writeText(t); toast('已复制到剪贴板'); }
  catch { toast('复制失败，请手动选择文本', 'warn'); }
}

// ============================================================
// 灵阵首页
// ============================================================
export async function renderAgents(page) {
  page.append(h('div', { class: 'topbar' },
    h('div', {}, h('h1', {}, '🛰 灵阵'), h('div', { class: 'sub' }, '一句话，调动一支专业 AI 团队')),
    h('div', { class: 'spacer' }),
    h('button', { class: 'btn mini', onclick: () => newTeamSheet() }, '+ 新建团队')
  ));

  const body = h('div', {});
  page.append(spinner());
  const wrap = page.lastChild;

  let data;
  try {
    const [m, teams, agents, kb, runs, gallery, triggers, drafts] = await Promise.all([
      meta(), GET('/api/teams'), GET('/api/agents'), GET('/api/kb'), GET('/api/runs'),
      GET('/api/teams/gallery').catch(() => ({ items: [] })),
      GET('/api/triggers').catch(() => ({ items: [] })),
      GET('/api/agent-drafts').catch(() => ({ items: [] }))
    ]);
    data = { m, teams, agents, kb, runs, gallery, triggers, drafts };
  } catch (e) { wrap.replaceWith(emptyState('加载失败', e.message)); return; }
  wrap.replaceWith(body);

  const { m, teams, agents, kb, runs, gallery, triggers, drafts } = data;

  // 配额条
  body.append(h('div', { class: 'glass lz-quota' },
    h('span', {}, `今日团队运行额度　${m.quota.used}/${m.quota.limit}`),
    h('div', { class: 'lz-quota-bar' }, h('i', { style: { width: Math.min(100, m.quota.used / m.quota.limit * 100) + '%' } })),
    m.member ? null : h('button', { class: 'btn mini ghost', onclick: () => nav('/member') }, '提额')
  ));

  // 🎰 随机整活：抽一支沙雕团队 + 随机任务，一键开跑
  body.append(h('button', { class: 'glass lz-fun-roll', onclick: () => rollFun(teams) },
    h('span', { class: 'lz-fun-emoji' }, '🎰'),
    h('span', { style: { flex: 1, textAlign: 'left' } },
      h('div', { class: 'lz-fun-title' }, '随机整活'),
      h('div', { class: 'lz-fun-sub' }, '夸夸群 / 赛博算命 / 废话文学… 抽个沙雕团队替你整活')),
    h('span', { class: 'lz-go' }, '手气 ›')));

  // 我的团队
  body.append(sectionHead('我的团队', teams.mine.length ? '点击进入工作台派活' : ''));
  if (!teams.mine.length) {
    body.append(h('div', { class: 'glass lz-tip' }, '还没有团队。从下面的模板一键创建，或点右上角「新建团队」。'));
  } else {
    const grid = h('div', { class: 'lz-grid' });
    for (const t of teams.mine) grid.append(teamCard(t));
    body.append(grid);
  }

  // 团队模板
  body.append(sectionHead('团队模板', '开箱即用，复制后可改'));
  const tg = h('div', { class: 'lz-grid' });
  for (const t of teams.templates) tg.append(teamCard(t, true));
  body.append(tg);

  // 团队广场（他人发布）
  if (gallery.items.length) {
    body.append(sectionHead('团队广场', '其他用户发布的团队，点开即可派活'));
    const gg = h('div', { class: 'lz-grid' });
    for (const t of gallery.items) gg.append(galleryCard(t));
    body.append(gg);
  }

  // 定时任务
  body.append(sectionHead('定时任务', '让团队按计划自动跑', h('button', { class: 'btn mini ghost', onclick: () => triggerSheet([...teams.mine, ...teams.templates]) }, '+ 新建')));
  const tl = h('div', {});
  if (!triggers.items.length) tl.append(h('div', { class: 'glass lz-tip' }, '还没有定时任务。给一支团队设个计划，它就会自动替你产出。'));
  else for (const t of triggers.items) tl.append(triggerCard(t));
  body.append(tl);

  // 草稿箱（站内动作 draft_post 的产物）
  if (drafts.items.length) {
    body.append(sectionHead('草稿箱', '智能体写好的文案，去发布前可再改'));
    const dl = h('div', {});
    for (const d of drafts.items) dl.append(draftCard(d));
    body.append(dl);
  }

  // 我的智能体
  body.append(sectionHead('智能体成员', '团队的组成单位', h('button', { class: 'btn mini ghost', onclick: () => agentEditor(null) }, '+ 新建成员')));
  const ag = h('div', { class: 'lz-agent-row' });
  for (const a of [...agents.mine, ...agents.templates]) ag.append(agentChip(a));
  body.append(ag);

  // 知识库
  body.append(sectionHead('知识库', 'RAG · 让团队有料可查', h('button', { class: 'btn mini ghost', onclick: () => kbEditor(null) }, '+ 新建')));
  const kg = h('div', { class: 'lz-agent-row' });
  for (const k of [...kb.mine, ...kb.templates]) kg.append(kbChip(k));
  body.append(kg);

  // 最近运行
  if (runs.items.length) {
    body.append(sectionHead('最近运行', ''));
    const rl = h('div', { class: 'glass menu-list' });
    for (const r of runs.items.slice(0, 8)) {
      const [label, cls] = STATUS[r.status] || ['—', ''];
      rl.append(h('button', { class: 'menu-item lz-run-item', onclick: () => nav(`/run/${r.id}`) },
        h('span', { class: `st-badge ${cls}` }, label),
        h('span', { class: 'lz-run-task' }, r.task),
        h('span', { class: 'mi-arrow' }, timeAgo(r.started_at))));
    }
    body.append(rl);
  }

  function teamCard(t, isTpl = false) {
    return h('div', { class: 'glass lz-team-card', onclick: () => nav(`/team/${t.id}`) },
      h('div', { class: 'lz-team-top' },
        avaEl(t.avatar, 'big'),
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('div', { class: 'lz-team-name' }, t.name, isTpl ? h('span', { class: 'lz-tpl-tag' }, '模板') : null),
          h('div', { class: 'lz-team-strat' }, `${STRAT_ICON[t.strategy] || ''} ${stratName(t.strategy)} · ${t.members.length} 名成员`)),
      ),
      t.goal ? h('div', { class: 'lz-team-goal' }, t.goal) : null,
      h('div', { class: 'lz-member-avas' }, t.members.slice(0, 6).map((mm) => avaEl(mm.avatar)))
    );
  }
  function galleryCard(t) {
    return h('div', { class: 'glass lz-team-card', onclick: () => nav(`/team/${t.id}`) },
      h('div', { class: 'lz-team-top' }, avaEl(t.avatar, 'big'),
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('div', { class: 'lz-team-name' }, t.name),
          h('div', { class: 'lz-team-strat' }, `${STRAT_ICON[t.strategy] || ''} ${stratName(t.strategy)} · by ${t.owner_name} · 跑过 ${t.run_count} 次`))),
      t.goal ? h('div', { class: 'lz-team-goal' }, t.goal) : null,
      h('div', { class: 'lz-member-avas' }, t.members.slice(0, 6).map((mm) => avaEl(mm.avatar)))
    );
  }
  function agentChip(a) {
    return h('button', { class: 'glass lz-agent-chip', onclick: () => agentEditor(a) },
      avaEl(a.avatar), h('div', { class: 'lz-ac-text' },
        h('div', { class: 'lz-ac-name' }, a.name, a.is_template ? h('span', { class: 'lz-tpl-tag' }, '模板') : null),
        h('div', { class: 'lz-ac-role' }, a.role || '通用助理')));
  }
  function kbChip(k) {
    return h('button', { class: 'glass lz-agent-chip', onclick: () => kbEditor(k) },
      avaEl('📚'), h('div', { class: 'lz-ac-text' },
        h('div', { class: 'lz-ac-name' }, k.name, k.is_template ? h('span', { class: 'lz-tpl-tag' }, '示例') : null),
        h('div', { class: 'lz-ac-role' }, `${k.chunk_count} 个知识片段`)));
  }
  function draftCard(d) {
    const bg = d.card?.bg;
    return h('div', { class: 'glass lz-draft', style: bg ? { borderLeft: `4px solid ${bg[1] || bg[0]}` } : {} },
      h('div', { class: 'lz-draft-text' }, d.text),
      h('div', { class: 'lz-draft-foot' },
        h('span', { class: 'lz-draft-meta' }, '🪄 智能体草稿'),
        h('div', { style: { flex: 1 } }),
        h('button', { class: 'btn mini', onclick: () => nav(`/compose?draft=${encodeURIComponent(d.text)}`) }, '去发布'),
        h('button', { class: 'btn mini ghost', onclick: async () => { try { await DEL(`/api/agent-drafts/${d.id}`); toast('已丢弃'); location.reload(); } catch (e) { toast(e.message, 'warn'); } } }, '丢弃')));
  }
}

const sectionHead = (title, sub, action) => h('div', { class: 'lz-sec-head' },
  h('div', {}, h('div', { class: 'lz-sec-title' }, title), sub ? h('div', { class: 'lz-sec-sub' }, sub) : null),
  action || null);

// ---------- 🎰 随机整活 ----------
const FUN_TEAM_NAMES = ['夸夸群', '赛博算命馆', '杠精辩论赛', '废话文学创作组'];
const FUN_PROMPTS = [
  '夸夸我今天又是不想上班的一天', '帮我算算今天适不适合摸鱼', '用废话文学点评一下「早睡早起身体好」',
  '帮我吐槽一下永远开不完的会', '夸夸刚加完班还在硬撑的我', '今天水逆吗，给我算一卦',
  '把「多喝热水」扩写成一段正确的废话', '帮我想个理由优雅地拒绝周末加班', '夸一夸坚持自律到第三天的我',
  '帮我把「在吗」翻译成一段有文化的废话'
];
async function rollFun(teams) {
  const pool = teams.templates.filter((t) => FUN_TEAM_NAMES.includes(t.name));
  const list = pool.length ? pool : teams.templates;
  if (!list.length) return toast('还没有可用团队', 'warn');
  const team = list[Math.floor(Math.random() * list.length)];
  const task = FUN_PROMPTS[Math.floor(Math.random() * FUN_PROMPTS.length)];
  try {
    const { run_id } = await POST(`/api/teams/${team.id}/run`, { task });
    toast(`🎰 ${team.name} 接活：${task}`);
    nav(`/run/${run_id}`);
  } catch (e) {
    if (e.extra?.need_member) confirmSheet('额度用完啦', e.message, '去看看会员', () => nav('/member'), false);
    else toast(e.message, 'warn');
  }
}

// ---------- 定时任务 ----------
const scheduleDesc = (t) => t.schedule_kind === 'daily'
  ? `每天 ${String(t.at_hour).padStart(2, '0')}:${String(t.at_minute).padStart(2, '0')}`
  : `每 ${t.interval_min} 分钟`;
function fmtNext(ts) {
  const d = ts - Date.now();
  if (d <= 0) return '即将';
  if (d < 3600_000) return `${Math.ceil(d / 60_000)} 分钟后`;
  if (d < 86400_000) return `${Math.round(d / 3600_000)} 小时后`;
  const t = new Date(ts);
  return `${t.getMonth() + 1}-${t.getDate()} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
}

function triggerCard(t) {
  const enSwitch = h('button', { class: `switch ${t.enabled ? 'on' : ''}` });
  enSwitch.onclick = async () => {
    try { const r = await PATCH(`/api/triggers/${t.id}`, { enabled: !t.enabled }); t.enabled = r.trigger.enabled; t.next_run_at = r.trigger.next_run_at; enSwitch.classList.toggle('on', t.enabled); nextEl.textContent = t.enabled ? `下次 ${fmtNext(t.next_run_at)}` : '已暂停'; toast(t.enabled ? '已启用' : '已暂停'); }
    catch (e) { toast(e.message, 'warn'); }
  };
  const nextEl = h('span', { class: 'lz-trigger-next' }, t.enabled ? `下次 ${fmtNext(t.next_run_at)}` : '已暂停');
  return h('div', { class: 'glass lz-trigger' },
    h('div', { class: 'lz-trigger-top' },
      h('div', { style: { flex: 1, minWidth: 0 } },
        h('div', { class: 'lz-trigger-name' }, '⏰ ', t.name),
        h('div', { class: 'lz-trigger-meta' }, `${t.team_name} · ${scheduleDesc(t)} · 跑过 ${t.run_count} 次`)),
      enSwitch),
    h('div', { class: 'lz-trigger-task' }, t.task),
    h('div', { class: 'lz-trigger-foot' }, nextEl, h('div', { style: { flex: 1 } }),
      t.last_run_id ? h('button', { class: 'btn mini ghost', onclick: () => nav(`/run/${t.last_run_id}`) }, '上次结果') : null,
      h('button', {
        class: 'btn mini ghost', onclick: async (e) => {
          e.currentTarget.disabled = true;
          try { const r = await POST(`/api/triggers/${t.id}/run-now`); nav(`/run/${r.run_id}`); }
          catch (err) { e.currentTarget.disabled = false; if (err.extra?.need_member) confirmSheet('额度用完啦', err.message, '去看看会员', () => nav('/member'), false); else toast(err.message, 'warn'); }
        }
      }, '▶ 立即跑'),
      h('button', { class: 'lz-mp-x', onclick: () => confirmSheet('删除定时任务', '不会影响团队本身。', '删除', async () => { await DEL(`/api/triggers/${t.id}`); toast('已删除'); location.reload(); }) }, '×')));
}

async function triggerSheet(teamPool) {
  sheet((box, close) => {
    if (!teamPool.length) { box.append(h('h3', {}, '新建定时任务'), h('p', { class: 'sheet-sub' }, '先创建或选择一个团队。')); return; }
    let teamId = teamPool[0].id, kind = 'interval';
    const teamRow = h('div', { class: 'lz-pick-list' });
    const renderTeams = () => { teamRow.innerHTML = ''; for (const t of teamPool) teamRow.append(h('button', { class: `lz-pick ${teamId === t.id ? 'on' : ''}`, onclick: () => { teamId = t.id; renderTeams(); } }, avaEl(t.avatar), h('div', { style: { flex: 1, textAlign: 'left' } }, h('div', { class: 'lz-mp-name' }, t.name), h('div', { class: 'lz-mp-role' }, `${STRAT_ICON[t.strategy] || ''} ${stratName(t.strategy)}`)), h('span', { class: 'lz-pick-tick' }, teamId === t.id ? '✓' : ''))); };
    renderTeams();
    const nameI = h('input', { class: 'input', maxlength: 30, placeholder: '任务名（可选）' });
    const taskI = h('textarea', { class: 'input', rows: 3, placeholder: '每次自动执行的任务，例如：给句灵想 3 个今天适合发的文案选题' });
    const intI = h('input', { class: 'input', type: 'number', value: '60', min: '30', style: { width: '90px' } });
    const hourI = h('input', { class: 'input', type: 'number', value: '9', min: '0', max: '23', style: { width: '64px' } });
    const minI = h('input', { class: 'input', type: 'number', value: '0', min: '0', max: '59', style: { width: '64px' } });
    const schedBody = h('div', { style: { marginTop: '8px' } });
    const kindRow = h('div', { class: 'lz-strat-row' });
    const renderSched = () => { schedBody.innerHTML = ''; schedBody.append(kind === 'interval' ? h('div', { class: 'lz-sched-line' }, '每', intI, '分钟（最少 30）') : h('div', { class: 'lz-sched-line' }, '每天', hourI, ':', minI, '（北京时间）')); };
    const renderKind = () => { kindRow.innerHTML = ''; for (const [k, label, desc] of [['interval', '⏱ 每隔一段', '每 N 分钟跑一次'], ['daily', '📅 每天定点', '每天某时刻跑一次']]) kindRow.append(h('button', { class: `lz-strat ${kind === k ? 'active' : ''}`, onclick: () => { kind = k; renderKind(); renderSched(); } }, h('div', { class: 'lz-strat-name' }, label), h('div', { class: 'lz-strat-blurb' }, desc))); };
    renderKind(); renderSched();
    box.append(h('h3', {}, '新建定时任务'),
      h('div', { class: 'field' }, h('label', {}, '选择团队'), teamRow),
      h('div', { class: 'field' }, h('label', {}, '任务名'), nameI),
      h('div', { class: 'field' }, h('label', {}, '自动执行的任务'), taskI),
      h('div', { class: 'field' }, h('label', {}, '调度方式'), kindRow, schedBody),
      h('button', {
        class: 'btn block', onclick: async () => {
          if (!taskI.value.trim()) return toast('写下要自动执行的任务', 'warn');
          try {
            await POST('/api/triggers', { team_id: teamId, name: nameI.value.trim(), task: taskI.value.trim(), schedule_kind: kind, interval_min: Number(intI.value) || 60, at_hour: Number(hourI.value) || 0, at_minute: Number(minI.value) || 0 });
            close(); toast('已创建定时任务'); location.reload();
          } catch (e) { toast(e.message, 'warn'); }
        }
      }, '创建'));
  });
}

// ============================================================
// 团队工作台（编排 + 派活）
// ============================================================
export async function renderTeam(page, { id }) {
  page.append(h('div', { class: 'topbar' },
    h('button', { class: 'icon-btn', onclick: () => nav('/agents') }, '‹'),
    h('div', {}, h('h1', {}, '团队工作台')), h('div', { class: 'spacer' })));
  page.append(spinner());
  const slot = page.lastChild;

  let team, members, allAgents, allKb, m;
  try {
    const [td, ag, kb, mm] = await Promise.all([GET(`/api/teams/${id}`), GET('/api/agents'), GET('/api/kb'), meta()]);
    team = { ...td.team }; members = td.members; allAgents = ag; allKb = kb; m = mm;
  } catch (e) { slot.replaceWith(emptyState('团队不存在', e.message)); return; }

  const editable = team.mine;
  const box = h('div', {});
  slot.replaceWith(box);
  // 可编辑的内存模型
  const model = {
    name: team.name, avatar: team.avatar, goal: team.goal, strategy: team.strategy,
    manager_note: team.manager_note, max_rounds: team.max_rounds,
    member_ids: members.map((x) => x.id), knowledge_ids: team.knowledge_ids || []
  };

  // 头部卡
  const header = h('div', { class: 'glass lz-team-header' });
  box.append(header);
  function renderHeader() {
    header.innerHTML = '';
    header.append(
      h('div', { class: 'lz-th-top' }, avaEl(model.avatar, 'big'),
        h('div', { style: { flex: 1 } },
          h('div', { class: 'lz-team-name', style: { fontSize: '18px' } }, model.name,
            team.is_template ? h('span', { class: 'lz-tpl-tag' }, '模板（只读）') : null),
          h('div', { class: 'lz-team-strat' }, `${STRAT_ICON[model.strategy]} ${stratName(model.strategy)}`))),
      model.goal ? h('div', { class: 'lz-team-goal', style: { marginTop: '8px' } }, '🎯 ' + model.goal) : null
    );
  }
  renderHeader();

  // 派活区（最重要：所有可用团队都能直接派活）
  const taskInput = h('textarea', { class: 'input lz-task', rows: 3, placeholder: '把任务交给这支团队，越具体越好。例如：帮我策划一场面向大学生的露营主题活动，给出主题、玩法和一条宣传文案。' });
  box.append(h('div', { class: 'glass lz-launch' },
    h('div', { class: 'lz-launch-title' }, '▶ 给团队派活'),
    taskInput,
    h('button', {
      class: 'btn block', style: { marginTop: '10px' },
      onclick: async (e) => {
        const task = taskInput.value.trim();
        if (!task) return toast('先写下要做的任务', 'warn');
        const btn = e.currentTarget; btn.disabled = true; btn.textContent = '团队集结中…';
        try {
          const { run_id } = await POST(`/api/teams/${id}/run`, { task });
          nav(`/run/${run_id}`);
        } catch (err) {
          btn.disabled = false; btn.textContent = '▶ 开始协作';
          if (err.extra?.need_member) confirmSheet('额度用完啦', err.message, '去看看会员', () => nav('/member'), false);
          else toast(err.message, 'warn');
        }
      }
    }, '▶ 开始协作')
  ));

  // 发布到团队广场（仅自有团队）
  if (editable) {
    let published = team.published;
    const pubSwitch = h('button', { class: `switch ${published ? 'on' : ''}` });
    pubSwitch.onclick = async () => {
      try { const r = await POST(`/api/teams/${id}/publish`, { published: !published }); published = r.published; pubSwitch.classList.toggle('on', published); toast(published ? '已发布到团队广场' : '已取消发布'); }
      catch (e) { toast(e.message, 'warn'); }
    };
    box.append(h('div', { class: 'glass menu-item', style: { padding: '12px 14px', marginBottom: '12px' } },
      h('div', { style: { flex: 1 } }, h('div', {}, '🌐 发布到团队广场'), h('div', { class: 'lz-tip' }, '让其他用户也能用你这支团队派活')), pubSwitch));

    // 对外 API
    const apiBox = h('div', { class: 'glass lz-edit-card' });
    box.append(apiBox);
    let hasApi = team.has_api;
    const renderApi = (newKey) => {
      apiBox.innerHTML = '';
      apiBox.append(h('div', { class: 'lz-edit-head' }, h('span', {}, '🔌 对外 API'),
        hasApi ? h('button', { class: 'btn mini ghost danger', onclick: async () => { try { await DEL(`/api/teams/${id}/api-key`); hasApi = false; renderApi(); toast('已吊销'); } catch (e) { toast(e.message, 'warn'); } } }, '吊销') : null));
      apiBox.append(h('div', { class: 'lz-tip' }, '生成密钥后，任意外部系统 / Webhook 可凭它同步调用这支团队（每日 50 次）。'));
      if (newKey) {
        apiBox.append(
          h('div', { class: 'lz-api-key' }, h('code', {}, newKey), h('button', { class: 'btn mini', onclick: () => copyText(newKey) }, '复制')),
          h('div', { class: 'lz-tip', style: { marginTop: '6px' } }, '⚠ 密钥只显示这一次，请妥善保存。'),
          h('pre', { class: 'lz-api-curl' }, `curl -X POST ${location.origin}/api/public/run \\\n  -H "Content-Type: application/json" \\\n  -d '{"key":"${newKey}","task":"你的任务"}'`));
      } else {
        apiBox.append(h('button', { class: 'btn block', style: { marginTop: '10px' }, onclick: async () => { try { const r = await POST(`/api/teams/${id}/api-key`); hasApi = true; renderApi(r.api_key); toast('已生成密钥'); } catch (e) { toast(e.message, 'warn'); } } }, hasApi ? '🔄 重新生成密钥' : '🔑 生成 API 密钥'));
      }
    };
    renderApi();
  }

  // 成员展示
  const memberBox = h('div', { class: 'glass lz-edit-card' });
  box.append(memberBox);
  function renderMembers() {
    memberBox.innerHTML = '';
    memberBox.append(h('div', { class: 'lz-edit-head' }, h('span', {}, `👥 成员（${model.member_ids.length}）`),
      editable ? h('button', { class: 'btn mini ghost', onclick: () => pickMembers() }, '+ 添加/移除') : null));
    const row = h('div', { class: 'lz-member-list' });
    for (const mid of model.member_ids) {
      const a = [...allAgents.mine, ...allAgents.templates].find((x) => x.id === mid) || members.find((x) => x.id === mid);
      if (!a) continue;
      row.append(h('div', { class: 'lz-member-pill' }, avaEl(a.avatar),
        h('div', {}, h('div', { class: 'lz-mp-name' }, a.name), h('div', { class: 'lz-mp-role' }, a.role || '')),
        editable ? h('button', { class: 'lz-mp-x', onclick: () => { model.member_ids = model.member_ids.filter((x) => x !== mid); renderMembers(); } }, '×') : null));
    }
    if (!model.member_ids.length) row.append(h('div', { class: 'lz-tip' }, '还没有成员，点「添加」从你的智能体里挑选。'));
    memberBox.append(row);
  }
  renderMembers();

  // 知识库挂载
  const kbBox = h('div', { class: 'glass lz-edit-card' });
  box.append(kbBox);
  function renderKbs() {
    kbBox.innerHTML = '';
    kbBox.append(h('div', { class: 'lz-edit-head' }, h('span', {}, `📚 挂载知识库（${model.knowledge_ids.length}）`),
      editable ? h('button', { class: 'btn mini ghost', onclick: () => pickKbs() }, '+ 挂载' ) : null));
    const row = h('div', { class: 'lz-member-list' });
    for (const kid of model.knowledge_ids) {
      const k = [...allKb.mine, ...allKb.templates].find((x) => x.id === kid);
      if (!k) continue;
      row.append(h('div', { class: 'lz-member-pill' }, avaEl('📚'),
        h('div', {}, h('div', { class: 'lz-mp-name' }, k.name), h('div', { class: 'lz-mp-role' }, `${k.chunk_count} 片段`)),
        editable ? h('button', { class: 'lz-mp-x', onclick: () => { model.knowledge_ids = model.knowledge_ids.filter((x) => x !== kid); renderKbs(); } }, '×') : null));
    }
    if (!model.knowledge_ids.length) row.append(h('div', { class: 'lz-tip' }, '挂载知识库后，带「知识库检索」工具的成员就能查资料。'));
    kbBox.append(row);
  }
  renderKbs();

  // 编排设置（仅自己的团队可编辑）
  if (editable) {
    const ec = h('div', { class: 'glass lz-edit-card' });
    const nameI = h('input', { class: 'input', maxlength: 24, value: model.name });
    const avatarI = h('input', { class: 'input', maxlength: 4, value: model.avatar, style: { width: '64px', textAlign: 'center' } });
    const goalI = h('textarea', { class: 'input', rows: 2, maxlength: 300, placeholder: '团队使命（写给队长的总目标）' });
    goalI.value = model.goal || '';
    const noteI = h('textarea', { class: 'input', rows: 2, maxlength: 400, placeholder: '给编排官的额外指令（语气、边界、偏好…）' });
    noteI.value = model.manager_note || '';
    const stratRow = h('div', { class: 'lz-strat-row' });
    const renderStrat = () => {
      stratRow.innerHTML = '';
      for (const s of m.strategies) {
        stratRow.append(h('button', { class: `lz-strat ${model.strategy === s.id ? 'active' : ''}`, onclick: () => { model.strategy = s.id; renderStrat(); renderHeader(); } },
          h('div', { class: 'lz-strat-name' }, `${s.icon} ${s.name}`),
          h('div', { class: 'lz-strat-blurb' }, s.blurb)));
      }
    };
    renderStrat();
    const roundsV = h('span', { class: 'lz-rounds-v' }, model.max_rounds);
    const rounds = h('div', { class: 'lz-rounds' },
      h('button', { class: 'btn mini ghost', onclick: () => { model.max_rounds = Math.max(1, model.max_rounds - 1); roundsV.textContent = model.max_rounds; } }, '−'),
      roundsV,
      h('button', { class: 'btn mini ghost', onclick: () => { model.max_rounds = Math.min(m.limits.max_rounds, model.max_rounds + 1); roundsV.textContent = model.max_rounds; } }, '+'));

    ec.append(
      h('div', { class: 'lz-edit-head' }, h('span', {}, '⚙️ 编排设置')),
      h('div', { class: 'field' }, h('label', {}, '名称 / 头像'), h('div', { style: { display: 'flex', gap: '8px' } }, nameI, avatarI)),
      h('div', { class: 'field' }, h('label', {}, '团队使命'), goalI),
      h('div', { class: 'field' }, h('label', {}, '协作策略'), stratRow),
      h('div', { class: 'field' }, h('label', {}, '编排官指令'), noteI),
      h('div', { class: 'field' }, h('label', {}, '每个成员最多工具轮数'), rounds),
      h('button', {
        class: 'btn block', onclick: async (e) => {
          const btn = e.currentTarget; btn.disabled = true;
          try {
            await PATCH(`/api/teams/${id}`, {
              name: nameI.value.trim(), avatar: avatarI.value.trim(), goal: goalI.value.trim(),
              strategy: model.strategy, manager_note: noteI.value.trim(), max_rounds: model.max_rounds,
              member_ids: model.member_ids, knowledge_ids: model.knowledge_ids
            });
            model.name = nameI.value.trim(); model.goal = goalI.value.trim(); renderHeader();
            toast('已保存');
          } catch (err) { toast(err.message, 'warn'); }
          btn.disabled = false;
        }
      }, '💾 保存修改'),
      h('button', { class: 'btn block ghost danger', style: { marginTop: '10px' }, onclick: () => confirmSheet('删除团队', '删除后不可恢复（成员与知识库不受影响）。', '删除', async () => { await DEL(`/api/teams/${id}`); toast('已删除'); nav('/agents'); }) }, '删除团队')
    );
    box.append(ec);
  } else {
    box.append(h('button', { class: 'btn block', style: { margin: '4px 0 14px' }, onclick: async () => {
      try { const { team: nt } = await POST(`/api/teams/${id}/clone`); toast('已复制为我的团队'); nav(`/team/${nt.id}`); }
      catch (e) { toast(e.message, 'warn'); }
    } }, '📋 用此模板创建我的团队'));
  }

  // 成员选择器
  function pickMembers() {
    sheet((sb, close) => {
      sb.append(h('h3', {}, '选择团队成员'), h('p', { class: 'sheet-sub' }, `最多 ${m.limits.max_members} 名`));
      const pool = [...allAgents.mine, ...allAgents.templates];
      const list = h('div', { class: 'lz-pick-list' });
      const sel = new Set(model.member_ids);
      for (const a of pool) {
        const on = () => sel.has(a.id);
        const item = h('button', { class: `lz-pick ${on() ? 'on' : ''}` },
          avaEl(a.avatar), h('div', { style: { flex: 1, textAlign: 'left' } },
            h('div', { class: 'lz-mp-name' }, a.name, a.is_template ? h('span', { class: 'lz-tpl-tag' }, '模板') : null),
            h('div', { class: 'lz-mp-role' }, a.role || '')),
          h('span', { class: 'lz-pick-tick' }, on() ? '✓' : ''));
        item.addEventListener('click', () => {
          if (sel.has(a.id)) sel.delete(a.id);
          else { if (sel.size >= m.limits.max_members) return toast(`最多 ${m.limits.max_members} 名成员`, 'warn'); sel.add(a.id); }
          item.classList.toggle('on', sel.has(a.id));
          item.querySelector('.lz-pick-tick').textContent = sel.has(a.id) ? '✓' : '';
        });
        list.append(item);
      }
      sb.append(list, h('button', { class: 'btn block', onclick: () => { model.member_ids = pool.filter((a) => sel.has(a.id)).map((a) => a.id); close(); renderMembers(); } }, '确定'));
    });
  }
  function pickKbs() {
    sheet((sb, close) => {
      sb.append(h('h3', {}, '挂载知识库'));
      const pool = [...allKb.mine, ...allKb.templates];
      if (!pool.length) { sb.append(h('p', { class: 'sheet-sub' }, '还没有知识库，先去首页新建一个。')); return; }
      const list = h('div', { class: 'lz-pick-list' });
      const sel = new Set(model.knowledge_ids);
      for (const k of pool) {
        const item = h('button', { class: `lz-pick ${sel.has(k.id) ? 'on' : ''}` },
          avaEl('📚'), h('div', { style: { flex: 1, textAlign: 'left' } },
            h('div', { class: 'lz-mp-name' }, k.name), h('div', { class: 'lz-mp-role' }, `${k.chunk_count} 片段`)),
          h('span', { class: 'lz-pick-tick' }, sel.has(k.id) ? '✓' : ''));
        item.addEventListener('click', () => { sel.has(k.id) ? sel.delete(k.id) : sel.add(k.id); item.classList.toggle('on', sel.has(k.id)); item.querySelector('.lz-pick-tick').textContent = sel.has(k.id) ? '✓' : ''; });
        list.append(item);
      }
      sb.append(list, h('button', { class: 'btn block', onclick: () => { model.knowledge_ids = pool.filter((k) => sel.has(k.id)).map((k) => k.id); close(); renderKbs(); } }, '确定'));
    });
  }
}

// ============================================================
// 作战室：实时直播团队协作
// ============================================================
export async function renderRun(page, { id }) {
  page.append(h('div', { class: 'topbar' },
    h('button', { class: 'icon-btn', onclick: () => nav('/agents') }, '‹'),
    h('div', {}, h('h1', {}, '作战室')), h('div', { class: 'spacer' }),
    h('button', { class: 'icon-btn', id: 'run-stop', hidden: true }, '⏹')));
  page.append(spinner());
  const slot = page.lastChild;

  let init;
  try { init = await GET(`/api/runs/${id}`); }
  catch (e) { slot.replaceWith(emptyState('运行不存在', e.message)); return; }
  const run = init.run;

  const head = h('div', { class: 'glass lz-run-head' });
  const timeline = h('div', { class: 'lz-timeline' });
  const resultBox = h('div', {});
  const container = h('div', {});
  container.append(head, h('div', { class: 'lz-tl-title' }, '协作过程'), timeline, resultBox);
  slot.replaceWith(container);

  const statusBadge = h('span', { class: 'st-badge' });
  function renderHead(r) {
    const [label, cls] = STATUS[r.status] || ['—', ''];
    statusBadge.className = `st-badge ${cls}`; statusBadge.textContent = label;
    head.innerHTML = '';
    head.append(
      h('div', { class: 'lz-rh-top' },
        h('div', { class: 'lz-rh-team' }, `${STRAT_ICON[r.strategy] || '🛰'} ${r.team_name}`, statusBadge,
          r.by_llm ? h('span', { class: 'lz-chip-llm' }, '大模型') : h('span', { class: 'lz-chip-local' }, '本地引擎')),
      ),
      h('div', { class: 'lz-rh-task' }, '🎯 ' + r.task));
  }
  renderHead(run);

  const stopBtn = document.getElementById('run-stop');
  stopBtn.onclick = async () => { try { await POST(`/api/runs/${id}/stop`); toast('已请求停止'); } catch (e) { toast(e.message, 'warn'); } };

  // 步骤渲染（按 id 去重、按 idx 排序）
  const stepsById = new Map();
  function upsert(step) { stepsById.set(step.id, step); renderTimeline(); }
  function renderTimeline() {
    timeline.innerHTML = '';
    const steps = [...stepsById.values()].sort((a, b) => a.idx - b.idx);
    for (const s of steps) timeline.append(stepNode(s));
  }
  for (const s of init.steps) stepsById.set(s.id, s);
  renderTimeline();

  function stepNode(s) {
    if (s.phase === 'tool') {
      return h('div', { class: 'lz-step lz-step-tool' },
        h('div', { class: 'lz-tool-line' }, `🔧 ${s.agent_name} 调用 `, h('b', {}, s.title.replace('调用工具 · ', '')),
          s.status === 'running' ? h('span', { class: 'lz-dots' }, '…') : null),
        s.tool_result ? h('div', { class: 'lz-tool-out' }, String(s.tool_result).slice(0, 400)) : null);
    }
    const phaseMeta = {
      plan: ['编排官拆解', 'lz-phase-plan'], act: ['', 'lz-phase-act'], synthesize: ['总编整合', 'lz-phase-synth']
    }[s.phase] || ['', ''];
    const running = s.status === 'running';
    const node = h('div', { class: `lz-step ${phaseMeta[1]} ${running ? 'lz-running' : ''}` },
      h('div', { class: 'lz-step-head' },
        avaEl(s.agent_avatar), h('div', { style: { flex: 1 } },
          h('div', { class: 'lz-step-name' }, s.agent_name, running ? h('span', { class: 'lz-work' }, '工作中', h('span', { class: 'lz-dots' }, '…')) : null),
          s.title ? h('div', { class: 'lz-step-title' }, s.title) : null)),
      s.output ? h('div', { class: 'lz-step-out' }, ...(s.phase === 'synthesize' ? [h('div', { class: 'lz-tip' }, '↓ 最终交付见下方')] : mdNodes(s.output))) : (running ? null : h('div', { class: 'lz-step-out lz-muted' }, '（无输出）'))
    );
    return node;
  }

  // 最终结果
  function renderResult(r) {
    resultBox.innerHTML = '';
    if (r.status === 'done' && r.result) {
      resultBox.append(h('div', { class: 'glass lz-result' },
        h('div', { class: 'lz-result-head' }, h('span', {}, '🧩 最终交付'),
          h('button', { class: 'btn mini ghost', onclick: () => copyText(r.result) }, '复制')),
        h('div', { class: 'md-body' }, ...mdNodes(r.result)),
        h('div', { class: 'lz-result-meta' }, `${r.step_count} 步 · ${r.by_llm ? '大模型协作' : '本地引擎'}${r.token_total ? ' · 约 ' + r.token_total + ' tokens' : ''}`),
        h('button', { class: 'btn block', style: { marginTop: '12px' }, onclick: () => nav(`/team/${r.team_id}`) }, '再派一个任务')));
    } else if (r.status === 'failed') {
      resultBox.append(h('div', { class: 'glass lz-result lz-fail' }, '运行失败：' + (r.error || '未知错误'),
        h('button', { class: 'btn block ghost', style: { marginTop: '10px' }, onclick: () => nav(`/team/${r.team_id}`) }, '返回团队')));
    } else if (r.status === 'stopped') {
      resultBox.append(h('div', { class: 'glass lz-result' }, '已停止。',
        h('button', { class: 'btn block ghost', style: { marginTop: '10px' }, onclick: () => nav(`/team/${r.team_id}`) }, '返回团队')));
    }
  }

  // 终态/进行中分支
  let es = null;
  function finish(r) {
    stopBtn.hidden = true;
    renderHead(r); renderResult(r);
    container.scrollIntoView?.({ block: 'end' });
  }
  if (run.status !== 'running') { finish(run); return () => es?.close(); }

  // 进行中：订阅 SSE
  stopBtn.hidden = false;
  es = sse(`/api/runs/${id}/events`, {
    step: (s) => { upsert(s); if (s.status === 'running') timeline.lastChild?.scrollIntoView?.({ block: 'nearest' }); },
    done: async () => {
      es?.close();
      try { const full = await GET(`/api/runs/${id}`); for (const s of full.steps) stepsById.set(s.id, s); renderTimeline(); finish(full.run); }
      catch { /* ignore */ }
    },
    error: (e) => { es?.close(); toast(e.error || '运行失败', 'warn'); GET(`/api/runs/${id}`).then((full) => finish(full.run)).catch(() => {}); }
  });
  return () => es?.close();
}

// ============================================================
// 智能体编辑器（新建 / 编辑 / 复制模板）
// ============================================================
async function agentEditor(agent) {
  const m = await meta();
  const a = agent || { name: '', avatar: '🤖', role: '', persona: '', tier: 'default', tools: [], temperature: 0.7, mine: true };
  const readOnly = agent && !agent.mine;
  sheet((box, close) => {
    const nameI = h('input', { class: 'input', maxlength: 24, value: a.name, placeholder: '成员名字，如「调研员·探」' });
    const avatarI = h('input', { class: 'input', maxlength: 4, value: a.avatar, style: { width: '64px', textAlign: 'center' } });
    const roleI = h('input', { class: 'input', maxlength: 60, value: a.role, placeholder: '一句话职能（队长据此派活）' });
    const personaI = h('textarea', { class: 'input', rows: 4, maxlength: 1200, placeholder: '人设 / 系统提示词：它是谁、怎么思考、输出什么' });
    personaI.value = a.persona || '';
    const sel = new Set(a.tools || []);
    const toolWrap = h('div', { class: 'lz-tool-grid' });
    for (const t of m.tools) {
      const item = h('button', { class: `lz-tool-opt ${sel.has(t.id) ? 'on' : ''}` }, `${t.icon} ${t.name}`);
      item.title = t.desc;
      item.addEventListener('click', () => { sel.has(t.id) ? sel.delete(t.id) : sel.add(t.id); item.classList.toggle('on', sel.has(t.id)); });
      toolWrap.append(item);
    }
    let tier = a.tier;
    const tierBtn = h('button', { class: `switch ${tier === 'premium' ? 'on' : ''}`, onclick: () => { tier = tier === 'premium' ? 'default' : 'premium'; tierBtn.classList.toggle('on', tier === 'premium'); } });

    box.append(
      h('h3', {}, readOnly ? '查看智能体' : (agent ? '编辑智能体' : '新建智能体')),
      h('div', { class: 'field' }, h('label', {}, '名字 / 头像'), h('div', { style: { display: 'flex', gap: '8px' } }, nameI, avatarI)),
      h('div', { class: 'field' }, h('label', {}, '职能'), roleI),
      h('div', { class: 'field' }, h('label', {}, '人设 / 提示词'), personaI),
      h('div', { class: 'field' }, h('label', {}, '可用工具'), toolWrap),
      h('div', { class: 'menu-item', style: { padding: '8px 0' } }, h('div', { style: { flex: 1 } },
        h('div', {}, '使用高级模型'), h('div', { class: 'lz-tip' }, '更聪明、成本更高；默认用高速模型')), tierBtn)
    );
    if (readOnly) {
      box.append(h('button', { class: 'btn block', onclick: async () => { try { const { agent: na } = await POST(`/api/agents/${a.id}/clone`); close(); toast('已复制为我的成员'); agentEditor(na); } catch (e) { toast(e.message, 'warn'); } } }, '📋 复制为我的成员'));
      [nameI, avatarI, roleI, personaI].forEach((el) => { el.disabled = true; });
      return;
    }
    box.append(h('button', {
      class: 'btn block', onclick: async (e) => {
        if (!nameI.value.trim()) return toast('起个名字吧', 'warn');
        e.currentTarget.disabled = true;
        const payload = { name: nameI.value.trim(), avatar: avatarI.value.trim() || '🤖', role: roleI.value.trim(), persona: personaI.value.trim(), tools: [...sel], tier, temperature: a.temperature };
        try {
          if (agent) await PATCH(`/api/agents/${a.id}`, payload);
          else await POST('/api/agents', payload);
          close(); toast('已保存'); if (location.hash === '#/agents') location.reload(); else nav('/agents');
        } catch (err) { e.currentTarget.disabled = false; toast(err.message, 'warn'); }
      }
    }, '💾 保存'));
    if (agent) box.append(h('button', { class: 'btn block ghost danger', style: { marginTop: '10px' }, onclick: () => confirmSheet('删除成员', '删除后，引用它的团队会自动跳过。', '删除', async () => { await DEL(`/api/agents/${a.id}`); close(); toast('已删除'); location.reload(); }) }, '删除'));
  });
}

// ============================================================
// 知识库编辑器
// ============================================================
async function kbEditor(kb) {
  if (!kb) {
    sheet((box, close) => {
      const nameI = h('input', { class: 'input', maxlength: 30, placeholder: '知识库名字' });
      const descI = h('input', { class: 'input', maxlength: 200, placeholder: '简介（可选）' });
      box.append(h('h3', {}, '新建知识库'),
        h('div', { class: 'field' }, h('label', {}, '名称'), nameI),
        h('div', { class: 'field' }, h('label', {}, '简介'), descI),
        h('button', { class: 'btn block', onclick: async () => { if (!nameI.value.trim()) return toast('起个名字', 'warn'); try { const { kb: nk } = await POST('/api/kb', { name: nameI.value.trim(), description: descI.value.trim() }); close(); kbEditor({ ...nk, mine: true }); } catch (e) { toast(e.message, 'warn'); } } }, '创建'));
    });
    return;
  }
  let detail;
  try { detail = await GET(`/api/kb/${kb.id}`); } catch (e) { return toast(e.message, 'warn'); }
  const editable = detail.kb.mine;
  sheet((box, close) => {
    box.append(h('h3', {}, '📚 ' + detail.kb.name),
      h('p', { class: 'sheet-sub' }, detail.kb.description || `${detail.kb.chunk_count} 个知识片段`));

    // 检索测试
    const qI = h('input', { class: 'input', placeholder: '试试检索：输入关键词或问题' });
    const hits = h('div', { class: 'lz-kb-hits' });
    box.append(h('div', { class: 'field' }, h('label', {}, '检索测试（RAG）'),
      h('div', { style: { display: 'flex', gap: '8px' } }, qI,
        h('button', { class: 'btn mini', onclick: async () => { if (!qI.value.trim()) return; try { const r = await POST(`/api/kb/${kb.id}/search`, { query: qI.value.trim() }); hits.innerHTML = ''; if (!r.hits.length) hits.append(h('div', { class: 'lz-tip' }, '没有匹配片段')); for (const x of r.hits) hits.append(h('div', { class: 'lz-kb-hit' }, h('div', { class: 'lz-kb-src' }, `${x.source} · 相关度 ${x.score}`), h('div', {}, x.text.slice(0, 160)))); } catch (e) { toast(e.message, 'warn'); } } }, '检索')), hits));

    // 来源列表
    if (detail.sources?.length) box.append(h('div', { class: 'field' }, h('label', {}, '已收录文档'),
      h('div', { class: 'lz-member-list' }, detail.sources.map((s) => h('div', { class: 'lz-member-pill' }, avaEl('📄'), h('div', {}, h('div', { class: 'lz-mp-name' }, s.source), h('div', { class: 'lz-mp-role' }, `${s.chunks} 片段`)))))));

    if (editable) {
      const srcI = h('input', { class: 'input', maxlength: 60, placeholder: '文档名（可选）' });
      const txtI = h('textarea', { class: 'input', rows: 5, placeholder: '粘贴文本内容，自动切片入库' });
      box.append(h('div', { class: 'field' }, h('label', {}, '+ 添加文档'), srcI, txtI,
        h('button', { class: 'btn block', style: { marginTop: '8px' }, onclick: async (e) => { if (!txtI.value.trim()) return toast('粘贴一些文本', 'warn'); e.currentTarget.disabled = true; try { const r = await POST(`/api/kb/${kb.id}/docs`, { source: srcI.value.trim(), text: txtI.value.trim() }); toast(`已切片 ${r.added} 段`); close(); kbEditor(kb); } catch (err) { e.currentTarget.disabled = false; toast(err.message, 'warn'); } } }, '入库')));
      box.append(h('button', { class: 'btn block ghost danger', onclick: () => confirmSheet('删除知识库', '其中所有片段会一并删除。', '删除', async () => { await DEL(`/api/kb/${kb.id}`); close(); toast('已删除'); location.reload(); }) }, '删除知识库'));
    }
  });
}

// ============================================================
// 新建团队
// ============================================================
async function newTeamSheet() {
  const [m, ag] = await Promise.all([meta(), GET('/api/agents')]);
  sheet((box, close) => {
    const nameI = h('input', { class: 'input', maxlength: 24, placeholder: '团队名字，如「内容创作小组」' });
    let strategy = 'orchestrate';
    const stratRow = h('div', { class: 'lz-strat-row' });
    const renderStrat = () => { stratRow.innerHTML = ''; for (const s of m.strategies) stratRow.append(h('button', { class: `lz-strat ${strategy === s.id ? 'active' : ''}`, onclick: () => { strategy = s.id; renderStrat(); } }, h('div', { class: 'lz-strat-name' }, `${s.icon} ${s.name}`), h('div', { class: 'lz-strat-blurb' }, s.blurb))); };
    renderStrat();
    const sel = new Set();
    const pool = [...ag.mine, ...ag.templates];
    const list = h('div', { class: 'lz-pick-list' });
    for (const a of pool) {
      const item = h('button', { class: 'lz-pick' }, avaEl(a.avatar), h('div', { style: { flex: 1, textAlign: 'left' } }, h('div', { class: 'lz-mp-name' }, a.name, a.is_template ? h('span', { class: 'lz-tpl-tag' }, '模板') : null), h('div', { class: 'lz-mp-role' }, a.role || '')), h('span', { class: 'lz-pick-tick' }, ''));
      item.addEventListener('click', () => { if (sel.has(a.id)) sel.delete(a.id); else { if (sel.size >= m.limits.max_members) return toast(`最多 ${m.limits.max_members} 名`, 'warn'); sel.add(a.id); } item.classList.toggle('on', sel.has(a.id)); item.querySelector('.lz-pick-tick').textContent = sel.has(a.id) ? '✓' : ''; });
      list.append(item);
    }
    box.append(h('h3', {}, '新建团队'),
      h('div', { class: 'field' }, h('label', {}, '名称'), nameI),
      h('div', { class: 'field' }, h('label', {}, '协作策略'), stratRow),
      h('div', { class: 'field' }, h('label', {}, `选择成员（最多 ${m.limits.max_members}）`), list),
      h('button', { class: 'btn block', onclick: async () => {
        if (!nameI.value.trim()) return toast('起个名字', 'warn');
        if (!sel.size) return toast('至少选 1 名成员', 'warn');
        try { const { team } = await POST('/api/teams', { name: nameI.value.trim(), strategy, member_ids: pool.filter((a) => sel.has(a.id)).map((a) => a.id) }); close(); nav(`/team/${team.id}`); }
        catch (e) { toast(e.message, 'warn'); }
      } }, '创建团队'));
  });
}
