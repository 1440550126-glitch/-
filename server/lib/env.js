// 零依赖 .env 加载：必须在任何读取 process.env 的模块之前最先 import。
// ES 模块按源码顺序、深度优先求值；本模块是叶子（仅依赖 node 内置），故会最先执行，
// 从而保证 llm.js 等在模块顶层读取 env 的代码能拿到 .env 里的值。
// 规则：不覆盖已存在的环境变量（真实环境变量 / --env-file 优先）；无 .env 时静默跳过。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

for (const file of ['.env', '.env.local']) {
  let text;
  try { text = fs.readFileSync(path.join(root, file), 'utf8'); } catch { continue; }
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const m = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    if (process.env[m[1]] === undefined) process.env[m[1]] = v;
  }
}
