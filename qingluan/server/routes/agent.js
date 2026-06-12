// 青鸾 · 对外 Agent API（/api/agent/v1，Bearer Token 鉴权，CORS 开放）
// 接入方式：① MCP（qingluan/mcp/server.mjs，推荐） ② 直接 HTTP（见 openapi.json）
import { GET, POST } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { toolSchemas, runTool } from '../lib/tools.js';

GET('/api/agent/v1/ping', async () => ({
  pong: true, app: '青鸾 · AI 短剧创作工坊', version: '0.1.0', tools: toolSchemas().length
}), { agent: true });

GET('/api/agent/v1/tools', async () => ({ tools: toolSchemas() }), { agent: true });

POST('/api/agent/v1/tools/:name', async ({ params, body }) => {
  return { result: await runTool(params.name, body || {}, 'http') };
}, { agent: true, maxBytes: 1024 * 1024 });

GET('/api/agent/v1/logs', async () => ({
  logs: q.all('SELECT channel, tool, args, ok, error, ms, created_at FROM agent_logs ORDER BY id DESC LIMIT 50')
}), { agent: true });

// OpenAPI 3.1 描述（无需鉴权即可读取 schema，便于客户端发现；裸 JSON，不走统一包装）
GET('/api/agent/v1/openapi.json', async ({ req, res }) => {
  const host = req.headers.host || 'localhost:4399';
  const tools = toolSchemas();
  const paths = {
    '/api/agent/v1/ping': { get: { summary: '连通性检查', security: [{ bearer: [] }], responses: { 200: { description: 'pong' } } } },
    '/api/agent/v1/tools': { get: { summary: '列出全部工具及参数 schema', security: [{ bearer: [] }], responses: { 200: { description: '工具列表' } } } }
  };
  for (const t of tools) {
    paths[`/api/agent/v1/tools/${t.name}`] = {
      post: {
        summary: t.description.split('。')[0],
        description: t.description,
        operationId: t.name,
        security: [{ bearer: [] }],
        requestBody: { content: { 'application/json': { schema: t.input_schema } } },
        responses: {
          200: { description: '统一返回 {ok:true,data:{result:…}}；失败 {ok:false,error:…}' }
        }
      }
    };
  }
  const doc = {
    openapi: '3.1.0',
    info: {
      title: '青鸾 · AI 短剧创作工坊 Agent API',
      version: '0.1.0',
      description: '把青鸾接入任意 Agent：所有创作能力（剧本/分镜/画布/图像/视频）均以工具形式开放。鉴权：Authorization: Bearer <AGENT_TOKEN>（设置页查看）。也可使用自带 MCP 服务器 qingluan/mcp/server.mjs。'
    },
    servers: [{ url: `http://${host}` }],
    components: { securitySchemes: { bearer: { type: 'http', scheme: 'bearer' } } },
    paths
  };
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*'
  });
  res.end(JSON.stringify(doc, null, 2));
  return undefined;
});
