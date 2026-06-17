// utils/realtime.js — 小程序 WebSocket 实时客户端（wx.connectSocket）
// 自动重连（指数退避）+ 心跳 + 事件订阅。事件名与后端一致：
// mood.updated / note.created / vault.updated / cat.updated / affection.received / partner.status / chat.message ...
let socket = null, connected = false, manualClose = false, retry = 0, heartbeat = null, curUrl = '';
const handlers = {};   // event -> Set(cb)

function dispatch(event, data) {
  (handlers[event] || []).forEach(cb => { try { cb(data); } catch (e) {} });
  (handlers['*'] || []).forEach(cb => { try { cb(event, data); } catch (e) {} });
}
function startHeartbeat() {
  stopHeartbeat();
  heartbeat = setInterval(() => { if (connected && socket) { try { socket.send({ data: JSON.stringify({ event: 'ping' }) }); } catch (e) {} } }, 25000);
}
function stopHeartbeat() { if (heartbeat) { clearInterval(heartbeat); heartbeat = null; } }
function reconnect() {
  if (manualClose || !curUrl) return;
  retry++;
  const delay = Math.min(16000, 1000 * Math.pow(2, retry));
  setTimeout(() => connect(curUrl), delay);
}
function connect(url) {
  if (!url) return;
  curUrl = url; manualClose = false;
  socket = wx.connectSocket({ url });
  socket.onOpen(() => { connected = true; retry = 0; startHeartbeat(); dispatch('__open'); });
  socket.onMessage(({ data }) => { try { const m = JSON.parse(data); if (m && m.event) dispatch(m.event, m.data); } catch (e) {} });
  socket.onClose(() => { connected = false; stopHeartbeat(); reconnect(); });
  socket.onError(() => { connected = false; });
}

module.exports = {
  init(url) { if (url) connect(url); },                       // 进 App 时调用
  on(event, cb) { (handlers[event] = handlers[event] || new Set()).add(cb); return () => this.off(event, cb); },
  off(event, cb) { if (handlers[event]) handlers[event].delete(cb); },
  close() { manualClose = true; stopHeartbeat(); if (socket) { try { socket.close(); } catch (e) {} } connected = false; },
  isConnected() { return connected; }
};
