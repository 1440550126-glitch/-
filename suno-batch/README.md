# SUNO 批量挂机 🎵

读一份 CSV（每行一首歌）→ 大模型自动生成 **歌名 / 曲风标签 / 分段歌词**（完全对齐 SUNO 歌词标准，支持中文/英文/双语）→ Playwright 驱动你自己登录好的浏览器，逐首填进 SUNO 创作面板并点生成。**终端控制台或网页控制面板**任选，可暂停/跳过/停止，支持断点续跑，还能自动下载生成好的音频。

歌词标准细节见 [`references/suno-lyric-standard.md`](references/suno-lyric-standard.md)。

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

**断点续跑**：进度写在 `var/results.jsonl`，中断后重跑自动跳过已成功的。想全部重来就删掉这个文件。

**自动下载音频（best-effort）**：加 `--download` 后，脚本监听 SUNO 前端接口捞出生成好的音频，用你的登录态下到 `var/downloads/`（清单 `var/downloads.jsonl`）。因为依赖 SUNO 内部接口形态，改版后可能失效——失效时**不影响生成**，只是下不到，可退回手动在 SUNO 资料库下载。

## 四、SUNO 改版了 / 找不到输入框怎么办

SUNO 页面 DOM 会不定期变，脚本靠 `config.json` 里的**候选选择器**定位（每个字段一组，逐个尝试，命中即用，所以单个失效也不至于全崩）。若报“找不到 xxx 输入框”：

```bash
npm run inspect   # 打开浏览器停在创作页
```

在页面上右键要填的输入框 → 检查，看它的 `placeholder` / `aria-label`，然后把对应选择器加到 `config.json` 里那个字段候选组的**最前面**即可。常见形态：
- 歌词框：`textarea[placeholder*="lyrics" i]`
- 曲风框：`textarea[placeholder*="style" i]`
- 歌名框：`input[placeholder*="title" i]`

## 五、节奏与安全建议

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
    ├── run.js           终端入口 + CLI
    ├── panel.js         网页控制面板（HTTP + SSE）
    ├── panel-page.js    面板前端页面（内联）
    ├── engine.js        批量核心循环（终端/网页共用）
    ├── suno.js          Playwright 页面操作（登录/填表/生成/额度检测）
    ├── llm.js           大模型生成 歌名/曲风/歌词（对齐 SUNO 标准 + 校验）
    ├── harvest.js       自动下载生成的音频（网络捕获，best-effort）
    ├── tasks.js         CSV 解析 + 断点续跑
    ├── control.js       终端控制台与热键
    └── config.js        配置加载
```
