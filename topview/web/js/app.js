// 爆款工厂 · 工作台 SPA（hash 路由，事件委托；零构建原生 ES Module）
import { GET, POST, DEL, bootstrap, pollTask, ApiErr } from './api.js';

const page = document.getElementById('page');
const overlay = document.getElementById('overlay');
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let BOOT = null;
let player = null;

function toast(msg, ms = 2200) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), ms);
}
const capText = (c) => ({ llm: '大模型', provider: '供应商', local: '本地' }[c] || c);

// ---------- 创作框表单状态 ----------
const form = { mode: 'url', url: '', title: '', brand: '', price: '', points: '', images: '', tone: 'ugc', kind: 'ad', ratio: '9:16', lang: 'zh', duration: 6 };

// ================= 视图 =================
async function viewHome() {
  const b = BOOT;
  const toneSeg = b.tones.map((t) => `<button class="${form.tone === t.id ? 'on' : ''}" data-act="tone" data-v="${t.id}" title="${esc(t.desc)}">${esc(t.name)}</button>`).join('');
  const inputBlock = form.mode === 'url'
    ? `<label>商品页链接（亚马逊 / Shopify / 速卖通 / 淘宝详情页等公开页面）</label>
       <input id="f-url" placeholder="https://… 粘贴商品链接" value="${esc(form.url)}">
       <div class="tip">仅读取公开商品信息（标题/主图/价格/卖点）。抓不到就切到「手填」。</div>`
    : `<div class="row"><div><label>商品标题</label><input id="f-title" value="${esc(form.title)}" placeholder="例：便携榨汁杯"></div>
         <div><label>品牌（可选）</label><input id="f-brand" value="${esc(form.brand)}"></div>
         <div style="max-width:120px"><label>价格</label><input id="f-price" value="${esc(form.price)}" placeholder="99"></div></div>
       <label>核心卖点（每行一个 / 逗号分隔）</label><textarea id="f-points" placeholder="一键榨汁&#10;USB 充电&#10;便携不漏">${esc(form.points)}</textarea>`;
  page.innerHTML = `
    <h1>把商品变成爆款带货视频</h1>
    <p class="sub">商品链接或卖点 → AI 写广告脚本 → 出图 / 出片 / 多语言字幕。${b.capabilities.script === 'local' ? '当前为本地引擎演示模式（零成本）。' : ''}</p>
    <div class="card">
      <div class="seg" style="margin-bottom:6px">
        <button class="${form.mode === 'url' ? 'on' : ''}" data-act="mode" data-v="url">🔗 商品链接</button>
        <button class="${form.mode === 'manual' ? 'on' : ''}" data-act="mode" data-v="manual">✍️ 手填信息</button>
      </div>
      ${inputBlock}
      <label>脚本套路</label><div class="seg">${toneSeg}</div>
      <div class="row" style="margin-top:6px">
        <div><label>形态</label><select id="f-kind">
          <option value="ad"${form.kind === 'ad' ? ' selected' : ''}>广告短片</option>
          <option value="ugc"${form.kind === 'ugc' ? ' selected' : ''}>数字人口播（UGC）</option></select></div>
        <div><label>画幅</label><select id="f-ratio">${b.ratios.map((r) => `<option${form.ratio === r ? ' selected' : ''}>${r}</option>`).join('')}</select></div>
        <div><label>语言</label><select id="f-lang">${b.langs.map((l) => `<option value="${l.id}"${form.lang === l.id ? ' selected' : ''}>${esc(l.name)}</option>`).join('')}</select></div>
        <div style="max-width:120px"><label>单镜秒</label><input id="f-dur" type="number" min="3" max="12" value="${form.duration}"></div>
      </div>
      <div style="margin-top:16px"><button data-act="gen">⚡ 一键成片（生成广告脚本）</button></div>
    </div>
    <h2>最近的项目</h2>
    <div id="recent" class="grid"><div class="empty">加载中…</div></div>`;
  GET('/api/projects').then(({ projects }) => {
    const r = document.getElementById('recent');
    if (!r) return;
    r.innerHTML = projects.length ? projects.map(projCard).join('') : `<div class="empty">还没有项目，上面创建第一个吧 👆</div>`;
  });
}

const projCard = (p) => `<a class="proj" href="#/project/${p.id}">
  <div class="cv" ${p.cover ? `style="background-image:url('${esc(p.cover)}')"` : ''}>${p.cover ? '' : (p.kind === 'ugc' ? '🧑‍💻' : '🛍')}</div>
  <div class="meta"><b>${esc(p.title)}</b><br><span>${esc(p.kind === 'ugc' ? '数字人口播' : '广告短片')} · ${esc(statusLabel(p.status))}</span></div></a>`;
const statusLabel = (s) => ({ draft: '草稿', scripted: '已成脚本', generating: '生成中', done: '已完成' }[s] || s);

function readForm() {
  const v = (id) => document.getElementById(id)?.value?.trim() ?? '';
  if (form.mode === 'url') form.url = v('f-url');
  else { form.title = v('f-title'); form.brand = v('f-brand'); form.price = v('f-price'); form.points = v('f-points'); }
  form.kind = v('f-kind') || 'ad'; form.ratio = v('f-ratio') || '9:16'; form.lang = v('f-lang') || 'zh';
  form.duration = Math.max(3, Math.min(12, Number(v('f-dur')) || 6));
}

async function doGenerate() {
  readForm();
  const body = { tone: form.tone, kind: form.kind, ratio: form.ratio, lang: form.lang, duration: form.duration };
  if (form.mode === 'url') {
    if (!form.url) return toast('请粘贴商品链接，或切到手填');
    body.url = form.url;
  } else {
    if (!form.title) return toast('至少填写商品标题');
    body.product = { title: form.title, brand: form.brand, price: form.price, points: form.points, images: form.images };
  }
  const btn = document.querySelector('[data-act="gen"]');
  if (btn) { btn.disabled = true; btn.textContent = '生成中…'; }
  try {
    const { project } = await POST('/api/commerce/product-to-video', body);
    toast('脚本生成成功！');
    location.hash = `#/project/${project.id}`;
  } catch (e) {
    toast(e instanceof ApiErr ? e.message : '生成失败');
    if (btn) { btn.disabled = false; btn.textContent = '⚡ 一键成片（生成广告脚本）'; }
  }
}

async function viewProjects() {
  page.innerHTML = `<h1>项目</h1><div class="grid" id="list"><div class="empty">加载中…</div></div>`;
  const { projects } = await GET('/api/projects');
  document.getElementById('list').innerHTML = projects.length ? projects.map(projCard).join('') : `<div class="empty">还没有项目</div>`;
}

async function viewProject(id) {
  page.innerHTML = `<div class="empty">加载中…</div>`;
  let p;
  try { p = await GET(`/api/projects/${id}`); } catch { page.innerHTML = `<div class="empty">项目不存在</div>`; return; }
  window.__p = p;
  const prod = p.product || {}; const sb = p.storyboard || {}; const shots = sb.shots || [];
  const langChips = BOOT.langs.filter((l) => l.id !== p.lang)
    .map((l) => `<span class="chip" data-act="langchip" data-v="${l.id}">${esc(l.name)}</span>`).join('');
  const locList = (p.localizations || []).map((l) =>
    `<span class="pill">${esc(l.name)}${l.by_llm ? '' : '（待译）'} <a href="#" data-act="srt" data-v="${l.lang}">SRT↓</a></span>`).join(' ');
  page.innerHTML = `
    <a href="#/projects" class="pill">← 返回</a>
    <h1>${esc(p.title)}</h1>
    <p class="sub">${esc(prod.title || '')} ${prod.price ? `· ${esc(prod.currency || '¥')}${esc(prod.price)}` : ''} · ${esc(p.kind === 'ugc' ? '数字人口播' : '广告短片')} · ${esc(p.ratio)} · ${esc(BOOT.langs.find((x) => x.id === p.lang)?.name || p.lang)} · <b>${esc(statusLabel(p.status))}</b></p>
    <div class="bar">
      <button data-act="media">🎬 生成画面 + 视频</button>
      <button class="ghost" data-act="play" ${shots.length ? '' : 'disabled'}>▶ 放映室</button>
      <button class="ghost" data-act="dub">🎙 配音方案</button>
      <select id="re-tone" style="max-width:180px">${BOOT.tones.map((t) => `<option value="${t.id}"${p.tone === t.id ? ' selected' : ''}>${esc(t.name)}</option>`).join('')}</select>
      <button class="ghost sm" data-act="rescript">↻ 重写脚本</button>
      <button class="ghost sm" data-act="srt" data-v="">导出主语言 SRT</button>
      <button class="ghost sm" data-act="del">删除</button>
    </div>
    ${sb.hook ? `<div class="card" style="margin-bottom:14px"><b>钩子</b>：${esc(sb.hook)}　|　<b>促单</b>：${esc(sb.cta || '')}</div>` : ''}
    <h2>分镜脚本（${shots.length}）</h2>
    <div class="shots">${shots.map(shotRow).join('') || '<div class="empty">还没有脚本</div>'}</div>
    <h2>多语言本地化</h2>
    <div class="card">
      <div class="tip">选择目标语言 → 翻译字幕/口播并生成分语言 SRT。${BOOT.capabilities.script === 'local' ? '本地模式下为「透传待译」，配置大模型后自动翻译。' : ''}</div>
      <div class="chips" style="margin:12px 0">${langChips}</div>
      <button class="sm" data-act="localize">🌍 生成多语言字幕</button>
      <div style="margin-top:12px">${locList || '<span class="tip">暂无</span>'}</div>
    </div>`;
}

const roleName = (r) => ({ hook: '钩子', pain: '痛点', benefit: '卖点', proof: '信任', cta: '促单' }[r] || r);
const shotRow = (s) => `<div class="shot">
  <div class="thumb">${s.video || s.image ? `<img src="${esc(s.video || s.image)}" alt="">` : '🎞'}</div>
  <div>
    <span class="role">${esc(roleName(s.role))} · ${s.duration}s</span>
    <div class="os">${esc(s.onscreen || '')}</div>
    <div class="vo">🎙 ${esc(s.voiceover || '')}</div>
    <div class="vi">🎬 ${esc(s.visual || '')}</div>
  </div></div>`;

// ---------- 动作 ----------
async function genMedia(id) {
  const btn = document.querySelector('[data-act="media"]');
  if (btn) { btn.disabled = true; btn.textContent = '生成中…'; }
  try {
    const r = await POST(`/api/projects/${id}/media`, { only: 'all' });
    if (r.pending && r.pending.length) {
      toast(`已提交 ${r.pending.length} 个视频任务，轮询中…`, 3000);
      await Promise.all(r.pending.map((t) => pollTask(t)));
    }
    toast('画面 / 视频生成完成');
  } catch (e) { toast(e instanceof ApiErr ? e.message : '生成失败'); }
  viewProject(id);
}

async function doLocalize(id) {
  const langs = [...document.querySelectorAll('.chip.on')].map((c) => c.dataset.v);
  if (!langs.length) return toast('先选至少一种目标语言');
  toast('翻译中…');
  try { await POST(`/api/projects/${id}/localize`, { langs }); toast('多语言字幕已生成'); viewProject(id); }
  catch (e) { toast(e instanceof ApiErr ? e.message : '本地化失败'); }
}

async function downloadSrt(id, lang) {
  try {
    const r = await GET(`/api/projects/${id}/srt${lang ? `?lang=${encodeURIComponent(lang)}` : ''}`);
    const blob = new Blob([r.srt], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `subtitle-${r.lang}.srt`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch (e) { toast(e instanceof ApiErr ? e.message : '导出失败'); }
}

async function rescript(id) {
  const tone = document.getElementById('re-tone')?.value;
  toast('重写脚本中…');
  try { await POST(`/api/projects/${id}/script`, { tone }); viewProject(id); }
  catch (e) { toast(e instanceof ApiErr ? e.message : '失败'); }
}

// ---------- 放映室（浏览器语音口播 + 字幕，按分镜时长连播） ----------
const BCP47 = { zh: 'zh-CN', en: 'en-US', ja: 'ja-JP', ko: 'ko-KR', es: 'es-ES', pt: 'pt-BR', fr: 'fr-FR', de: 'de-DE', id: 'id-ID', th: 'th-TH', vi: 'vi-VN', ar: 'ar-SA', ru: 'ru-RU', it: 'it-IT', tr: 'tr-TR' };
function openPlayer(p) {
  const shots = (p.storyboard?.shots || []).filter((s) => s.video || s.image || s.onscreen);
  if (!shots.length) return toast('还没有可播放的内容');
  let i = 0, timer = null;
  overlay.innerHTML = `<div class="player">
    <img id="pl-img" alt=""><p class="cap" id="pl-cap"></p><div class="pbar" id="pl-bar"></div>
    <button class="x" data-act="closeplay">✕</button></div>`;
  const synth = window.speechSynthesis;
  const play = () => {
    if (i >= shots.length) return closePlayer();
    const s = shots[i];
    const img = document.getElementById('pl-img'); const cap = document.getElementById('pl-cap'); const bar = document.getElementById('pl-bar');
    if (img) img.src = s.video || s.image || '';
    if (cap) cap.textContent = s.onscreen || '';
    if (bar) { bar.style.transition = 'none'; bar.style.width = '0%'; requestAnimationFrame(() => { bar.style.transition = `width ${s.duration}s linear`; bar.style.width = '100%'; }); }
    if (synth && s.voiceover) { try { synth.cancel(); const u = new SpeechSynthesisUtterance(s.voiceover); u.lang = BCP47[p.lang] || p.lang; synth.speak(u); } catch { /* ignore */ } }
    timer = setTimeout(() => { i++; play(); }, (s.duration || 4) * 1000);
  };
  player = { close: () => { clearTimeout(timer); try { synth && synth.cancel(); } catch { /* */ } } };
  play();
}
function closePlayer() { if (player) player.close(); player = null; overlay.innerHTML = ''; }

// ================= 设置 =================
async function viewSettings() {
  const s = await GET('/api/settings');
  const base = location.origin;
  page.innerHTML = `
    <h1>设置</h1>
    <p class="sub">不配任何 Key 也能用本地引擎跑通全流程。配置火山方舟（或 OpenAI 兼容）后自动切换为真实生成。</p>
    <div class="card">
      <h2 style="margin-top:0">模型接入</h2>
      <label>火山方舟 API Key ${s.ark_api_key_set ? '（已配置，留空不改）' : ''}</label><input id="s-ark" placeholder="UUID 形态的 API Key">
      <div class="row">
        <div><label>Ark Base URL</label><input id="s-base" value="${esc(s.ark_base_url)}"></div>
        <div><label>对话模型</label><input id="s-mc" value="${esc(s.model_chat)}"></div>
      </div>
      <div class="row">
        <div><label>图像模型</label><input id="s-mi" value="${esc(s.model_image)}"></div>
        <div><label>视频模型</label><input id="s-mv" value="${esc(s.model_video)}"></div>
      </div>
      <label>OpenAI API Key（可选，用 gpt-image-1 出图）${s.openai_api_key_set ? '（已配置）' : ''}</label><input id="s-oai" placeholder="sk-…">
      <div style="margin-top:14px"><button data-act="savecfg">保存</button></div>
      <div class="tip">能力状态：脚本 <b>${capText(s.capabilities.script)}</b> · 图像 <b>${capText(s.capabilities.image)}</b> · 视频 <b>${capText(s.capabilities.video)}</b></div>
    </div>
    <div class="card" style="margin-top:16px">
      <h2 style="margin-top:0">Agent 接入（MCP / OpenAPI）</h2>
      <div class="kv"><span>Agent Token</span><code>${esc(s.agent_token)}</code></div>
      <div class="kv"><span>OpenAPI</span><code>${base}/api/agent/v1/openapi.json</code></div>
      <div class="kv"><span>MCP (HTTP)</span><code>${base}/api/agent/v1/mcp</code></div>
      <p class="tip" style="margin-top:10px">Claude Code 接入（stdio）：</p>
      <code style="display:block;white-space:pre-wrap;padding:10px">claude mcp add topview --env TOPVIEW_TOKEN=${esc(s.agent_token)} -- node $(pwd)/topview/mcp/server.mjs</code>
    </div>`;
}
async function saveCfg() {
  const v = (id) => document.getElementById(id)?.value?.trim();
  const body = { ark_base_url: v('s-base'), model_chat: v('s-mc'), model_image: v('s-mi'), model_video: v('s-mv') };
  if (v('s-ark')) body.ark_api_key = v('s-ark');
  if (v('s-oai')) body.openai_api_key = v('s-oai');
  try { await POST('/api/settings', body); BOOT = await bootstrap(true); toast('已保存'); viewSettings(); }
  catch (e) { toast(e instanceof ApiErr ? e.message : '保存失败'); }
}

// ================= 路由 + 事件 =================
function setNav(name) { document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('on', a.dataset.nav === name)); }
async function route() {
  closePlayer();
  if (!BOOT) BOOT = await bootstrap();
  document.getElementById('cap').innerHTML = `脚本 <b>${capText(BOOT.capabilities.script)}</b> · 图 <b>${capText(BOOT.capabilities.image)}</b> · 片 <b>${capText(BOOT.capabilities.video)}</b>`;
  const h = location.hash.slice(1) || '/';
  const m = h.match(/^\/project\/(.+)$/);
  if (m) { setNav('projects'); return viewProject(m[1]); }
  if (h.startsWith('/projects')) { setNav('projects'); return viewProjects(); }
  if (h.startsWith('/settings')) { setNav('settings'); return viewSettings(); }
  setNav('home'); return viewHome();
}

document.addEventListener('click', (e) => {
  const t = e.target.closest('[data-act]'); if (!t) return;
  const act = t.dataset.act, v = t.dataset.v;
  const pid = window.__p?.id;
  if (act === 'mode') { readForm(); form.mode = v; viewHome(); }
  else if (act === 'tone') { readForm(); form.tone = v; viewHome(); }
  else if (act === 'gen') doGenerate();
  else if (act === 'media') genMedia(pid);
  else if (act === 'play') openPlayer(window.__p);
  else if (act === 'closeplay') closePlayer();
  else if (act === 'dub') { e.preventDefault(); POST(`/api/projects/${pid}/dubbing`).then((r) => toast(r.note, 4000)).catch(() => toast('失败')); }
  else if (act === 'rescript') rescript(pid);
  else if (act === 'langchip') t.classList.toggle('on');
  else if (act === 'localize') doLocalize(pid);
  else if (act === 'srt') { e.preventDefault(); downloadSrt(pid, v); }
  else if (act === 'del') { if (confirm('删除该项目？')) DEL(`/api/projects/${pid}`).then(() => { location.hash = '#/projects'; }); }
  else if (act === 'savecfg') saveCfg();
});

window.addEventListener('hashchange', route);
route();
