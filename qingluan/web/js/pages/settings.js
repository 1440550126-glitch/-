// 设置：火山方舟接入 / 模型与价格 / 偏好 / 用量统计
import { GET, POST, PATCH, bootstrap } from '../api.js';
import { h, icon, toast } from '../ui.js';

export async function renderSettings(page) {
  const s = await GET('/api/settings');

  const keyIn = h('input', { class: 'input', placeholder: s.ark_api_key_masked ? `已配置 ${s.ark_api_key_masked}（输入新值覆盖，输入 clear 清除）` : '方舟 API Key（控制台 → API Key 管理 → 创建）', type: 'password', autocomplete: 'off' });
  const baseIn = h('input', { class: 'input', value: s.ark_base_url });
  const chatIn = h('input', { class: 'input', value: s.model_chat });
  const imageIn = h('input', { class: 'input', value: s.model_image });
  const videoIn = h('input', { class: 'input', value: s.model_video });
  const wmSel = h('select', { class: 'select' }, [['false', '不加水印'], ['true', '加 AI 水印']].map(([v, l]) => h('option', { value: v, selected: String(s.watermark) === v }, l)));
  const nameIn = h('input', { class: 'input', value: s.user_name });
  const p1 = h('input', { class: 'input', type: 'number', step: '0.0001', value: s.price_chat_in });
  const p2 = h('input', { class: 'input', type: 'number', step: '0.0001', value: s.price_chat_out });
  const p3 = h('input', { class: 'input', type: 'number', step: '0.01', value: s.price_image });
  const p4 = h('input', { class: 'input', type: 'number', step: '0.01', value: s.price_video_sec });

  const fld = (label, el, hint = '') => h('div', {}, h('label', { class: 'fld' }, label), el,
    hint ? h('div', { style: { fontSize: '12px', color: 'var(--ink3)', marginTop: '3px' } }, hint) : null);

  const saveBtn = h('button', { class: 'btn primary', onclick: async () => {
    saveBtn.disabled = true;
    try {
      const body = {
        ark_base_url: baseIn.value.trim(), model_chat: chatIn.value.trim(), model_image: imageIn.value.trim(), model_video: videoIn.value.trim(),
        watermark: wmSel.value === 'true', user_name: nameIn.value.trim() || '创作者',
        price_chat_in: Number(p1.value), price_chat_out: Number(p2.value), price_image: Number(p3.value), price_video_sec: Number(p4.value)
      };
      const k = keyIn.value.trim();
      if (k) body.ark_api_key = k === 'clear' ? '' : k;
      const r = await PATCH('/api/settings', body);
      toast(r.ark_enabled ? '已保存，方舟模式已启用' : '已保存（当前本地引擎模式）', 'ok');
      keyIn.value = '';
      await bootstrap(true);
    } catch (e) { toast(e.message, 'err'); }
    saveBtn.disabled = false;
  } });
  saveBtn.innerHTML = `${icon('check')} 保存设置`;

  const testOut = h('span', { style: { fontSize: '12.5px', color: 'var(--ink2)' } });
  const testBtn = h('button', { class: 'btn', onclick: async () => {
    testBtn.disabled = true;
    testOut.textContent = '测试中…';
    try {
      const r = await POST('/api/settings/test');
      testOut.textContent = `✓ ${r.model} 连通，${r.latency_ms}ms，回复：${r.reply}`;
      testOut.style.color = 'var(--ok)';
    } catch (e) { testOut.textContent = '✗ ' + e.message; testOut.style.color = 'var(--err)'; }
    testBtn.disabled = false;
  } });
  testBtn.innerHTML = `${icon('refresh', 15)} 测试连接`;

  const arkCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '火山方舟接入'),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } },
      '开通文档：', h('a', { href: 'https://www.volcengine.com/docs/82379', target: '_blank' }, '方舟模型服务文档 ↗'), ' · ',
      h('a', { href: 'https://console.volcengine.com/ark', target: '_blank' }, '方舟控制台 ↗'),
      '。Key 仅存本机数据库 / 环境变量，永不下发给页面。'),
    fld('API Key', keyIn, s.ark_key_source === 'env' ? '当前使用环境变量 ARK_API_KEY（设置页保存会优先生效）' : '注意：AKLT 开头的是 AccessKey，不是方舟 API Key'),
    fld('接口地址', baseIn),
    fld('对话模型（剧本/解析/Agent）', chatIn, '如 doubao-seed-1-6-250615 或接入点 ep-xxxx'),
    fld('图像模型（Seedream）', imageIn, '如 doubao-seedream-4-0-250828'),
    fld('视频模型（Seedance）', videoIn, 'Seedance 2.0 发布后直接替换模型 ID 即可'),
    fld('水印', wmSel),
    h('div', { style: { display: 'flex', gap: '10px', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap' } }, saveBtn, testBtn, testOut));

  const priceCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '成本估算单价'),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } }, '仅用于本地成本看板展示，请按方舟控制台实际定价调整（单位：元）。'),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld('对话输入 / 千token', p1), fld('对话输出 / 千token', p2), fld('图片 / 张', p3), fld('视频 / 秒', p4)));

  const prefCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '10px' } }, '偏好'),
    fld('称呼（首页问候）', nameIn),
    h('p', { style: { fontSize: '12px', color: 'var(--ink3)', marginTop: '12px' } },
      `数据库：${s.db_path}`, h('br'), `生成文件：${s.upload_dir}`));

  const stats = await GET('/api/stats');
  const statCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '10px' } }, `用量与成本（累计 ¥${stats.cost_total_yuan} · 今日 ¥${stats.cost_today_yuan}）`),
    stats.by_feature.length
      ? h('table', { class: 'stat-table' },
        h('thead', {}, h('tr', {}, ['功能', '渠道', '次数', 'tokens', '图', '视频秒', '成本'].map((t) => h('th', {}, t)))),
        h('tbody', {}, stats.by_feature.map((r) => h('tr', {},
          h('td', {}, r.feature), h('td', {}, r.provider), h('td', {}, r.calls),
          h('td', {}, (r.ptok || 0) + (r.ctok || 0)), h('td', {}, r.imgs || 0), h('td', {}, r.vsec || 0),
          h('td', {}, `¥${(Number(r.cost_micro || 0) / 1e6).toFixed(4)}`)))))
      : h('p', { style: { color: 'var(--ink3)', fontSize: '13px' } }, '还没有用量记录'));

  page.append(
    h('div', { class: 'topbar line' }, h('h1', {}, '设置'), h('span', { class: 'grow' }),
      h('span', { class: `pill ${s.ark_api_key_masked ? 'teal' : ''}` }, s.ark_api_key_masked ? '方舟已配置' : '本地引擎模式')),
    h('div', { class: 'wrap', style: { marginTop: '16px' } },
      h('div', { class: 'set-grid' },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '16px' } }, arkCard),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '16px' } }, priceCard, prefCard, statCard))));
}
