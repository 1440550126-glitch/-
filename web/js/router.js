// Hash 路由：支持 :参数、页面清理函数、底部导航联动
const routes = [];
let cleanup = null;

export function route(pattern, render, opts = {}) {
  const keys = [];
  const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, (m) => { keys.push(m.slice(1)); return '([^/]+)'; }) + '$');
  routes.push({ regex, keys, render, opts });
}

export const nav = (path) => { location.hash = path; };

export async function dispatch() {
  const path = location.hash.replace(/^#/, '') || '/feed';
  const page = document.getElementById('page');
  const navBar = document.getElementById('nav');

  for (const r of routes) {
    const m = path.match(r.regex);
    if (!m) continue;
    const params = {};
    r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });

    if (typeof cleanup === 'function') { try { cleanup(); } catch { /* noop */ } }
    cleanup = null;
    page.innerHTML = '';
    page.scrollTop = 0;
    page.classList.remove('page-enter');
    void page.offsetWidth;             // 重新触发入场动画
    page.classList.add('page-enter');
    page.classList.toggle('no-nav', !!r.opts.hideNav);
    navBar.hidden = !!r.opts.hideNav;
    highlightNav(path);
    try {
      cleanup = await r.render(page, params);
    } catch (e) {
      console.error(e);
      page.innerHTML = '';
      page.append(document.createTextNode('页面打开失败：' + (e.message || '')));
    }
    return;
  }
  nav('/feed');
}

function highlightNav(path) {
  document.querySelectorAll('.nav-item').forEach((el) => {
    el.classList.toggle('active', path.startsWith(el.dataset.path || '###'));
  });
}

export function startRouter() {
  window.addEventListener('hashchange', dispatch);
  dispatch();
}
