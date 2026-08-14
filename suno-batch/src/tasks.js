// CSV 任务读取 + 断点续跑记录。零依赖，自带一个能处理引号/换行/转义的 CSV 解析器。
import { readFileSync, existsSync, appendFileSync, mkdirSync, writeFileSync } from 'node:fs';
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
      playlist: unescape(o.playlist || o.tag || o.tags),   // 歌单/标签（可空，空则自动归类）
    };
    task.id = taskId(task);
    return task;
  });
}

// 稳定任务 ID：用 theme+title 做哈希，用于断点续跑去重（改了 theme/title 视为新任务）。
export function taskId(t) {
  return createHash('sha1').update(`${t.theme}|${t.title}`).digest('hex').slice(0, 10);
}

// 已完成记录（用「最后一次状态」判断，这样质量回捞把 ok 覆盖为 error 后能重新排上）。
export function loadDone(resultsPath) {
  const done = new Set();
  for (const [id, status] of loadStatuses(resultsPath)) if (status === 'ok') done.add(id);
  return done;
}

export function recordResult(resultsPath, entry) {
  mkdirSync(dirname(resultsPath), { recursive: true });
  appendFileSync(resultsPath, JSON.stringify({ ...entry, ts: new Date().toISOString() }) + '\n');
}

// 读每个任务 id 的「最后一次状态」（用于重试队列判断）。
export function loadStatuses(resultsPath) {
  const last = new Map();
  if (!existsSync(resultsPath)) return last;
  for (const line of readFileSync(resultsPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try { const r = JSON.parse(line); if (r.id) last.set(r.id, r.status); } catch {}
  }
  return last;
}

// 曾尝试过但未成功（error / skipped_credits）的任务 id 集合——重试队列的来源。
export function loadFailed(resultsPath) {
  const failed = new Set();
  for (const [id, status] of loadStatuses(resultsPath)) {
    if (status !== 'ok' && status !== 'dry' && status !== 'generated') failed.add(id);
  }
  return failed;
}

// 生成歌单/标签索引：把成功的歌按 playlist 分组，写成 Markdown，便于归档查阅。
export function writePlaylistIndex(resultsPath, outPath) {
  if (!existsSync(resultsPath)) return null;
  const groups = new Map();
  for (const line of readFileSync(resultsPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try {
      const r = JSON.parse(line);
      if (r.status !== 'ok') continue;
      const key = (r.playlist && r.playlist.trim()) || '未分类';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(r);
    } catch {}
  }
  if (!groups.size) return null;
  let md = `# 歌单索引\n\n生成时间：${new Date().toLocaleString('zh-CN')}\n\n`;
  for (const [name, songs] of [...groups].sort((a, b) => b[1].length - a[1].length)) {
    md += `## 🎵 ${name}（${songs.length}）\n\n`;
    for (const s of songs) md += `- **${s.title || '(无题)'}** — \`${s.style || ''}\`${s.instrumental ? ' · 器乐' : ''}\n`;
    md += '\n';
  }
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, md);
  return outPath;
}
