# SUNO 歌词与曲风标准（生成对齐用）

本文件是 `llm.js` 生成歌词/曲风时遵循的标准，也是你自己写词时的参考。SUNO 会更新，但下面这套核心写法长期通用。

## 一、歌词结构：方括号 meta-tag

SUNO 靠**英文方括号标签**识别歌曲结构，标签本身不会被唱出来。标签始终用英文（SUNO 对英文结构标签识别最准），**歌词正文用目标语言**。

常用结构标签（按出现顺序）：
- `[Intro]` 前奏
- `[Verse]` / `[Verse 1]` / `[Verse 2]` 主歌
- `[Pre-Chorus]` 预副歌（情绪爬升）
- `[Chorus]` 副歌（记忆点，最重要）
- `[Post-Chorus]` 副歌尾钩
- `[Hook]` 钩子句
- `[Bridge]` 桥段（转折/升华）
- `[Refrain]` 叠句
- `[Break]` / `[Interlude]` 间奏
- `[Instrumental]` 纯器乐段
- `[Guitar Solo]` / `[Solo]` 独奏
- `[Outro]` / `[End]` 尾声

制作/演唱提示也可用方括号插在段落前，用来指挥情绪与编曲：
`[Building intensity]`、`[Whispered]`、`[Powerful vocals]`、`[Soft piano]`、`[Beat drop]`、`[Half-time]`、`[Acappella]`。

## 二、人声细节：圆括号

圆括号里放**和声、加花、回声、气声**等，会被当作演唱内容轻声处理：
```
[Chorus]
我还在这里 (still here)
等风把答案吹来 (oooh-woah)
```

## 三、歌词硬约束

- **总字数**：控制在 **3000 字符以内**（SUNO 有上限，超了会被截断；留余量最安全）。
- **段落**：至少包含 `[Verse]` 与 `[Chorus]`；完整结构推荐 Intro→Verse→Pre-Chorus→Chorus→Verse→Chorus→Bridge→Chorus→Outro，但不必全用，3–5 段即可。
- **每行可唱**：一行别太长，口语顺、有韵脚、有记忆点。副歌要能记住、能传唱。
- **纯器乐**（instrumental）：不写歌词，或只用 `[Instrumental]` 之类结构+情绪标签；`style` 里明确无人声。

## 四、语言模式（本工具支持三种）

CSV 的 `language` 列（或 .env `DEFAULT_LANGUAGE`）决定：

| 取值 | 行为 |
|---|---|
| `中文` / `zh` / `chinese` | 正文全中文，结构标签仍英文 |
| `英文` / `en` / `english` | 正文全英文 |
| `双语` / `中英` / `中英文` / `bilingual` | **主歌中文、副歌英文**（或穿插），这是 SUNO 上很讨喜的做法：既有母语叙事又有英文记忆点。也可同段中英对照 |

双语示例：
```
[Verse]
夜色把城市折叠成一封信
我把想念写在没寄出的行

[Chorus]
Hold on to the light (别放手)
We'll be alright tonight (我们会没事的)
```

## 五、曲风字段（Style of Music）标准

`style` 是喂给 SUNO「Style of Music」框的，逗号分隔的**英文音乐术语**，越精准越好。建议覆盖这几维：

`流派, 人声类型, 情绪, 乐器/制作, 速度`

例：
- `city pop, female vocal, dreamy, warm synth, 90bpm`
- `trap, male rap vocal, dark, 808 bass, hard-hitting, 140bpm`
- `folk ballad, soft male vocal, nostalgic, acoustic guitar, fingerpicking`
- 纯器乐：`ambient piano, instrumental, no vocals, soft pads, 60bpm, meditative`

约束：
- **英文为主**，用 SUNO 认识的通用音乐术语。
- **≤ 200 字符**，精炼不堆砌。
- **绝不写歌手/乐队真名**（如 Jay Chou、Taylor Swift）——SUNO 会过滤甚至报错，改用「风格描述」代替（如 `mandopop, R&B-influenced`）。

## 六、歌名（Title）

短、有记忆点、不带书名号。中文歌名或英文歌名都可，跟随歌曲语言基调即可。

## 七、生成输出契约（llm.js 使用）

模型必须返回纯 JSON（无解释、无代码块）：
```json
{ "title": "...", "style": "...", "lyrics": "..." }
```
其中 `lyrics` 是带 `[Verse]/[Chorus]` 等英文结构标签、正文按语言模式的完整歌词；纯器乐时为 `""`。
