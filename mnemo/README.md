# Mnemo · 你的本地 7×24 AI 伙伴

> 在终端本地运行 · **永久记忆、越来越懂你** · **接入任意大模型** · **可学技能、装插件** · 后台 7×24 跑任务

Mnemo 取自记忆女神 **Mnemosyne**——它的第一性原理就是"记住你"。一个长期陪伴、
不断积累对你的了解、可以自主在后台干活的私人 AI 助理。

**核心哲学：零依赖也能跑。** 只要有 Python ≥ 3.10，不装任何第三方库、不配任何
API Key 就能启动完整系统（走离线兜底）；配上任意大模型后，推理与工具能力全面解锁。

```bash
cd mnemo
python -m mnemo doctor      # 环境自检
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

## 你要的功能 → 现在就能用

| 你的需求 | Mnemo 的实现 |
| --- | --- |
| 在终端本地运行 | 纯 Python CLI，`mnemo` / `python -m mnemo`，数据全在本地 `~/.mnemo` |
| 7×24 跑任务 | `mnemo daemon` 守护进程 + 持久化任务调度（`every 30m` / `@hourly` / `@daily 09:00` / `@startup`） |
| 越来越懂你 + 永久记忆 | SQLite 三层记忆：长期事实库 + 全量对话留存 + **不断进化的用户画像**（自动抽取姓名/偏好/高频话题），每轮对话后自动学习 |
| 接入任何大模型 | Provider 抽象 + **通用文本工具协议**：Anthropic / OpenAI 兼容 / Ollama 本地 / 离线兜底，`provider=auto` 自动挑可用后端；插件可注册全新后端 |
| 学技能 | Markdown 技能（带元信息），`mnemo skill learn --url/--file`，命中任务时自动注入；即学即用 |
| 下载插件 | `mnemo plugin install <git或本地路径>`，插件可注入工具/技能/新大模型后端 |
| 市面上没有的 | 见下方[路线图](#路线图想要别人没有的)——主动式记忆、自我进化技能、跨设备记忆同步等 |

---

## 常用命令

```bash
mnemo                       # 交互对话（REPL）。内置 /memory /profile /skills /provider /forget /new
mnemo run "把当前目录的 README 总结成3点"   # 单次任务（带工具：读写文件/Shell/抓网页…）
mnemo -v run "..."          # -v 显示思考与工具调用细节

mnemo memory profile        # 看"它对你的了解"
mnemo memory list           # 列出长期记忆
mnemo memory add "我女儿生日是 5 月 20 日" --importance 5
mnemo memory search 生日

mnemo provider list         # 各大模型后端是否就绪
mnemo provider test         # 实际打一次模型连通性

mnemo skill list            # 技能列表（内置 + 自有）
mnemo skill learn --url https://example.com/some-skill.md
mnemo skill new my-workflow # 生成技能模板

mnemo plugin install ./examples/plugins/hello   # 安装示例插件（新增 coin_flip 工具）
mnemo plugin list

mnemo task add --name 每日简报 --every "@daily 08:30" --prompt "用 daily-briefing 技能给我做今日简报"
mnemo task list
mnemo daemon                # 启动 7×24 守护进程（Ctrl-C 退出）
mnemo daemon --once         # 只巡检一次（可挂到系统 cron）

mnemo doctor                # 环境自检
```

---

## 架构

```
mnemo/
├─ cli.py          命令行入口：把各能力串起来（chat/run/memory/skill/plugin/task/daemon/doctor）
├─ agent.py        核心循环：组装上下文 → 调模型 → 解析工具 → 执行 → 循环 → 固化记忆
├─ config.py       分层配置：默认 < config.json < .mnemo.json < 环境变量
├─ memory.py       永久记忆：facts(事实) / episodes(对话) / profile(画像) / topics(话题)，CJK 友好检索
├─ tools.py        工具：读写文件 / Shell / 抓网页 / 记忆读写 / 时间，可被插件扩展
├─ skills.py       技能：Markdown(带 frontmatter) 加载、相关性匹配注入、learn 学习
├─ plugins.py      插件：本地/git 安装，register(ctx) 钩子注入 工具/技能/Provider
├─ daemon.py       守护进程：任务持久化 + 调度器（间隔/每日/启动）
├─ providers/      大模型后端：base 抽象 + anthropic / openai / ollama / offline + 注册表(auto)
└─ skills_builtin/ 内置技能（daily-briefing / summarize-url）
```

**为什么用"文本工具协议"而不是各家 function-calling？** 因为目标是"接入**任何**大模型"——
包括本地开源模型。让模型用统一的 ```tool {json}``` 代码块发起调用，是兼容性的最大公约数；
未来可为支持原生 tool-use 的后端做增强（见路线图），但默认协议保证人人可用。

---

## 写一个插件（30 秒）

```
my-plugin/
├─ plugin.json        {"name":"my-plugin","version":"0.1.0","entry":"entry.py"}
└─ entry.py
```

```python
# entry.py
def register(ctx):
    def my_tool(args, c):
        return "hello " + args.get("name", "world")
    ctx.tools.add("greet", "打个招呼", {"name": "名字"}, my_tool)
    # ctx.register_provider("my_llm", MyProvider)   # 还能接入全新大模型后端
    # ctx.skills.add_runtime(Skill(...))            # 也能注入技能
```

```bash
mnemo plugin install ./my-plugin
```

完整示例见 [`examples/plugins/hello`](examples/plugins/hello)。
⚠ 插件会执行任意代码，只安装可信来源（CLI 安装时会二次确认）。

---

## 路线图（想要"别人没有的"）

已搭好可扩展底座，下面这些能力按此架构逐步加：

- **主动式记忆**：守护进程定期回顾近期对话，自动提炼/合并/遗忘记忆（记忆的"睡眠巩固"），并主动提醒。
- **自我进化技能**：一次成功的复杂任务后，Agent 自动把过程沉淀为一个新技能（`skill learn` 自动化），越用越强。
- **向量语义记忆**：在现有关键词检索上叠加 provider embedding，命中更准（接口已预留 `Provider.embed`）。
- **原生 tool-use 增强**：为 Anthropic/OpenAI 等接入各家原生函数调用，提速提稳，文本协议作兜底。
- **多 Agent 协作**：把任务拆给子 Agent 并行（研究员/编码/审阅），主 Agent 汇总。
- **技能/插件市场**：`mnemo plugin search`，一个去中心化的技能与插件注册表。
- **跨设备记忆同步**：把 `~/.mnemo` 加密同步，换机也"还是那个懂你的它"。
- **多模态与语音**：语音唤醒、读图、读 PDF。
- **审批与安全沙箱**：高危工具的细粒度确认、容器化执行、操作审计。

---

## 测试

```bash
python -m unittest discover -s tests -v     # 15 项全链路冒烟（记忆/画像/工具循环/调度/技能/离线）
```

## 数据与隐私

所有记忆与配置都在本地 `~/.mnemo`（可用 `MNEMO_HOME` 改）。密钥优先从环境变量读取，
不强制写入磁盘。删除 `~/.mnemo/mnemo.db` 即"失忆"。

> 这是与同仓库「AI句灵」社交产品相互独立的全新子项目。
