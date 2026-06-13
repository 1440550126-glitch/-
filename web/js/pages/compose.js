// 发布页：写文案 → 实时 AI 预览卡 → 发布（提交即动效：文字当场活过来飞出）
import { POST } from '../api.js';
import { h, toast, previewCardEl } from '../ui.js';
import { store } from '../store.js';
import { nav } from '../router.js';
import { playSubmitAnim } from '../anim/player.js';

export function renderCompose(page) {
  const topic = store.topic && location.hash.includes('topic=') ? store.topic : null;

  const ta = h('textarea', {
    class: 'input', rows: 5, maxlength: 300,
    placeholder: topic ? `今日话题「${topic.title}」：${topic.description}` : '写下此刻想说的话…\n比如：「我在等风，也在等你。」'
  });
  const counter = h('div', { style: { textAlign: 'right', fontSize: '11px', color: 'var(--ink-3)', marginTop: '6px' } }, '0 / 300');
  const previewSlot = h('div', { style: { marginTop: '14px' } },
    h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', fontWeight: 600, marginBottom: '8px' } }, '✨ AI 预览卡（发布后大家看到的样子）'),
    h('div', { class: 'empty', style: { padding: '24px' } }, '开始输入，预览卡会跟着你的情绪变化')
  );

  let debounce = null;
  ta.addEventListener('input', () => {
    counter.textContent = `${ta.value.length} / 300`;
    clearTimeout(debounce);
    debounce = setTimeout(async () => {
      const text = ta.value.trim();
      if (text.length < 2) return;
      try {
        const { card } = await POST('/api/ai/preview', { content: text });
        previewSlot.innerHTML = '';
        previewSlot.append(
          h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', fontWeight: 600, marginBottom: '8px' } },
            `✨ AI 预览卡 · 情绪「${card.emotion}」· ${card.scene}`),
          previewCardEl({ content: text, card, author: store.me }, { compact: false })
        );
      } catch { /* 预览失败静默 */ }
    }, 450);
  });

  const publishBtn = h('button', {
    class: 'btn block', style: { marginTop: '16px' },
    onclick: async () => {
      const content = ta.value.trim();
      if (content.length < 2) { toast('写点什么吧，哪怕只有几个字'); return; }
      publishBtn.disabled = true;
      try {
        const r = await POST('/api/posts', { content, topic_id: topic?.id });
        // 自伤关怀内容：温柔提示，绝不做庆祝动效
        if (r.care) { toast(r.notice, 'care'); nav('/feed'); return; }
        // 提交即动效：用刚生成的预览卡，让这句话当场活过来飞出
        await playSubmitAnim(content, r.post?.card);
        if (r.notice) toast(r.notice);
        else toast('已活过来 ✨ 长按卡片可再次回放');
        nav('/feed');
      } catch (e) {
        toast(e.message, 'warn');
        publishBtn.disabled = false;
      }
    }
  }, '发布');

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '写句子')),
      h('div', { class: 'spacer' })
    ),
    topic ? h('div', { class: 'chip active', style: { marginBottom: '12px' } }, `# ${topic.title}`) : null,
    h('div', { class: 'glass card' }, ta, counter),
    previewSlot,
    publishBtn,
    h('div', { class: 'notice-bar', style: { marginTop: '14px' } },
      '发布即表示同意《社区规范》。内容将经过审核，AI 生成的预览卡与动画均会标识「AI 辅助生成」。')
  );
}
