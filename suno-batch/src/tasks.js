// CSV 任务读取 + 断点续跑记录。零依赖，自带一个能处理引号/换行/转义的 CSV 解析器。
import { readFileSync, existsSync, appendFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { createHash } from 'node:crypto';

// 解析 CSV 文本 → 行数组（每行是字段数组）。支持 "" 引号内逗号/换行、"" 转义引号。
export function parseCsv(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  const t = text.replace(/\r\n?/g, '\n');
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (inQuotes) {
      if (c === '"') {
        if (t[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter(r => r.some(x => x.trim() !== ''));
}

// 把 CSV 读成对象数组：第一行是表头。CSV 单元格里的 \n 字面量会还原为真实换行（方便在表格里写多段歌词）。
export function readTasks(csvPath) {
  const rows = parseCsv(readFileSync(csvPath, 'utf8'));
  if (!rows.length) return [];
  const header = rows[0].map(h => h.trim().toLowerCase());
  const unescape = v => (v || '').replace(/\\n/g, '\n').trim();
  return rows.slice(1).map((cols, idx) => {
    const o = {};
    header.forEach((h, i) => { o[h] = cols[i] !== undefined ? cols[i] : ''; });
    const task = {
      index: idx,
      theme: unescape(o.theme),
      genre: unescape(o.genre),
      language: unescape(o.language),
      mood: unescape(o.mood),
      title: unescape(o.title),
      style: unescape(o.style),
      lyrics: unescape(o.lyrics),
      instrumental: String(o.instrumental || '').trim().toLowerCase() === 'true',
    };
    task.id = taskId(task);
    return task;
  });
}

// 稳定任务 ID：用 theme+title 做哈希，用于断点续跑去重（改了 theme/title 视为新任务）。
export function taskId(t) {
  return createHash('sha1').update(`${t.theme}|${t.title}`).digest('hex').slice(0, 10);
}

// 已完成记录（results.jsonl，每行一条），用于续跑时跳过。
export function loadDone(resultsPath) {
  const done = new Set();
  if (!existsSync(resultsPath)) return done;
  for (const line of readFileSync(resultsPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try { const r = JSON.parse(line); if (r.status === 'ok') done.add(r.id); } catch {}
  }
  return done;
}

export function recordResult(resultsPath, entry) {
  mkdirSync(dirname(resultsPath), { recursive: true });
  appendFileSync(resultsPath, JSON.stringify({ ...entry, ts: new Date().toISOString() }) + '\n');
}
