// LingCraft · 一句话生成：输入需求 → 大模型产出单文件 HTML → 沙箱 iframe 即时预览 → 改 / 下载 / 分享。
// 安全：生成物只经 iframe srcdoc 渲染（无 same-origin 的 sandbox = opaque origin）+ 注入严格 CSP
// （default-src none / connect-src none）。绝不把任何凭据放进 URL——否则沙箱代码可读自身 URL 后外泄。
import { GET, POST, DEL } from './api.js';

// 注入到 srcdoc 的 CSP：断网(connect-src none)、禁一切外联，脚本/样式内联可跑。sandbox 属性另管来源隔离。
const PREVIEW_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; media-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'";
function sandboxed(html) {
  const meta = `<meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}">`;
  const s = String(html || '');
  if (/<head[^>]*>/i.test(s)) return s.replace(/<head[^>]*>/i, (m) => m + meta);      // 作为 <head> 首个节点，先于任何脚本
  if (/<html[^>]*>/i.test(s)) return s.replace(/<html[^>]*>/i, (m) => m + '<head>' + meta + '</head>');
  return meta + s;
}

// ---------------- DOM 小工具 ----------------
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'value') el.value = v;
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) { if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid))); }
  return el;
}
const $app = () => document.getElementById('app');
function mount(node) { const a = $app(); a.innerHTML = ''; a.append(node); window.scrollTo(0, 0); }
function toast(msg, warn) {
  const t = h('div', { class: 'lc-toast' + (warn ? ' warn' : '') }, msg);
  document.body.append(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2400);
}
const nav = (hash) => { location.hash = hash; };
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtTime = (ts) => { const d = new Date(ts); return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

function header() {
  return h('header', { class: 'lc-top' },
    h('div', { class: 'lc-brand', onclick: () => nav('#/') },
      h('img', { class: 'lc-logo', src: '/craft/logo.svg', alt: 'LingCraft' }),
      h('div', {}, h('b', {}, 'LingCraft'), h('small', {}, '一句话 · 立得效果'))),
    h('nav', { class: 'lc-nav' },
      h('a', { href: '/lingzhen', target: '_blank', rel: 'noopener' }, 'AI 团队 ↗')));
}
const shell = (...c) => h('div', { class: 'lc-shell' }, header(), h('main', {}, ...c));
const spinner = (label) => h('div', { class: 'lc-spin' }, h('div', { class: 'lc-spin-d' }), label || '加载中…');

// ---------------- 首页：输入 + 示例 + 我的作品 ----------------
const EXAMPLES = [
  '做一个贪吃蛇小游戏，霓虹风格，手机也能玩',
  '做一个 2048 小游戏，带动画和最高分记录',
  '做一个打字练习小游戏，倒计时60秒统计手速',
  '一个粒子随鼠标汇聚成文字「LingMirror」的炫酷效果页',
  '一个新年倒计时页面，带烟花动画',
  '一个产品落地页：AI 视频生成工具，深色科技风，含定价区'
];

async function renderHome() {
  mount(shell(spinner()));
  let mine = { items: [], quota: { used: 0, limit: 8 } };
  try { mine = await GET('/api/craft/mine'); } catch { /* 首次未登录，自动游客后为空 */ }

  const ta = h('textarea', { class: 'lc-ta', rows: 3, placeholder: '一句话描述你想要的游戏 / 页面 / 效果，例如：做一个贪吃蛇小游戏，霓虹风格' });
  const btn = h('button', { class: 'lc-btn xl' }, '⚡ 生成');
  const phases = ['正在理解你的想法…', '正在写代码…', '正在排版与调样式…', '快好了，正在打包预览…'];
  btn.addEventListener('click', async () => {
    const prompt = ta.value.trim();
    if (!prompt) { ta.focus(); toast('先描述一下你想要什么', true); return; }
    btn.disabled = true; ta.disabled = true;
    let i = 0; btn.textContent = phases[0];
    const timer = setInterval(() => { btn.textContent = phases[Math.min(++i, phases.length - 1)]; }, 2600);
    try { const { artifact } = await POST('/api/craft/generate', { prompt }); nav(`#/a/${artifact.id}`); }
    catch (e) { toast(e.message, true); btn.disabled = false; ta.disabled = false; btn.textContent = '⚡ 生成'; }
    finally { clearInterval(timer); }
  });

  const chips = h('div', { class: 'lc-chips' }, EXAMPLES.map((x) =>
    h('button', { class: 'lc-chip', onclick: () => { ta.value = x; ta.focus(); } }, x)));

  const works = mine.items.length
    ? h('div', { class: 'lc-grid' }, mine.items.map((a) => h('div', { class: 'lc-card', onclick: () => nav(`#/a/${a.id}`) },
        h('b', {}, a.title || '未命名'),
        h('p', {}, a.prompt),
        h('div', { class: 'lc-card-f' },
          h('span', { class: a.by_llm ? 'lc-tag llm' : 'lc-tag' }, a.by_llm ? '大模型' : '本地模板'),
          a.share_id ? h('span', { class: 'lc-tag pub' }, '已分享') : null,
          h('small', {}, fmtTime(a.updated_at))))))
    : h('p', { class: 'lc-hint center' }, '还没有作品——上面输入一句话，30 秒后你就有第一个能玩的了。');

  mount(shell(
    h('section', { class: 'lc-hero' },
      h('h1', {}, '一句话，生成', h('span', { class: 'lc-grad' }, '能玩的作品')),
      h('p', {}, '小游戏 · 交互页面 · 视觉效果 —— 生成即预览，改一句再生成，满意直接下载/分享。')),
    h('div', { class: 'lc-box' }, ta, btn,
      h('div', { class: 'lc-quota' }, `今日已用 ${mine.quota.used} / ${mine.quota.limit >= 1e6 ? '∞' : mine.quota.limit}`)),
    h('div', { class: 'lc-sec' }, '试试这些'), chips,
    h('div', { class: 'lc-sec' }, `我的作品（${mine.items.length}）`), works));
}

// ---------------- 作品页：预览 / 代码 / 修改 / 下载 / 分享 ----------------
async function renderArtifact(id) {
  mount(shell(spinner()));
  let a;
  try { a = (await GET(`/api/craft/${id}`)).artifact; }
  catch (e) { mount(shell(h('p', { class: 'lc-hint center' }, '作品不存在或无权访问：' + e.message))); return; }

  let tab = 'preview';
  const frameWrap = h('div', { class: 'lc-frame-wrap' });
  const codeWrap = h('div', { class: 'lc-code', hidden: true });
  function loadFrame() {
    frameWrap.innerHTML = '';
    // 用 srcdoc 直接喂已鉴权取回的 HTML（凭据只走 Authorization 头，绝不进 URL）；
    // sandbox 无 allow-same-origin = opaque origin，srcdoc 内代码读不到主站 token，也过不了注入的 CSP。
    frameWrap.append(h('iframe', {
      class: 'lc-frame', sandbox: 'allow-scripts allow-pointer-lock',
      srcdoc: sandboxed(a.html)
    }));
  }
  function loadCode() {
    codeWrap.innerHTML = '';
    codeWrap.append(
      h('button', { class: 'lc-btn sm ghost lc-copy', onclick: () => navigator.clipboard?.writeText(a.html).then(() => toast('代码已复制')) }, '复制代码'),
      h('pre', {}, h('code', {}, a.html)));
  }
  const tabs = h('div', { class: 'lc-tabs' });
  function paintTabs() {
    tabs.innerHTML = '';
    for (const [k, label] of [['preview', '▶ 预览'], ['code', '</> 代码']]) {
      tabs.append(h('button', { class: 'lc-tab' + (tab === k ? ' on' : ''), onclick: () => { tab = k; frameWrap.hidden = k !== 'preview'; codeWrap.hidden = k !== 'code'; paintTabs(); } }, label));
    }
  }
  paintTabs(); loadFrame(); loadCode();

  const rIn = h('input', { class: 'lc-in', placeholder: '继续修改：例如「把配色改成红色系，再加个暂停按钮」' });
  const rBtn = h('button', { class: 'lc-btn' }, '改一版');
  rBtn.addEventListener('click', async () => {
    const instruction = rIn.value.trim();
    if (!instruction) { rIn.focus(); return; }
    rBtn.disabled = true; rBtn.textContent = '修改中…';
    try {
      const r = await POST(`/api/craft/${id}/revise`, { instruction });
      a = { ...a, ...(r.artifact) };
      a.html = (await GET(`/api/craft/${id}`)).artifact.html;
      loadFrame(); loadCode(); rIn.value = ''; toast('已更新，看看效果');
    } catch (e) { toast(e.message, true); }
    rBtn.disabled = false; rBtn.textContent = '改一版';
  });
  rIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') rBtn.click(); });

  function download() {
    const blob = new Blob([a.html], { type: 'text/html' });
    const link = h('a', { href: URL.createObjectURL(blob), download: (a.title || 'craft') + '.html' });
    document.body.append(link); link.click(); link.remove();
  }
  async function share() {
    try {
      const { share_id } = await POST(`/api/craft/${id}/share`);
      const url = `${location.origin}/api/public/craft/${share_id}`;
      await navigator.clipboard?.writeText(url).catch(() => {});
      toast('分享链接已复制，打开即玩：' + url);
    } catch (e) { toast(e.message, true); }
  }
  async function del() {
    if (!confirm('删除这个作品？')) return;
    try { await DEL(`/api/craft/${id}`); toast('已删除'); nav('#/'); } catch (e) { toast(e.message, true); }
  }

  mount(shell(
    h('button', { class: 'lc-back', onclick: () => nav('#/') }, '‹ 我的作品'),
    h('div', { class: 'lc-work-head' },
      h('div', {}, h('h2', {}, a.title || '未命名'), h('small', { class: 'lc-hint' }, a.by_llm ? '大模型生成' : '本地模板生成（接入大模型后可深度定制）')),
      h('div', { class: 'lc-acts' },
        h('button', { class: 'lc-btn sm ghost', onclick: download }, '⬇ 下载 HTML'),
        h('button', { class: 'lc-btn sm ghost', onclick: share }, '🔗 分享'),
        h('button', { class: 'lc-btn sm ghost danger', onclick: del }, '删除'))),
    tabs, frameWrap, codeWrap,
    h('div', { class: 'lc-revise' }, rIn, rBtn)));
}

// ---------------- 路由 ----------------
function route() {
  const hash = location.hash || '#/';
  document.title = 'LingCraft · 一句话生成';
  const m = hash.match(/^#\/a\/(\d+)/);
  if (m) return renderArtifact(m[1]);
  return renderHome();
}
window.addEventListener('hashchange', route);
route();
