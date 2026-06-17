# Mnemo · 你的本地 7×24 AI 伙伴

> 在终端本地运行 · **永久记忆、越来越懂你** · **接入任意大模型** · **可学技能、装插件** · 后台 7×24 跑任务

Mnemo 取自记忆女神 **Mnemosyne**——它的第一性原理就是"记住你"。一个长期陪伴、
不断积累对你的了解、可以自主在后台干活的私人 AI 助理。

**核心哲学：零依赖也能跑。** 只要有 Python ≥ 3.10，不装任何第三方库、不配任何
API Key 就能启动完整系统（走离线兜底）；配上任意大模型后，推理与工具能力全面解锁。

```bash
cd mnemo
python -m mnemo doctor      # 环境自检（含能力探测）
python -m mnemo             # 进入对话（默认命令）
```

想要"开箱即真智能"，配一个 Key 即可（任选其一）：

```bash
export ANTHROPIC_API_KEY=sk-ant-...            # Claude
# 或任意 OpenAI 兼容接口（DeepSeek / Kimi / 通义百炼 / 火山方舟 / vLLM …）
export OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.deepseek.com/v1 OPENAI_MODEL=deepseek-chat
# 或零成本本地：启动 Ollama，mnemo 会自动探测接入
```

也可 `pip install -e .` 后直接用 `mnemo` 命令（等价于 `python -m mnemo`）。

---

## 能力总览（全部已实现并测试）

| 你的需求 | Mnemo 的实现 |
| --- | --- |
| 本地终端运行 | 纯 Python CLI，数据全在本地 `~/.mnemo` |
| 7×24 跑任务 | `mnemo daemon` 守护进程 + 持久化调度（`every 30m`/`@hourly`/`@daily 09:00`/`@startup`） |
| 永久记忆 + 越来越懂你 | SQLite 三层记忆（事实/全量对话/进化画像/话题），每轮对话后自动抽取姓名·偏好·话题 |
| **主动式记忆** | **向量语义检索**（`memory.semantic`）+ **记忆巩固/遗忘**（合并近重复、淡忘陈旧）+ **定时提醒**（守护进程到点主动触发） |
| 接入任何大模型 | Provider 抽象 + 通用文本工具协议；`auto` 自动挑可用后端；**可选原生 function-calling**（`native_tools`） |
| 学技能 + **自我进化** | Markdown 技能即学即用；**一次成功任务可自动沉淀为新技能**（`skill distill` / `run --distill`） |
| 下载插件 + **市场** | `plugin install <git/本地>`；**`market search/install`** 从 registry 按名安装技能/插件 |
| **多 Agent 协作** | `delegate` 工具：主 Agent 把聚焦子任务派给角色化子 Agent |
| **多模态 + 语音** | `see`/`view_image`（视觉）、`speak`（TTS）、`transcribe`（whisper STT），按能力探测优雅降级 |
| **安全沙箱** | 全量工具**审计日志**（`mnemo audit`）+ 审批策略（`tools.confirm_danger` / `tools.deny`）+ 高危命令拦截 |
| **跨设备同步** | `sync export/import` 口令加密打包 `~/.mnemo`，换机也"还是那个懂你的它" |
| **图形界面 + 团队共享** | `serve` 本地 Web UI（手机/电脑），`--host 0.0.0.0 --token` 局域网多人共用一份记忆 |
| **记忆图谱** | `memory graph` 导出可拖拽的关系图 HTML；语义检索叠加 **LSH 近似最近邻**加速 |
| **容器沙箱** | `sandbox.engine=docker/podman` 时 `run_shell` 在容器内 `--network none` 隔离执行 |
| **接入 MCP 生态** | `mnemo mcp add/test`：把任意 Model Context Protocol 服务（文件系统/搜索/GitHub/数据库…）的工具并入 Mnemo（stdio JSON-RPC，纯标准库） |
| **逐字流式输出** | 交互对话实时打字机效果（`ui.stream`）；工具调用步骤不回显其 JSON，仅最终答案流式 |
| **用量与成本观测** | `mnemo usage`：今日/7天/累计/按模型 的 token 计量；真实用量优先、拿不到则本地估算；成本仅在 `config.pricing` 配置后才计算 |

---

## 常用命令

```bash
# 对话与任务
mnemo                       # 交互对话。内置 /memory /profile /skills /provider /forget /distill /new
mnemo run "把当前目录 README 总结成3点"
mnemo run "研究X并给方案" --distill research-flow   # 完成后把过程沉淀为技能
mnemo -v run "..."          # 显示思考与工具细节

# 记忆（永久 + 主动）
mnemo memory profile        # 看"它对你的了解"
mnemo memory add "我女儿生日 5/20" --importance 5
mnemo memory search 生日
mnemo memory remind "给妈妈打电话" --when "in 2h"    # 守护进程到点主动提醒
mnemo memory reminders
mnemo memory consolidate    # 主动巩固：合并近重复、淡忘陈旧
mnemo memory backfill       # 为记忆补算语义向量（需后端支持 embed）

# 大模型后端
mnemo provider list / test
mnemo config set native_tools true     # 对支持的后端启用原生 function-calling
mnemo config set memory.semantic true  # 启用向量语义检索

# 接入 MCP 服务（整个 MCP 工具生态为你所用）
mnemo mcp add filesystem --command npx --arg -y \
      --arg @modelcontextprotocol/server-filesystem --arg /data
mnemo mcp test filesystem               # 连接并列出其工具（注册名形如 filesystem.read_file）
mnemo mcp list

# 用量与成本观测
mnemo usage                              # 今日/7天/累计/按模型 的 token 用量
mnemo config set pricing.gpt-4o-mini '{"in":0.15,"out":0.6}'   # 配单价后才显示成本

# 技能与插件
mnemo skill list / show <名> / new <名> / learn --url <md> / distill --name <名>
mnemo plugin install ./examples/plugins/hello
mnemo market --registry ./examples/registry.json list
mnemo market --registry ./examples/registry.json install hello

# 图形界面（手机/电脑浏览器）与团队共享
mnemo serve                              # 本地 Web UI：http://127.0.0.1:8765
mnemo serve --host 0.0.0.0 --token 口令  # 局域网团队共享（多人共用一份记忆）

# 记忆图谱（自包含 HTML，可拖拽）
mnemo memory graph --out mnemo-graph.html

# 多模态与语音
mnemo see photo.jpg --prompt "图里有什么"
mnemo see clip.mp4                        # 视频：抽关键帧逐帧理解（需 ffmpeg）
mnemo speak "你好，我是 Mnemo"
mnemo voice                               # 语音对话：录音→转写→回答→朗读

# 市场信任链
mnemo market --registry r.json --key K sign     # 给 registry 签名
mnemo market --registry r.json --key K verify    # 校验签名
mnemo market rate hello 5 --note 好用            # 本地评分

# 7×24 守护、安全、同步
mnemo task add --name 每日简报 --every "@daily 08:30" --prompt "用 daily-briefing 技能做今日简报"
mnemo daemon                # 启动守护进程（到点跑任务 + 触发提醒 + 每日巩固记忆）
mnemo audit                 # 工具调用审计日志
mnemo config set sandbox.engine docker     # run_shell 改为容器内隔离执行
mnemo sync export backup.mnemo --passphrase 你的口令
mnemo sync import backup.mnemo --passphrase 你的口令

mnemo doctor                # 环境自检 + 能力探测
```

---

## 架构

```
mnemo/
├─ cli.py          命令行入口：串起全部能力
├─ agent.py        核心循环：文本工具协议 / 原生 function-calling 双路径 + 记忆固化 + 轨迹
├─ config.py       分层配置：默认 < config.json < .mnemo.json < 环境变量
├─ memory.py       永久记忆：facts/episodes/profile/topics/reminders；关键词+向量检索；巩固/遗忘
├─ tools.py        工具：文件/Shell/网页/记忆/提醒/委派/视觉/语音；审批与拦截
├─ skills.py       技能：Markdown 加载、相关性注入、learn 学习、distill 自我进化
├─ plugins.py      插件：本地/git 安装，register(ctx) 注入 工具/技能/Provider
├─ market.py       市场：registry 搜索/安装 + HMAC 签名校验 + sha256 完整性 + 本地评分
├─ mcp.py          MCP 客户端：stdio JSON-RPC 接入任意 MCP 服务，工具并入 registry
├─ usage.py        用量观测：token 计量（真实用量优先 + 本地估算）+ 可选成本
├─ sync.py         跨设备同步：打包 + 口令加密（PBKDF2 + SHA256 流 + HMAC）
├─ serve.py        本地 Web 图形界面 + JSON API（团队共享）
├─ viz.py          记忆图谱渲染（内联力导向 HTML）
├─ media.py        视频关键帧抽取（ffmpeg）
├─ voice.py        语音对话：录音 / whisper 转写 / TTS
├─ daemon.py       守护进程：任务调度 + 主动提醒 + 每日记忆巩固
├─ providers/      大模型后端：base 抽象 + anthropic/openai/ollama/offline + 注册表(auto)
└─ skills_builtin/ 内置技能
```

**为什么用"文本工具协议"作默认？** 目标是接入**任何**大模型（含本地开源）。统一的
` ```tool {json} ``` ` 是兼容性最大公约数；对 OpenAI/Anthropic 可一键切换 `native_tools=true`
走更稳的原生函数调用。

---

## 写一个插件（30 秒）

```python
# my-plugin/entry.py   （配 my-plugin/plugin.json: {"name":"my-plugin","entry":"entry.py"}）
def register(ctx):
    ctx.tools.add("greet", "打个招呼", {"name": "名字"},
                  lambda args, c: "hello " + args.get("name", "world"))
    # ctx.register_provider("my_llm", MyProvider)   # 还能接入全新大模型后端
```

```bash
mnemo plugin install ./my-plugin
```

完整示例见 [`examples/plugins/hello`](examples/plugins/hello)。
⚠ 插件会执行任意代码，只安装可信来源（CLI 安装时会二次确认）。

---

## 测试

```bash
python -m unittest discover -s tests -v   # 67 项全链路冒烟，全部通过
```

覆盖：记忆/画像、语义检索+LSH ANN、巩固/遗忘、提醒、工具循环、原生 function-calling、
自我进化技能、多 Agent 委派、安全审计/策略、容器沙箱、市场签名/评分、加密同步、
记忆图谱、Web 服务（含鉴权）、多模态/语音、**MCP 客户端（自带假服务端到端）**、
**逐字流式输出**、**用量计量与定价**。

## 路线图（已大量落地，继续推进）

已实现：主动式记忆、自我进化技能、向量+ANN、原生工具调用、多 Agent、市场签名评分、
加密同步、多模态+语音、安全沙箱、记忆图谱、Web GUI、局域网团队共享、
**MCP 客户端（接入整个 MCP 工具生态）**、**逐字流式输出**、**用量与成本观测**。

继续探索：官方去中心化市场托管、记忆图谱的因果/时间维度、桌面/移动原生端、
实时语音流（边说边答）、流式响应下的精确用量回传、多用户权限与共享记忆的细粒度隔离。

## 数据与隐私

所有记忆与配置都在本地 `~/.mnemo`（可用 `MNEMO_HOME` 改）。密钥优先从环境变量读取，
不强制写入磁盘。删除 `~/.mnemo/mnemo.db` 即"失忆"；`sync` 导出的备份默认建议加口令。

> 这是与同仓库「AI句灵」社交产品相互独立的全新子项目。
