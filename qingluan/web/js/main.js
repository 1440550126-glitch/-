// 青鸾 · 前端入口：Hash 路由 + 应用壳
import { GET, bootstrap } from './api.js';
import { h, icon, LOGO_SVG, toast } from './ui.js';
import { renderHome } from './pages/home.js';
import { renderAssets } from './pages/assets.js';
import { renderProject } from './pages/project.js';
import { renderCanvas } from './pages/canvas.js';
import { renderAgent } from './pages/agent.js';
import { renderSettings } from './pages/settings.js';

const routes = [];
let cleanup = null;
export const nav = (path) => { location.hash = path; };

function route(pattern, render, opts = {}) {
  const keys = [];
  const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, (m) => { keys.push(m.slice(1)); return '([^/]+)'; }) + '$');
  routes.push({ regex, keys, render, opts });
}

route('/home', renderHome, { nav: '/home' });
route('/assets', renderAssets, { nav: '/assets' });
route('/assets/:tab', renderAssets, { nav: '/assets' });
route('/project/:id', renderProject, { nav: '/home' });
route('/canvas/:id', renderCanvas, { full: true });
route('/agent', renderAgent, { nav: '/agent' });
route('/settings', renderSettings, { nav: '/settings' });

async function dispatch() {
  const path = location.hash.replace(/^#/, '') || '/home';
  const page = document.getElementById('page');
  for (const r of routes) {
    const m = path.match(r.regex);
    if (!m) continue;
    const params = {};
    r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });
    if (typeof cleanup === 'function') { try { cleanup(); } catch { /* noop */ } }
    cleanup = null;
    document.getElementById('app').classList.toggle('full', !!r.opts.full);
    page.innerHTML = '';
    page.scrollTop = 0;
    highlight(r.opts.nav || '');
    try {
      cleanup = await r.render(page, params);
      if (!r.opts.full) refreshSidebarProjects();
    } catch (e) {
      console.error(e);
      page.append(h('div', { class: 'wrap' }, h('div', { class: 'empty' }, h('p', {}, '页面打开失败：' + (e.message || '')))));
    }
    return;
  }
  nav('/home');
}

function highlight(path) {
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.toggle('active', el.dataset.path === path));
}

// ---- 侧边栏 ----
async function renderSidebar() {
  const side = document.getElementById('sidebar');
  const boot = await bootstrap().catch(() => null);
  const item = (label, ic, path) =>
    h('button', { class: 'nav-item', dataset: { path }, onclick: () => nav(path) }, h('span', { html: icon(ic) }), label);
  side.append(
    h('div', { class: 'brand' },
      h('span', { class: 'logo', html: LOGO_SVG }),
      h('div', {}, h('b', {}, '青鸾'), h('small', {}, 'AI 短剧创作工坊'))),
    item('创作首页', 'home', '/home'),
    item('资产库', 'folder', '/assets'),
    item('Agent 接入', 'robot', '/agent'),
    item('设置', 'settings', '/settings'),
    h('div', { class: 'side-sec' }, h('span', {}, '创作历史'), h('a', { href: '#/home' }, '全部')),
    h('div', { id: 'side-projects' }),
    h('div', { class: 'side-foot' },
      h('span', { class: 'pill teal', id: 'side-provider', onclick: () => nav('/settings'), title: '模型接入状态' },
        boot?.ark?.enabled ? '火山方舟 · 已接入' : '本地引擎 · 零成本'),
      h('span', { class: 'pill', id: 'side-cost', onclick: () => nav('/settings'), title: '累计成本' },
        `累计成本 ¥${boot?.stats?.cost_total_yuan ?? '0'}`))
  );
  refreshSidebarProjects();
}

export async function refreshSidebarProjects() {
  const box = document.getElementById('side-projects');
  if (!box) return;
  try {
    const projects = await GET('/api/projects');
    box.innerHTML = '';
    if (!projects.length) box.append(h('div', { class: 'side-proj' }, h('i', { style: { color: 'var(--ink3)' } }, '还没有项目')));
    for (const p of projects.slice(0, 7)) {
      box.append(h('div', { class: 'side-proj', onclick: () => nav(`/project/${p.id}`) },
        h('span', { class: `dot ${p.status}` }), h('i', {}, p.title)));
    }
    const boot = await bootstrap(true);
    const cost = document.getElementById('side-cost');
    if (cost) cost.textContent = `累计成本 ¥${boot.stats.cost_total_yuan}`;
    const prov = document.getElementById('side-provider');
    if (prov) prov.textContent = boot.ark.enabled ? '火山方舟 · 已接入' : '本地引擎 · 零成本';
  } catch { /* 服务暂不可用 */ }
}

window.addEventListener('hashchange', dispatch);
renderSidebar().then(dispatch).catch((e) => { console.error(e); toast('初始化失败：' + e.message, 'err'); dispatch(); });
