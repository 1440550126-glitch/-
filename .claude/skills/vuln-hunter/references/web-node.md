# Node / JS / Web / 微信小程序 · 专属 Sink 与陷阱

面向本仓库这类技术栈：**Node 22 零依赖服务端（`node:sqlite` + 原生 `http`）+ 原生 ES Modules 前端 + 管理后台 SPA + 微信小程序**。下面是这套栈里最容易出问题的地方。

## 一、Node 服务端

### SQL（`node:sqlite` / better-sqlite3 风格）
- 危险：`db.prepare(`SELECT ... WHERE id = ${req...}`)`、`db.exec(拼接串)`。
- 安全：`db.prepare('... WHERE id = ?').get(id)`、命名参数 `@id`。
- **重点排查**：`ORDER BY`/`LIMIT`/表名/列名**无法参数化**——若这些来自用户输入（如排序字段、分页），必须走白名单，否则仍是注入。
- 二阶注入：存进 DB 时安全，读出来再拼进另一条查询就中招。

### 命令 / 代码执行
- `child_process.exec/execSync`（走 shell，危险）vs `spawn/execFile` + 数组参数 + `shell:false`（安全）。
- `eval`、`new Function`、`vm`、动态 `require(变量)`、`import(变量)`。
- 模板/Manifest：本仓库有「大模型导演产出 Animation Manifest，客户端当播放器」——若 Manifest 里的字段被前端 `eval` 或拼进 `Function`/直接当选择器/直接 `innerHTML`，就是注入面。审 manifest 从产出到消费的全链路。

### 路径 / 文件
- `fs.readFile/writeFile/createReadStream` + `path.join(base, 用户输入)`。规范化后校验仍在 base 内：`const p = path.resolve(base, name); if (!p.startsWith(base + path.sep)) reject`。
- 静态资源服务：手写的静态文件路由极易路径穿越（`GET /static/../../server/lib/db.js`）。检查有没有 decode 后再拼、空字节、`..` 过滤是否可绕。
- 上传：保存路径/文件名是否用了用户提供的原始名？扩展名/`Content-Type` 校验能否绕（双扩展名、大小写、`image/png` 伪造）？

### 鉴权中间件
- 手写 HTTP 服务（非 Express）常靠「在每个 handler 顶部调 `requireAuth(req)`」——**极易某个 handler 漏调**。逐个路由核对：是否都过了鉴权？管理接口是否都过了 `requireAdmin`？
- token 校验：从 cookie/header 取 token → 查库/验签。看有没有「只 decode 不校验」「过期不管」「用户被封/注销后 token 仍有效」。
- 比对密钥/签名用 `crypto.timingSafeEqual`，不是 `===`。

### SSRF / 外连
- LLM 客户端：本仓库支持「任意 OpenAI 兼容接口，用户填 base_url」。若 base_url / 图片 URL / webhook 来自**用户可控**且服务端直接请求 → SSRF 打内网/云元数据。区分「管理员配置的可信 base_url」和「普通用户可控的 URL」。
- 头像/图片「按 URL 抓取」、导入远程剧本/资源。

### 原型链污染（Node 高发）
- grep 递归合并/深拷贝/`obj[a][b]=c`（a/b 可控）、`JSON.parse` 后 `Object.assign`/自写 merge。
- 影响：污染 `Object.prototype` → 绕过 `if (opts.isAdmin)` 类判断、DoS、甚至配合模板/`child_process` 达 RCE。

### 配置 / 密钥
- **本仓库明确点名**：`.env` 的 `ADMIN_PASSWORD`、`APP_SECRET` 上线前必改；默认后台口令 `admin / jvling-admin-2026`（README 里就写着）——**默认口令 + 管理后台可达 = 直接高危**，务必核实生产是否强制改。
- 硬编码：grep 代码里的 `secret`/`password`/`key`/`token` 常量、`.env.example` 是否含真密钥。
- CORS：手写 `Access-Control-Allow-Origin` 是否回显 `Origin`（等于 `*`）又带 `credentials`。
- 报错：生产是否把栈/SQL/内部路径回显给客户端。

### 竞态（Node 单线程但异步有窗口）
- 「先 `await` 查余额/配额/库存 → 再 `await` 扣减」之间有 await 点 = 并发窗口。支付、星尘额度扣点、优惠、游戏动作限流、验证码一次性——都查有没有原子操作/唯一约束/行锁兜底。
- SQLite：是否用事务 + `UPDATE ... WHERE balance >= x` 原子扣减，还是「读-改-写」。

## 二、原生前端 H5 / SPA

- **XSS**：`innerHTML`/`insertAdjacentHTML`/`document.write` + 用户内容（帖子、评论、昵称、AI 生成文案）。原生前端没有框架自动转义，**存储型 XSS 风险很高**。审：文案/评论/昵称渲染成 DOM 时有没有转义或用 `textContent`。
- **DOM XSS**：`location.hash`/`search`/`localStorage` → sink。
- **CSP**：有没有内容安全策略；`unsafe-inline` 是否让 XSS 可执行。
- **敏感逻辑在前端**：价格/权限/额度判断只在前端做（服务端不复核）= 逻辑漏洞。青少年模式、会员解锁、免费次数若只前端拦，直接调接口绕过。
- **CSRF**：若用 cookie 鉴权，改状态接口要有 CSRF token / SameSite / Origin 校验。
- **开放重定向 / postMessage**：`location = 用户输入`；`message` 事件不校验 `origin`。
- **WebGL/Canvas**：一般不是安全面，但若 shader/manifest 参数可控且被当代码，留意。

## 三、微信小程序（`miniprogram/`）

- **AppSecret 泄露**：`AppSecret`、支付商户密钥**绝不能**出现在小程序前端代码里——必须在服务端。grep 小程序目录里的 `secret`/`mchKey`/`apiKey`。
- **服务端不可信客户端**：小程序上报的 openid、金额、分数、身份都可伪造，服务端必须以自己校验/`code2session` 结果为准，不能信客户端传的 openid。
- **深链参数**：`onLoad(options)` 里的 `scene`/`query` 是外部可控输入，别直接信任（拼接、鉴权跳过）。
- **本地存储**：`wx.setStorage` 里存 token/敏感信息，越狱/调试可读。
- **request 域名与 HTTPS**：是否校验，是否有明文传输敏感数据。
- **登录态**：`code2session` 后 session_key 管理、自定义登录态 token 的签发与失效。

## 四、这类应用的高价值业务逻辑靶点（结合本仓库功能）

- **支付/会员/星尘额度**：金额是否服务端定价、回调是否验签、重复回调幂等、额度并发扣减原子性、退款上限、青少年模式禁消费是否服务端强制。
- **审核绕过**：敏感词三级审核 + 大模型机审——能否用编码/零宽字符/拆字/图片文字绕过；「转人工」队列里的内容会不会已经对外可见；自伤内容处理是否稳妥。
- **AI 暖场 / 计数诚信**：README 声称「AI 点赞不进热度、不伪造热度」——核实实现是否真的隔离；能否刷赞/刷评论/刷话题。
- **桌游私有信息泄露**：卧底词 / 狼人身份 / 预言家查验结果 / 女巫药剂 / 夜间行动，是否**只**通过私有通道发给应得的人；SSE 频道订阅是否鉴权（能否订阅别人房间/别人视角）；服务端是否权威裁决（投票、发言顺序、计时）还是信客户端。
- **越权**：房间管理、后台强制关房、举报处理、用户封禁/注销——普通用户能否触达管理动作（垂直越权）；能否操作他人订单/帖子/资料（水平越权 IDOR）。
