// 爆款工厂 · 对外 Agent API（/api/agent/v1，Bearer Token 鉴权，CORS 开放）
// 接入方式：① MCP（topview/mcp/server.mjs，推荐） ② 直接 HTTP（见 openapi.json） ③ MCP over HTTP
import { GET, POST } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { toolSchemas, runTool } from '../lib/tools.js';

const VERSION = '0.1.0';
const INSTRUCTIONS = '爆款工厂是开放的 AI 电商带货视频平台。建议先 studio_overview 了解现状；招牌流程：product_to_video(商品链接/信息→广告分镜) → generate_media(出图/出片) → get_task 轮询 → generate_dubbing 配音 → localize_project 多语言。';

GET('/api/agent/v1/ping', async () => ({ pong: true, app: '爆款工厂', version: VERSION, tools: toolSchemas().length }), { agent: true });
GET('/api/agent/v1/tools', async () => ({ tools: toolSchemas() }), { agent: true });
POST('/api/agent/v1/tools/:name', async ({ params, body }) => ({ result: await runTool(params.name, body || {}, 'http') }), { agent: true, maxBytes: 1024 * 1024 });
GET('/api/agent/v1/logs', async () => ({ logs: q.all('SELECT channel,tool,args,ok,error,ms,created_at FROM agent_logs ORDER BY id DESC LIMIT 50') }), { agent: true });

// ---------------- MCP over Streamable HTTP（无状态精简版） ----------------
async function mcpHandle(msg) {
  const { id, method, params } = msg || {};
  const reply = (result) => ({ jsonrpc: '2.0', id, result });
  const error = (code, message) => ({ jsonrpc: '2.0', id, error: { code, message } });
  if (!msg || msg.jsonrpc !== '2.0' || typeof method !== 'string') return error(-32600, 'Invalid Request');
  if (id === undefined) return null; // notification
  switch (method) {
    case 'initialize':
      return reply({
        protocolVersion: params?.protocolVersion || '2024-11-05',
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'topview-factory', title: '爆款工厂 · AI 电商带货视频', version: VERSION },
        instructions: INSTRUCTIONS
      });
    case 'ping': return reply({});
    case 'tools/list':
      return reply({ tools: toolSchemas().map((t) => ({ name: t.name, description: t.description, inputSchema: t.input_schema })) });
    case 'tools/call':
      try {
        const result = await runTool(params?.name, params?.arguments || {}, 'mcp');
        return reply({ content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] });
      } catch (e) {
        return reply({ content: [{ type: 'text', text: `工具执行失败：${e.message}` }], isError: true });
      }
    default: return error(-32601, `Method not found: ${method}`);
  }
}
POST('/api/agent/v1/mcp', async ({ res, body }) => {
  const messages = Array.isArray(body) ? body : [body];
  const replies = (await Promise.all(messages.map(mcpHandle))).filter(Boolean);
  const headers = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' };
  if (!replies.length) { res.writeHead(202, headers); res.end(); return undefined; }
  res.writeHead(200, headers);
  res.end(JSON.stringify(Array.isArray(body) ? replies : replies[0]));
  return undefined;
}, { agent: true, maxBytes: 1024 * 1024 });

// ---------------- OpenAPI 3.1（免鉴权读取 schema，便于发现） ----------------
GET('/api/agent/v1/openapi.json', async ({ req, res }) => {
  const host = req.headers.host || 'localhost:4499';
  const tools = toolSchemas();
  const paths = {
    '/api/agent/v1/ping': { get: { summary: '连通性检查', security: [{ bearer: [] }], responses: { 200: { description: 'pong' } } } },
    '/api/agent/v1/tools': { get: { summary: '列出全部工具及参数 schema', security: [{ bearer: [] }], responses: { 200: { description: '工具列表' } } } }
  };
  for (const t of tools) {
    paths[`/api/agent/v1/tools/${t.name}`] = {
      post: {
        summary: t.description.split('。')[0], description: t.description, operationId: t.name, security: [{ bearer: [] }],
        requestBody: { content: { 'application/json': { schema: t.input_schema } } },
        responses: { 200: { description: '统一返回 {ok:true,data:{result:…}}；失败 {ok:false,error:…}' } }
      }
    };
  }
  const doc = {
    openapi: '3.1.0',
    info: { title: '爆款工厂 · Agent API', version: VERSION, description: '把电商带货视频创作能力开放给任意 Agent。鉴权：Authorization: Bearer <AGENT_TOKEN>（设置页查看）。也可用自带 MCP 服务器 topview/mcp/server.mjs。' },
    servers: [{ url: `http://${host}` }],
    components: { securitySchemes: { bearer: { type: 'http', scheme: 'bearer' } } },
    paths
  };
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' });
  res.end(JSON.stringify(doc, null, 2));
  return undefined;
});
