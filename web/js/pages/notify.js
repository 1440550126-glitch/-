// 消息通知中心
import { GET, POST } from '../api.js';
import { h, avatarEl, timeAgo, emptyState, aiBadge } from '../ui.js';
import { store } from '../store.js';
import { nav } from '../router.js';

const KIND_META = {
  like: ['💗', '赞了你的文案'],
  comment: ['💬', '评论了你的文案'],
  reply: ['↩️', '回复了你'],
  follow: ['➕', '关注了你'],
  ai: ['🤖', '评论了你的文案'],
  system: ['📢', '系统通知']
};

export async function renderNotify(page) {
  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '消息')),
      h('div', { class: 'spacer' })
    )
  );
  const list = h('div', { class: 'stagger' });
  page.append(list);

  const { items } = await GET('/api/notifications').catch(() => ({ items: [] }));
  POST('/api/notifications/read').then(() => {
    if (store.me) store.me.unread_notifications = 0;
    document.getElementById('bell-badge')?.remove();
  }).catch(() => {});

  if (!items.length) {
    list.append(emptyState('还没有消息', '收到的赞和评论都会出现在这里'));
    return;
  }
  for (const n of items) {
    const [icon, label] = KIND_META[n.kind] || ['🔔', ''];
    list.append(h('div', {
      class: 'glass menu-item', style: { marginBottom: '10px', cursor: n.post_id ? 'pointer' : 'default', opacity: n.read ? 0.75 : 1 },
      onclick: () => { if (n.post_id) nav(`/post/${n.post_id}`); }
    },
      n.actor ? avatarEl(n.actor, 38) : h('div', { style: { fontSize: '24px', width: '38px', textAlign: 'center' } }, icon),
      h('div', { style: { flex: 1, minWidth: 0 } },
        h('div', { style: { fontSize: '13px', fontWeight: 600, display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' } },
          n.actor ? n.actor.nickname : '句灵小管家',
          n.actor?.is_ai || n.kind === 'ai' ? aiBadge('AI') : null,
          h('span', { style: { color: 'var(--ink-3)', fontWeight: 400 } }, label)),
        n.content ? h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', marginTop: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, n.content) : null,
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginTop: '3px' } }, timeAgo(n.created_at))),
      !n.read ? h('span', { style: { width: '8px', height: '8px', borderRadius: '50%', background: 'var(--brand-2)', flexShrink: 0 } }) : null
    ));
  }
}
