// Agent 接入中心：MCP / HTTP API / 内置 Agent 演练场
import { GET, POST, bootstrap } from '../api.js';
import { h, icon, toast, copyText, fmtTime } from '../ui.js';
import { createAgentChat } from '../agentchat.js';

export async function renderAgent(page) {
  const boot = await bootstrap(true);
  const token = boot.agent_token;
  const base = location.origin;

  const mcpCmd = `claude mcp add qingluan \\
  --env QINGLUAN_BASE=${base} \\
  --env QINGLUAN_TOKEN=${token} \\
  -- node ${boot.mcp_path}`;
  const mcpJson = `{
  "mcpServers": {
    "qingluan": {
      "command": "node",
      "args": ["${boot.mcp_path}"],
      "env": { "QINGLUAN_BASE": "${base}", "QINGLUAN_TOKEN": "${token}" }
    }
  }
}`;
  const curlCmd = `curl -X POST ${base}/api/agent/v1/tools/generate_script \\
  -H "Authorization: Bearer ${token}" \\
  -H "Content-Type: application/json" \\
  -d '{"idea":"外卖小哥捡到一张黑卡","genre":"都市逆袭"}'`;

  function codeBlock(text, tip) {
    const pre = h('pre', { class: 'code' }, text);
    pre.append(h('button', { class: 'btn xs cp', style: { background: 'rgba(255,255,255,.1)', borderColor: 'rgba(255,255,255,.2)', color: '#fff' }, onclick: () => copyText(text, tip), html: `${icon('copy', 13)} 复制` }));
    return pre;
  }

  const card = (titleHtml, ...children) => h('div', { class: 'card pad' }, h('h3', { style: { fontSize: '15px', marginBottom: '10px', display: 'flex', gap: '8px', alignItems: 'center' }, html: titleHtml }), ...children);

  const tokenChip = h('span', { class: 'pill gold', style: { cursor: 'pointer' }, title: '点击复制', onclick: () => copyText(token, 'Token 已复制') }, `Token：${token.slice(0, 10)}…${token.slice(-4)}`);
  const rotateBtn = h('button', { class: 'btn sm', onclick: async () => {
    if (!confirm('重置后旧 Token 立即失效，所有已接入的 Agent 需要更新配置。继续？')) return;
    await POST('/api/settings/agent-token/rotate');
    toast('已重置，页面即将刷新', 'ok');
    setTimeout(() => location.reload(), 800);
  } }, '重置 Token');

  // 工具列表
  const toolsBox = h('div', { class: 'card', style: { marginTop: '16px', overflow: 'hidden' } });
  (async () => {
    try {
      const res = await fetch('/api/agent/v1/tools', { headers: { Authorization: `Bearer ${token}` } });
      const data = (await res.json()).data;
      const table = h('table', { class: 'tool-table' },
        h('thead', {}, h('tr', {}, h('th', { style: { width: '230px' } }, '工具'), h('th', {}, '说明'))),
        h('tbody', {}, data.tools.map((t) => h('tr', {}, h('td', {}, t.name), h('td', {}, t.description)))));
      toolsBox.append(
        h('div', { class: 'panel-head' }, h('b', {}, `开放工具（${data.tools.length} 个）`), h('span', { class: 'grow' }),
          h('a', { href: '/api/agent/v1/openapi.json', target: '_blank' }, 'OpenAPI 描述 ↗')),
        h('div', { style: { maxHeight: '380px', overflowY: 'auto' } }, table));
    } catch (e) { toolsBox.append(h('div', { class: 'empty' }, h('p', {}, '工具列表加载失败：' + e.message))); }
  })();

  // 调用日志
  const logsBox = h('div', { class: 'card', style: { marginTop: '16px', overflow: 'hidden' } });
  (async () => {
    const stats = await GET('/api/stats');
    const rows = stats.agent_logs || [];
    logsBox.append(h('div', { class: 'panel-head' }, h('b', {}, '最近 Agent 调用'), h('span', { class: 'grow' }),
      h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, 'MCP / HTTP / 内置共用一套工具')));
    if (!rows.length) { logsBox.append(h('div', { class: 'empty' }, h('p', {}, '还没有调用记录，接入后这里会展示足迹'))); return; }
    const table = h('table', { class: 'tool-table' },
      h('tbody', {}, rows.map((l) => h('tr', {},
        h('td', {}, l.tool),
        h('td', {},
          h('span', { class: `pill ${l.channel === 'mcp' ? 'teal' : l.channel === 'builtin' ? 'gold' : ''}`, style: { marginRight: '8px' } }, l.channel),
          l.ok ? h('span', { class: 'pill green' }, `${l.ms}ms`) : h('span', { class: 'pill red', title: l.error }, '失败'),
          h('span', { style: { color: 'var(--ink3)', marginLeft: '8px', fontSize: '12px' } }, fmtTime(l.created_at)))))));
    logsBox.append(h('div', { style: { maxHeight: '300px', overflowY: 'auto' } }, table));
  })();

  // 演练场
  const playBox = h('div', { class: 'card', style: { marginTop: '16px', height: '520px', display: 'flex', flexDirection: 'column', overflow: 'hidden' } },
    h('div', { class: 'panel-head' }, h('b', {}, '内置创作 Agent 演练场'), h('span', { class: 'grow' }),
      h('span', { style: { fontSize: '12px', color: 'var(--ink3)' } }, boot.ark.enabled ? '由方舟大模型驱动（函数调用）' : '本地规则模式，配置方舟 Key 解锁大模型')));
  const chatHost = h('div', { style: { flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 } });
  playBox.append(chatHost);
  createAgentChat(chatHost, {});

  page.append(
    h('div', { class: 'topbar line' }, h('h1', {}, 'Agent 接入'), tokenChip, rotateBtn, h('span', { class: 'grow' }),
      h('span', { class: 'pill teal' }, '像小云雀 Skill，但完全开放')),
    h('div', { class: 'wrap' },
      h('p', { style: { color: 'var(--ink2)', margin: '14px 0 16px', fontSize: '13.5px' } },
        '青鸾的全部创作能力（建项目 / 写剧本 / 解析分镜 / 画布编排 / 生图 / 生视频 / 查任务与成本）都以工具形式开放，三种接入任选：'),
      h('div', { class: 'agent-grid' },
        card(`${icon('terminal')} ① MCP 接入 <span class="pill teal">推荐</span>`,
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', marginBottom: '8px' } }, 'Claude Code 一条命令接入（先启动青鸾服务）：'),
          codeBlock(mcpCmd, 'MCP 命令已复制'),
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', margin: '10px 0 8px' } }, 'Cursor / Cherry Studio 等通用 MCP 客户端用 JSON 配置：'),
          codeBlock(mcpJson, 'JSON 配置已复制')),
        card(`${icon('link')} ② HTTP API 接入`,
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', marginBottom: '8px' } },
            '任意语言/框架直接调用 REST 工具端点，OpenAPI 描述可被 Agent 框架自动加载：'),
          codeBlock(curlCmd, 'curl 示例已复制'),
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', margin: '10px 0 0' } },
            '· 端点：POST /api/agent/v1/tools/{工具名}', h('br'), '· 鉴权：Authorization: Bearer Token', h('br'), '· 描述文件：GET /api/agent/v1/openapi.json')),
        card(`${icon('robot')} ③ 内置创作 Agent`,
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)' } },
            '不接外部工具也能用：每个项目工作台自带 Agent 对话，由同一套工具驱动，像聊天一样完成「建项目 → 写剧本 → 解析 → 生图 → 出片」全流程。'),
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', marginTop: '8px' } },
            '配置火山方舟 Key 后升级为大模型函数调用循环；未配置时为本地规则模式，主流程同样可走通。'))),
      toolsBox, playBox, logsBox));
}
