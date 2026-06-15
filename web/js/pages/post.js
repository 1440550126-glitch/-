// 帖子详情：动画入口 + 评论 / 回复
import { GET, POST, DEL } from '../api.js';
import { h, toast, avatarEl, aiBadge, timeAgo, emptyState } from '../ui.js';
import { store } from '../store.js';
import { postCardEl, reportSheet } from './feed.js';
import { openAnimPlayer } from '../anim/player.js';
import { openSongPlayer } from '../anim/song.js';

export async function renderPost(page, params) {
  let post;
  try { post = await GET(`/api/posts/${params.id}`); }
  catch (e) { page.append(emptyState(e.message)); return; }

  const commentList = h('div', {});
  let replyTo = null;   // {parent_id, reply_to_user, nickname}

  const input = h('input', { class: 'input', placeholder: '说点什么…', maxlength: 200 });
  const replyTip = h('div', { style: { fontSize: '11px', color: 'var(--brand)', marginBottom: '6px' }, hidden: true });

  function commentEl(cm, isReply = false) {
    const el = h('div', { class: 'comment' },
      avatarEl(cm.author, isReply ? 26 : 34),
      h('div', { class: 'c-body' },
        h('div', { class: 'c-name' },
          cm.author?.nickname,
          cm.author?.is_ai ? aiBadge(cm.ai_label || 'AI 生成') : null,
          cm.reply_to ? h('span', { style: { color: 'var(--ink-3)' } }, `回复 @${cm.reply_to}`) : null
        ),
        h('div', { class: 'c-text' }, cm.content),
        h('div', { class: 'c-meta' },
          timeAgo(cm.created_at),
          h('span', {
            onclick: () => {
              replyTo = { parent_id: cm.parent_id || cm.id, reply_to_user: cm.author.id, nickname: cm.author.nickname };
              replyTip.hidden = false;
              replyTip.textContent = `回复 @${cm.author.nickname}（点此取消）`;
              input.focus();
            }, style: { cursor: 'pointer' }
          }, '回复'),
          cm.is_mine
            ? h('span', { style: { cursor: 'pointer' }, onclick: async () => { try { await DEL(`/api/comments/${cm.id}`); toast('已删除'); loadComments(); } catch (e) { toast(e.message, 'warn'); } } }, '删除')
            : h('span', { style: { cursor: 'pointer' }, onclick: () => reportSheet('comment', cm.id) }, '举报')
        ),
        cm.replies?.length ? h('div', { class: 'replies' }, cm.replies.map((r) => commentEl(r, true))) : null
      )
    );
    return el;
  }

  async function loadComments() {
    try {
      const { items } = await GET(`/api/posts/${post.id}/comments`);
      commentList.innerHTML = '';
      if (!items.length) commentList.append(emptyState('还没有评论', '第一个温柔的人会是你吗'));
      else for (const cm of items) commentList.append(commentEl(cm));
    } catch (e) { toast(e.message, 'warn'); }
  }

  replyTip.addEventListener('click', () => { replyTo = null; replyTip.hidden = true; });

  const send = h('button', {
    class: 'btn mini', style: { flexShrink: 0 },
    onclick: async () => {
      const content = input.value.trim();
      if (!content) return;
      try {
        await POST(`/api/posts/${post.id}/comments`, { content, parent_id: replyTo?.parent_id, reply_to_user: replyTo?.reply_to_user });
        input.value = '';
        replyTo = null; replyTip.hidden = true;
        toast('评论成功');
        loadComments();
      } catch (e) { toast(e.message, 'warn'); }
    }
  }, '发送');

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '详情')),
      h('div', { class: 'spacer' })
    ),
    postCardEl(post, { onRemoved: () => history.back() }),
    h('div', { style: { display: 'flex', gap: '10px', marginBottom: '16px' } },
      h('button', { class: 'btn block gold', onclick: () => openAnimPlayer(post) }, '✨ 让它活过来'),
      h('button', { class: 'btn block', onclick: () => openSongPlayer(post) }, '🎵 听这句话')
    ),
    h('div', { class: 'glass card' },
      h('div', { style: { fontWeight: 700, fontSize: '14px', marginBottom: '4px' } }, `评论 ${post.comment_count || ''}`),
      commentList,
      replyTip,
      h('div', { style: { display: 'flex', gap: '8px', marginTop: '10px' } }, input, send)
    )
  );
  loadComments();
}
