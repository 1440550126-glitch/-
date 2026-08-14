# SUNO 批量挂机 🎵

读一份 CSV（每行一首歌）→ 大模型自动生成 **歌名 / 曲风标签 / 分段歌词**（完全对齐 SUNO 歌词标准，支持中文/英文/双语）→ Playwright 驱动你自己登录好的浏览器，逐首填进 SUNO 创作面板并点生成。**终端控制台或网页控制面板**任选，可暂停/跳过/停止，支持断点续跑，还能自动下载生成好的音频。

歌词标准细节见 [`references/suno-lyric-standard.md`](references/suno-lyric-standard.md)。
**第一次在本机跑，请按 [`docs/本地验收清单.md`](docs/本地验收清单.md) 一步步验收校准**（含选择器失效的修法）。

> ⚠️ 仅用于自动化你**自己的 SUNO 账号**。请遵守 SUNO 的服务条款与额度限制；默认节奏很保守（每首间隔 ~45s 且随机抖动），别改太激进把账号刷崩。

## 一、装依赖（只需一次）

```bash
cd suno-batch
npm install
npx playwright install chromium   # 装浏览器内核
```

## 二、配置

```bash
cp .env.example .env      # 填 LLM_API_KEY 等（复用主项目同名变量即可）
cp tasks.example.csv tasks.csv   # 按需改任务
```

**CSV 列**（`tasks.example.csv` 有示例）：

| 列 | 含义 | 留空会怎样 |
|---|---|---|
| `theme` | 主题/灵感（给大模型的种子） | 建议填 |
| `genre` | 期望曲风提示 | 大模型自选 |
| `language` | 歌词语言：`中文` / `英文` / `双语` | 用 .env 的 `DEFAULT_LANGUAGE` |
| `mood` | 情绪基调 | 可空 |
| `title` | 歌名 | **留空则大模型生成** |
| `style` | 曲风标签（喂给 SUNO 的 Style） | **留空则大模型生成** |
| `lyrics` | 歌词（多段用 `\n` 或表格内换行） | **留空则大模型生成；给片段会按结构补全** |
| `instrumental` | `true`=纯器乐（不填词） | 默认 false |
| `playlist` | 歌单/标签 | **留空则按曲风/情绪自动归类** |

> 三项（title/style/lyrics）都填满且歌词已带 `[Verse]` 之类结构标签的行，不会调用大模型，直接用你写的。
>
> **语言 = 双语** 时：主歌中文叙事 + 副歌英文记忆点（SUNO 上很讨喜的做法）。生成严格遵循 SUNO 结构标签（`[Verse]` `[Chorus]` `[Bridge]`…）、括号和声/加花、曲风字段规范（英文术语、≤200 字符、绝不写歌手真名），细节见 `references/suno-lyric-standard.md`。

## 三、跑起来

**方式 A · 网页控制面板（推荐，直观）**
```bash
npm run login          # ① 第一次：弹出浏览器登录 SUNO（登录态记住，之后免登）
npm run panel          # ② 打开 http://localhost:8787 → 进度条/当前歌/实时日志 + 暂停/跳过/停止按钮
npm run panel -- --download   # 同时自动下载生成好的音频到 var/downloads/
```

**方式 B · 终端**
```bash
npm run login    # ① 登录一次
npm run gen      # ② 可选：只生成内容落盘（var/results.jsonl），先审歌词
npm run dry      # ③ 可选：只填表不点生成，验证选择器和填入效果
npm start        # ④ 正式挂机（终端热键 p 暂停 / s 跳过等待 / q 退出）
npm run download # 正式挂机 + 自动下载音频
```

额度不足会**自动暂停**并提示，充值后点“继续”/按 `p` 继续（会重试当前这首）。

**失败自动重试**：单首生成失败会自动重试 `RETRY_MAX` 次（默认 2 次，额度不足不算——那会自动暂停）。跑完后想只补之前失败的：`npm run retry`。

**断点续跑**：进度写在 `var/results.jsonl`，中断后重跑自动跳过已成功的。想全部重来就删掉这个文件。

## 四、每日定时挂机

长期挂着，每天到点自动跑一轮（适合每天匀速产出、别一次性刷爆额度）：
```bash
npm run daily              # 每天 DAILY_AT（默认 03:00）自动跑，Ctrl+C 退出
node src/scheduler.js --now --download --playlist   # 立即先跑一轮，之后每天定时；顺带下载+归类歌单
```
`.env` 里 `DAILY_AT=03:00` 设时间、`DAILY_LIMIT=20` 设每天最多几首（0=不限）。登录态持久化，通常无需每天重登。

## 五、自动打标签 / 归类歌单

每首歌会归到一个歌单/标签：CSV 填了 `playlist` 就用你的；留空则按曲风/情绪**自动归类**（规则见 `src/tagger.js`，可自改）。

- **本地归档（可靠）**：开 `--download` 时，音频按歌单分文件夹存到 `var/downloads/<歌单>/`；每轮结束生成歌单索引 `var/playlists.md`。
- **SUNO 站内歌单（best-effort）**：加 `--playlist`，生成完自动去 SUNO 资料库把歌加进对应歌单。依赖页面结构，改版可能失效（失效不影响生成/下载，可退回手动加）；选择器在 `config.json` 的 `selectors.playlist.*`，用 `npm run inspect` 核对更新。

```bash
npm run panel -- --download --playlist   # 面板挂机 + 下载 + 站内歌单归类
npm start -- --playlist                   # 终端挂机 + 站内歌单归类
```

**自动下载音频（best-effort）**：加 `--download` 后，脚本监听 SUNO 前端接口捞出生成好的音频，用你的登录态下到 `var/downloads/`（清单 `var/downloads.jsonl`）。因为依赖 SUNO 内部接口形态，改版后可能失效——失效时**不影响生成**，只是下不到，可退回手动在 SUNO 资料库下载。

## 六、多账号轮换（额度不够用时）

多个 SUNO 账号轮流用，一个号额度耗尽自动切下一个，全部耗尽才暂停：

```bash
# .env 里配好账号目录（每个目录一个号）
# ACCOUNTS=.suno-profile-a,.suno-profile-b,.suno-profile-c
npm run login:all          # 逐个弹出浏览器，把每个号都登录一次
npm start -- --rotate      # 挂机；配了多个 ACCOUNTS 时默认就开轮换
```
下载与去重跨账号贯通（同一首不会重复下）。单账号时这套完全不影响。

## 七、生成质量回捞（自动筛掉跑坏的重生成）

加 `--quality`：每轮生成后，用 SUNO 返回的时长/状态给每首打分——**时长过短、状态异常、没出音频**的判为「跑坏」，自动标记重排，下次 `npm run retry` 或每日定时会重新生成它。

```bash
npm start -- --download --quality        # 下载 + 质检回捞
npm run panel -- --download --quality --playlist --rotate   # 全家桶
```
阈值在 `.env` 的 `QUALITY_MIN_SEC`（默认 30 秒）。这是基于元数据的可靠信号（跑坏的生成通常时长极短或状态异常）；「听内容判跑题」需要音频模型，属后续增强。

## 八、SUNO 改版了 / 找不到输入框怎么办

SUNO 页面 DOM 会不定期变，脚本靠 `config.json` 里的**候选选择器**定位（每个字段一组，逐个尝试，命中即用，所以单个失效也不至于全崩）。若报“找不到 xxx 输入框”：

```bash
npm run inspect   # 打开浏览器停在创作页
```

在页面上右键要填的输入框 → 检查，看它的 `placeholder` / `aria-label`，然后把对应选择器加到 `config.json` 里那个字段候选组的**最前面**即可。常见形态：
- 歌词框：`textarea[placeholder*="lyrics" i]`
- 曲风框：`textarea[placeholder*="style" i]`
- 歌名框：`input[placeholder*="title" i]`

## 九、节奏与安全建议

- `.env` 里 `BETWEEN_SONGS_MS` 控制每首间隔，默认 45s + 随机抖动，别调太小。
- `HEADLESS=false`（默认）能看到窗口便于盯梢；确认稳定后可设 `true` 省资源。
- 登录态、`.env`、生成结果都在 `.gitignore` 里，不会误提交。

## 文件结构

```
suno-batch/
├── config.json          SUNO 选择器 + 节奏（改版时改这里）
├── tasks.example.csv    任务模板
├── .env.example         大模型/节奏/面板/下载 配置模板
├── references/
│   └── suno-lyric-standard.md   SUNO 歌词与曲风标准（生成对齐 + 你自己写词参考）
└── src/
    ├── run.js           终端入口 + CLI（含 --retry-only / --playlist / --download）
    ├── panel.js         网页控制面板（HTTP + SSE）
    ├── panel-page.js    面板前端页面（内联）
    ├── scheduler.js     每日定时挂机（--now 立即先跑一轮）
    ├── engine.js        批量核心循环（各端共用，含失败重试 + 账号轮换）
    ├── session.js       浏览器会话/多账号轮换/登录（单账号也走这里）
    ├── suno.js          Playwright 页面操作（登录/填表/生成/额度检测）
    ├── llm.js           大模型生成 歌名/曲风/歌词（对齐 SUNO 标准 + 校验）
    ├── tagger.js        自动打标签/归类（规则可自改）
    ├── playlist.js      SUNO 站内歌单归类（best-effort UI）
    ├── quality.js       生成质量回捞（时长/状态质检，跑坏的重排）
    ├── harvest.js       自动下载生成的音频（网络捕获，按歌单分文件夹）
    ├── tasks.js         CSV 解析 + 断点续跑 + 重试队列 + 歌单索引
    ├── control.js       终端控制台与热键
    └── config.js        配置加载
```
