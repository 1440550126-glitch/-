// AI 治愈陪聊页：和「句灵」1 对 1 倾诉。温柔、被听见、缓解压力。
import { GET, POST } from '../api.js';
import { h, toast, aiBadge, mascot, confirmSheet } from '../ui.js';
import { nav } from '../router.js';

export async function renderChat(page) {
  page.classList.add('no-nav', 'chat-page');

  const scroll = h('div', { class: 'cc-wrap' });
  const input = h('textarea', { class: 'cc-input', rows: 1, maxlength: 500, placeholder: '把心里的话说给句灵听…' });
  const sendBtn = h('button', { class: 'cc-send', 'aria-label': '发送' }, '↑');

  const toBottom = () => requestAnimationFrame(() => { scroll.scrollTop = scroll.scrollHeight + 999; });

  function bubble(m) {
    const me = m.role === 'user';
    return h('div', { class: `cc-row ${me ? 'me' : ''}` },
      me ? null : h('div', { class: 'cc-ava' }, mascot(34)),
      h('div', { class: `cc-bubble ${me ? 'me' : 'ai'} ${m.care ? 'care' : ''}` }, m.content)
    );
  }

  let sending = false;
  async function send() {
    const text = input.value.trim();
    if (!text || sending) return;
    sending = true; sendBtn.disabled = true;
    input.value = ''; autoGrow();
    scroll.append(bubble({ role: 'user', content: text }));
    const typing = h('div', { class: 'cc-row' }, h('div', { class: 'cc-ava' }, mascot(34)),
      h('div', { class: 'cc-bubble ai typing' }, h('span'), h('span'), h('span')));
    scroll.append(typing); toBottom();
    try {
      const r = await POST('/api/ai/chat', { content: text });
      typing.remove();
      scroll.append(bubble(r.reply));
      if (r.care && r.hotline) scroll.append(h('div', { class: 'cc-hotline' }, '☎️ ', r.hotline));
      toBottom();
    } catch (e) {
      typing.remove();
      toast(e.message, 'warn');
      input.value = text; autoGrow();   // 失败保留输入，方便重试
    } finally {
      sending = false; sendBtn.disabled = false; input.focus();
    }
  }

  function autoGrow() {
    input.style.height = 'auto';
    input.style.height = Math.min(120, input.scrollHeight) + 'px';
  }
  input.addEventListener('input', autoGrow);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener('click', send);

  const clearBtn = h('button', { class: 'icon-btn', onclick: () => {
    confirmSheet('清空这段对话？', '清空后这段倾诉记录将不可恢复，句灵会重新陪你开始。', '清空对话', async () => {
      try { await POST('/api/ai/chat/clear'); location.reload(); } catch (e) { toast(e.message, 'warn'); }
    });
  } }, '🧹');

  page.append(
    h('div', { class: 'topbar', style: { padding: '8px 12px', flexShrink: 0 } },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', { style: { flex: 1 } },
        h('h1', { style: { fontSize: '17px' } }, '句灵 · 陪你说说话'),
        h('div', { class: 'sub', style: { display: 'flex', gap: '6px', alignItems: 'center' } }, aiBadge('AI 陪伴'), '温柔倾听，不评判')
      ),
      clearBtn
    ),
    scroll,
    h('div', { class: 'cc-bar' }, input, sendBtn)
  );

  // 加载历史 + 开场白 + 合规提示
  let data;
  try { data = await GET('/api/ai/chat'); }
  catch (e) { toast(e.message, 'warn'); data = { messages: [], greeting: '', disclaimer: '' }; }

  scroll.append(h('div', { class: 'cc-notice' }, '💛 ', data.disclaimer || '句灵是 AI 陪伴，不能替代专业心理咨询。'));
  if (!data.messages?.length && data.greeting) scroll.append(bubble({ role: 'assistant', content: data.greeting }));
  for (const m of data.messages || []) scroll.append(bubble(m));
  toBottom();
  setTimeout(() => input.focus(), 200);
}
