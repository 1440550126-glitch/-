// 用户主页 + 我的
import { GET, POST, DEL } from '../api.js';
import { h, toast, avatarEl, aiBadge, memberBadge, emptyState, sheet } from '../ui.js';
import { store, refreshMe, avatarMeta } from '../store.js';
import { nav } from '../router.js';
import { postCardEl } from './feed.js';

export async function renderUser(page, params) {
  let data;
  try { data = await GET(`/api/users/${params.id}`); }
  catch (e) { page.append(emptyState(e.message)); return; }
  const { user, stats, viewer } = data;

  const followBtn = h('button', { class: `btn mini ${viewer?.following ? 'ghost' : ''}` }, viewer?.following ? '已关注' : '+ 关注');
  followBtn.addEventListener('click', async () => {
    try {
      const on = followBtn.textContent === '+ 关注';
      await (on ? POST(`/api/users/${user.id}/follow`) : DEL(`/api/users/${user.id}/follow`));
      followBtn.textContent = on ? '已关注' : '+ 关注';
      followBtn.classList.toggle('ghost', on);
    } catch (e) { toast(e.message, 'warn'); }
  });

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', { class: 'spacer' })
    ),
    h('div', { class: 'profile-head' },
      avatarEl(user, 64),
      h('div', { style: { flex: 1 } },
        h('div', { style: { fontWeight: 800, fontSize: '18px', display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' } },
          user.nickname, user.is_ai ? aiBadge(user.ai_label || 'AI 账号') : null, user.is_member ? memberBadge() : null),
        h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', marginTop: '4px' } }, user.bio || '这个人还没写简介')
      ),
      viewer && !viewer.is_me ? followBtn : null
    ),
    h('div', { class: 'stat-row' },
      h('div', { class: 'glass stat' }, h('div', { class: 'v' }, stats.posts), h('div', { class: 'k' }, '文案')),
      h('div', { class: 'glass stat' }, h('div', { class: 'v' }, user.follower_count), h('div', { class: 'k' }, '粉丝')),
      h('div', { class: 'glass stat' }, h('div', { class: 'v' }, stats.likes_received), h('div', { class: 'k' }, '获赞'))
    )
  );

  const list = h('div', {});
  page.append(list);
  const { items } = await GET(`/api/users/${user.id}/posts`).catch(() => ({ items: [] }));
  if (!items.length) list.append(emptyState('还没有发布过文案'));
  else for (const p of items) list.append(postCardEl(p));
}

export async function renderMe(page) {
  await refreshMe();
  const me = store.me;
  if (!me) { nav('/login'); return; }

  const tabBtns = h('div', { class: 'chip-row' });
  const list = h('div', {});
  let tab = 'posts';

  async function loadList() {
    list.innerHTML = '';
    const url = tab === 'posts' ? `/api/users/${me.id}/posts` : '/api/me/collects';
    const { items } = await GET(url).catch(() => ({ items: [] }));
    if (!items.length) list.append(emptyState(tab === 'posts' ? '还没有发布过文案' : '还没有收藏'));
    else for (const p of items) list.append(postCardEl(p, { onRemoved: loadList }));
  }
  const renderTabs = () => {
    tabBtns.innerHTML = '';
    for (const [id, name] of [['posts', '我的文案'], ['collects', '我的收藏']]) {
      tabBtns.append(h('button', { class: `chip ${tab === id ? 'active' : ''}`, onclick: () => { tab = id; renderTabs(); loadList(); } }, name));
    }
  };
  renderTabs();

  page.append(
    h('div', { class: 'profile-head' },
      avatarEl(me, 64),
      h('div', { style: { flex: 1 } },
        h('div', { style: { fontWeight: 800, fontSize: '18px', display: 'flex', gap: '6px', alignItems: 'center' } },
          me.nickname, me.is_member ? memberBadge() : null),
        h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', marginTop: '4px' } },
          me.is_guest ? '游客账号 · 注册后可跨设备登录' : `@${me.username || ''}`)
      ),
      h('button', { class: 'icon-btn', onclick: () => editProfileSheet() }, '✏️')
    ),
    h('div', { class: 'stat-row' },
      h('div', { class: 'glass stat', onclick: () => nav('/member') }, h('div', { class: 'v' }, me.is_member ? '已开通' : '未开通'), h('div', { class: 'k' }, '会员')),
      h('div', { class: 'glass stat', onclick: () => nav('/member') }, h('div', { class: 'v' }, me.credits), h('div', { class: 'k' }, '星尘额度')),
      h('div', { class: 'glass stat' }, h('div', { class: 'v' }, me.following_count), h('div', { class: 'k' }, '关注'))
    ),
    h('button', { class: 'glass cc-entry', style: { width: '100%' }, onclick: () => nav('/chat') },
      h('div', { class: 'cc-entry-ic' }, '💛'),
      h('div', { style: { flex: 1, textAlign: 'left' } },
        h('div', { style: { fontWeight: 700, fontSize: '14.5px' } }, '句灵陪你说说话'),
        h('div', { style: { fontSize: '11.5px', color: 'var(--ink-2)', marginTop: '2px' } }, '心里有事？AI 陪伴温柔倾听，缓解压力')),
      h('span', { class: 'mi-arrow' }, '›')
    ),
    h('div', { class: 'glass menu-list', style: { marginBottom: '14px' } },
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/member') }, '👑 会员中心', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => ordersSheet() }, '🧾 我的订单', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/settings') }, '⚙️ 设置与隐私', h('span', { class: 'mi-arrow' }, '›'))
    ),
    tabBtns, list
  );
  loadList();

  function editProfileSheet() {
    sheet((box, close) => {
      const nickname = h('input', { class: 'input', value: me.nickname, maxlength: 12 });
      const bio = h('input', { class: 'input', value: me.bio || '', maxlength: 60, placeholder: '一句话介绍自己' });
      let chosen = me.avatar;
      const grid = h('div', { class: 'avatar-pick' });
      const renderGrid = () => {
        grid.innerHTML = '';
        for (const a of store.boot?.avatars || []) {
          grid.append(h('button', {
            class: `ap ${chosen === a.id ? 'sel' : ''}`,
            onclick: () => { chosen = a.id; renderGrid(); }
          }, avatarEl({ avatar: a.id }, 42)));
        }
      };
      renderGrid();
      box.append(
        h('h3', {}, '编辑资料'),
        h('div', { class: 'field' }, h('label', {}, '昵称'), nickname),
        h('div', { class: 'field' }, h('label', {}, '简介'), bio),
        h('div', { class: 'field' }, h('label', {}, `头像 · ${avatarMeta(chosen).name}`), grid),
        h('button', {
          class: 'btn block',
          onclick: async () => {
            try {
              const { PATCH } = await import('../api.js');
              await PATCH('/api/me', { nickname: nickname.value.trim(), bio: bio.value.trim(), avatar: chosen });
              await refreshMe();
              toast('已保存');
              close();
              nav('/me'); location.reload();
            } catch (e) { toast(e.message, 'warn'); }
          }
        }, '保存')
      );
    });
  }

  async function ordersSheet() {
    const { items } = await GET('/api/me/orders').catch(() => ({ items: [] }));
    sheet((box) => {
      box.append(h('h3', {}, '我的订单'));
      if (!items.length) box.append(emptyState('还没有订单'));
      for (const o of items) {
        box.append(h('div', { class: 'glass card', style: { padding: '12px 14px' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: '13.5px', fontWeight: 600 } },
            h('span', {}, o.title),
            h('span', { style: { color: o.status === 'paid' ? 'var(--mint)' : 'var(--ink-3)' } }, o.status === 'paid' ? '已支付' : o.status === 'pending' ? '待支付' : '已取消')),
          h('div', { style: { fontSize: '11px', color: 'var(--ink-3)', marginTop: '4px' } },
            `¥${(o.amount_fen / 100).toFixed(2)} · ${new Date(o.created_at).toLocaleString()} · ${o.id}`)
        ));
      }
    });
  }
}
