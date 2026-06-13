// 内置创作 Agent 聊天组件（项目页 / Agent 页共用）
import { POST } from './api.js';
import { h, icon, toast } from './ui.js';

const SUGGESTIONS = [
  '做一部末日生存的电影，写剧本并解析分镜',
  '创建一个都市逆袭短剧并一键成片',
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

  log.append(botBubble('你好，我是灵境AI创作 Agent。我会先分析你的意图、规划步骤，再动手操作工作台（建项目 / 写剧本 / 解析分镜 / 出图 / 出片 / 配音 / 一键成片）。直接吩咐，或点下面的快捷指令。'));

  function userBubble(text) {
    return h('div', { class: 'msg user' }, h('div', { class: 'bubble' }, text));
  }
  function botBubble(text, { steps = [], byLLM = null, thinking = '', plan = [] } = {}) {
    return h('div', { class: 'msg bot' },
      thinking ? h('div', { class: 'agent-think' }, h('b', {}, '💭 思考'), h('span', {}, thinking)) : null,
      plan?.length ? h('div', { class: 'agent-plan' }, '📋 规划：', plan.map((p, i) => h('span', { class: 'plan-step' }, `${i + 1}.${p}`))) : null,
      steps.length ? h('div', { class: 'steps' }, steps.map((s) =>
        h('div', { class: `step ${s.ok ? '' : 'err'}`, title: s.summary || '' }, `⚙ ${s.tool} ${s.ok ? '✓' : '✗'}`))) : null,
      h('div', { class: 'bubble' }, text),
      byLLM === null ? null : h('div', { class: 'meta' }, byLLM ? '火山方舟驱动（意图分析 + 函数调用）' : '本地意图引擎（配置方舟 Key 后由大模型驱动）'));
  }

  let busy = false;
  async function send() {
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true;
    input.value = '';
    messages.push({ role: 'user', content: text });
    log.append(userBubble(text));
    const waiting = h('div', { class: 'msg bot' }, h('div', { class: 'bubble' }, h('span', { class: 'pulse' }, 'Agent 正在分析意图、规划与执行…')));
    log.append(waiting);
    log.scrollTop = log.scrollHeight;
    try {
      const r = await POST('/api/ai/agent', { messages, project_id: projectId });
      messages.push({ role: 'assistant', content: r.reply });
      waiting.replaceWith(botBubble(r.reply, { steps: r.steps || [], byLLM: r.by_llm, thinking: r.thinking || '', plan: r.plan || [] }));
      if (r.steps?.length) onAction?.(r.steps);
    } catch (e) {
      waiting.replaceWith(botBubble('出错了：' + e.message));
      toast(e.message, 'err');
    }
    busy = false;
    log.scrollTop = log.scrollHeight;
  }

  container.append(h('div', { class: 'chat' }, log, sugg, h('div', { class: 'chat-input' }, input, sendBtn)));
  return { focus: () => input.focus() };
}
