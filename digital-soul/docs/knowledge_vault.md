# 自生长知识库（Claude × Obsidian）

让数字分身把学到的、聊到的知识，一篇篇写成 **Obsidian 笔记**，自动连成知识图谱，
越长越大、越连越密——你随时能用 [Obsidian](https://obsidian.md) 打开 `data/vault/` 看那张图。

完全**本地优先**：就是一个目录里的 `.md` 文件，标准 Obsidian 语法，能 git、能离线、能换任何 markdown 工具打开。

## "自生长"长在哪

- **自动连链**：写新笔记时，正文里提到的"已有笔记"会自动连成 `[[双链]]`——图谱自己长起来。
- **自动建桩**：你写了 `[[豆瓣酱]]` 但还没这篇，它自动建一篇"（待充实）"的桩，保持图谱连通。
- **反向链接 / 标签索引 / 孤岛检测 / 关联建议**：随时知道谁连了谁、哪些还孤零零、哪两篇也许该连。
- **总览 MOC**：`_index.md` 自动汇总统计、标签索引、孤岛、待充实，是知识库的门面。
- **每日流水**：`日记/<日期>.md` 记当天聊到的，带 `[[链接]]`。

## 对分身说（写对话里就能长）

```
把「回锅肉」记进知识库：川菜名菜，二刀肉先煮再炒，配蒜苗豆瓣。
把川菜记进知识库：八大菜系之一，回锅肉麻婆豆腐都是川菜。   ← 自动连上[[回锅肉]]
知识库里关于回锅肉                                       ← 看正文 + 谁提到它 + 关联建议
知识库里都有啥
整理知识库                                              ← 统计 + 建议 + 刷新 _index.md
```

## 命令行（`scripts/vault.py`，操作的是同一座 `data/vault`）

```bash
python scripts/vault.py demo                 # 撒几篇互相关联的，先看它怎么长
python scripts/vault.py add 回锅肉 "川菜名菜…" --tags 川菜,家常菜
python scripts/vault.py capture "妈最拿手的是 [[回锅肉]]" --tags 妈
python scripts/vault.py find 回锅肉           # 正文 + 反链 + 关联建议
python scripts/vault.py consolidate          # 孤岛 / 待充实 / 关联建议
python scripts/vault.py index                # 生成 _index.md 总览
python scripts/vault.py --root /想要的/路径 list
```

然后用 Obsidian 打开 `data/vault/`，在「图谱视图」里就能看见它连成的网。

## 代码结构

- `dsoul/obsidian.py`：Obsidian markdown 的渲染/解析（frontmatter、`[[双链]]`、`#标签`），零依赖、纯逻辑可单测。
- `dsoul/knowledge_vault.py`：`Vault` —— 写/长/捕获、自动连链与建桩、图谱（反链/孤岛/标签）、关联建议、整理、日记、总览。
- `Agent.knowledge_vault()` / `knowledge_vault_handle()`：对话入口；库根在 `data/vault`（`config/identity.yaml` 里 `knowledge_vault:` 可改路径）。

## 隐私

知识库可能含个人内容，已在 `.gitignore` 里排除 `data/vault/`（默认不入库）。
想分享某些笔记，单独拷出来或换个公开目录即可。

## 接本地大模型更聪明

这套引擎不依赖大模型也能跑（连链靠"提到已有笔记名"的精确匹配）。接上本地 Ollama 后，
可以让模型从对话里**自动提炼概念、起标题、判断该连哪些笔记**，自生长会更"懂"。
