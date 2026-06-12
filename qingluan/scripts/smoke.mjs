#!/usr/bin/env node
// 青鸾 · 冒烟测试：API 全链路 + Agent API + MCP stdio（零依赖，临时库，不污染数据）
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const PORT = 4519;
const BASE = `http://127.0.0.1:${PORT}`;
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'ql-smoke-'));

let passed = 0;
let failed = 0;
const ok = (cond, name) => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ ${name}`); }
};

const server = spawn(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(ROOT, 'server', 'index.js')], {
  env: { ...process.env, QINGLUAN_PORT: PORT, QINGLUAN_DB_PATH: path.join(TMP, 'db.sqlite'), QINGLUAN_UPLOAD_DIR: path.join(TMP, 'up'), QINGLUAN_FAST_LOCAL: '1', ARK_API_KEY: '' },
  stdio: ['ignore', 'pipe', 'pipe']
});
server.stderr.on('data', (d) => process.env.SMOKE_VERBOSE && console.error(String(d)));

async function until(fn, ms = 8000) {
  const t0 = Date.now();
  for (;;) {
    try { const r = await fn(); if (r) return r; } catch { /* retry */ }
    if (Date.now() - t0 > ms) throw new Error('timeout');
    await new Promise((r) => setTimeout(r, 150));
  }
}
async function api(method, p, body, token) {
  const res = await fetch(BASE + p, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, ...json };
}

try {
  console.log('\n— 启动与基础 —');
  const boot = await until(async () => (await api('GET', '/api/bootstrap')).data, 10000);
  ok(boot.app.name === '青鸾', 'bootstrap 返回应用信息');
  ok(/^qlk_/.test(boot.agent_token), '首次启动自动生成 Agent Token');
  ok(boot.ark.enabled === false, '未配 Key 时为本地引擎模式');

  console.log('— 项目与剧本 —');
  const p = (await api('POST', '/api/projects', { title: '冒烟剧', genre: '悬疑反转', idea: '便利店午夜来客' })).data;
  ok(p.id && p.title === '冒烟剧', '创建项目');
  const gs = (await api('POST', '/api/ai/script', { project_id: p.id })).data;
  ok(gs.script.length > 300 && gs.by_llm === false, '本地引擎生成剧本');
  ok(gs.script.includes('第 1 场'), '剧本含场次结构');
  const upd = (await api('PATCH', `/api/projects/${p.id}`, { ratio: '9:16' })).data;
  ok(upd.ratio === '9:16', '更新项目画幅');

  console.log('— 解析与画布 —');
  const parsed = (await api('POST', '/api/ai/parse', { project_id: p.id })).data;
  ok(parsed.storyboard.characters.length >= 2, `解析出角色 ×${parsed.storyboard.characters.length}`);
  ok(parsed.storyboard.shots.length >= 4, `解析出分镜 ×${parsed.storyboard.shots.length}`);
  ok(!!parsed.canvas_id, '自动创建画布');
  const cv = (await api('GET', `/api/canvases/${parsed.canvas_id}`)).data;
  ok(cv.nodes.length >= parsed.storyboard.shots.length, `画布节点 ×${cv.nodes.length}`);
  ok(cv.edges.length >= parsed.storyboard.shots.length, `画布连线 ×${cv.edges.length}`);
  const shotNode = cv.nodes.find((n) => n.type === 'shot');
  const moved = (await api('PATCH', `/api/canvases/${cv.id}`, { nodes: cv.nodes.map((n) => n.id === shotNode.id ? { ...n, x: 999 } : n) }));
  ok(moved.ok, '保存画布');
  const cv2 = (await api('GET', `/api/canvases/${cv.id}`)).data;
  ok(cv2.nodes.find((n) => n.id === shotNode.id).x === 999, '画布数据持久化');

  console.log('— 图像与视频（本地引擎） —');
  const img = (await api('POST', '/api/ai/image', { prompt: '雨夜便利店空镜', name: '便利店', kind: 'scene', project_id: p.id, node_id: cv.nodes.find((n) => n.type === 'scene').id })).data;
  ok(img.url.startsWith('/uploads/') && img.provider === 'local', '本地出图并落盘');
  const imgFile = await fetch(BASE + img.url);
  ok(imgFile.status === 200 && (await imgFile.text()).includes('<svg'), '生成文件可访问');
  const vid = (await api('POST', '/api/ai/video', { prompt: '主角推门而入', duration: 4, project_id: p.id, node_id: shotNode.id, name: '镜头 1', order: 1 })).data;
  ok(vid.taskId && vid.status === 'running', '创建视频任务');
  const done = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${vid.taskId}`)).data;
    return t.status === 'succeeded' ? t : null;
  });
  ok(done.result.url.startsWith('/uploads/'), '视频任务完成并产出文件');
  const cv3 = (await api('GET', `/api/canvases/${cv.id}`)).data;
  ok(cv3.nodes.find((n) => n.id === shotNode.id).data.video === done.result.url, '视频回写画布节点');

  console.log('— 资产库 —');
  const assets = (await api('GET', '/api/assets')).data;
  ok(assets.length >= 2, `资产自动入库 ×${assets.length}`);
  const up = (await api('POST', '/api/upload', { name: '上传图', data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' })).data;
  ok(up.url.startsWith('/uploads/'), '上传 dataURL 资产');
  const ren = (await api('PATCH', `/api/assets/${up.id}`, { name: '重命名图' })).data;
  ok(ren.name === '重命名图', '重命名资产');

  console.log('— Agent API（Token 鉴权） —');
  const noAuth = await api('GET', '/api/agent/v1/ping');
  ok(noAuth.status === 401, '无 Token 拒绝（401）');
  const token = boot.agent_token;
  const ping = await api('GET', '/api/agent/v1/ping', undefined, token);
  ok(ping.data?.pong === true, 'Token 通过 ping');
  const tools = (await api('GET', '/api/agent/v1/tools', undefined, token)).data;
  ok(tools.tools.length >= 14, `开放工具 ×${tools.tools.length}`);
  const openapi = await (await fetch(BASE + '/api/agent/v1/openapi.json')).json();
  ok(openapi.openapi === '3.1.0' && Object.keys(openapi.paths).length >= 16, 'OpenAPI 描述完整');
  const ov = (await api('POST', '/api/agent/v1/tools/studio_overview', {}, token)).data;
  ok(ov.result.projects >= 1, '工具调用 studio_overview');
  const batch = (await api('POST', '/api/agent/v1/tools/generate_storyboard_media', { project_id: p.id, target: 'images', limit: 3 }, token)).data;
  ok(batch.result.generated >= 1, `批量出图工具 ×${batch.result.generated}`);
  const badTool = await api('POST', '/api/agent/v1/tools/not_exist', {}, token);
  ok(badTool.status === 400, '未知工具报错');

  console.log('— 内置 Agent（本地意图） —');
  const chat1 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '创建一个废土科幻项目并写剧本' }] })).data;
  ok(chat1.steps.some((s) => s.tool === 'create_project') && chat1.steps.some((s) => s.tool === 'generate_script'), 'Agent 连续调用 创建+写剧本');
  const chat2 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '解析分镜' }] })).data;
  ok(chat2.steps.some((s) => s.tool === 'parse_script'), 'Agent 解析分镜');
  const logs = (await api('GET', '/api/agent/v1/logs', undefined, token)).data;
  ok(logs.logs.length >= 4, `Agent 调用日志 ×${logs.logs.length}`);

  console.log('— 设置 —');
  const set1 = await api('PATCH', '/api/settings', { ark_api_key: 'AKLTxxxx' });
  ok(set1.status === 400, '拦截 AccessKey 误填');
  const set2 = (await api('PATCH', '/api/settings', { user_name: '导演' }));
  ok(set2.ok, '保存偏好');
  const set3 = (await api('GET', '/api/settings')).data;
  ok(set3.user_name === '导演', '设置生效');
  const stats = (await api('GET', '/api/stats')).data;
  ok(Number(stats.cost_total_yuan) === 0, '本地模式成本为 0');

  console.log('— MCP Server（stdio 端到端） —');
  const mcp = spawn(process.execPath, [path.join(ROOT, 'mcp', 'server.mjs')], {
    env: { ...process.env, QINGLUAN_BASE: BASE, QINGLUAN_TOKEN: token },
    stdio: ['pipe', 'pipe', 'ignore']
  });
  const mcpReplies = new Map();
  let buf = '';
  mcp.stdout.on('data', (d) => {
    buf += String(d);
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx); buf = buf.slice(idx + 1);
      if (!line.trim()) continue;
      try { const m = JSON.parse(line); if (m.id !== undefined) mcpReplies.set(m.id, m); } catch { /* noop */ }
    }
  });
  const mcpSend = (m) => mcp.stdin.write(JSON.stringify(m) + '\n');
  const mcpWait = (id) => until(() => mcpReplies.get(id), 8000);
  mcpSend({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18' } });
  const init = await mcpWait(1);
  ok(init.result.serverInfo.name === 'qingluan-studio', 'MCP initialize');
  ok(init.result.protocolVersion === '2025-06-18', 'MCP 回显协议版本');
  mcpSend({ jsonrpc: '2.0', method: 'notifications/initialized' });
  mcpSend({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  const tl = await mcpWait(2);
  ok(tl.result.tools.length >= 14 && tl.result.tools[0].inputSchema, 'MCP tools/list');
  mcpSend({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'list_projects', arguments: {} } });
  const tc = await mcpWait(3);
  ok(tc.result.content[0].text.includes('冒烟剧'), 'MCP tools/call 取到真实数据');
  mcpSend({ jsonrpc: '2.0', id: 4, method: 'ping' });
  ok((await mcpWait(4)) && true, 'MCP ping');
  mcp.kill();
} catch (e) {
  failed++;
  console.error('  ✗ 异常中断：', e.message);
} finally {
  server.kill();
  fs.rmSync(TMP, { recursive: true, force: true });
}

console.log(`\n${failed ? '❌' : '✅'} 青鸾冒烟测试：${passed} 通过 / ${failed} 失败\n`);
process.exit(failed ? 1 : 0);
