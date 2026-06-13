#!/usr/bin/env node
// 灵境AI · MCP Server（零依赖，stdio 传输）
// 把灵境AI工作台的全部创作能力以 MCP 工具形式暴露给任意 Agent（Claude Code / Cursor / Cherry Studio…）。
//
// 接入示例（Claude Code）：
//   claude mcp add lingjing \
//     --env LINGJING_TOKEN=<设置页的 Agent Token> \
//     -- node /绝对路径/lingjing/mcp/server.mjs
//
// 环境变量 / 参数：
//   LINGJING_BASE  灵境AI服务地址，默认 http://127.0.0.1:4399  （或 --base=...）
//   LINGJING_TOKEN Agent Token，工作台「Agent 接入」页查看      （或 --token=...）
import { createInterface } from 'node:readline';

const argv = Object.fromEntries(process.argv.slice(2).filter((a) => a.startsWith('--')).map((a) => {
  const [k, ...v] = a.replace(/^--/, '').split('=');
  return [k, v.join('=') || '1'];
}));
const BASE = (argv.base || process.env.LINGJING_BASE || process.env.QINGLUAN_BASE || 'http://127.0.0.1:4399').replace(/\/+$/, '');
const TOKEN = argv.token || process.env.LINGJING_TOKEN || process.env.QINGLUAN_TOKEN || '';
const VERSION = '0.1.0';

async function api(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const json = await res.json().catch(() => ({}));
  if (!json.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json.data;
}

let toolCache = null;
async function listTools() {
  if (!toolCache) {
    const data = await api('GET', '/api/agent/v1/tools');
    toolCache = data.tools.map((t) => ({ name: t.name, description: t.description, inputSchema: t.input_schema }));
  }
  return toolCache;
}

const out = (msg) => process.stdout.write(JSON.stringify(msg) + '\n');
const reply = (id, result) => out({ jsonrpc: '2.0', id, result });
const fail = (id, code, message) => out({ jsonrpc: '2.0', id, error: { code, message } });

async function handle(msg) {
  const { id, method, params } = msg;
  try {
    switch (method) {
      case 'initialize':
        return reply(id, {
          protocolVersion: params?.protocolVersion || '2024-11-05',
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'lingjing-studio', title: '灵境AI · 短剧创作工坊', version: VERSION },
          instructions:
            '灵境AI是开源的 AI 短剧创作工坊（剧本→分镜→画布→图像→视频，火山方舟驱动）。' +
            '建议先调用 studio_overview 了解现状；创作流程：create_project → generate_script → parse_script → generate_storyboard_media(images) → generate_storyboard_media(videos) → get_task 轮询。'
        });
      case 'ping':
        return reply(id, {});
      case 'tools/list':
        return reply(id, { tools: await listTools() });
      case 'tools/call': {
        const { name, arguments: args } = params || {};
        try {
          const data = await api('POST', `/api/agent/v1/tools/${encodeURIComponent(name)}`, args || {});
          return reply(id, { content: [{ type: 'text', text: JSON.stringify(data.result, null, 2) }] });
        } catch (e) {
          return reply(id, { content: [{ type: 'text', text: `工具执行失败：${e.message}` }], isError: true });
        }
      }
      case 'notifications/initialized':
      case 'notifications/cancelled':
        return; // 通知无需应答
      default:
        if (id !== undefined) fail(id, -32601, `Method not found: ${method}`);
    }
  } catch (e) {
    if (id !== undefined) fail(id, -32603, e.message || 'internal error');
  }
}

const rl = createInterface({ input: process.stdin, terminal: false });
rl.on('line', (line) => {
  const s = line.trim();
  if (!s) return;
  let msg;
  try { msg = JSON.parse(s); } catch { return out({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }); }
  handle(msg);
});
rl.on('close', () => process.exit(0));

process.stderr.write(`[lingjing-mcp] ready, base=${BASE}, token=${TOKEN ? 'set' : 'MISSING(请配置 LINGJING_TOKEN)'}\n`);
