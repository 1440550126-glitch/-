// 资产库：素材 / 角色 / 画布
import { GET, POST, PATCH, DEL, uploadFile } from '../api.js';
import { h, icon, toast, modal, confirmDlg, copyText, fmtTime, mediaEl, isVideoUrl } from '../ui.js';
import { nav } from '../main.js';

const SOURCE_CN = { upload: '上传', ark: '方舟', local: '本地' };

export async function renderAssets(page, params = {}) {
  let tab = ['material', 'character', 'canvas'].includes(params.tab) ? params.tab : 'material';
  let keyword = '';

  const body = h('div', { class: 'wrap' });
  const tabs = h('div', { class: 'tabs' },
    tabBtn('material', 'image', '素材'), tabBtn('character', 'user', '角色'), tabBtn('canvas', 'layout', '画布'));

  function tabBtn(key, ic, label) {
    return h('button', {
      class: `tab ${tab === key ? 'on' : ''}`,
      onclick: (e) => {
        tab = key;
        tabs.querySelectorAll('.tab').forEach((t) => t.classList.remove('on'));
        e.currentTarget.classList.add('on');
        history.replaceState(null, '', `#/assets/${key}`);
        load();
      }
    }, h('span', { html: icon(ic, 15) }), label);
  }

  const search = h('input', { class: 'input', placeholder: '搜索名称 / 提示词…', style: { width: '220px' },
    oninput: (e) => { keyword = e.target.value.trim(); clearTimeout(search._t); search._t = setTimeout(load, 250); } });

  const fileInput = h('input', { type: 'file', accept: 'image/*,video/mp4,video/webm', multiple: true, style: { display: 'none' },
    onchange: async () => {
      for (const f of fileInput.files) {
        try { await uploadFile(f, tab === 'character' ? 'character' : 'material'); toast(`已上传 ${f.name}`, 'ok'); }
        catch (e) { toast(`${f.name}: ${e.message}`, 'err'); }
      }
      fileInput.value = '';
      load();
    } });

  function aiGenModal() {
    const prompt = h('textarea', { class: 'textarea', rows: 3, placeholder: '例如：美式复古好莱坞风格，雨夜霓虹街头，一辆老式跑车，电影质感' });
    const name = h('input', { class: 'input', placeholder: '资产名称' });
    const kind = h('select', { class: 'select' },
      [['scene', '场景'], ['character', '角色形象'], ['prop', '道具'], ['frame', '分镜画面']].map(([v, l]) => h('option', { value: v, selected: tab === 'character' ? v === 'character' : v === 'scene' }, l)));
    const ratio = h('select', { class: 'select' }, ['16:9', '9:16', '1:1'].map((r) => h('option', { value: r }, r)));
    modal({
      title: 'AI 生成图片素材',
      body: h('div', {},
        h('label', { class: 'fld' }, '提示词'), prompt,
        h('label', { class: 'fld' }, '名称'), name,
        h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
          h('div', {}, h('label', { class: 'fld' }, '用途'), kind),
          h('div', {}, h('label', { class: 'fld' }, '画幅'), ratio))),
      actions: [
        { label: '取消' },
        { label: '生成', kind: 'accent', onClick: async () => {
          if (!prompt.value.trim()) { toast('先填提示词', 'err'); return false; }
          try {
            const r = await POST('/api/ai/image', { prompt: prompt.value.trim(), name: name.value.trim(), kind: kind.value, ratio: ratio.value, tab: tab === 'character' ? 'character' : '' });
            toast(r.provider === 'ark' ? '方舟出图完成' : '本地占位图已生成', 'ok');
            load();
          } catch (e) { toast(e.message, 'err'); return false; }
        } }
      ]
    });
  }

  const grid = h('div', { class: tab === 'canvas' ? 'proj-grid' : 'asset-grid' });

  async function load() {
    grid.className = tab === 'canvas' ? 'proj-grid' : 'asset-grid';
    grid.innerHTML = '';
    grid.append(h('div', { class: 'empty', style: { gridColumn: '1/-1' } }, h('div', { class: 'spinner', style: { margin: '0 auto' } })));
    if (tab === 'canvas') {
      const list = await GET('/api/canvases');
      grid.innerHTML = '';
      if (!list.length) return grid.append(emptyBox('还没有画布，从首页「自由画布」或项目解析自动创建'));
      for (const c of list) {
        grid.append(h('div', { class: 'card proj-card', onclick: () => nav(`/canvas/${c.id}`) },
          h('div', { class: 'proj-cover' }, h('span', { html: icon('layout', 32) }), h('span', { class: 'ratio-tag' }, c.ratio)),
          h('div', { class: 'proj-meta' },
            h('b', {}, c.name),
            h('div', { class: 'row' }, h('span', { class: 'pill' }, `${c.node_count} 节点`),
              h('span', { class: 'grow' }), h('span', {}, fmtTime(c.updated_at))))));
      }
      return;
    }
    const list = await GET(`/api/assets?tab=${tab}&q=${encodeURIComponent(keyword)}`);
    grid.innerHTML = '';
    if (!list.length) return grid.append(emptyBox(keyword ? '没有匹配的资产' : '空空如也，点右上角「新增」上传或 AI 生成'));
    for (const a of list) grid.append(assetCard(a));
  }

  function emptyBox(text) {
    return h('div', { class: 'card empty', style: { gridColumn: '1/-1' } }, h('div', { html: icon('folder', 38) }), h('p', {}, text));
  }

  function assetCard(a) {
    const thumb = h('div', { class: 'asset-thumb', onclick: () => previewAsset(a) },
      a.url ? mediaEl(a.url, { controls: false }) : h('span', { html: icon('image', 26) }));
    return h('div', { class: `card asset-card ${a.tab === 'character' ? 'portrait' : ''}` }, thumb,
      h('div', { class: 'asset-acts' },
        h('button', { class: 'iconbtn', title: '重命名', html: icon('pencil', 14), onclick: () => renameAsset(a) }),
        h('button', { class: 'iconbtn', title: '复制地址', html: icon('copy', 14), onclick: () => copyText(location.origin + a.url) }),
        h('button', { class: 'iconbtn', title: '删除', html: icon('trash', 14), onclick: async () => {
          if (!await confirmDlg(`删除资产「${a.name}」？`)) return;
          await DEL(`/api/assets/${a.id}`);
          load();
        } })),
      h('div', { class: 'asset-meta' },
        h('b', { title: a.prompt || a.name }, a.name),
        a.kind === 'video' ? h('span', { class: 'pill orange' }, '视频') : null,
        h('span', { class: `pill ${a.source === 'ark' ? 'teal' : ''}` }, SOURCE_CN[a.source] || a.source)));
  }

  function previewAsset(a) {
    modal({
      wide: true,
      title: a.name,
      body: h('div', {},
        h('div', { style: { borderRadius: '12px', overflow: 'hidden', background: '#10161f', display: 'flex', justifyContent: 'center' } },
          (() => { const el = mediaEl(a.url); el.style.maxHeight = '60vh'; el.style.width = 'auto'; el.style.maxWidth = '100%'; if (isVideoUrl(a.url)) el.autoplay = true; return el; })()),
        a.prompt ? h('p', { style: { marginTop: '10px', fontSize: '13px', color: 'var(--ink2)' } }, `提示词：${a.prompt}`) : null),
      actions: [{ label: '复制地址', onClick: () => { copyText(location.origin + a.url); return false; } }, { label: '关闭', kind: 'primary' }]
    });
  }

  function renameAsset(a) {
    const input = h('input', { class: 'input', value: a.name });
    modal({
      title: '重命名资产', body: input,
      actions: [{ label: '取消' }, { label: '保存', kind: 'primary', onClick: async () => {
        await PATCH(`/api/assets/${a.id}`, { name: input.value.trim() || a.name });
        load();
      } }]
    });
  }

  const addBtn = h('button', { class: 'btn primary', onclick: () => {
    if (tab === 'canvas') return POST('/api/canvases', { name: '未命名画布' }).then((c) => nav(`/canvas/${c.id}`));
    modal({
      title: '新增资产',
      body: h('div', { style: { display: 'flex', gap: '10px', flexDirection: 'column' } },
        h('button', { class: 'btn', style: { justifyContent: 'flex-start' }, onclick: () => { document.querySelector('.modal-mask')?.remove(); fileInput.click(); } },
          h('span', { html: icon('upload') }), '上传本地文件（图片 / 视频）'),
        h('button', { class: 'btn', style: { justifyContent: 'flex-start' }, onclick: () => { document.querySelector('.modal-mask')?.remove(); aiGenModal(); } },
          h('span', { html: icon('spark') }), 'AI 生成图片')),
      actions: []
    });
  } });
  addBtn.innerHTML = `${icon('plus')} 新增`;

  page.append(
    h('div', { class: 'topbar line' }, h('h1', {}, '资产库'), h('span', { class: 'grow' }), search, addBtn, fileInput),
    body);
  body.append(h('div', { style: { margin: '16px 0' } }, tabs), grid);
  await load();
}
