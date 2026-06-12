// 项目工作台：剧本编辑 / AI 生成 / 分镜表 / 角色场景卡 / Agent
import { GET, POST, PATCH, pollUntilDone } from '../api.js';
import { h, icon, toast, debounce, mediaEl, modal, STATUS_CN, isVideoUrl } from '../ui.js';
import { nav, refreshSidebarProjects } from '../main.js';
import { runBatchGenerate } from '../batch.js';
import { createAgentChat } from '../agentchat.js';
import { openStylePicker, shortStyle } from '../stylelib.js';

const RATIOS = ['16:9', '9:16', '1:1', '4:3', '21:9'];

export async function renderProject(page, params) {
  let project = await GET(`/api/projects/${params.id}`);
  let canvas = project.canvas_id ? await GET(`/api/canvases/${project.canvas_id}`).catch(() => null) : null;
  let rightTab = project.storyboard ? ((project.storyboard.episodes?.length || 0) > 1 ? 'episodes' : 'shots') : 'agent';

  const nodeByKey = () => {
    const map = new Map();
    for (const n of canvas?.nodes || []) if (n.data?.key) map.set(n.data.key, n);
    return map;
  };

  // ---------- 顶栏 ----------
  const titleInput = h('input', {
    class: 'input', value: project.title,
    style: { width: '260px', fontWeight: '700', fontSize: '16px', background: 'transparent', borderColor: 'transparent' },
    onfocus: (e) => { e.target.style.borderColor = 'var(--line2)'; e.target.style.background = '#fff'; },
    onblur: async (e) => {
      e.target.style.borderColor = 'transparent'; e.target.style.background = 'transparent';
      const v = e.target.value.trim();
      if (v && v !== project.title) { project = await PATCH(`/api/projects/${project.id}`, { title: v }); refreshSidebarProjects(); }
    }
  });
  const statusPill = h('span', { class: `pill ${project.status === 'parsed' ? 'teal' : ''}` }, STATUS_CN[project.status] || project.status);
  const ratioSel = h('select', { class: 'select', style: { width: '96px' },
    onchange: async (e) => { project = await PATCH(`/api/projects/${project.id}`, { ratio: e.target.value }); toast('画幅已更新', 'ok'); } },
    RATIOS.map((r) => h('option', { value: r, selected: r === project.ratio }, r)));

  const styleBtn = h('button', {
    class: 'btn', title: project.style ? `当前风格：${project.style}` : '选择画面风格（影响生图/生视频）',
    onclick: () => openStylePicker({
      current: project.style, onPick: async (style) => {
        project = await PATCH(`/api/projects/${project.id}`, { style });
        styleBtn.innerHTML = `${icon('wand', 15)} ${shortStyle(project.style)}`;
        styleBtn.title = project.style ? `当前风格：${project.style}` : '选择画面风格';
        toast(style ? `风格已设为「${shortStyle(style)}」，新生成的图与视频自动套用` : '已恢复默认风格', 'ok');
      }
    })
  });
  styleBtn.innerHTML = `${icon('wand', 15)} ${shortStyle(project.style)}`;

  const parseBtn = h('button', { class: 'btn accent', onclick: doParse });
  parseBtn.innerHTML = `${icon('layers')} 解析分镜`;
  const canvasBtn = h('button', { class: 'btn', onclick: () => project.canvas_id ? nav(`/canvas/${project.canvas_id}`) : toast('先解析剧本生成画布', 'err') });
  canvasBtn.innerHTML = `${icon('layout')} 打开画布`;
  const batchBtn = h('button', { class: 'btn primary', onclick: () => {
    if (!project.canvas_id) return toast('先解析剧本生成画布', 'err');
    batchBtn.disabled = true;
    runBatchGenerate(project.canvas_id, { onDone: async () => { batchBtn.disabled = false; await reload(); } });
  } });
  batchBtn.innerHTML = `${icon('wand')} 一键生成`;

  async function doParse() {
    if (!scriptArea.value.trim()) return toast('剧本是空的，先写点什么或用 AI 生成', 'err');
    parseBtn.disabled = true;
    parseBtn.innerHTML = `${icon('loader')} 解析中…`;
    try {
      saveScript.flush();
      const r = await POST('/api/ai/parse', { project_id: project.id });
      toast(r.by_llm ? '方舟解析完成' : '本地引擎解析完成', 'ok');
      rightTab = 'shots';
      await reload();
    } catch (e) { toast(e.message, 'err'); }
    parseBtn.disabled = false;
    parseBtn.innerHTML = `${icon('layers')} 解析分镜`;
  }

  // ---------- 左侧：剧本 ----------
  const scriptArea = h('textarea', { class: 'script-area', placeholder: '在这里写剧本…\n\n推荐格式：\n《剧名》\n【人物】\n名字（身份）：人设\n\n第 1 场 ｜ 场景：场景名 ｜ 日 ｜ 内\n（动作描述）\n名字：台词\n', value: project.script || '' });
  const saveHint = h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, '');
  const saveScript = debounce(async () => {
    saveHint.textContent = '保存中…';
    try { await PATCH(`/api/projects/${project.id}`, { script: scriptArea.value }); saveHint.textContent = '已保存'; }
    catch (e) { saveHint.textContent = '保存失败'; toast(e.message, 'err'); }
  }, 900);
  scriptArea.addEventListener('input', () => { saveHint.textContent = '编辑中…'; saveScript(); });

  const ideaIn = h('input', { class: 'input', placeholder: '创意（留空则按现有创意/标题发挥）', style: { flex: 1 } });
  const genreSel = h('select', { class: 'select', style: { width: '130px' } },
    ['', '都市逆袭', '赘婿战神', '甜宠虐恋', '悬疑反转', '古装宫斗', '废土科幻'].map((g) => h('option', { value: g, selected: g === project.genre }, g || '类型随意')));
  const genBtn = h('button', { class: 'btn', onclick: async () => {
    genBtn.disabled = true;
    genBtn.innerHTML = `${icon('loader')} 生成中…`;
    try {
      const r = await POST('/api/ai/script', { project_id: project.id, idea: ideaIn.value.trim(), genre: genreSel.value });
      scriptArea.value = r.script;
      toast(r.by_llm ? '方舟剧本已生成' : '本地引擎剧本已生成', 'ok');
      await reload();
    } catch (e) { toast(e.message, 'err'); }
    genBtn.disabled = false;
    genBtn.innerHTML = `${icon('spark')} AI 写剧本`;
  } });
  genBtn.innerHTML = `${icon('spark')} AI 写剧本`;

  const leftCard = h('div', { class: 'card' },
    h('div', { class: 'panel-head' }, h('b', {}, '剧本'), h('span', { class: 'grow' }), saveHint),
    h('div', { style: { padding: '14px 18px' } }, scriptArea),
    h('div', { style: { display: 'flex', gap: '8px', padding: '12px 18px', borderTop: '1px solid var(--line)' } }, ideaIn, genreSel, genBtn));

  // ---------- 右侧 ----------
  const rightCard = h('div', { class: 'card' });

  function rTab(key, label, count) {
    return h('button', { class: `tab ${rightTab === key ? 'on' : ''}`, onclick: () => { rightTab = key; renderRight(); } },
      label, count ? h('span', { class: 'pill', style: { marginLeft: '2px' } }, count) : null);
  }

  function renderRight() {
    const sb = project.storyboard;
    const multiEp = (sb?.episodes?.length || 0) > 1;
    rightCard.innerHTML = '';
    rightCard.append(h('div', { class: 'panel-head' },
      h('div', { class: 'tabs' },
        rTab('episodes', '分集', sb?.episodes?.length || null),
        rTab('shots', '分镜', sb?.shots?.length), rTab('cast', '角色', sb?.characters?.length),
        rTab('scenes', '场景/道具', (sb?.scenes?.length || 0) + (sb?.props?.length || 0)), rTab('agent', 'Agent')),
      h('span', { class: 'grow' })));
    const body = h('div', { style: { minHeight: '420px', display: 'flex', flexDirection: 'column' } });
    rightCard.append(body);

    if (rightTab === 'agent') {
      body.style.height = '560px';
      createAgentChat(body, { projectId: project.id, onAction: () => reload(true) });
      return;
    }
    if (!sb) {
      body.append(h('div', { class: 'empty' }, h('div', { html: icon('layers', 38) }),
        h('p', {}, '还没有分镜。写好剧本后点击「解析分镜」，自动拆出角色 / 场景 / 镜头并搭建画布'),
        h('button', { class: 'btn accent', onclick: doParse }, '解析分镜')));
      return;
    }
    if (rightTab === 'episodes') return renderEpisodes(body, sb);
    if (rightTab === 'shots') return renderShots(body, sb, multiEp);
    if (rightTab === 'cast') return renderCards(body, sb.characters, 'character');
    renderCards(body, [...sb.scenes.map((s) => ({ ...s, _kind: 'scene' })), ...sb.props.map((p) => ({ ...p, _kind: 'prop' }))], 'scene');
  }

  // ---------- 分集（对标小云雀「分集视频」） ----------
  function renderEpisodes(body, sb) {
    const byKey = nodeByKey();
    const list = h('div', { style: { padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: '12px' } });
    for (const ep of sb.episodes) {
      const shots = sb.shots.filter((s) => (s.episode || 'e1') === ep.key);
      const nodes = shots.map((s) => byKey.get(s.key)).filter(Boolean);
      const withImage = nodes.filter((n) => n.data.image).length;
      const withVideo = nodes.filter((n) => n.data.video).length;
      const running = nodes.some((n) => n.data.task_status === 'running');
      const genBtn2 = h('button', { class: 'btn sm', disabled: !project.canvas_id, onclick: () => {
        genBtn2.disabled = true;
        runBatchGenerate(project.canvas_id, { episode: ep.key, onDone: async () => { genBtn2.disabled = false; await reload(true); } });
      } });
      genBtn2.innerHTML = `${icon('wand', 14)} 本集一键生成`;
      list.append(h('div', { class: 'card', style: { padding: '14px 16px', display: 'flex', alignItems: 'center', gap: '14px' } },
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('b', { style: { fontSize: '14px' } }, `第${ep.order}集 · ${ep.title}`,
            running ? h('span', { class: 'pill orange pulse', style: { marginLeft: '8px' } }, '生成中') : null),
          ep.summary ? h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', margin: '3px 0 0' } }, ep.summary) : null,
          h('div', { style: { display: 'flex', gap: '6px', marginTop: '7px', flexWrap: 'wrap' } },
            h('span', { class: 'pill' }, `分镜 ${shots.length}`),
            h('span', { class: `pill ${withImage === shots.length && shots.length ? 'teal' : ''}` }, `首帧 ${withImage}/${shots.length}`),
            h('span', { class: `pill ${withVideo === shots.length && shots.length ? 'green' : ''}` }, `视频 ${withVideo}/${shots.length}`))),
        genBtn2));
    }
    const ideaIn2 = h('input', { class: 'input', placeholder: '本集创意（可空，AI 自动升级剧情）', style: { flex: 1 } });
    const addBtn = h('button', { class: 'btn accent', onclick: async () => {
      addBtn.disabled = true;
      addBtn.innerHTML = `${icon('loader')} 续写中…`;
      try {
        const r = await POST('/api/ai/episode', { project_id: project.id, idea: ideaIn2.value.trim() });
        toast(`第 ${r.episode_order} 集已续写并重新解析${r.by_llm ? '' : '（本地引擎）'}`, 'ok');
        await reload();
      } catch (e) { toast(e.message, 'err'); }
      addBtn.disabled = false;
      addBtn.innerHTML = `${icon('plus', 15)} 新增一集`;
    } });
    addBtn.innerHTML = `${icon('plus', 15)} 新增一集`;
    list.append(h('div', { style: { display: 'flex', gap: '8px', marginTop: '2px' } }, ideaIn2, addBtn));
    body.append(list);
  }

  function renderShots(body, sb, multiEp = false) {
    const byKey = nodeByKey();
    const sceneName = (key) => sb.scenes.find((s) => s.key === key)?.name || '';
    const epOrder = (key) => sb.episodes?.find((e) => e.key === key)?.order || 1;
    for (const shot of sb.shots) {
      const node = byKey.get(shot.key);
      const img = node?.data.image || '';
      const video = node?.data.video || '';
      const running = node?.data.task_status === 'running';
      const thumb = h('div', { class: 'shot-thumb', title: img ? '查看大图' : '', onclick: () => (video || img) && preview(video || img, shot) },
        video || img ? mediaEl(video && !isVideoUrl(video) ? video : (img || video), { controls: false }) : h('span', { html: icon('image', 17) }));
      const mediaBtns = h('div', { class: 'shot-media' }, thumb,
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '4px' } },
          h('button', { class: 'btn xs', disabled: !node, title: img ? '重新生成首帧' : '生成首帧图', onclick: (e) => genShotImage(e.currentTarget, shot, node) }, img ? '重出图' : '生首帧'),
          running
            ? h('span', { class: 'pill orange pulse' }, '视频生成中')
            : h('button', { class: 'btn xs', disabled: !node, title: '生成该镜头视频', onclick: (e) => genShotVideo(e.currentTarget, shot, node) }, video ? '重出片' : '生视频')));
      body.append(h('div', { class: 'shot-row' },
        h('span', { class: 'no' }, String(shot.order).padStart(2, '0')),
        h('div', { class: 'desc' },
          h('b', {}, multiEp ? h('span', { class: 'pill teal', style: { marginRight: '6px' } }, `第${epOrder(shot.episode || 'e1')}集`) : null,
            `${shot.shot_type} · ${sceneName(shot.scene)} · ${shot.duration}s`),
          h('span', {}, shot.action),
          shot.dialogue ? h('div', { class: 'dlg' }, `「${shot.dialogue}」`) : null),
        mediaBtns));
    }
  }

  function preview(url, shot) {
    modal({
      wide: true, title: `镜头 ${shot.order} · ${shot.shot_type}`,
      body: h('div', { style: { borderRadius: '12px', overflow: 'hidden', background: '#10161f' } },
        (() => { const el = mediaEl(url); el.style.width = '100%'; if (isVideoUrl(url)) el.autoplay = true; return el; })()),
      actions: [{ label: '关闭', kind: 'primary' }]
    });
  }

  async function genShotImage(btn, shot, node) {
    btn.disabled = true; btn.textContent = '出图中…';
    try {
      await POST('/api/ai/image', { prompt: shot.image_prompt, name: `镜头 ${shot.order}`, kind: 'frame', project_id: project.id, node_id: node.id });
      toast(`镜头 ${shot.order} 首帧完成`, 'ok');
      await reload(true);
    } catch (e) { toast(e.message, 'err'); btn.disabled = false; btn.textContent = '生首帧'; }
  }
  async function genShotVideo(btn, shot, node) {
    btn.disabled = true; btn.textContent = '排队…';
    try {
      const fresh = await GET(`/api/canvases/${project.canvas_id}`);
      const cur = fresh.nodes.find((n) => n.id === node.id);
      const r = await POST('/api/ai/video', {
        prompt: shot.video_prompt || shot.action, image_url: cur?.data.image || '', duration: shot.duration,
        project_id: project.id, node_id: node.id, name: `镜头 ${shot.order}`, order: shot.order
      });
      await reload(true);
      pollUntilDone(r.taskId).then(async (t) => {
        toast(t.status === 'succeeded' ? `镜头 ${shot.order} 视频完成` : `镜头 ${shot.order} 失败：${t.error}`, t.status === 'succeeded' ? 'ok' : 'err');
        await reload(true);
      });
    } catch (e) { toast(e.message, 'err'); btn.disabled = false; }
  }

  function renderCards(body, items, defaultKind) {
    const byKey = nodeByKey();
    const grid = h('div', { class: 'char-grid' });
    if (!items.length) { body.append(h('div', { class: 'empty' }, h('p', {}, '暂无内容'))); return; }
    for (const it of items) {
      const kind = it._kind || defaultKind;
      const node = byKey.get(it.key);
      const img = node?.data.image || '';
      const genBtn2 = h('button', { class: 'btn xs', style: { position: 'absolute', bottom: '8px', right: '8px' }, disabled: !node, onclick: async (e) => {
        e.currentTarget.disabled = true; e.currentTarget.textContent = '生成中…';
        try {
          await POST('/api/ai/image', { prompt: it.image_prompt, name: it.name, kind, project_id: project.id, node_id: node.id, tab: kind === 'character' ? 'character' : '' });
          toast(`${it.name} 完成`, 'ok');
          await reload(true);
        } catch (err) { toast(err.message, 'err'); }
      } }, img ? '重生成' : '生成');
      grid.append(h('div', { class: 'char-card' },
        h('div', { class: 'ph' }, img ? h('img', { src: img }) : h('span', { html: icon(kind === 'character' ? 'user' : kind === 'prop' ? 'box' : 'image', 26) }), genBtn2),
        h('div', { class: 'info' },
          h('b', {}, it.name, it.role ? h('span', { class: 'pill teal' }, it.role) : kind === 'prop' ? h('span', { class: 'pill' }, '道具') : null),
          h('p', { title: it.image_prompt }, it.desc || it.image_prompt))));
    }
    body.append(grid);
  }

  async function reload(soft = false) {
    project = await GET(`/api/projects/${project.id}`);
    canvas = project.canvas_id ? await GET(`/api/canvases/${project.canvas_id}`).catch(() => null) : null;
    if (!soft) scriptArea.value = project.script || '';
    statusPill.textContent = STATUS_CN[project.status] || project.status;
    statusPill.className = `pill ${project.status === 'parsed' ? 'teal' : ''}`;
    titleInput.value = project.title;
    renderRight();
    refreshSidebarProjects();
  }

  // 有进行中的视频任务时轮询刷新
  const pollTimer = setInterval(async () => {
    const running = (canvas?.nodes || []).filter((n) => n.data?.task_status === 'running');
    if (!running.length) return;
    for (const n of running) {
      if (n.data.task_id) { try { await GET(`/api/ai/task/${n.data.task_id}`); } catch { /* noop */ } }
    }
    await reload(true);
  }, 4000);

  page.append(
    h('div', { class: 'topbar line' },
      h('button', { class: 'btn ghost sm', html: icon('back'), onclick: () => nav('/home') }),
      titleInput, statusPill, h('span', { class: 'grow' }),
      ratioSel, styleBtn, parseBtn, canvasBtn, batchBtn),
    h('div', { class: 'wrap', style: { maxWidth: '1440px', marginTop: '16px' } },
      h('div', { class: 'work-grid' }, leftCard, rightCard)));
  renderRight();

  return () => { clearInterval(pollTimer); saveScript.cancel(); };
}
