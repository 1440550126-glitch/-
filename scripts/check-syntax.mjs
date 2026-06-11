// 全仓 JS 语法检查（server / web / admin）
import { execFileSync } from 'node:child_process';
import { readdirSync, statSync } from 'node:fs';
import path from 'node:path';

const roots = ['server', 'web', 'admin', 'scripts'];
let bad = 0, total = 0;
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(js|mjs)$/.test(name)) {
      total++;
      try { execFileSync(process.execPath, ['--check', p], { stdio: 'pipe' }); }
      catch (e) { bad++; console.error(`❌ ${p}\n${e.stderr}`); }
    }
  }
}
for (const r of roots) walk(r);
console.log(bad ? `❌ ${bad}/${total} 个文件有语法错误` : `✅ ${total} 个 JS 文件语法全部通过`);
process.exit(bad ? 1 : 0);
