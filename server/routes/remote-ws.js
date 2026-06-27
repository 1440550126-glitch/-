// 远程控制 Mac · WebSocket 流式通道（鼠标实时控制）
//   ws /api/remote/agent/ws   — Mac agent 连这条，接收流式动作
//   ws /api/remote/stream     — 浏览器控制台连这条，发送鼠标移动/点击/滚动
// 鉴权：?token=<REMOTE_TOKEN>（WS 握手阶段无法带自定义头，只能走 query）。
import { handshake, wsConnection } from '../lib/ws.js';
import * as remote from '../lib/remote.js';

export function attachRemoteWs(server) {
  server.on('upgrade', (req, socket) => {
    let pathname, token;
    try {
      const u = new URL(req.url, 'http://localhost');
      pathname = u.pathname;
      token = u.searchParams.get('token') || '';
    } catch { socket.destroy(); return; }

    if (pathname !== '/api/remote/agent/ws' && pathname !== '/api/remote/stream') { socket.destroy(); return; }
    if (!remote.remoteEnabled() || !remote.checkToken(token)) { socket.destroy(); return; }
    if (!handshake(req, socket)) return;

    const conn = wsConnection(socket);
    if (pathname === '/api/remote/agent/ws') remote.attachAgentStream(conn);
    else remote.attachControllerStream(conn);
  });
}
