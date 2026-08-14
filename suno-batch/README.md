# SUNO 批量挂机 🎵

读一份 CSV（每行一首歌）→ 大模型自动生成 **歌名 / 曲风标签 / 分段歌词** → Playwright 驱动你自己登录好的浏览器，逐首填进 SUNO 创作面板并点生成。带终端控制台，可暂停/跳过/退出，支持断点续跑。

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
| `language` | 歌词语言 | 用 .env 的 `DEFAULT_LANGUAGE` |
| `mood` | 情绪基调 | 可空 |
| `title` | 歌名 | **留空则大模型生成** |
| `style` | 曲风标签（喂给 SUNO 的 Style） | **留空则大模型生成** |
| `lyrics` | 歌词（多段用 `\n` 或表格内换行） | **留空则大模型生成** |
| `instrumental` | `true`=纯器乐（不填词） | 默认 false |

> 三项（title/style/lyrics）都填满的行不会调用大模型，直接用你写的。

## 三、跑起来

```bash
npm run login    # ① 第一次：弹出浏览器，手动登录 SUNO（登录态会记住，之后免登）
npm run gen      # ② 可选：先只生成内容落盘（var/results.jsonl），审歌词
npm run dry      # ③ 可选：只填表不点生成，验证选择器和填入效果
npm start        # ④ 正式挂机
```

挂机时终端热键：**p** 暂停/继续 · **s** 跳过当前等待 · **q** 优雅退出。
额度不足会自动暂停并提示，充值后按 **p** 继续（会重试当前这首）。

**断点续跑**：进度写在 `var/results.jsonl`，中断后重跑 `npm start` 自动跳过已成功的。想全部重来就删掉这个文件。

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
├── .env.example         大模型与节奏配置模板
└── src/
    ├── run.js           主流程 + CLI
    ├── suno.js          Playwright 页面操作（登录/填表/生成/额度检测）
    ├── llm.js           大模型生成 歌名/曲风/歌词
    ├── tasks.js         CSV 解析 + 断点续跑
    ├── control.js       终端控制台与热键
    └── config.js        配置加载
```
