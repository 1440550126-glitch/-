// Agent 接入中心：MCP / HTTP API / 内置 Agent 演练场
import { GET, POST, PATCH, bootstrap } from '../api.js';
import { h, icon, toast, copyText, fmtTime } from '../ui.js';
import { createAgentChat } from '../agentchat.js';

export async function renderAgent(page) {
  const boot = await bootstrap(true);
  const token = boot.agent_token;
  const base = location.origin;

  const mcpCmd = `claude mcp add lingjing \\
  --env LINGJING_BASE=${base} \\
  --env LINGJING_TOKEN=${token} \\
  -- node ${boot.mcp_path}`;
  const mcpJson = `{
  "mcpServers": {
    "lingjing": {
      "command": "node",
      "args": ["${boot.mcp_path}"],
      "env": { "LINGJING_BASE": "${base}", "LINGJING_TOKEN": "${token}" }
    }
  }
}`;
  const curlCmd = `curl -X POST ${base}/api/agent/v1/tools/generate_script \\
  -H "Authorization: Bearer ${token}" \\
  -H "Content-Type: application/json" \\
  -d '{"idea":"外卖小哥捡到一张黑卡","genre":"都市逆袭"}'`;
  const mcpHttp = `{
  "mcpServers": {
    "lingjing": {
      "url": "${base}/api/agent/v1/mcp",
      "headers": { "Authorization": "Bearer ${token}" }
    }
  }
}`;

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

  // Agent 调度参数（思考/规划/自动执行/温度/步数）
  const sset = await GET('/api/settings').catch(() => ({ agent: {} }));
  const ag = sset.agent || {};
  const agToggle = (key, label, def, hint) => {
    const sel = h('select', { class: 'select', style: { width: 'auto' } },
      [['true', '开'], ['false', '关']].map(([v, l]) => h('option', { value: v, selected: String(ag[key] ?? def) === v }, l)));
    sel.dataset.key = key;
    return h('label', { class: 'ag-field', title: hint || '' }, h('span', {}, label), sel);
  };
  const tempIn = h('input', { class: 'input', type: 'number', min: 0, max: 1.3, step: 0.1, value: ag.temperature ?? 0.5, style: { width: '70px' } });
  const stepIn = h('input', { class: 'input', type: 'number', min: 1, max: 24, step: 1, value: ag.max_steps ?? 10, style: { width: '70px' } });
  const planSel = agToggle('plan_first', '先分析意图', true, '执行前先做意图分析与规划（思考）');
  const thinkSel = agToggle('thinking', '展示思考', true, '在对话里显示思考与规划');
  const autoSel = agToggle('autorun', '自动执行', true, '关闭则只给计划、等你回复"执行"');
  const agentCfgBox = h('div', { class: 'card pad', style: { marginTop: '16px' } },
    h('h3', { style: { fontSize: '15px', marginBottom: '4px' } }, '🧠 Agent 调度参数',
      boot.ark.enabled ? h('span', { class: 'pill teal', style: { marginLeft: '8px' } }, '方舟驱动') : h('span', { class: 'pill', style: { marginLeft: '8px' } }, '本地意图引擎')),
    h('p', { style: { fontSize: '12.5px', color: 'var(--ink3)', marginBottom: '10px' } },
      'Agent 会先分析你的意图、规划步骤，再智能调度工具执行。这些参数控制它的"思考方式"与"行动力度"。'),
    h('div', { class: 'ag-grid' },
      planSel, thinkSel, autoSel,
      h('label', { class: 'ag-field', title: '创造力：越高越发散（剧本更天马行空），越低越稳（执行更可控）' }, h('span', {}, '创造力(温度)'), tempIn),
      h('label', { class: 'ag-field', title: '单轮最多调用多少个工具，越大越能一口气做完整条链路' }, h('span', {}, '单轮最大步数'), stepIn)),
    h('button', { class: 'btn primary', style: { marginTop: '14px' }, onclick: async (e) => {
      e.currentTarget.disabled = true;
      try {
        await PATCH('/api/settings', {
          agent_plan_first: planSel.querySelector('select').value === 'true',
          agent_thinking: thinkSel.querySelector('select').value === 'true',
          agent_autorun: autoSel.querySelector('select').value === 'true',
          agent_temperature: Number(tempIn.value), agent_max_steps: Number(stepIn.value)
        });
        toast('Agent 参数已保存', 'ok');
      } catch (err) { toast(err.message, 'err'); }
      e.currentTarget.disabled = false;
    } }, '保存参数'));

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
        '灵境AI的全部创作能力（建项目 / 写剧本 / 解析分镜 / 画布编排 / 生图 / 生视频 / 查任务与成本）都以工具形式开放，三种接入任选：'),
      h('div', { class: 'agent-grid' },
        card(`${icon('terminal')} ① MCP 接入 <span class="pill teal">推荐</span>`,
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', marginBottom: '8px' } }, 'Claude Code 一条命令接入（先启动灵境AI服务）：'),
          codeBlock(mcpCmd, 'MCP 命令已复制'),
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', margin: '10px 0 8px' } }, 'Cursor / Cherry Studio 等本地 MCP 客户端（stdio）：'),
          codeBlock(mcpJson, 'JSON 配置已复制'),
          h('p', { style: { fontSize: '12.5px', color: 'var(--ink2)', margin: '10px 0 8px' } },
            '远程/云端个人助理（OpenClaw、Hermes Agent 等）用 ', h('b', {}, 'HTTP 版 MCP'), '，填 URL 即可，无需本地进程：'),
          codeBlock(mcpHttp, 'HTTP MCP 配置已复制')),
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
      toolsBox, agentCfgBox, playBox, logsBox));
}
