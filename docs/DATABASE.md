# 数据库设计

默认 SQLite（`node:sqlite`，WAL 模式，单文件 `var/jvling.sqlite`），结构定义见 [`server/schema.sql`](../server/schema.sql)。字段语义与 PostgreSQL 对齐，迁移要点在文末。

## 表清单（17 张）

| 表 | 用途 | 关键设计 |
|---|---|---|
| `users` | 用户/AI 暖场账号/管理员 | `is_ai` 标识 AI 账号（永不伪装真人）；`member_until` 会员到期；`credits` 星尘额度；`equipped` 已装备皮肤 JSON；`settings` 用户开关（关闭暖场/青少年模式等）；注销=匿名化（status=deleted） |
| `posts` | 文案帖子 | `card` AI 预览卡 JSON；`manifest` 缓存默认动画指令；`status` active/pending/removed/rejected；`like_count` 只计真人，`ai_like_count` 单独计数**不进热度**；`hot_score` 互动加权 |
| `comments` | 评论 | `parent_id` 楼中楼拍平两层；`reply_to_user` 被回复人；`is_ai` 暖场评论标识 |
| `likes` / `collects` | 点赞/收藏 | 联合主键 (user_id, post_id) 天然去重 |
| `follows` / `blocks` | 关注/拉黑 | 拉黑双向过滤信息流与评论 |
| `reports` | 举报 | target_type 支持 post/comment/user/room_message；处理人/备注/状态 |
| `moderation_logs` | 审核日志 | 系统拦截、人工操作、封禁全留痕 |
| `sensitive_words` | 敏感词 | 三级：block 拦截 / review 转人工 / selfharm 关怀+人工；后台热更（30s 缓存） |
| `ai_usage_logs` | AI 成本账本 | 每次调用记 provider/model/tokens/**cost_micro（微元）**/是否兜底/延迟；后台按日按功能聚合 |
| `ai_topics` | 今日话题 | 按东八区自然日唯一 |
| `warmup_logs` | 暖场动作日志 | 发帖/评论/点赞/组局提醒全留痕，频控依据 |
| `quota_usage` | 每日配额 | (user, day, kind) 计数：发帖/评论/动画生成防刷 |
| `credit_logs` | 额度流水 | 购买入账/高级生成扣点，ref 关联订单或帖子 |
| `skins` / `user_skins` | 皮肤目录/拥有 | `payload` 仅含外观参数（渐变/装饰/粒子色），游戏逻辑不可见 |
| `orders` | 订单 | member/skin/credits 三类；pending→paid 状态机；channel 预留 iap/wxpay |
| `game_rooms` / `room_messages` | 房间快照/房内消息 | 运行态在内存（权威），定期落快照；消息持久化供举报取证 |
| `word_pairs` | 卧底词库 | 按 used_count 升序取词避免重复 |
| `settings` | 系统 KV | 暖场配置、应用密钥等 |

## 热度公式

`hot = 3·like + 4·comment + 3·collect + 2·share + 0.2·play`，推荐流按 `hot / (age_hours + 2)^1.4` 时间衰减排序（近 7 天窗口内存排序，MVP 规模足够；规模化后移离线任务）。AI 点赞不参与。

## 迁移 PostgreSQL 要点

1. `INTEGER PRIMARY KEY AUTOINCREMENT` → `BIGSERIAL PRIMARY KEY`；时间戳可保持 ms 整数或改 `timestamptz`。
2. JSON 文本字段（card/manifest/equipped/settings/payload/state）→ `jsonb`。
3. `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`；`INSERT ... ON CONFLICT(...) DO UPDATE` 语法一致。
4. 数据访问集中在 `server/lib/db.js`（prepare/get/all/run 四个方法），替换为 pg 连接池即可，业务层 SQL 改动极小。
5. 房间运行态与限流桶迁 Redis（`server/lib/hub.js`、`httpx.rateLimit` 为唯一改造点）。
