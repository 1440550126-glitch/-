// AI句灵 入口：启动、底部导航、路由注册、流体背景
import { h } from './ui.js';
import { route, startRouter, nav } from './router.js';
import { store, loadBoot, refreshMe } from './store.js';
import { getToken } from './api.js';
import { initFluid } from './fx/fluid.js';

import { renderLogin } from './pages/login.js';
import { renderFeed } from './pages/feed.js';
import { renderCompose } from './pages/compose.js';
import { renderPost } from './pages/post.js';
import { renderUser, renderMe } from './pages/user.js';
import { renderGames } from './pages/games.js';
import { renderRoom } from './pages/room.js';
import { renderShop } from './pages/shop.js';
import { renderMember } from './pages/member.js';
import { renderSettings, renderBlocks, renderAbout } from './pages/settings.js';
import { renderNotify } from './pages/notify.js';
import { renderChat } from './pages/chat.js';
import { sse } from './api.js';

const fluid = initFluid(document.getElementById('fluid-bg'));
export const setBgDark = (v) => fluid.setDark(v);

function buildNav() {
  const el = document.getElementById('nav');
  el.innerHTML = '';
  const items = [
    ['/feed', '✨', '广场'],
    ['/games', '🎲', '桌游'],
    ['compose', '+', ''],
    ['/shop', '🛍', '商城'],
    ['/me', '🐾', '我的']
  ];
  for (const [path, icon, label] of items) {
    if (path === 'compose') {
      el.append(h('button', { class: 'nav-fab', onclick: () => nav('/compose') }, '✎'));
    } else {
      el.append(h('button', {
        class: 'nav-item', 'data-path': path, onclick: () => nav(path)
      }, h('span', { class: 'ni' }, icon), h('span', {}, label)));
    }
  }
}

route('/login', renderLogin, { hideNav: true });
route('/feed', renderFeed);
route('/compose', renderCompose, { hideNav: true });
route('/post/:id', renderPost, { hideNav: true });
route('/user/:id', renderUser, { hideNav: true });
route('/me', renderMe);
route('/games', renderGames);
route('/room/:id', renderRoom, { hideNav: true });
route('/shop', renderShop);
route('/member', renderMember, { hideNav: true });
route('/settings', renderSettings, { hideNav: true });
route('/blocks', renderBlocks, { hideNav: true });
route('/about/:doc', renderAbout, { hideNav: true });
route('/notify', renderNotify, { hideNav: true });
route('/chat', renderChat, { hideNav: true });

(async () => {
  buildNav();
  try { await loadBoot(); } catch { /* 启动常量失败不致命 */ }
  if (getToken()) await refreshMe();
  if (!store.me && location.hash !== '#/login') {
    location.replace('#/login');
  }
  startRouter();
  // 个人实时通道：在线时小铃铛即时更新
  if (store.me) {
    sse('/api/inbox/events', {
      notify: () => {
        store.me.unread_notifications = (store.me.unread_notifications || 0) + 1;
        const badge = document.getElementById('bell-badge');
        if (badge) badge.textContent = store.me.unread_notifications;
        else document.getElementById('bell-btn')?.append(
          Object.assign(document.createElement('span'), { id: 'bell-badge', className: 'bell-badge', textContent: store.me.unread_notifications })
        );
      }
    });
  }
})();
