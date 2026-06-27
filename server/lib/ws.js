// 极简 WebSocket 服务端（零依赖，仅够远程控制流式通道用）。
// Node 内置只有 WebSocket「客户端」全局，没有服务端，这里手写握手 + 帧编解码。
// 只处理文本帧 + ping/pong + close；客户端→服务端帧带掩码，服务端→客户端不带。
import crypto from 'node:crypto';

const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const MAX_FRAME = 1 << 20;   // 1MB，控制消息很小，超了直接断

export function handshake(req, socket) {
  const key = req.headers['sec-websocket-key'];
  if (!key || (req.headers.upgrade || '').toLowerCase() !== 'websocket') { socket.destroy(); return false; }
  const accept = crypto.createHash('sha1').update(key + GUID).digest('base64');
  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n' +
    'Upgrade: websocket\r\n' +
    'Connection: Upgrade\r\n' +
    `Sec-WebSocket-Accept: ${accept}\r\n\r\n`
  );
  return true;
}

export function wsConnection(socket) {
  const conn = { socket, alive: true, onmessage: null, onclose: null };
  let buf = Buffer.alloc(0);

  socket.on('data', (chunk) => {
    buf = Buffer.concat([buf, chunk]);
    for (;;) {
      const frame = decodeFrame(buf);
      if (frame === 'too-big') { conn.close(); return; }
      if (!frame) break;
      buf = frame.rest;
      if (frame.opcode === 0x8) { conn.close(); return; }                       // close
      if (frame.opcode === 0x9) { sendFrame(socket, 0xA, frame.payload); continue; } // ping → pong
      if (frame.opcode === 0xA) continue;                                       // pong
      if (frame.opcode === 0x1 || frame.opcode === 0x0) conn.onmessage?.(frame.payload.toString('utf8'));
    }
  });

  const done = () => { if (!conn.alive) return; conn.alive = false; conn.onclose?.(); try { socket.destroy(); } catch { /* ignore */ } };
  socket.on('close', done);
  socket.on('error', done);
  socket.setNoDelay?.(true);   // 流式低延迟，关 Nagle

  conn.send = (data) => {
    if (!conn.alive) return;
    sendFrame(socket, 0x1, Buffer.from(typeof data === 'string' ? data : JSON.stringify(data)));
  };
  conn.close = done;
  return conn;
}

function decodeFrame(buf) {
  if (buf.length < 2) return null;
  const opcode = buf[0] & 0x0f;
  const masked = (buf[1] & 0x80) !== 0;
  let len = buf[1] & 0x7f;
  let off = 2;
  if (len === 126) { if (buf.length < off + 2) return null; len = buf.readUInt16BE(off); off += 2; }
  else if (len === 127) { if (buf.length < off + 8) return null; len = Number(buf.readBigUInt64BE(off)); off += 8; }
  if (len > MAX_FRAME) return 'too-big';
  let mask;
  if (masked) { if (buf.length < off + 4) return null; mask = buf.subarray(off, off + 4); off += 4; }
  if (buf.length < off + len) return null;
  let payload = buf.subarray(off, off + len);
  if (masked) {
    const out = Buffer.allocUnsafe(len);
    for (let i = 0; i < len; i++) out[i] = payload[i] ^ mask[i & 3];
    payload = out;
  }
  return { opcode, payload, rest: buf.subarray(off + len) };
}

function sendFrame(socket, opcode, payload) {
  const len = payload.length;
  let header;
  if (len < 126) { header = Buffer.allocUnsafe(2); header[1] = len; }
  else if (len < 65536) { header = Buffer.allocUnsafe(4); header[1] = 126; header.writeUInt16BE(len, 2); }
  else { header = Buffer.allocUnsafe(10); header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2); }
  header[0] = 0x80 | opcode;   // FIN + opcode；服务端→客户端不加掩码
  try { socket.write(Buffer.concat([header, payload])); } catch { /* socket gone */ }
}
