// 首页：问候 + 三种创作入口 + 项目网格
import { GET, POST, DEL, bootstrap } from '../api.js';
import { h, icon, toast, confirmDlg, fmtTime, STATUS_CN } from '../ui.js';
import { nav } from '../main.js';
import { loadStyles } from '../stylelib.js';

const GENRES = ['都市逆袭', '赘婿战神', '甜宠虐恋', '悬疑反转', '古装宫斗', '废土科幻'];
const RATIOS = ['16:9', '9:16', '1:1', '4:3', '21:9'];

export async function renderHome(page) {
  const boot = await bootstrap();
  let entryTab = 'ai';

  const hero = h('div', { class: 'hero fadein' },
    h('h2', { html: `Hi ${boot.user_name}，和 <em>青鸾</em> 一起创作专属短剧` }),
    h('p', {}, '剧本 → 分镜 → 画布 → 成片，全流程开放：网页操作，或让任何 Agent 替你动手'),
    h('div', { class: 'hero-pills' },
      h('span', { class: 'pill' }, boot.ark.enabled ? `火山方舟 · ${boot.ark.model_video}` : '本地引擎模式 · 配置方舟 Key 解锁真实生成'),
      h('span', { class: 'pill' }, 'MCP / OpenAPI 全开放'),
      h('span', { class: 'pill' }, `今日成本 ¥${boot.stats.cost_today_yuan}`)),
    h('div', { class: 'bird', html: `<svg viewBox="0 0 100 100" width="120" height="120"><path d="M22 62 Q40 30 64 34 Q80 37 84 24 Q83 44 70 50 Q84 52 88 46 Q83 62 66 60 Q52 59 44 66 Q38 71 38 80 L33 70 Q24 70 18 76 Q19 66 22 62 Z" fill="rgba(255,255,255,.14)"/></svg>` }));

  const entryBody = h('div', { class: 'entry-body' });
  const tabs = h('div', { class: 'tabs' },
    tabBtn('ai', 'spark', 'AI 生剧本'), tabBtn('paste', 'film', '粘贴 / 上传剧本'), tabBtn('canvas', 'layout', '自由画布'));

  function tabBtn(key, ic, label) {
    return h('button', {
      class: `tab ${entryTab === key ? 'on' : ''}`,
      onclick: (e) => {
        entryTab = key;
        tabs.querySelectorAll('.tab').forEach((t) => t.classList.remove('on'));
        e.currentTarget.classList.add('on');
        fillEntry();
      }
    }, h('span', { html: icon(ic, 15) }), label);
  }

  function fillEntry() {
    entryBody.innerHTML = '';
    if (entryTab === 'ai') entryBody.append(aiEntry());
    else if (entryTab === 'paste') entryBody.append(pasteEntry());
    else entryBody.append(canvasEntry());
  }

  function genreChips() {
    let selected = '';
    const row = h('div', { class: 'genre-row' }, GENRES.map((g) =>
      h('button', {
        class: 'chip', onclick: (e) => {
          selected = selected === g ? '' : g;
          row.querySelectorAll('.chip').forEach((c) => c.classList.toggle('on', c.textContent === selected));
        }
      }, g)));
    return { row, get: () => selected };
  }

  function ratioSelect(def = '16:9') {
    return h('select', { class: 'select', style: { width: '110px' } },
      RATIOS.map((r) => h('option', { value: r, selected: r === def }, r)));
  }

  function aiEntry() {
    const idea = h('textarea', { class: 'textarea', rows: 3, placeholder: '在此输入你构想的故事，可以包含：故事设定、主角特征、剧情脉络、最终结局…\n例如：外卖小哥送餐时捡到一张能透支一亿的黑卡，开启都市逆袭' });
    const genres = genreChips();
    const episodes = h('select', { class: 'select', style: { width: '100px' }, title: '集数（多集自动用钩子衔接，可随时再续写）' }, [1, 2, 3].map((n) => h('option', { value: n, selected: n === 1 }, `${n} 集`)));
    const scenes = h('select', { class: 'select', style: { width: '110px' } }, [3, 4, 5, 6].map((n) => h('option', { value: n, selected: n === 4 }, `${n} 场/集`)));
    const ratio = ratioSelect();
    const styleSel = h('select', { class: 'select', style: { width: '170px' }, title: '画面风格（生图/生视频自动套用）' }, h('option', { value: '' }, '默认风格'));
    loadStyles().then(({ cats, styles }) => {
      for (const c of cats) {
        styleSel.append(h('optgroup', { label: c.name }, styles.filter((s) => s.cat === c.id).map((s) => h('option', { value: s.name }, s.name))));
      }
    }).catch(() => { /* 风格库可选 */ });
    const btn = h('button', {
      class: 'btn accent', onclick: async () => {
        btn.disabled = true;
        btn.innerHTML = `${icon('loader')} 正在生成剧本…`;
        try {
          const r = await POST('/api/ai/script', { idea: idea.value.trim(), genre: genres.get(), num_scenes: Number(scenes.value), num_episodes: Number(episodes.value), style: styleSel.value });
          toast(r.by_llm ? '方舟剧本已生成' : '本地引擎剧本已生成（配置方舟 Key 可解锁大模型创作）', 'ok');
          nav(`/project/${r.project.id}`);
        } catch (e) { toast(e.message, 'err'); btn.disabled = false; btn.innerHTML = `${icon('spark')} 生成剧本并创建项目`; }
      }
    });
    btn.innerHTML = `${icon('spark')} 生成剧本并创建项目`;
    return h('div', {}, idea, genres.row,
      h('div', { class: 'entry-actions' }, episodes, scenes, ratio, styleSel, h('span', { class: 'grow' }), btn));
  }

  function pasteEntry() {
    const ta = h('textarea', { class: 'textarea', rows: 6, placeholder: '把剧本粘贴到这里（支持「第 N 场 / 名字：台词 /（动作）」格式，普通小说文本也可以）…' });
    const file = h('input', { type: 'file', accept: '.txt,.md', style: { display: 'none' }, onchange: () => {
      const f = file.files[0];
      if (!f) return;
      const r = new FileReader();
      r.onload = () => { ta.value = String(r.result).slice(0, 60000); toast(`已读取《${f.name}》`, 'ok'); };
      r.readAsText(f);
    } });
    const title = h('input', { class: 'input', placeholder: '项目名（可留空，自动取《剧名》）', style: { width: '240px' } });
    const btn = h('button', {
      class: 'btn primary', onclick: async () => {
        if (!ta.value.trim()) return toast('先粘贴剧本内容', 'err');
        btn.disabled = true;
        try {
          const m = ta.value.match(/《(.+?)》/);
          const p = await POST('/api/projects', { title: title.value.trim() || m?.[1] || '未命名短剧' });
          await PATCHscript(p.id, ta.value);
          toast('项目已创建', 'ok');
          nav(`/project/${p.id}`);
        } catch (e) { toast(e.message, 'err'); btn.disabled = false; }
      }
    });
    btn.innerHTML = `${icon('plus')} 创建项目`;
    return h('div', {}, ta,
      h('div', { class: 'entry-actions' },
        h('button', { class: 'btn', onclick: () => file.click() }, h('span', { html: icon('upload', 15) }), '上传 .txt'),
        file, title, h('span', { class: 'grow' }), btn));
  }

  async function PATCHscript(id, script) {
    const { PATCH } = await import('../api.js');
    return PATCH(`/api/projects/${id}`, { script });
  }

  function canvasEntry() {
    const name = h('input', { class: 'input', placeholder: '画布名称，如：美式复古好莱坞', style: { width: '280px' } });
    const ratio = ratioSelect();
    const btn = h('button', {
      class: 'btn primary', onclick: async () => {
        btn.disabled = true;
        try {
          const c = await POST('/api/canvases', { name: name.value.trim() || '未命名画布', ratio: ratio.value });
          nav(`/canvas/${c.id}`);
        } catch (e) { toast(e.message, 'err'); btn.disabled = false; }
      }
    });
    btn.innerHTML = `${icon('layout')} 新建空白画布`;
    return h('div', {},
      h('p', { style: { color: 'var(--ink2)', fontSize: '13px', margin: '2px 0 12px' } },
        '不从剧本开始，直接在节点画布上自由编排：角色 / 场景 / 道具 / 分镜随意连线，逐镜生成图与视频。'),
      h('div', { class: 'entry-actions' }, name, ratio, h('span', { class: 'grow' }), btn));
  }

  fillEntry();

  const grid = h('div', { class: 'proj-grid' });
  async function loadProjects() {
    const projects = await GET('/api/projects');
    grid.innerHTML = '';
    if (!projects.length) {
      grid.append(h('div', { class: 'card empty', style: { gridColumn: '1/-1' } },
        h('div', { html: icon('film', 40) }), h('p', {}, '还没有项目，用上面的入口开始你的第一部短剧')));
      return;
    }
    for (const p of projects) grid.append(projCard(p));
  }

  function projCard(p) {
    const cover = h('div', { class: 'proj-cover' },
      p.cover ? h('img', { src: p.cover, loading: 'lazy' }) : h('span', { html: icon('film', 34) }),
      h('span', { class: 'ratio-tag' }, p.ratio),
      h('div', { class: 'hover-acts' },
        h('button', { class: 'btn sm', onclick: (e) => { e.stopPropagation(); nav(`/project/${p.id}`); } }, '打开'),
        p.canvas_id ? h('button', { class: 'btn sm', onclick: (e) => { e.stopPropagation(); nav(`/canvas/${p.canvas_id}`); } }, '画布') : null,
        h('button', {
          class: 'btn sm danger', onclick: async (e) => {
            e.stopPropagation();
            if (!await confirmDlg(`删除项目《${p.title}》？画布会一并删除，已生成的资产会保留在资产库。`)) return;
            await DEL(`/api/projects/${p.id}`);
            toast('已删除', 'ok');
            loadProjects();
          }
        }, '删除')));
    return h('div', { class: 'card proj-card', onclick: () => nav(`/project/${p.id}`) }, cover,
      h('div', { class: 'proj-meta' },
        h('b', {}, p.title),
        h('div', { class: 'row' },
          h('span', { class: `pill ${p.status === 'parsed' ? 'teal' : p.status === 'done' ? 'green' : ''}` }, STATUS_CN[p.status] || p.status),
          p.genre ? h('span', {}, p.genre) : null,
          h('span', { class: 'grow' }), h('span', {}, fmtTime(p.updated_at)))));
  }

  page.append(hero,
    h('div', { class: 'entry-card fadein' }, tabs, entryBody),
    h('div', { class: 'wrap' },
      h('div', { class: 'sec-head' }, h('h3', {}, '我的项目'), h('small', {}, '点击卡片进入工作台')),
      grid));
  await loadProjects();
}
