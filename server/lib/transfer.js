// 远程控制 Mac · 文件中转（落盘临时存储，不进内存；带 TTL 自动清理）
// 浏览器↔Mac 的文件都先经服务器磁盘暂存一份，取走或超时即删。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { uid, now } from './util.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIR = process.env.REMOTE_TMP_DIR || path.join(__dirname, '..', '..', 'var', 'remote-tmp');
fs.mkdirSync(DIR, { recursive: true });

const TTL = 10 * 60_000;
export const MAX_FILE = Number(process.env.REMOTE_MAX_FILE) || 500 * 1024 * 1024;   // 单文件上限，默认 500MB
const store = new Map();   // id -> { id, file, name, size, device, at }

const safeName = (n) => String(n || 'file').replace(/[/\\]/g, '_').slice(0, 200);

export function create(name, device) {
  const id = uid('tf_', 12);
  return { id, file: path.join(DIR, id), name: safeName(name), device: device || null, at: now() };
}
export function commit(t, size) {
  store.set(t.id, { id: t.id, file: t.file, name: t.name, size, device: t.device, at: now() });
  sweep();
  return store.get(t.id);
}
export function get(id) { return store.get(id) || null; }
export function remove(id) {
  const m = store.get(id);
  if (m) { try { fs.unlinkSync(m.file); } catch { /* 已删 */ } store.delete(id); }
}
function sweep() {
  const cut = now() - TTL;
  for (const [id, m] of store) if (m.at < cut) remove(id);
}
