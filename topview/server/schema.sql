-- 爆款工厂 · AI 电商带货视频 数据表
CREATE TABLE IF NOT EXISTS projects (
  id         TEXT PRIMARY KEY,
  title      TEXT NOT NULL DEFAULT '未命名广告',
  kind       TEXT NOT NULL DEFAULT 'ad',     -- ad(广告片) | ugc(数字人口播)
  tone       TEXT NOT NULL DEFAULT 'ugc',    -- 脚本套路：ugc/painpoint/unboxing/koc/feature
  product    TEXT NOT NULL DEFAULT '{}',     -- JSON {url,title,brand,price,currency,points[],images[],desc}
  lang       TEXT NOT NULL DEFAULT 'zh',     -- 主语言
  style      TEXT NOT NULL DEFAULT '',       -- 画面风格（注入生图/生视频提示词）
  ratio      TEXT NOT NULL DEFAULT '9:16',
  duration   INTEGER NOT NULL DEFAULT 6,     -- 单镜目标时长（秒）
  storyboard TEXT NOT NULL DEFAULT '{}',     -- JSON {hook,cta,shots:[{key,order,role,onscreen,voiceover,visual,duration,image,video,audio}]}
  status     TEXT NOT NULL DEFAULT 'draft',  -- draft|scripted|generating|done
  cover      TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  deleted_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assets (
  id         TEXT PRIMARY KEY,
  kind       TEXT NOT NULL DEFAULT 'image',  -- image|video|audio
  name       TEXT NOT NULL DEFAULT '未命名',
  url        TEXT NOT NULL DEFAULT '',
  prompt     TEXT NOT NULL DEFAULT '',
  lang       TEXT NOT NULL DEFAULT '',
  source     TEXT NOT NULL DEFAULT 'local',  -- upload|local|ark|openai
  project_id TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_proj ON assets(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
  id         TEXT PRIMARY KEY,
  kind       TEXT NOT NULL,                  -- image|video|audio|avatar
  status     TEXT NOT NULL DEFAULT 'queued', -- queued|running|succeeded|failed
  provider   TEXT NOT NULL DEFAULT 'local',
  model      TEXT NOT NULL DEFAULT '',
  remote_id  TEXT NOT NULL DEFAULT '',
  prompt     TEXT NOT NULL DEFAULT '',
  params     TEXT NOT NULL DEFAULT '',       -- JSON
  result     TEXT NOT NULL DEFAULT '',       -- JSON {url}
  error      TEXT NOT NULL DEFAULT '',
  project_id TEXT NOT NULL DEFAULT '',
  shot_key   TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, created_at DESC);

-- 多语言本地化：每个项目 × 每种语言一份翻译稿 + 字幕
CREATE TABLE IF NOT EXISTS localizations (
  id         TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  lang       TEXT NOT NULL,
  shots      TEXT NOT NULL DEFAULT '[]',     -- JSON [{key,onscreen,voiceover}]
  srt        TEXT NOT NULL DEFAULT '',
  by_llm     INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  UNIQUE(project_id, lang)
);

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
  channel    TEXT NOT NULL,                  -- http|mcp|builtin
  tool       TEXT NOT NULL,
  args       TEXT NOT NULL DEFAULT '',
  ok         INTEGER NOT NULL DEFAULT 1,
  error      TEXT NOT NULL DEFAULT '',
  ms         INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
