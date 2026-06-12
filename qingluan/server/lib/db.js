import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..', '..', '..');

export const DB_PATH = process.env.QINGLUAN_DB_PATH || path.join(ROOT, 'var', 'qingluan.sqlite');
export const UPLOAD_DIR = process.env.QINGLUAN_UPLOAD_DIR || path.join(ROOT, 'var', 'qingluan-uploads');
fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

export const db = new DatabaseSync(DB_PATH);
db.exec('PRAGMA journal_mode = WAL;');
db.exec(fs.readFileSync(path.join(__dirname, '..', 'schema.sql'), 'utf8'));

// 轻量迁移：老库补新列（IF NOT EXISTS 建表不会更新已有表）
try { db.exec(`ALTER TABLE canvases ADD COLUMN doodles TEXT NOT NULL DEFAULT '[]'`); } catch { /* 列已存在 */ }
try { db.exec(`ALTER TABLE projects ADD COLUMN seed INTEGER NOT NULL DEFAULT 0`); } catch { /* 列已存在 */ }

const cache = new Map();
function stmt(sql) {
  let s = cache.get(sql);
  if (!s) { s = db.prepare(sql); cache.set(sql, s); }
  return s;
}

export const q = {
  get: (sql, ...args) => stmt(sql).get(...args),
  all: (sql, ...args) => stmt(sql).all(...args),
  run: (sql, ...args) => stmt(sql).run(...args)
};

export function getSetting(key, fallback = null) {
  const row = q.get('SELECT value FROM settings WHERE key = ?', key);
  if (!row) return fallback;
  try { return JSON.parse(row.value); } catch { return row.value; }
}
export function setSetting(key, value) {
  q.run(
    'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    key, JSON.stringify(value)
  );
}
