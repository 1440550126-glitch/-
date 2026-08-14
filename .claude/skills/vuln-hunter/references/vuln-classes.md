# 漏洞类别 · 检测判据、grep 线索、真实 vs 误报

每一类都给：**怎么找（source→sink 判据 + grep 线索）**、**怎么确认是真的（别当喊狼来了的人）**、**常见误报**。
grep 线索是「去哪看」的起点，不是判据本身——**必须读全上下文再下结论**。

---

## 1. 认证 Authentication

**找**：定位签发/校验凭据的代码——`login`、`token`、`jwt`、`session`、`verify`、`sign`、`bcrypt`/`hash`、`cookie`。
**攻击点**：
- JWT：`alg:none` 接受？密钥硬编码/弱？只解码不验签（`decode` vs `verify`）？过期不校验？
- 会话：token 用 `Math.random()`/时间戳生成（可预测）？登出不失效？固定会话（session fixation）？
- 密码：明文/弱哈希（md5/sha1 无盐）存储？重置流程 token 可预测/不过期/可枚举？
- 校验码/OTP：可爆破（无限流）？一码多用？回显在响应里？
- 比对：`==`/`===` 直接比签名/token（时序侧信道，应 `timingSafeEqual`）。
**确认**：能构造一个「不该通过却通过」或「能伪造他人身份」的具体请求。
**误报**：框架已用安全库正确校验；token 虽短但服务端还有二次校验。

## 2. 授权 / 越权 Authorization（Web 应用头号真实漏洞）

**找**：**每一个**读写用户数据的接口，看它有没有校验「当前登录用户是否有权操作这条具体数据」。grep：路由定义、`req.user`/`ctx.user`/`session.uid`、`where id =`。
**攻击点**：
- **IDOR**：`GET /order/:id` 只按 id 查，不校验 `order.uid === currentUser`。把 id 换成别人的即越权。数字自增 id 尤其危险。
- **垂直越权**：管理接口只靠「前端不显示按钮」保护，直接调用即通。缺 `isAdmin` 中间件，或中间件漏挂在某几个路由上。
- **强制浏览**：`/admin/*` 未统一鉴权；某个子路由忘了加。
- **越权字段**：能改本不可改的字段（见 mass assignment）。
**确认**：明确指出「接口 X 在第 N 行用了 id 查询，但没有任何一行校验归属」。对比同仓库*有*做校验的接口作反证。
**误报**：鉴权在上游中间件里统一做了（要读中间件确认覆盖了该路由）；数据本就是公开的。

## 3. SQL / NoSQL 注入

**找**：查询构造处。grep：`query(`、`execute(`、`` ` `` 模板串里嵌变量、字符串 `+` 拼进 SQL、`$where`、`.find(` 直接吃对象、`sequelize.query`、`db.prepare` 后又拼接。
**判据**：用户输入**直接拼进**查询字符串 = 高危；用参数化占位符（`?`/`$1`/命名参数）= 安全。
**NoSQL**：body 直接当查询对象（`{username: req.body.username}` 若 body 传 `{$ne:null}`）；`$where`/`$regex` 注入。
**确认**：给出注入 payload 和它会改变查询语义的原因（如 `' OR '1'='1`、`'; DROP`、`{"$gt":""}`）。
**误报**：ORM 参数化了；输入是被强转成数字/枚举白名单的；拼接的是常量不是用户数据。

## 4. 命令注入 / RCE

**找**：grep `exec(`、`execSync`、`spawn`（`shell:true`）、`` child_process ``、反引号、`eval(`、`new Function(`、`vm.runIn*`、`require(` 变量、模板引擎 `compile`。
**判据**：用户输入进入 shell 命令字符串 / 代码求值 = Critical。
**确认**：指出可控段落与注入字符（`;`、`|`、`$()`、`&&`、换行）。
**误报**：`spawn` 用数组参数且 `shell:false`（参数不经 shell 解析）；`eval` 的输入是常量。

## 5. SSRF · 服务端请求伪造

**找**：grep `fetch(`、`axios`、`http.get`、`request(`、`new URL(`、图片/头像「按 URL 抓取」、Webhook 回调、导入远程资源、SSO 元数据。
**判据**：用户可控 URL / host 被服务端发起请求。
**攻击点**：打内网（`169.254.169.254` 云元数据、`localhost` 管理面、内网服务）、`file://`/`gopher://`、DNS rebinding、重定向绕过白名单、`@` 混淆、十进制/十六进制 IP。
**确认**：说明能访问到的内部目标与危害。
**误报**：有严格白名单（协议+host 都校验，且校验后不再重新解析）；只允许固定域名。

## 6. 路径穿越 / 任意文件读写

**找**：grep 文件 API + 用户输入拼路径：`path.join(base, req.xxx)`、`readFile(userPath)`、下载/导出/预览/上传保存、ZIP 解压、模板文件名可控。
**判据**：用户输入进入文件路径且未规范化校验（`../`、绝对路径、`%2e%2e`、空字节、软链接、zip slip）。
**确认**：给出 `../../etc/passwd` 类 payload 与它能读/写到的敏感文件。
**误报**：用 `path.resolve` 后校验仍在 base 目录内；用固定白名单文件名。

## 7. 不可信数据处理

- **原型链污染（JS 特有，重点）**：grep 递归 `merge`/`extend`/`assign`、`JSON.parse` 后合并、`obj[key]=val` 且 key 可控、`lodash.merge`/`set`。攻击：传 `__proto__`/`constructor.prototype` 污染全局，可致 RCE/鉴权绕过/DoS。
- **批量赋值 Mass Assignment**：grep `Object.assign(model, req.body)`、`{...req.body}` 存库、`new Model(req.body)`、`update(req.body)`。攻击：多塞 `isAdmin`/`role`/`balance`/`price`/`status`。判据：是否有字段白名单（pick）？
- **反序列化 / XXE**：`JSON.parse` 一般安全，但 YAML/自定义反序列化、XML 解析开了外部实体、`node-serialize` 之类危险。
- **确认**：给出污染/覆盖的具体字段与后果。**误报**：有白名单 pick、有 schema 校验、对象无原型（`Object.create(null)`）。

## 8. XSS · 跨站脚本

**找**：grep `innerHTML`、`insertAdjacentHTML`、`document.write`、`dangerouslySetInnerHTML`、`v-html`、模板里 `{{{ }}}`/未转义插值、拼 HTML 字符串、`res.send` 直接回显用户输入。
**类型**：反射（输入→响应）、存储（存库→他人页面渲染）、DOM（`location`/`hash`→sink）。
**确认**：追出「用户输入 → 未转义 → 进入 HTML/JS 上下文」的完整路径，给 payload。注意上下文（HTML、属性、JS、URL、CSS 转义规则不同）。
**误报**：框架默认转义（React/Vue 文本插值）；有 CSP 且无 `unsafe-inline`；输出走了正确转义函数。

## 9. CSRF / 客户端

**找**：改状态的接口（POST/PUT/DELETE）是否只靠 cookie 鉴权且无 CSRF token / SameSite / Origin 校验；开放重定向（`Location=用户输入`）；`postMessage` 不校验 `origin`；`window.opener`。
**确认**：说明能诱导受害者浏览器发出的越权写请求。
**误报**：用 Authorization header（非 cookie）鉴权；`SameSite=Strict/Lax` 且非 GET；有 CSRF token 校验。

## 10. 业务逻辑（扫描器盲区 · 你的最大价值）

没有 grep 银弹，靠理解业务。重点审：
- **支付/退款/订单**：金额前端可改？价格从请求体取而非服务端查？退款金额>订单额？重复回调重复发货？回调不验签可伪造「已支付」？
- **配额/额度/优惠券**：并发扣减竞态（先查后扣有窗口）？负数使用返充值？券可叠加/复用/跨账户？
- **状态机**：跳步（直接调「发货」跳过「支付」）？逆向（已完成→改回待处理）？
- **计数/风控**：点赞/投票/签到可刷？限流按什么维度（能换 IP/账号绕过）？
- **游戏逻辑**（本仓库有卧底/狼人杀）：私有信息（词/身份/夜间行动/查验结果）是否只发给该发的人？服务端是否可信裁决，还是信客户端上报？能否读到别人的座位私有通道？
**确认**：写出具体操作序列与非预期结果。这类漏洞最有说服力，务必给「攻击者操作步骤」。

## 11. 敏感信息 / 配置

**找**：硬编码密钥/口令（`recon.sh` 已扫）、日志打印敏感数据、报错回显栈/SQL、`.env`/`.git`/备份可访问、默认口令未改、CORS 过宽（`*` + credentials）、缺安全 header（`X-Content-Type-Options`、`X-Frame-Options`/CSP、`Strict-Transport-Security`）、Cookie 缺 `HttpOnly`/`Secure`/`SameSite`。
**确认**：指出泄露的具体秘密/信息及其可被谁获取。
**误报**：`.env.example` 里是占位符；密钥来自环境变量而非硬编码；调试信息仅在 dev 环境。

## 12. 加密 / 随机 / 时序

**找**：`Math.random()` 生成 token/密码/OTP；弱哈希（md5/sha1）存密码；ECB 模式；硬编码 IV/salt/key；`==` 比对 HMAC/签名；自研加密。
**确认**：说明可预测性/可爆破性/侧信道如何被利用。
**误报**：`crypto.randomBytes`/`randomUUID`；bcrypt/scrypt/argon2 存密码；`timingSafeEqual` 比对。

---

## 通用确认纪律

1. **走全链路**：从 source 一路读到 sink，确认中间没有有效防护把它挡掉。只看一行就下结论 = 误报之源。
2. **给可复现证据**：请求/参数/payload/前置条件；能给 `curl` 就给。
3. **不确定就标 needs-verification**，写清还差什么证据，别包装成已确认。
4. **同类成片**：找到一个就 grep 同模式全仓，往往一挖一串。
