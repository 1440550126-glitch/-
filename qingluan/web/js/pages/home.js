// 首页：问候 + 三种创作入口 + 项目网格
import { GET, POST, DEL, bootstrap, pollUntilDone } from '../api.js';
import { h, icon, toast, confirmDlg, fmtTime, STATUS_CN, mediaEl, isVideoUrl, doodle, stagger, tilt3d } from '../ui.js';
import { nav } from '../main.js';
import { loadStyles } from '../stylelib.js';
import { initFluid } from '../fx/fluid.js';
import { openAssetPicker } from '../assetpick.js';

const GENRES = ['都市逆袭', '赘婿战神', '甜宠虐恋', '悬疑反转', '古装宫斗', '废土科幻'];
const RATIOS = ['16:9', '9:16', '1:1', '4:3', '21:9'];

export async function renderHome(page) {
  const boot = await bootstrap();
  let entryTab = 'ai';

  // ---------- 万能创作框：一句话 → 短片 / 图片 / 短剧项目 ----------
  function quickBox() {
    let mode = 'short';
    const ta = h('textarea', { class: 'textarea', rows: 2, placeholder: '告诉我，今天想创作一点什么？例如：雨夜霓虹街头，一只机械猫撑着伞走过水洼，电影质感', onkeydown: (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) start(); } });
    const modeChips = h('div', { style: { display: 'flex', gap: '7px', flexWrap: 'wrap' } });
    const mk = (key, label, desc) => h('button', {
      class: `chip ${mode === key ? 'on' : ''}`, title: desc,
      onclick: (e) => { mode = key; modeChips.querySelectorAll('.chip').forEach((c) => c.classList.remove('on')); e.currentTarget.classList.add('on'); sync(); }
    }, label);
    modeChips.append(
      mk('short', '🎬 沉浸式短片', '一句话直接出视频，自动入资产库'),
      mk('image', '🖼 生成图片', '输入描述即刻出图，快速验证灵感'),
      mk('drama', '📖 短剧项目', '生成剧本并创建项目，进入完整流程'));
    const modelSel = h('select', { class: 'select', title: '视频模型（仅本次生效，列表在设置页维护）' },
      (boot.video_models || []).map((m) => h('option', { value: m.id, selected: m.id === boot.ark.model_video }, m.label)));
    const ratioQ = h('select', { class: 'select' }, ['16:9', '9:16', '1:1'].map((r) => h('option', { value: r }, r)));
    const durSel = h('select', { class: 'select' }, [3, 5, 8, 10].map((n) => h('option', { value: n, selected: n === 5 }, `${n} 秒`)));
    const resSel = h('select', { class: 'select', title: '分辨率' }, [['', '分辨率·自动'], ['480p', '480P'], ['720p', '720P'], ['1080p', '1080P']].map(([v, l]) => h('option', { value: v }, l)));
    // 一镜到底：首帧 + 尾帧（可选，Seedance 首尾帧自然过渡）
    let frameA = null;
    let frameB = null;
    const mkFrameBtn = (label, get, set) => {
      const b = h('button', {
        class: 'btn sm', title: `${label}图（可选）${label === '尾帧' ? '：配合首帧实现「一镜到底」自然过渡' : '：让画面更稳定'}`,
        onclick: () => openAssetPicker({ title: `选择${label}图`, onPick: (a) => { set(a); render(); } })
      });
      const render = () => {
        b.innerHTML = get()
          ? `<img src="${get().url}" style="width:18px;height:18px;border-radius:4px;object-fit:cover"> ${label}✓`
          : `${label}图`;
      };
      render();
      return b;
    };
    const frameBtnA = mkFrameBtn('首帧', () => frameA, (v) => { frameA = v; });
    const frameBtnB = mkFrameBtn('尾帧', () => frameB, (v) => { frameB = v; });
    const startBtn = h('button', { class: 'btn accent', onclick: () => start() });
    startBtn.innerHTML = `${icon('spark')} 立即开始`;
    const result = h('div');

    function sync() {
      modelSel.style.display = mode === 'short' ? '' : 'none';
      durSel.style.display = mode === 'short' ? '' : 'none';
      resSel.style.display = mode === 'short' ? '' : 'none';
      frameBtnA.style.display = mode === 'short' ? '' : 'none';
      frameBtnB.style.display = mode === 'short' ? '' : 'none';
      ta.placeholder = mode === 'drama'
        ? '输入你构想的故事：设定、主角、剧情脉络、结局…将生成剧本并创建项目'
        : mode === 'image'
          ? '描述你想要的画面，例如：复古好莱坞风格，黄昏加油站旁的老式跑车'
          : '告诉我，今天想创作一点什么？例如：雨夜霓虹街头，一只机械猫撑着伞走过水洼，电影质感';
    }

    async function start() {
      const text = ta.value.trim();
      if (!text) return toast('先描述一下你的想法', 'err');
      startBtn.disabled = true;
      startBtn.innerHTML = `${icon('loader')} 创作中…`;
      const done = () => { startBtn.disabled = false; startBtn.innerHTML = `${icon('spark')} 立即开始`; };
      try {
        if (mode === 'drama') {
          const r = await POST('/api/ai/script', { idea: text });
          toast('剧本已生成，进入项目工作台', 'ok');
          nav(`/project/${r.project.id}`);
          return;
        }
        if (mode === 'image') {
          const r = await POST('/api/ai/image', { prompt: text, name: text.slice(0, 16), kind: 'scene', ratio: ratioQ.value });
          showResult(r.url, `${r.provider === 'ark' ? '方舟 Seedream 出图完成' : '本地占位图（配置方舟 Key 出真图）'} · 已存入资产库`);
          done();
          return;
        }
        const r = await POST('/api/ai/video', {
          prompt: text, name: text.slice(0, 16), ratio: ratioQ.value, duration: Number(durSel.value),
          model: modelSel.value, resolution: resSel.value,
          image_url: frameA?.url || '', last_image_url: frameB?.url || ''
        });
        showPending(`${boot.ark.enabled ? '方舟 Seedance 生成中（约 1-3 分钟）' : '本地引擎生成中（数秒）'}…`);
        const t = await pollUntilDone(r.taskId);
        if (t.status === 'succeeded') showResult(t.result.url, `${t.provider === 'ark' ? '方舟出片完成' : '本地预览片'} · 已存入资产库`);
        else { result.innerHTML = ''; toast('生成失败：' + (t.error || ''), 'err'); }
        done();
      } catch (e) { toast(e.message, 'err'); done(); }
    }

    function showPending(text) {
      result.innerHTML = '';
      result.append(h('div', { class: 'quick-result' }, h('div', { class: 'spinner' }), h('div', { class: 'qr-info' }, text)));
    }
    function showResult(url, caption) {
      result.innerHTML = '';
      const m = mediaEl(url);
      if (isVideoUrl(url)) m.autoplay = true;
      result.append(h('div', { class: 'quick-result' },
        h('div', { class: 'qr-media' }, m),
        h('div', { class: 'qr-info' }, h('b', {}, caption),
          h('a', { href: '#/assets', style: { color: '#7fd8c9' } }, '打开资产库 →'))));
    }

    sync();
    return h('div', {},
      h('div', { class: 'quickbox' }, ta,
        h('div', { class: 'quick-controls' }, modeChips, h('span', { class: 'grow' }), frameBtnA, frameBtnB, modelSel, ratioQ, durSel, resSel,
          doodle('arrow', { color: 'var(--accent2)', size: 30, delay: 700, rotate: -64, style: { margin: '0 0 8px 2px' } }),
          startBtn)),
      result);
  }

  const fluidCanvas = h('canvas', { class: 'fluid-bg', 'aria-hidden': 'true' });
  const hero = h('div', { class: 'hero fadein' },
    fluidCanvas,
    h('h2', {}, `Hi ${boot.user_name}，和 `,
      h('em', { style: { position: 'relative', display: 'inline-block' } }, '青鸾',
        doodle('circle', { color: 'rgba(226,94,62,.85)', size: 92, delay: 500, width: 3, style: { position: 'absolute', left: '-14px', top: '-9px' } })),
      ' 一起创作专属短剧'),
    h('p', {}, '一句话成片 · 剧本 → 分镜 → 画布 → 成片全流程 · 任何 Agent 都能替你动手'),
    quickBox(),
    h('div', { class: 'hero-pills', style: { marginTop: '14px' } },
      h('span', { class: 'pill' }, boot.ark.enabled ? `火山方舟 · ${boot.ark.model_video}` : '本地引擎模式 · 配置方舟 Key 解锁真实生成'),
      h('span', { class: 'pill' }, 'MCP / OpenAPI 全开放'),
      h('span', { class: 'pill' }, `今日成本 ¥${boot.stats.cost_today_yuan}`)),
    doodle('star', { color: 'rgba(255,209,102,.9)', size: 22, delay: 900, rotate: -14, style: { position: 'absolute', right: '178px', top: '30px' } }),
    doodle('spark', { color: 'rgba(127,216,201,.85)', size: 30, delay: 1100, style: { position: 'absolute', right: '46px', bottom: '34px' } }),
    doodle('squiggle', { color: 'rgba(255,255,255,.4)', size: 72, delay: 1300, rotate: 8, style: { position: 'absolute', left: '36px', bottom: '26px' } }),
    h('div', { class: 'bird', style: { top: '14%', transform: 'none' }, html: `<svg viewBox="0 0 100 100" width="110" height="110"><path d="M22 62 Q40 30 64 34 Q80 37 84 24 Q83 44 70 50 Q84 52 88 46 Q83 62 66 60 Q52 59 44 66 Q38 71 38 80 L33 70 Q24 70 18 76 Q19 66 22 62 Z" fill="rgba(255,255,255,.16)"/></svg>` }));

  const entryBody = h('div', { class: 'entry-body' });
  const tabs = h('div', { class: 'tabs' },
    tabBtn('ai', 'spark', 'AI 生剧本'), tabBtn('remake', 'refresh', '爆款复刻'),
    tabBtn('paste', 'film', '粘贴 / 上传剧本'), tabBtn('canvas', 'layout', '自由画布'));

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
    else if (entryTab === 'remake') entryBody.append(remakeEntry());
    else if (entryTab === 'paste') entryBody.append(pasteEntry());
    else entryBody.append(canvasEntry());
  }

  // 爆款复刻：参考文案结构 → 新主题剧本
  function remakeEntry() {
    const ref = h('textarea', { class: 'textarea', rows: 4, placeholder: '粘贴参考的爆款文案 / 短剧台本 / 视频口播稿…\nAI 会解析它的钩子手法、节奏结构和情绪曲线' });
    const topic = h('input', { class: 'input', placeholder: '你的新主题，例如：宠物殡葬师的温情日常 / 我家的智能咖啡机', style: { marginTop: '10px' } });
    const genres = genreChips();
    const btn = h('button', {
      class: 'btn accent', onclick: async () => {
        if (!ref.value.trim()) return toast('先粘贴参考爆款文案', 'err');
        if (!topic.value.trim()) return toast('填一下你的新主题', 'err');
        btn.disabled = true;
        btn.innerHTML = `${icon('loader')} 解析结构并创作中…`;
        try {
          const r = await POST('/api/ai/remake', { reference: ref.value.trim(), topic: topic.value.trim(), genre: genres.get() });
          toast(`已复刻结构${r.analysis?.hook ? `「${r.analysis.hook}」` : ''}生成剧本${r.by_llm ? '' : '（本地引擎）'}`, 'ok');
          nav(`/project/${r.project.id}`);
        } catch (e) {
          toast(e.message, 'err');
          btn.disabled = false;
          btn.innerHTML = `${icon('refresh')} 解析爆点结构并生成剧本`;
        }
      }
    });
    btn.innerHTML = `${icon('refresh')} 解析爆点结构并生成剧本`;
    return h('div', {}, ref, topic, genres.row,
      h('div', { class: 'entry-actions' },
        h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, '自动解析：钩子手法 · 节奏结构 · 情绪曲线 · 可复用爆点'),
        h('span', { class: 'grow' }), btn));
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
        doodle('star', { color: 'var(--gold)', size: 24, delay: 300, rotate: 12 }),
        h('div', { html: icon('film', 40) }), h('p', {}, '还没有项目，用上面的入口开始你的第一部短剧')));
      return;
    }
    for (const p of projects) {
      const card = projCard(p);
      tilt3d(card);
      grid.append(card);
    }
    stagger(grid);
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
            if (!await confirmDlg(`把项目《${p.title}》移入回收站？随时可以恢复。`, { okLabel: '移入回收站' })) return;
            await DEL(`/api/projects/${p.id}`);
            toast('已移入回收站，可从「我的项目 → 回收站」恢复', 'ok');
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
      h('div', { class: 'sec-head' }, h('h3', {}, '我的项目'), h('small', {}, '点击卡片进入工作台'),
        h('span', { class: 'grow' }),
        h('button', { class: 'btn ghost sm', onclick: openTrash, html: `${icon('trash', 14)} 回收站` })),
      grid));

  async function openTrash() {
    const { modal } = await import('../ui.js');
    const body = h('div');
    const m = modal({ title: h('span', { html: `${icon('trash')} 回收站` }), wide: true, body, actions: [] });
    async function render() {
      const rows = await GET('/api/projects/trash');
      body.innerHTML = '';
      if (!rows.length) {
        body.append(h('div', { class: 'empty' }, h('p', {}, '回收站是空的')));
        return;
      }
      body.append(h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '50vh', overflowY: 'auto' } },
        rows.map((p) => h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 12px', borderRadius: '10px', background: 'var(--bg2)' } },
          h('b', { style: { flex: 1, fontSize: '13.5px' } }, p.title),
          h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, `删除于 ${fmtTime(p.deleted_at)}`),
          h('button', { class: 'btn sm accent', onclick: async () => { await POST(`/api/projects/${p.id}/restore`); toast('已恢复', 'ok'); render(); loadProjects(); } }, '恢复'),
          h('button', { class: 'btn sm danger', onclick: async () => {
            if (!await confirmDlg(`彻底删除《${p.title}》？画布一并删除，不可恢复（资产库文件保留）。`)) return;
            await DEL(`/api/projects/${p.id}?purge=1`);
            toast('已彻底删除', 'ok');
            render();
          } }, '彻底删除')))));
    }
    await render();
  }
  const fluid = initFluid(fluidCanvas);
  await loadProjects();
  return () => fluid.destroy();
}
