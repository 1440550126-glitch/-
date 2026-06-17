# 猫约时光 · 后端接口设计（v1）

把当前前端原型（`utils/store.js` 的本地读写）对应到正式后端。技术栈无关（Node/Java/Go 均可），客户端为微信小程序。

---

## 0. 通用约定

- **Base URL**：`https://api.maoyue.example.com/api`
- **协议**：HTTPS + JSON；实时用 WebSocket（见 §16）。
- **鉴权**：除登录外，所有请求带 `Authorization: Bearer <token>`（JWT）。
- **统一响应体**：
  ```json
  { "code": 0, "msg": "ok", "data": { } }
  ```
  `code=0` 成功；非 0 为业务错误。HTTP 用标准状态码（401 未登录 / 403 无权限 / 404 / 409 冲突 / 429 限流）。
- **时间**：统一毫秒时间戳（int64）或 ISO8601；日期用 `YYYY-MM-DD`。
- **分页**：`?cursor=<id>&limit=20`，返回 `{ list, nextCursor }`。
- **幂等**：涉及金额/支付/写操作支持 `Idempotency-Key` 请求头，重复提交返回首次结果。
- **资源归属**：情侣类数据均挂在 `couple_id` 下，服务端校验当前用户属于该情侣；**会员门禁在服务端二次校验**（前端不可信）。
- **文件**：图片走对象存储，先 `POST /upload/token` 拿直传凭证，客户端直传后回传 URL。

---

## 1. 鉴权与用户

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/login` | 微信登录：`{ code }`(wx.login) → `{ token, user, isNewUser }` |
| POST | `/auth/refresh` | 刷新 token |
| GET | `/me` | 当前用户资料（含会员/实名/主题/绑定状态） |
| PUT | `/me` | 更新昵称/头像 `{ nickname, avatar }` |
| POST | `/me/logout` | 退出登录 |
| POST | `/me/cancel` | 注销账号（数据匿名化） |

`GET /me` → 
```json
{ "id":"u_1","nickname":"我","avatar":"🐱","theme":"coral",
  "verified":true,"member":{"isMember":true,"tier":"yearly","expireAt":1750000000000},
  "coupleId":"c_1","bound":true }
```

## 2. 用户设置（主题 / 关心提醒）

| 方法 | 路径 | 对应 store |
|---|---|---|
| PUT | `/me/settings` | `{ theme }` ← `setTheme` |
| GET | `/me/remind` | ← `getRemind` |
| PUT | `/me/remind` | `{ enabled, minutes }` ← `setRemind` |

> 主题也可纯本地存；放服务端可多端同步。

## 3. 情侣关系（绑定 / 解绑 / 邀请）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/couple` | 当前情侣信息（`getCouple`，含 `loveDays` 服务端算） |
| PUT | `/couple` | 改昵称备注/头像/在一起日期 `{ partnerRemark, startDate }`（`setCouple`） |
| POST | `/couple/invite` | 生成邀请码/二维码 → `{ code, expireAt }` |
| POST | `/couple/bind` | `{ code }` 接受邀请并绑定（双方校验，建立 `couple`） |
| POST | `/couple/unbind` | 解绑 —— **需会员**，服务端校验 `member.isMember`，否则 403 `MEMBER_REQUIRED` |

## 4. 每日：心情 / 每日一问

| 方法 | 路径 | 对应 store |
|---|---|---|
| GET | `/mood/today` | `getMood`（返回 self + partner 当天心情） |
| PUT | `/mood/today` | `{ emoji, text }` ← `setSelfMood`（写后 WS 推 `mood.updated` 给对方） |
| GET | `/daily-question` | `getDailyQuestion`（服务端按日期出题，返回双方作答） |
| POST | `/daily-question/answer` | `{ text }` ← `answerDailyQuestion`（对方答完才互相可见，可选） |

## 5. 纸条 / 愿望清单

| 方法 | 路径 | 对应 store |
|---|---|---|
| GET | `/notes?cursor=&limit=` | `getNotes` |
| POST | `/notes` | `{ text }` ← `addNote`（WS 推 `note.created`） |
| DELETE | `/notes/:id` | `removeNote` |
| GET | `/wishes` | `getWishes` |
| POST | `/wishes` | `{ text }` ← `addWish` |
| PATCH | `/wishes/:id` | `{ done }` ← `toggleWish` |
| DELETE | `/wishes/:id` | `removeWish` |

## 6. 一起养的猫（共享状态）

| 方法 | 路径 | 对应 store |
|---|---|---|
| GET | `/cat` | `getCat`（服务端做跨天饱食度衰减） |
| POST | `/cat/feed` | `feedCat`（服务端校验每日次数上限，返回 `{ cat, leveledUp }`） |
| POST | `/cat/pet` | `petCat` |
| POST | `/cat/play` | `playCat` |
| PUT | `/cat/name` | `{ name }` ← `renameCat` |

> 猫是情侣共享对象：任一方操作后 WS 推 `cat.updated`。喂养上限/成长公式放服务端，防作弊。

## 7. 纪念日 / 时光回忆

| 方法 | 路径 | 对应 store |
|---|---|---|
| GET | `/anniversaries` | `getAnniversaries`（服务端算 `diff`/`passedDays`） |
| POST | `/anniversaries` | `{ name, date, repeatYearly }` ← `addAnniversary` |
| DELETE | `/anniversaries/:id` | `removeAnniversary` |
| GET | `/memories?cursor=&limit=` | `getMemories` |
| POST | `/memories` | `{ text, date, photoUrl }` ← `addMemory` |
| DELETE | `/memories/:id` | `removeMemory` |
| POST | `/upload/token` | 取图片直传凭证（回忆照片） |

## 8. 情侣点餐

| 方法 | 路径 | 对应 store |
|---|---|---|
| GET | `/dining/menu` | `getMenu` |
| POST | `/dining/menu` | `{ name, emoji }` ← `addDish` |
| DELETE | `/dining/menu/:id` | `removeDish` |

> 随机"今天吃什么"在客户端算即可；如需"发给TA"，调 §15 互动接口。

## 9. 小金库（共同记账，双方互通）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/vault` | `{ balance, stats:{totalIn,totalOut} }` ← `getVault`+`vaultStats` |
| GET | `/vault/txns?cursor=&limit=` | `getVaultTx` |
| POST | `/vault/deposit` | `{ amount, note }` ← `vaultDeposit`（需 `Idempotency-Key`） |
| POST | `/vault/spend` | `{ amount, note }` ← `vaultSpend`（需 `Idempotency-Key`） |

`POST /vault/deposit` →
```json
{ "code":0, "data":{ "balance":1834.00, "txn":{"id":"t_9","type":"in","amount":520,"note":"旅行基金","createdAt":1750000000000} } }
```
> 写后对**两端**都 WS 推 `vault.updated`。金额服务端校验、记流水、可加每日上限。**仅记账，无真实资金流**；若日后接真实充值/提现需金融合规与支付牌照。

## 10. 状态 / 定位 / 使用情况

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| POST | `/status/report` | 上报自己 `{ battery, charging, lat, lng }`，更新 `last_active_at`（省电：节流上报） |
| GET | `/status/partner` | TA 的状态 `{ battery, lastActiveAt, online, location?, distanceKm }` ← `getPartnerStatus` |
| POST | `/status/poke` | 提醒/戳 TA ← `pokePartner`（触发 §15 通知 + 可能的订阅消息） |
| POST | `/usage/report` | 可选：`{ opensToday, inAppMs }` 上报（`recordOpen/recordHide/getUsage` 主要在本地，聚合可上报） |

- **打开次数 / App内时长 / 上次离开间隔**：以本地为主，按需聚合上报做统计。
- **系统级其它 App 使用**：小程序无法获取，不提供该接口。
- **关心提醒**：服务端定时任务扫描"TA 未活跃时长 ≥ 用户设置阈值" → 发**订阅消息**（§15）。

## 11. 缘分匹配（需会员）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/match/pool?limit=` | 推荐候选（排除已喜欢/已跳过）← `getMatchPool`，**需会员**否则 403 |
| POST | `/match/action` | `{ targetId, like }` ← `matchAction` → `{ matched, profile }`；互相喜欢则建 thread |
| POST | `/match/reset` | `resetMatch`（测试/重新推荐） |

> 候选返回含 `verified`（已实名/未实名）。真实匹配建议有推荐策略 + 反作弊 + 内容审核。

## 12. 聊天（大厅 / 私聊 / AI媒婆）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/hall?cursor=&limit=` | 缘分大厅消息 ← `getHall` |
| POST | `/hall` | `{ text }` ← `sendHall`（**先过内容审核** `msgSecCheck`） |
| GET | `/threads` | 私聊会话列表 ← `getThreads` |
| GET | `/threads/:id/messages?cursor=` | 某会话消息 ← `getThread` |
| POST | `/threads/:id/messages` | `{ text }` ← `sendThread`（审核后投递，WS 推 `chat.message`） |

- **AI媒婆**：`thread.type='ai'`，消息进 AI 服务生成回复（带"AI"标识、输出过审）。
- 大厅/私聊都要：敏感词 + 机审 + 举报/拉黑。

## 13. 会员与支付（微信支付）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/membership` | 套餐列表 + 当前状态 ← `getMember` |
| POST | `/membership/order` | `{ plan }` 下单 → 返回 `wx.requestPayment` 所需支付参数 |
| POST | `/pay/wxpay/notify` | 微信支付**异步回调**（验签 → 开通会员 ← `openMember`） |
| GET | `/membership/order/:id` | 查订单状态（客户端支付后轮询/兜底） |

> `openMember/cancelMember` 由支付回调与到期任务驱动；前端不能直接置为会员。权益（解绑、匹配、主题）在各接口服务端校验。

## 14. 实名认证

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| GET | `/verify` | 实名状态 ← `getVerify`（只返回状态，不返回证件号） |
| POST | `/verify/submit` | `{ name, idNo }` → 调权威核验渠道 ← `setVerified`；**证件号不落明文**，加密/脱敏 |

## 15. 互动与通知（传情 / 戳一戳 / 订阅消息）

| 方法 | 路径 | 说明 / 对应 store |
|---|---|---|
| POST | `/interactions` | `{ type }` type∈[miss,hug,kiss,night,poke,remind,...] ← `logInteraction`；WS 推 `affection.received` |
| GET | `/notifications?cursor=` | 通知列表（赞/传情/纸条/纪念日/匹配/系统） |
| POST | `/notifications/read` | 标记已读 |
| POST | `/subscribe/grant` | 上报用户授权的订阅消息模板 id（`requestSubscribeMessage` 后） |

**订阅消息模板（需在小程序后台申请）**：关心提醒、收到传情/纸条、纪念日提醒、匹配成功、对方上线。

---

## 16. WebSocket 实时事件

- 连接：`wss://api.maoyue.example.com/ws?token=<jwt>`，心跳 30s（兼作在线状态/last_active）。
- 服务端 → 客户端事件（`{ event, data }`）：

| event | 触发 | data |
|---|---|---|
| `mood.updated` | 对方更新心情 | `{ mood }` |
| `note.created` | 对方贴纸条 | `{ note }` |
| `dailyq.answered` | 对方回答每日一问 | `{ answer }` |
| `cat.updated` | 猫状态变化 | `{ cat }` |
| `vault.updated` | 金库变动 | `{ balance, txn }` |
| `affection.received` | 收到想你/抱抱/戳 | `{ type, fromName }` |
| `partner.status` | TA 电量/在线/位置变化 | `{ battery, online, location }` |
| `chat.message` | 新私聊/大厅消息 | `{ threadId, message }` |
| `match.matched` | 匹配成功 | `{ profile }` |

> 不在线时的事件转**订阅消息**推送。

---

## 17. 数据表结构（要点）

```
users(id, openid, unionid, nickname, avatar, theme,
      verified, verify_channel, member_tier, member_expire_at,
      battery, charging, last_lat, last_lng, loc_updated_at,
      last_active_at, created_at)

match_profiles(user_id, gender, age, city, bio, tags_json, looking_for, visible)

invite_codes(code, user_id, expire_at, used_by)
couples(id, user_a, user_b, start_date, status, created_at)   # status: active/unbound

moods(id, couple_id, user_id, date, emoji, text)              # uniq(couple,user,date)
daily_questions(id, couple_id, date, q_index)                 # uniq(couple,date)
daily_answers(id, dq_id, user_id, text)
notes(id, couple_id, from_user, text, created_at)
wishes(id, couple_id, text, done, created_by, created_at)
cats(couple_id PK, name, level, exp, intimacy, fullness, last_date, fed_today, played_today)
anniversaries(id, couple_id, name, date, repeat_yearly)
memories(id, couple_id, user_id, date, text, photo_url, created_at)
dishes(id, couple_id, name, emoji)

vaults(couple_id PK, balance)
vault_txns(id, couple_id, user_id, type, amount, note, created_at, idem_key)

match_actions(id, user_id, target_id, action, created_at)     # action: like/pass
matches(id, user_a, user_b, created_at)
threads(id, type, user_a, user_b, last_msg, updated_at)       # type: private/ai
messages(id, thread_id, from_user, text, audited, created_at)
hall_messages(id, user_id, text, audited, created_at)

orders(id, user_id, plan, amount, wx_transaction_id, status, idem_key, created_at)
verifications(id, user_id, status, channel, created_at)       # 不存明文证件号
interactions(id, couple_id, user_id, type, created_at)
remind_settings(user_id PK, enabled, minutes)
notifications(id, user_id, type, payload_json, read, created_at)
subscribe_grants(user_id, template_id, granted_at)
```

---

## 18. store.js ↔ 接口映射速查

| store.js | 接口 |
|---|---|
| getTheme/setTheme | GET/PUT `/me/settings` |
| getMember/openMember/cancelMember | GET `/membership` · 支付回调 |
| getVerify/setVerified | GET `/verify` · POST `/verify/submit` |
| getCouple/setCouple/loveDays | GET/PUT `/couple` |
| bind/unbind/invite | `/couple/invite` `/couple/bind` `/couple/unbind` |
| getMood/setSelfMood | GET/PUT `/mood/today` |
| getDailyQuestion/answerDailyQuestion | `/daily-question` (+ `/answer`) |
| getNotes/addNote/removeNote | `/notes` CRUD |
| getWishes/addWish/toggleWish/removeWish | `/wishes` CRUD |
| getCat/feedCat/petCat/playCat/renameCat | `/cat` (+ feed/pet/play/name) |
| getAnniversaries/add/remove | `/anniversaries` CRUD |
| getMemories/add/remove | `/memories` CRUD (+ upload) |
| getMenu/addDish/removeDish | `/dining/menu` CRUD |
| getVault/getVaultTx/vaultDeposit/vaultSpend/vaultStats | `/vault` (+ /txns /deposit /spend) |
| getMatchPool/matchAction/resetMatch | `/match/pool` `/match/action` `/match/reset` |
| getHall/sendHall | `/hall` GET/POST |
| getThreads/getThread/sendThread/ensureThreadFor | `/threads` 系列 |
| getStat/logInteraction | POST `/interactions` |
| recordOpen/recordHide/getUsage | 本地为主，可 POST `/usage/report` |
| getPartnerStatus/pokePartner | GET `/status/partner` · POST `/status/poke` |
| getRemind/setRemind/partnerNeedsCare | GET/PUT `/me/remind`（提醒由服务端任务触发） |

---

## 19. 权限与安全要点

1. **会员门禁服务端校验**：`/couple/unbind`、`/match/*` 必须查 `member.isMember`，前端开关只是体验。
2. **资源归属校验**：所有 couple 资源校验 `current_user ∈ couple`；私聊校验是会话成员。
3. **金额安全**：`/vault/*` 用 `Idempotency-Key` 防重复；金额服务端校验、记流水、可加每日/单笔上限。
4. **内容审核**：大厅/私聊/纸条/昵称/资料发布前过 `msgSecCheck`/`imgSecCheck` + 敏感词；留举报、拉黑、人工复核。
5. **隐私最小化**：证件号不落明文；位置可关闭可模糊；电量/位置节流上报；提供注销与数据导出。
6. **限流**：登录、发消息、匹配、金库写操作分别限流防刷。
7. **支付安全**：回调验签、订单幂等、金额与商户号校验；会员状态以服务端为准。

> 实现顺序建议：鉴权/用户 → 情侣绑定 → 心情/纸条/纪念日（打通"双人同步 + WS"）→ 小金库 → 聊天 + 审核 → 会员支付 → 匹配 → 实名 → 状态/提醒推送。
