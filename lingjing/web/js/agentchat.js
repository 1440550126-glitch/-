// 内置创作 Agent 聊天组件（项目页 / Agent 页共用）
import { POST } from './api.js';
import { h, icon, toast } from './ui.js';

const SUGGESTIONS = [
  '创建一个都市逆袭项目并写剧本',
  '解析分镜',
  '生成全部图片',
  '生成全部视频',
  '现在进度怎么样'
];

export function createAgentChat(container, { projectId = '', onAction } = {}) {
  const messages = [];
  const log = h('div', { class: 'chat-log' });
  const input = h('input', { class: 'input', placeholder: '让 Agent 帮你创作，例如：解析分镜并生成全部图片…', onkeydown: (e) => { if (e.key === 'Enter') send(); } });
  const sendBtn = h('button', { class: 'btn accent', onclick: () => send(), html: icon('send', 15) });
  const sugg = h('div', { class: 'chat-sugg' }, SUGGESTIONS.map((s) =>
    h('button', { class: 'chip', onclick: () => { input.value = s; send(); } }, s)));

  log.append(botBubble('你好，我是灵境AI创作 Agent。我能直接操作工作台：建项目、写剧本、解析分镜、生成图与视频。试试下面的快捷指令，或直接吩咐。', [], null));

  function userBubble(text) {
    return h('div', { class: 'msg user' }, h('div', { class: 'bubble' }, text));
  }
  function botBubble(text, steps = [], byLLM = null) {
    return h('div', { class: 'msg bot' },
      steps.length ? h('div', { class: 'steps' }, steps.map((s) =>
        h('div', { class: `step ${s.ok ? '' : 'err'}`, title: s.summary || '' }, `⚙ ${s.tool} ${s.ok ? '✓' : '✗'}`))) : null,
      h('div', { class: 'bubble' }, text),
      byLLM === null ? null : h('div', { class: 'meta' }, byLLM ? '由火山方舟大模型驱动' : '本地规则模式（配置方舟 Key 后由大模型驱动）'));
  }

  let busy = false;
  async function send() {
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true;
    input.value = '';
    messages.push({ role: 'user', content: text });
    log.append(userBubble(text));
    const thinking = h('div', { class: 'msg bot' }, h('div', { class: 'bubble' }, h('span', { class: 'pulse' }, 'Agent 正在执行…')));
    log.append(thinking);
    log.scrollTop = log.scrollHeight;
    try {
      const r = await POST('/api/ai/agent', { messages, project_id: projectId });
      messages.push({ role: 'assistant', content: r.reply });
      thinking.replaceWith(botBubble(r.reply, r.steps || [], r.by_llm));
      if (r.steps?.length) onAction?.(r.steps);
    } catch (e) {
      thinking.replaceWith(botBubble('出错了：' + e.message, [], null));
      toast(e.message, 'err');
    }
    busy = false;
    log.scrollTop = log.scrollHeight;
  }

  container.append(h('div', { class: 'chat' }, log, sugg, h('div', { class: 'chat-input' }, input, sendBtn)));
  return { focus: () => input.focus() };
}
