-- 青鸾 · AI 短剧创作工坊 数据表
CREATE TABLE IF NOT EXISTS projects (
  id         TEXT PRIMARY KEY,
  title      TEXT NOT NULL DEFAULT '未命名短剧',
  idea       TEXT NOT NULL DEFAULT '',
  genre      TEXT NOT NULL DEFAULT '',
  style      TEXT NOT NULL DEFAULT '',
  ratio      TEXT NOT NULL DEFAULT '16:9',
  script     TEXT NOT NULL DEFAULT '',
  storyboard TEXT NOT NULL DEFAULT '',     -- JSON：角色/场景/道具/分镜
  canvas_id  TEXT NOT NULL DEFAULT '',
  cover      TEXT NOT NULL DEFAULT '',
  seed       INTEGER NOT NULL DEFAULT 0,   -- 画面一致性：项目级生成种子（Seedream seed）
  status     TEXT NOT NULL DEFAULT 'draft', -- draft|parsed|generating|done
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  id         TEXT PRIMARY KEY,
  tab        TEXT NOT NULL DEFAULT 'material',  -- material(素材)|character(角色)
  kind       TEXT NOT NULL DEFAULT 'image',     -- image|video
  name       TEXT NOT NULL DEFAULT '未命名',
  url        TEXT NOT NULL DEFAULT '',
  poster     TEXT NOT NULL DEFAULT '',
  prompt     TEXT NOT NULL DEFAULT '',
  note       TEXT NOT NULL DEFAULT '',
  source     TEXT NOT NULL DEFAULT 'upload',    -- upload|ark|local
  project_id TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_tab ON assets(tab, created_at DESC);

CREATE TABLE IF NOT EXISTS canvases (
  id         TEXT PRIMARY KEY,
  project_id TEXT NOT NULL DEFAULT '',
  name       TEXT NOT NULL DEFAULT '未命名画布',
  ratio      TEXT NOT NULL DEFAULT '16:9',
  nodes      TEXT NOT NULL DEFAULT '[]',
  edges      TEXT NOT NULL DEFAULT '[]',
  doodles    TEXT NOT NULL DEFAULT '[]',    -- 涂鸦笔手绘批注
  viewport   TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id         TEXT PRIMARY KEY,
  kind       TEXT NOT NULL,                     -- image|video
  status     TEXT NOT NULL DEFAULT 'queued',    -- queued|running|succeeded|failed
  provider   TEXT NOT NULL DEFAULT 'local',     -- local|ark
  model      TEXT NOT NULL DEFAULT '',
  remote_id  TEXT NOT NULL DEFAULT '',
  prompt     TEXT NOT NULL DEFAULT '',
  params     TEXT NOT NULL DEFAULT '',          -- JSON
  result     TEXT NOT NULL DEFAULT '',          -- JSON {url, poster, asset_id}
  error      TEXT NOT NULL DEFAULT '',
  cost_micro INTEGER NOT NULL DEFAULT 0,
  project_id TEXT NOT NULL DEFAULT '',
  node_id    TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, created_at DESC);

CREATE TABLE IF NOT EXISTS usage_logs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  feature           TEXT NOT NULL,
  provider          TEXT NOT NULL DEFAULT 'local',
  model             TEXT NOT NULL DEFAULT '',
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  images            INTEGER NOT NULL DEFAULT 0,
  video_seconds     INTEGER NOT NULL DEFAULT 0,
  cost_micro        INTEGER NOT NULL DEFAULT 0,
  ok                INTEGER NOT NULL DEFAULT 1,
  created_at        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_day ON usage_logs(created_at);

CREATE TABLE IF NOT EXISTS agent_logs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  channel    TEXT NOT NULL,        -- http|mcp|builtin
  tool       TEXT NOT NULL,
  args       TEXT NOT NULL DEFAULT '',
  ok         INTEGER NOT NULL DEFAULT 1,
  error      TEXT NOT NULL DEFAULT '',
  ms         INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
