// 句灵广场：推荐 / 最新 / 关注 / 热门榜 + 今日话题 + 长按文字变动画
import { GET, POST, DEL } from '../api.js';
import { h, toast, avatarEl, aiBadge, memberBadge, previewCardEl, timeAgo, longPress, burst, emptyState, sheet } from '../ui.js';
import { store } from '../store.js';
import { nav } from '../router.js';
import { openAnimPlayer } from '../anim/player.js';

export function postCardEl(post, { onRemoved } = {}) {
  const author = post.author || {};
  const card = h('div', { class: 'glass post-card' });

  const head = h('div', { class: 'post-head' },
    h('div', { style: { cursor: 'pointer' }, onclick: () => nav(`/user/${author.id}`) }, avatarEl(author, 40)),
    h('div', {},
      h('div', { class: 'name' },
        author.nickname,
        author.is_ai ? aiBadge('AI 暖场官') : null,
        author.is_member && !author.is_ai ? memberBadge() : null
      ),
      h('div', { class: 'time' }, timeAgo(post.created_at), post.status === 'pending' ? ' · 审核中' : '')
    ),
    h('button', { class: 'more', onclick: () => moreSheet(post, onRemoved) }, '···')
  );

  const preview = previewCardEl(post);
  longPress(preview, () => openAnimPlayer(post));
  preview.addEventListener('click', () => nav(`/post/${post.id}`));

  const v = post.viewer || {};
  const likeBtn = h('button', { class: `pa-btn ${v.liked ? 'on' : ''}` }, v.liked ? '💗' : '🤍', h('span', {}, post.like_count || ''));
  likeBtn.addEventListener('click', async () => {
    try {
      const on = !likeBtn.classList.contains('on');
      const r = on ? await POST(`/api/posts/${post.id}/like`) : await DEL(`/api/posts/${post.id}/like`);
      likeBtn.classList.toggle('on', on);
      likeBtn.firstChild.textContent = on ? '💗' : '🤍';
      likeBtn.lastChild.textContent = r.like_count || '';
      if (on) burst(likeBtn);
    } catch (e) { toast(e.message, 'warn'); }
  });

  const colBtn = h('button', { class: `pa-btn ${v.collected ? 'on-c' : ''}` }, v.collected ? '⭐' : '☆', h('span', {}, post.collect_count || ''));
  colBtn.addEventListener('click', async () => {
    try {
      const on = !colBtn.classList.contains('on-c');
      const r = on ? await POST(`/api/posts/${post.id}/collect`) : await DEL(`/api/posts/${post.id}/collect`);
      colBtn.classList.toggle('on-c', on);
      colBtn.firstChild.textContent = on ? '⭐' : '☆';
      colBtn.lastChild.textContent = r.collect_count || '';
      if (on) burst(colBtn, '#f5b84c');
    } catch (e) { toast(e.message, 'warn'); }
  });

  const actions = h('div', { class: 'post-actions' },
    likeBtn,
    h('button', { class: 'pa-btn', onclick: () => nav(`/post/${post.id}`) }, '💬', h('span', {}, post.comment_count || '')),
    colBtn,
    h('button', {
      class: 'pa-btn', onclick: async () => {
        try {
          const r = await POST(`/api/posts/${post.id}/share`);
          const text = `${r.share_text} ${location.origin}${r.share_url}`;
          await navigator.clipboard?.writeText(text).catch(() => {});
          toast('分享文案已复制 📋');
        } catch (e) { toast(e.message, 'warn'); }
      }
    }, '↗', h('span', {}, post.share_count || '')),
    h('div', { style: { flex: 1 } }),
    post.ai_like_count ? h('span', { style: { fontSize: '10px', color: 'var(--ink-3)' } }, `小句灵赞过`) : null,
    post.play_count ? h('span', { style: { fontSize: '10px', color: 'var(--ink-3)', marginLeft: '8px' } }, `▶ ${post.play_count}`) : null
  );

  card.append(head);
  if (post.rec_reason) card.append(h('div', { class: 'rec-reason' }, '✨ ', post.rec_reason));
  card.append(preview, actions);
  return card;
}

function moreSheet(post, onRemoved) {
  sheet((box, close) => {
    box.append(h('h3', {}, '更多操作'));
    if (post.viewer?.is_author) {
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '10px', color: 'var(--danger)' },
        onclick: async () => {
          close();
          try { await DEL(`/api/posts/${post.id}`); toast('已删除'); onRemoved?.(); } catch (e) { toast(e.message, 'warn'); }
        }
      }, '🗑 删除这条文案'));
    } else {
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '10px' },
        onclick: async () => {
          close();
          try { await POST(`/api/posts/${post.id}/feedback`, { kind: 'dismiss' }); toast('好的，会少推这类内容～'); onRemoved?.(); }
          catch (e) { toast(e.message, 'warn'); }
        }
      }, '🙈 不感兴趣（少推这类）'));
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '10px' },
        onclick: () => { close(); reportSheet('post', post.id); }
      }, '🚨 举报这条内容'));
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '10px' },
        onclick: async () => {
          close();
          try { await POST(`/api/users/${post.author.id}/block`); toast('已拉黑，将不再看到 TA 的内容'); onRemoved?.(); } catch (e) { toast(e.message, 'warn'); }
        }
      }, '🙈 拉黑作者'));
    }
    box.append(h('button', { class: 'btn block ghost', onclick: close }, '取消'));
  });
}

export function reportSheet(targetType, targetId) {
  sheet((box, close) => {
    box.append(h('h3', {}, '举报原因'));
    const reasons = store.boot?.report_reasons || ['其他'];
    for (const r of reasons) {
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '8px' },
        onclick: async () => {
          close();
          try {
            const res = await POST('/api/reports', { target_type: targetType, target_id: targetId, reason: r });
            toast(res.message || '已收到举报');
          } catch (e) { toast(e.message, 'warn'); }
        }
      }, r));
    }
  });
}

export async function renderFeed(page) {
  let tab = 'rec';
  let cursor = null;
  let loading = false;

  const list = h('div', {});
  const topicSlot = h('div', {});
  const tasteSlot = h('div', {});

  // 「越来越懂你」：仅推荐页展示，画像积累够了才出现，让个性化被用户感知到
  async function loadTaste() {
    tasteSlot.innerHTML = '';
    if (tab !== 'rec') return;
    try {
      const t = await GET('/api/me/taste');
      if (!t.enough) return;
      const tags = [...(t.emotions || []), ...(t.authors || [])].slice(0, 4);
      if (!tags.length) return;
      tasteSlot.append(h('div', { class: 'glass taste-banner' },
        h('span', { class: 'tb-ic' }, '🪄'),
        h('div', { style: { flex: 1 } },
          h('div', { class: 'tb-t' }, '句灵越来越懂你'),
          h('div', { class: 'tb-tags' }, ...tags.map((x) => h('span', { class: 'taste-tag' }, x))))
      ));
    } catch { /* 画像失败不影响信息流 */ }
  }

  const tabs = [['rec', '推荐'], ['new', '最新'], ['follow', '关注'], ['hot', '热门榜']];
  const chipRow = h('div', { class: 'chip-row' });
  const renderChips = () => {
    chipRow.innerHTML = '';
    for (const [id, name] of tabs) {
      chipRow.append(h('button', {
        class: `chip ${tab === id ? 'active' : ''}`,
        onclick: () => { tab = id; cursor = null; list.innerHTML = ''; renderChips(); loadTaste(); loadMore(true); }
      }, name));
    }
  };
  renderChips();

  page.append(
    h('div', { class: 'topbar' },
      h('div', {}, h('h1', {}, 'AI句灵'), h('div', { class: 'sub' }, '让每一句话活过来')),
      h('div', { class: 'spacer' }),
      h('button', { class: 'icon-btn', id: 'bell-btn', style: { position: 'relative' }, onclick: () => nav('/notify') }, '🔔',
        store.me?.unread_notifications ? h('span', { id: 'bell-badge', class: 'bell-badge' }, store.me.unread_notifications) : null),
      h('button', { class: 'icon-btn', onclick: () => nav('/member') }, '👑')
    ),
    topicSlot, chipRow, tasteSlot, list
  );

  // 今日话题（AI 生成，带标识）
  GET('/api/ai/topic').then(({ topic }) => {
    if (!topic) return;
    store.topic = topic;
    topicSlot.append(h('div', { class: 'glass topic-banner', onclick: () => nav(`/compose?topic=${topic.id}`) },
      h('div', { class: 'tb-title' }, '📌 今日话题：', topic.title, aiBadge()),
      h('div', { class: 'tb-desc' }, topic.description),
      h('button', { class: 'btn mini tb-go' }, '参与')
    ));
  }).catch(() => {});

  async function loadMore(first = false) {
    if (loading) return;
    loading = true;
    try {
      const qPart = tab === 'rec' || tab === 'hot'
        ? `offset=${cursor || 0}` : `before=${cursor || 0}`;
      const data = await GET(`/api/posts?tab=${tab}&${qPart}`);
      if (data.need_login) { list.append(emptyState('登录后查看关注的人', '先去广场逛逛吧')); return; }
      const items = data.items || [];
      if (first && !items.length) {
        list.append(emptyState(tab === 'follow' ? '还没有关注任何人' : '这里还很安静', '发一句话，让它活过来吧'));
      }
      const frag = h('div', { class: 'stagger' });
      for (const p of items) frag.append(postCardEl(p, { onRemoved: () => { cursor = null; list.innerHTML = ''; loadMore(true); } }));
      list.append(frag);
      cursor = tab === 'rec' || tab === 'hot' ? data.next_offset : data.next;
      more.hidden = cursor == null;
    } catch (e) {
      toast(e.message, 'warn');
    } finally {
      loading = false;
    }
  }

  const more = h('button', { class: 'btn block ghost', style: { marginTop: '4px' }, onclick: () => loadMore() }, '看看更多');
  page.append(more);
  loadTaste();
  await loadMore(true);

  // 触底加载
  const onScroll = () => {
    if (cursor != null && page.scrollTop + page.clientHeight > page.scrollHeight - 420) loadMore();
  };
  page.addEventListener('scroll', onScroll);
  return () => page.removeEventListener('scroll', onScroll);
}
