// 设置：火山方舟接入 / 模型与价格 / 偏好 / 用量统计
import { GET, POST, PATCH, bootstrap } from '../api.js';
import { h, icon, toast } from '../ui.js';

export async function renderSettings(page) {
  const s = await GET('/api/settings');

  const keyIn = h('input', { class: 'input', placeholder: s.ark_api_key_masked ? `已配置 ${s.ark_api_key_masked}（输入新值覆盖，输入 clear 清除）` : '方舟 API Key（控制台 → API Key 管理 → 创建）', type: 'password', autocomplete: 'off' });
  const baseIn = h('input', { class: 'input', value: s.ark_base_url });
  const chatIn = h('input', { class: 'input', value: s.model_chat });
  const imageIn = h('input', { class: 'input', value: s.model_image });
  const imageProIn = h('input', { class: 'input', value: s.model_image_pro || '' });
  const videoIn = h('input', { class: 'input', value: s.model_video });
  const videoOptsIn = h('textarea', { class: 'textarea', rows: 4, value: s.model_video_options || '', placeholder: 'Seedance 1.0 Pro|doubao-seedance-1-0-pro-250528' });
  const imageOptsIn = h('textarea', { class: 'textarea', rows: 3, value: s.model_image_options || '', placeholder: 'GPT Image|gpt-image-1' });
  const openaiKeyIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.openai_api_key_masked ? `已配置 ${s.openai_api_key_masked}（输入新值覆盖，clear 清除）` : 'OpenAI API Key（sk-...）' });
  const openaiBaseIn = h('input', { class: 'input', value: s.openai_base_url || '' });
  const googleKeyIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.google_api_key_masked ? `已配置 ${s.google_api_key_masked}（输入新值覆盖，clear 清除）` : 'Google API Key（Gemini API）' });
  const googleBaseIn = h('input', { class: 'input', value: s.google_base_url || '' });
  const dashKeyIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.dashscope_api_key_masked ? `已配置 ${s.dashscope_api_key_masked}（输入新值覆盖，clear 清除）` : '阿里云百炼 API Key（sk-...，统一 Key）' });
  const dashBaseIn = h('input', { class: 'input', value: s.dashscope_base_url || '' });
  const viduKeyIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.vidu_api_key_masked ? `已配置 ${s.vidu_api_key_masked}（输入新值覆盖，clear 清除）` : 'Vidu API Key（platform.vidu.com）' });
  const viduBaseIn = h('input', { class: 'input', value: s.vidu_base_url || '' });
  const klingAkIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.kling_access_key_masked ? `已配置 ${s.kling_access_key_masked}（覆盖，clear 清除）` : 'Kling AccessKey' });
  const klingSkIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.kling_secret_key_masked ? `已配置 ${s.kling_secret_key_masked}（覆盖，clear 清除）` : 'Kling SecretKey' });
  const klingBaseIn = h('input', { class: 'input', value: s.kling_base_url || '' });
  const moxingKeyIn = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.moxing_api_key_masked ? `已配置 ${s.moxing_api_key_masked}（输入新值覆盖，clear 清除）` : '墨行AI API Key（sk-...，moxing.pro）' });
  const moxingBaseIn = h('input', { class: 'input', value: s.moxing_base_url || '' });
  const extraIn = h('input', { class: 'input', value: s.video_extra_args || '', placeholder: '如 --camerafixed true' });
  const wmSel = h('select', { class: 'select' }, [['false', '不加水印'], ['true', '加 AI 水印']].map(([v, l]) => h('option', { value: v, selected: String(s.watermark) === v }, l)));
  const fbSel = h('select', { class: 'select' }, [['false', '关闭（推荐：失败时报真实错误，便于排查）'], ['true', '开启（失败时用本地占位图/视频兜底）']].map(([v, l]) => h('option', { value: v, selected: String(!!s.local_fallback) === v }, l)));
  const qc = s.qc || {};
  const qcEnSel = h('select', { class: 'select' }, [['true', '开启'], ['false', '关闭']].map(([v, l]) => h('option', { value: v, selected: String(qc.enabled !== false) === v }, l)));
  const qcFixSel = h('select', { class: 'select' }, [['true', '自动改正后复检'], ['false', '只记录不改']].map(([v, l]) => h('option', { value: v, selected: String(qc.autofix !== false) === v }, l)));
  const qcScoreIn = h('input', { class: 'input', type: 'number', min: 50, max: 95, step: 5, value: qc.min_score ?? 75, style: { width: '80px' } });
  const chainSel = h('select', { class: 'select' }, [['true', '接龙（推荐·连贯，上段尾帧→下段首帧，同场景衔接，需 ffmpeg）'], ['false', '并行（快，各镜独立首帧，不连贯）']].map(([v, l]) => h('option', { value: v, selected: String(s.video_chain !== false) === v }, l)));
  const exprSel = h('select', { class: 'select' }, [['false', '关闭'], ['true', '开启（全流程为主要角色生成表情库）']].map(([v, l]) => h('option', { value: v, selected: String(!!s.auto_expressions) === v }, l)));
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
        ark_base_url: baseIn.value.trim(), model_chat: chatIn.value.trim(), model_image: imageIn.value.trim(), model_image_pro: imageProIn.value.trim(), model_video: videoIn.value.trim(),
        model_video_options: videoOptsIn.value.trim(), video_extra_args: extraIn.value.trim(),
        model_image_options: imageOptsIn.value.trim(),
        openai_base_url: openaiBaseIn.value.trim(), google_base_url: googleBaseIn.value.trim(), dashscope_base_url: dashBaseIn.value.trim(), vidu_base_url: viduBaseIn.value.trim(), kling_base_url: klingBaseIn.value.trim(), moxing_base_url: moxingBaseIn.value.trim(),
        watermark: wmSel.value === 'true', local_fallback: fbSel.value === 'true',
        qc_enabled: qcEnSel.value === 'true', qc_autofix: qcFixSel.value === 'true', qc_min_score: Number(qcScoreIn.value), video_chain: chainSel.value === 'true', auto_expressions: exprSel.value === 'true',
        user_name: nameIn.value.trim() || '创作者',
        price_chat_in: Number(p1.value), price_chat_out: Number(p2.value), price_image: Number(p3.value), price_video_sec: Number(p4.value)
      };
      const k = keyIn.value.trim();
      if (k) body.ark_api_key = k === 'clear' ? '' : k;
      const ok2 = openaiKeyIn.value.trim();
      if (ok2) body.openai_api_key = ok2;
      const gk = googleKeyIn.value.trim();
      if (gk) body.google_api_key = gk;
      const dk = dashKeyIn.value.trim();
      if (dk) body.dashscope_api_key = dk;
      const vk = viduKeyIn.value.trim();
      if (vk) body.vidu_api_key = vk;
      const kak = klingAkIn.value.trim();
      if (kak) body.kling_access_key = kak;
      const ksk = klingSkIn.value.trim();
      if (ksk) body.kling_secret_key = ksk;
      const mxk = moxingKeyIn.value.trim();
      if (mxk) body.moxing_api_key = mxk;
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

  // 一键诊断：分别真实调用 对话/图像/视频 三类模型，定位"视频走本地"的真因
  const diagOut = h('div', { style: { fontSize: '12.5px', marginTop: '10px', display: 'none', flexDirection: 'column', gap: '4px' } });
  const diagBtn = h('button', { class: 'btn', onclick: async () => {
    diagBtn.disabled = true; diagOut.style.display = 'flex'; diagOut.innerHTML = '<span>正在逐个真实调用对话/图像/视频模型…（视频较慢，请稍候）</span>';
    try {
      const r = await POST('/api/settings/diagnose');
      diagOut.innerHTML = '';
      for (const [k, label] of [['chat', '对话/剧本'], ['image', '图像 Seedream'], ['video', '视频 Seedance']]) {
        const d = r[k]; if (!d) continue;
        diagOut.append(h('div', { style: { color: d.ok ? 'var(--ok)' : 'var(--err)' } },
          `${d.ok ? '✓' : '✗'} ${label}（${d.model}）：${d.ok ? '可用 ' + d.ms + 'ms' : d.error}`));
      }
      if (!r.video?.ok) diagOut.append(h('div', { style: { color: 'var(--ink2)', marginTop: '4px' } },
        '💡 视频失败多为：①模型 ID 写成了名称但你的账号需用「推理接入点 ep-xxxx」②该模型未在控制台开通 ③地域与接口地址不符。把上面的真实报错按提示改即可。'));
    } catch (e) { diagOut.innerHTML = ''; diagOut.append(h('div', { style: { color: 'var(--err)' } }, '✗ ' + e.message)); }
    diagBtn.disabled = false;
  } });
  diagBtn.innerHTML = `🔧 一键诊断三模型`;

  const arkCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '火山方舟接入'),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } },
      '开通文档：', h('a', { href: 'https://www.volcengine.com/docs/82379', target: '_blank' }, '方舟模型服务文档 ↗'), ' · ',
      h('a', { href: 'https://console.volcengine.com/ark', target: '_blank' }, '方舟控制台 ↗'),
      '。Key 仅存本机数据库 / 环境变量，永不下发给页面。'),
    fld('API Key', keyIn, s.ark_key_source === 'env' ? '当前使用环境变量 ARK_API_KEY（设置页保存会优先生效）' : '注意：AKLT 开头的是 AccessKey，不是方舟 API Key'),
    fld('接口地址', baseIn),
    fld('对话模型（剧本/解析/Agent）', chatIn, '如 doubao-seed-1-6-250615 或接入点 ep-xxxx'),
    fld('图像模型（Seedream）', imageIn, '分镜首帧/道具用，如 doubao-seedream-4-0-250828'),
    fld('🏆 顶配图像模型（角色三视图 / 全场景图）', imageProIn, '全片"定海神针"参考图专用最强模型；可填更强的模型 ID 或 ep- 推理接入点，留空则回退默认最强模型'),
    fld('视频模型（Seedance，默认）', videoIn, 'Seedance 2.0 发布后直接替换模型 ID 即可'),
    fld('创作框可选视频模型（每行：显示名|模型ID）', videoOptsIn, '首页创作框与 Agent 可按次选用；加一行 Seedance 2.0|<模型ID> 即生效'),
    fld('视频任务附加参数', extraIn, '追加到 Seedance 文本命令末尾（按官方文档填，如 --camerafixed true）'),
    fld('水印', wmSel),
    fld('生成失败时本地兜底', fbSel, '已接入方舟时建议关闭：失败会直接报真实原因（模型未开通/ID 错误/无额度），不再悄悄给本地占位'),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' } },
      fld('AIQC 质检', qcEnSel, '出片前用视觉模型审查画面'),
      fld('发现问题', qcFixSel, '自动按建议改提示词重生成'),
      fld('放行分数', qcScoreIn, '低于此分判为需修复')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld('视频生成方式', chainSel, '接龙=上段视频尾帧作下段首帧，画面更连贯（需 ffmpeg）'),
      fld('角色表情库自动生成', exprSel, '全流程为主角/反派生成喜怒哀乐表情集，分镜按情绪自动取用')),
    h('div', { style: { display: 'flex', gap: '10px', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap' } }, saveBtn, testBtn, diagBtn, testOut),
    diagOut);

  // 其它模型供应商：OpenAI GPT Image（图）、Google Veo 3（视频）——各用各自独立 API Key
  const pillState = (on) => h('span', { class: `pill ${on ? 'teal' : ''}`, style: { marginLeft: '8px' } }, on ? '已开通' : '未配置');
  const provCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '其它模型供应商（多 API 自由切换）'),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } },
      'GPT Image（OpenAI）与 Veo 3（Google）各用各自独立 API Key，与火山方舟并存、可自由选用。视频模型在上方「创作框可选视频模型」里已内置 Veo 3；图像模型在下方维护，"生成图片"时即可下拉选择。'),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld(h('span', {}, 'OpenAI API Key（GPT Image）', pillState(s.openai_enabled)), openaiKeyIn, '控制台 platform.openai.com → API keys；用于 gpt-image-1'),
      fld('OpenAI 接口地址', openaiBaseIn, '默认 https://api.openai.com/v1，可填代理/兼容网关')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld(h('span', {}, 'Google API Key（Veo 3）', pillState(s.google_enabled)), googleKeyIn, 'Google AI Studio → Get API key；用于 Veo 3 视频'),
      fld('Google 接口地址', googleBaseIn, '默认 Gemini API：generativelanguage.googleapis.com/v1beta')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld(h('span', {}, '阿里云百炼 API Key（千问/通义万相·统一）', pillState(s.alibaba_enabled)), dashKeyIn, '一个 Key 通用：对话用千问（model_chat 填 qwen-max 等），图/视频选通义万相'),
      fld('DashScope 接口地址', dashBaseIn, '默认 https://dashscope.aliyuncs.com')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld(h('span', {}, 'Vidu API Key（全能参考·多主体一致）', pillState(s.vidu_enabled)), viduKeyIn, '国产多图参考最强；视频选 Vidu Q1，配合「🎭 全能参考一键出片」'),
      fld('Vidu 接口地址', viduBaseIn, '默认 https://api.vidu.com')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' } },
      fld(h('span', {}, 'Kling AccessKey（可灵·快手）', pillState(s.kling_enabled)), klingAkIn, '国产视频第一梯队'),
      fld('Kling SecretKey', klingSkIn, 'AK/SK 在快手开放平台获取'),
      fld('Kling 接口地址', klingBaseIn, '默认 api-beijing.klingai.com')),
    h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } },
      fld(h('span', {}, '墨行AI Key（聚合站·一个 Key 调多家）', pillState(s.moxing_enabled)), moxingKeyIn, '一个 sk- Key 调 Kling-V3/Sora/Veo/Seedance；视频选「墨行AI·…」开头的模型即走聚合站'),
      fld('墨行AI 接口地址', moxingBaseIn, '默认 https://www.moxing.pro/v1')),
    fld('创作框可选图像模型（每行：显示名|模型ID）', imageOptsIn, '加一行 GPT Image|gpt-image-1 或 通义万相|wanx2.1-t2i-turbo 即可在「生成图片」里下拉选用'));

  // 语音合成（配音）
  const ttsAppid = h('input', { class: 'input', value: s.tts_appid || '', placeholder: '语音技术 AppID' });
  const ttsToken = h('input', { class: 'input', type: 'password', autocomplete: 'off', placeholder: s.tts_token_masked ? `已配置 ${s.tts_token_masked}（输入新值覆盖，输入 clear 清除）` : 'Access Token' });
  const ttsVoice = h('input', { class: 'input', value: s.tts_voice || '', placeholder: 'BV001_streaming' });
  const ttsOut = h('span', { style: { fontSize: '12.5px', color: 'var(--ink2)' } });
  const ttsTestBtn = h('button', { class: 'btn', onclick: async () => {
    ttsTestBtn.disabled = true;
    ttsOut.textContent = '合成中…';
    try {
      const r = await POST('/api/settings/tts-test');
      ttsOut.innerHTML = '';
      ttsOut.append('✓ 合成成功 ', h('audio', { src: r.url, controls: true, autoplay: true, style: { height: '28px', verticalAlign: 'middle' } }));
    } catch (e) { ttsOut.textContent = '✗ ' + e.message; ttsOut.style.color = 'var(--err)'; }
    ttsTestBtn.disabled = false;
  } });
  ttsTestBtn.innerHTML = `${icon('refresh', 15)} 试听`;
  const ttsCard = h('div', { class: 'card pad' },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '语音合成（配音）',
      h('span', { class: `pill ${s.tts_enabled ? 'teal' : ''}`, style: { marginLeft: '8px' } }, s.tts_enabled ? '已配置' : '未配置')),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } },
      '火山引擎控制台 → 语音技术 → 语音合成，开通后获取 AppID 与 Access Token（与方舟 Key 不同体系）。配置后：分集面板/分镜可一键配音，放映室自动同步播放；不配置也可用浏览器朗读。'),
    fld('AppID', ttsAppid),
    fld('Access Token', ttsToken),
    fld('音色 voice_type', ttsVoice, '如 BV001_streaming（通用女声）/ BV002_streaming（通用男声），以控制台音色列表为准'),
    h('div', { style: { display: 'flex', gap: '10px', alignItems: 'center', marginTop: '14px', flexWrap: 'wrap' } },
      h('button', { class: 'btn primary', onclick: async (e) => {
        const b = e.currentTarget;
        b.disabled = true;
        try {
          const body = { tts_appid: ttsAppid.value.trim(), tts_voice: ttsVoice.value.trim() || 'BV001_streaming' };
          if (ttsToken.value.trim()) body.tts_token = ttsToken.value.trim();
          await PATCH('/api/settings', body);
          toast('语音合成设置已保存', 'ok');
          ttsToken.value = '';
        } catch (err) { toast(err.message, 'err'); }
        b.disabled = false;
      } }, '保存配音设置'),
      ttsTestBtn, ttsOut));

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
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '16px' } }, arkCard, provCard, ttsCard),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: '16px' } }, priceCard, prefCard, statCard))));
}
