# API 一览

统一返回 `{ok:true, data}` / `{ok:false, error, ...extra}`；鉴权 `Authorization: Bearer <token>`（SSE 用 `?token=`）。限流：登录用户 80 写/300 读每分钟，匿名 30 写。🔒=需登录，👑=需管理员。

## 账号
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册（用户名/密码/昵称，昵称过审核） |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/guest` | 游客一键进入（device_id 绑定） |
| GET | `/api/me` 🔒 | 当前用户（含会员/额度/装备/设置） |
| PATCH | `/api/me` 🔒 | 编辑昵称/简介/头像/设置（关闭暖场、青少年模式…） |
| POST | `/api/me/deactivate` 🔒 | 注销（匿名化） |

## 文案社交
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/posts?tab=rec\|new\|follow\|hot` | 四种信息流（游标/偏移分页，过滤拉黑与隐藏 AI） |
| POST | `/api/posts` 🔒 | 发布（三级审核：拦截/转人工/自伤关怀；自动生成预览卡；触发暖场排队） |
| GET/DELETE | `/api/posts/:id` | 详情 / 删除（作者或管理员） |
| POST/DELETE | `/api/posts/:id/like` 🔒 | 点赞/取消 |
| POST/DELETE | `/api/posts/:id/collect` 🔒 | 收藏/取消 |
| POST | `/api/posts/:id/share` 🔒 | 分享（计数+返回分享文案） |
| POST | `/api/posts/:id/play` 🔒 | 动画播放计数 |
| GET/POST | `/api/posts/:id/comments` | 评论树 / 发评论（支持 parent_id 楼中楼、reply_to_user） |
| DELETE | `/api/comments/:id` 🔒 | 删除（评论者/楼主/管理员） |
| GET | `/api/users/:id` `/api/users/:id/posts` | 主页与作品 |
| POST/DELETE | `/api/users/:id/follow` `/block` 🔒 | 关注 / 拉黑 |
| GET | `/api/me/collects` `/api/me/blocks` 🔒 | 我的收藏 / 拉黑列表 |
| POST | `/api/reports` 🔒 | 举报（post/comment/user/room_message） |

## AI
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ai/preview` 🔒 | 发布前实时预览卡（本地规则，零成本） |
| GET | `/api/ai/styles` 🔒 | 动画风格列表 + 配额状态 + 额度余额 |
| POST | `/api/posts/:id/manifest` 🔒 | **生成文字变动画 Manifest**。免费 ink 3 次/日；会员风格需会员（100 次/日防刷）；高级风格扣星尘额度（会员 8 折），LLM 失败自动落规则引擎 |
| GET | `/api/ai/topic` | 今日话题（AI 生成 · 带标识） |

## 桌游（谁是卧底）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/rooms` | 大厅房间列表（+我所在房间） |
| POST | `/api/rooms` 🔒 | 创建（4-8 人、AI 陪练开关、房主房间主题皮肤纯外观） |
| GET | `/api/rooms/:id` | 房间状态（含**只发给本人**的词）+ 最近消息 |
| POST | `.../join` `/leave` `/ready` `/start` `/kick` 🔒 | 房间动作（start 自动 AI 补位） |
| POST | `.../speak` 🔒 | 描述发言（轮到才能说；不能含自己的词；过审核） |
| POST | `.../vote` 🔒 | 投票（活人、不可投自己、平票无人出局） |
| POST | `.../chat` 🔒 | 闲聊（过审核） |
| GET (SSE) | `/api/rooms/:id/events` 🔒 | state/msg/word(私发)/kicked/closed |
| GET (SSE) | `/api/lobby/events` | rooms 实时列表 + notice（AI 组局提醒） |

## 商城
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/shop/catalog` | 皮肤（含公平声明）+ 会员方案 + 额度包 |
| POST | `/api/shop/orders` 🔒 | 下单（member/skin/credits；**青少年模式拒绝**） |
| POST | `/api/shop/orders/:id/pay` 🔒 | 沙盒支付回调（幂等；正式版换微信/支付宝/IAP 验单） |
| GET | `/api/me/orders` `/api/me/skins` 🔒 | 订单 / 衣橱 |
| POST | `/api/me/equip` 🔒 | 装备/卸下（校验拥有） |

## 管理后台 👑（前缀 `/api/admin`）
`/stats` 总览 ·`/users`+`/users/:id/ban|unban` ·`/posts?status=`+`/posts/:id/action`(approve/reject/remove/restore) ·`/comments`+`/comments/:id/remove` ·`/reports`+`/reports/:id/handle` ·`/warmup`(GET/PUT 配置)+`/warmup/trigger`(手动发帖/重生话题) ·`/skins`+`/skins/:id/update`(调价/上下架) ·`/orders` ·`/ai-usage?days=`(日报/按功能/逐条) ·`/sensitive-words`(增删，30s 生效) ·`/moderation-logs`

## 其他
`GET /api/health` 健康检查 · `GET /api/bootstrap` 启动常量（头像/会员方案/举报原因/合规文案）

## Animation Manifest 协议（v2 摘要）

服务端是导演，客户端是播放器。端无关，Flutter/小程序可按此协议实现渲染器：

```jsonc
{
  "v": 2, "style": "ink", "seed": 1234,
  "emotion": { "key": "孤独", "valence": -0.45, "arousal": 0.25, "intensity": 0.6 },
  "palette": { "bg": ["#1c1d2e", "#272a44"], "ink": "#e8e6f7", "accent": "#9d8cff", "glow": "#7c6cff" },
  "scene": { "name": "有风经过的地方", "weather": "none|rain|snow", "ground": "line|sea|none", "skyline": false, "night": true },
  "text": { "mode": "particle_assemble", "glow": true },
  "actors": [{ "id": "p1", "type": "figure|figure2|cat|heart|brokenheart|moon|sun|cloud|umbrella", "x": 0.5, "y": 0.74, "behavior": "wait|walk|run|hug|look_up|breathe|sleep|bounce|pulse|float" }],
  "particles": [{ "kind": "windline|raindrop|snowflake|petal|star|spark|shard|firefly|bubble", "density": 0.62 }],
  "flows": [{ "from": "text", "kind": "windline", "strength": 0.6 }],
  "timeline": [{ "t": 0, "target": "text", "action": "glow", "dur": 0.7, "sound": "chime" }],
  "soundscape": { "ambient": "wind|rain|waves|night|fire|none", "volume": 0.4 },
  "behavior": { "loop": true, "loopFrom": 3.2, "breath": 0.6, "jitter": 0.24, "speedCurve": "gentle|eager" },
  "duration": 9, "caption": "一句画面旁白（LLM 增强时）",
  "meta": { "generated_by": "rule|llm|llm_premium", "ai_label": "内容由 AI 辅助生成" }
}
```

LLM 增强走"JSON 补丁 + 白名单校验 + 数值钳制"合并进规则基底，模型输出永远不会直接驱动渲染。
