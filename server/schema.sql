-- AI句灵 数据库结构（SQLite 方言，字段语义与 PostgreSQL 对齐，迁移说明见 docs/DATABASE.md）

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT UNIQUE,            -- 游客为空
  pass_hash     TEXT,                   -- scrypt(salt:hash)
  device_id     TEXT UNIQUE,            -- 游客一键登录标识
  nickname      TEXT NOT NULL,
  avatar        TEXT NOT NULL DEFAULT 'blob_1',
  bio           TEXT DEFAULT '',
  role          TEXT NOT NULL DEFAULT 'user',     -- user | admin
  is_ai         INTEGER NOT NULL DEFAULT 0,       -- AI 暖场账号（永远明确标识，不伪装真人）
  ai_persona    TEXT,                             -- AI 账号人设描述
  status        TEXT NOT NULL DEFAULT 'active',   -- active | banned | deleted
  banned_until  INTEGER,
  banned_reason TEXT,
  member_until  INTEGER NOT NULL DEFAULT 0,       -- 会员到期时间(ms)，0=非会员
  credits       INTEGER NOT NULL DEFAULT 0,       -- 高级 AI 额度（点）
  equipped      TEXT NOT NULL DEFAULT '{}',       -- 已装备皮肤 {card_frame, avatar_frame, bubble, anim_fx, room_theme}
  settings      TEXT NOT NULL DEFAULT '{}',       -- {no_ai_warmup, teen_mode, ...}
  follower_count  INTEGER NOT NULL DEFAULT 0,
  following_count INTEGER NOT NULL DEFAULT 0,
  created_at    INTEGER NOT NULL,
  last_seen     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS posts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  content       TEXT NOT NULL,
  topic_id      INTEGER,
  card          TEXT NOT NULL DEFAULT '{}',       -- AI 预览卡样式 JSON
  manifest      TEXT,                             -- 缓存的默认风格动画 Manifest
  status        TEXT NOT NULL DEFAULT 'active',   -- active | pending(待人工审核) | removed | rejected
  remove_reason TEXT,
  is_ai         INTEGER NOT NULL DEFAULT 0,
  ai_label      TEXT,                             -- AI 内容标识文案
  like_count    INTEGER NOT NULL DEFAULT 0,       -- 仅真实用户互动计入热度
  ai_like_count INTEGER NOT NULL DEFAULT 0,       -- AI 暖场点赞单独计数，不计入热度（不伪造热度）
  comment_count INTEGER NOT NULL DEFAULT 0,
  collect_count INTEGER NOT NULL DEFAULT 0,
  share_count   INTEGER NOT NULL DEFAULT 0,
  play_count    INTEGER NOT NULL DEFAULT 0,       -- 文字变动画播放次数
  hot_score     REAL NOT NULL DEFAULT 0,
  created_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_posts_feed ON posts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_hot  ON posts(status, hot_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS comments (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id       INTEGER NOT NULL REFERENCES posts(id),
  user_id       INTEGER NOT NULL REFERENCES users(id),
  parent_id     INTEGER,                          -- 根评论 id（楼中楼）
  reply_to_user INTEGER,                          -- 被回复人
  content       TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active',   -- active | pending | removed
  is_ai         INTEGER NOT NULL DEFAULT 0,
  created_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, created_at);

CREATE TABLE IF NOT EXISTS likes (
  user_id INTEGER NOT NULL, post_id INTEGER NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, post_id)
);
CREATE TABLE IF NOT EXISTS collects (
  user_id INTEGER NOT NULL, post_id INTEGER NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, post_id)
);
CREATE TABLE IF NOT EXISTS follows (
  follower_id INTEGER NOT NULL, followee_id INTEGER NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY (follower_id, followee_id)
);
CREATE TABLE IF NOT EXISTS blocks (
  user_id INTEGER NOT NULL, blocked_id INTEGER NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, blocked_id)
);

CREATE TABLE IF NOT EXISTS reports (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter_id INTEGER NOT NULL,
  target_type TEXT NOT NULL,           -- post | comment | user | room_message
  target_id   TEXT NOT NULL,
  reason      TEXT NOT NULL,
  detail      TEXT DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'open',   -- open | resolved | dismissed
  handled_by  INTEGER,
  handle_note TEXT,
  handled_at  INTEGER,
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS moderation_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  actor       TEXT NOT NULL,           -- system | ai | admin:<id>
  action      TEXT NOT NULL,           -- block | review | remove | restore | ban | ...
  target_type TEXT,
  target_id   TEXT,
  detail      TEXT,
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sensitive_words (
  word     TEXT PRIMARY KEY,
  category TEXT NOT NULL DEFAULT 'block',   -- block(直接拦截) | review(转人工) | selfharm(关怀+人工)
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_usage_logs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id           INTEGER,            -- 0/NULL = 系统(暖场/话题)
  feature           TEXT NOT NULL,      -- manifest | manifest_premium | warmup_post | warmup_comment | topic | game_host | words
  provider          TEXT NOT NULL,      -- local | ark | openai | ...
  model             TEXT NOT NULL,
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  cost_micro        INTEGER NOT NULL DEFAULT 0,   -- 成本，微元（1元 = 1_000_000）
  ok                INTEGER NOT NULL DEFAULT 1,
  fallback          INTEGER NOT NULL DEFAULT 0,   -- 是否走了本地兜底
  latency_ms        INTEGER NOT NULL DEFAULT 0,
  created_at        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_usage_time ON ai_usage_logs(created_at);

CREATE TABLE IF NOT EXISTS ai_topics (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  day         TEXT NOT NULL UNIQUE,     -- YYYY-MM-DD
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  by_llm      INTEGER NOT NULL DEFAULT 0,
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS warmup_logs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  action     TEXT NOT NULL,             -- post | comment | like | lobby_notice | topic
  target_id  TEXT,
  content    TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quota_usage (
  user_id INTEGER NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day, kind)
);

CREATE TABLE IF NOT EXISTS credit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL, delta INTEGER NOT NULL, reason TEXT NOT NULL, ref TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS skins (
  id        TEXT PRIMARY KEY,           -- slug
  name      TEXT NOT NULL,
  type      TEXT NOT NULL,              -- card_frame | avatar_frame | bubble | anim_fx | room_theme
  rarity    TEXT NOT NULL,              -- normal | rare | fine | epic | legend | limited
  price_fen INTEGER NOT NULL DEFAULT 0, -- 0 = 免费
  blurb     TEXT NOT NULL DEFAULT '',
  payload   TEXT NOT NULL DEFAULT '{}', -- 纯外观参数（渐变/粒子色等），不含任何数值优势
  enabled   INTEGER NOT NULL DEFAULT 1,
  sort      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_skins (
  user_id INTEGER NOT NULL, skin_id TEXT NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, skin_id)
);

CREATE TABLE IF NOT EXISTS orders (
  id         TEXT PRIMARY KEY,          -- ord_xxxxxxxx
  user_id    INTEGER NOT NULL,
  kind       TEXT NOT NULL,             -- member | skin | credits
  item_id    TEXT NOT NULL,
  title      TEXT NOT NULL,
  amount_fen INTEGER NOT NULL,
  status     TEXT NOT NULL DEFAULT 'pending',   -- pending | paid | canceled
  channel    TEXT NOT NULL DEFAULT 'sandbox',   -- sandbox(模拟支付) | iap | wxpay | alipay
  created_at INTEGER NOT NULL,
  paid_at    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS game_rooms (
  id          TEXT PRIMARY KEY,         -- 6 位房间码
  name        TEXT NOT NULL,
  game_type   TEXT NOT NULL DEFAULT 'undercover',
  status      TEXT NOT NULL DEFAULT 'waiting',  -- waiting | playing | ended
  host_id     INTEGER NOT NULL,
  max_players INTEGER NOT NULL DEFAULT 6,
  allow_bots  INTEGER NOT NULL DEFAULT 1,
  theme       TEXT,                     -- 房主装备的房间主题皮肤（纯外观）
  state       TEXT NOT NULL DEFAULT '{}',
  round       INTEGER NOT NULL DEFAULT 0,
  winner      TEXT,
  created_at  INTEGER NOT NULL,
  ended_at    INTEGER
);

CREATE TABLE IF NOT EXISTS room_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id    TEXT NOT NULL,
  user_id    INTEGER NOT NULL,          -- 0 = AI 主持人/系统
  nickname   TEXT NOT NULL,
  kind       TEXT NOT NULL,             -- chat | speak | host | system
  content    TEXT NOT NULL,
  round      INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_room_messages ON room_messages(room_id, id);

CREATE TABLE IF NOT EXISTS word_pairs (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  civilian  TEXT NOT NULL,
  undercover TEXT NOT NULL,
  used_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- AI 治愈陪聊：1 对 1 倾听对话历史（self-harm 内容标记 care，不回喂作普通上下文）
CREATE TABLE IF NOT EXISTS ai_chat_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL,
  role       TEXT NOT NULL,               -- user | assistant
  content    TEXT NOT NULL,
  care       INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_chat ON ai_chat_messages(user_id, id);

CREATE TABLE IF NOT EXISTS notifications (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL,            -- 接收者
  kind       TEXT NOT NULL,               -- like | comment | reply | follow | system | ai
  actor_id   INTEGER,                     -- 触发者（system 为空）
  post_id    INTEGER,
  comment_id INTEGER,
  content    TEXT NOT NULL DEFAULT '',
  read       INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, read, id DESC);
