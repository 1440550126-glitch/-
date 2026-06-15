# digital-soul · 本地数字分身智能体框架

> 一个**完全本地运行**（16G 内存即可）的智能体：它用**你的性格、记忆和关系**来对话和行动——
> 认得你的人、记得你的经历、知道**听谁的、不听谁的**，并且可以**接入机器人**执行动作。

## 先说清楚它是什么、不是什么

- ❌ **它不是"意识上传"，也不是永生。** 人脑的记忆目前无法被"读"出来，主观意识能否被复制更是悬而未决的哲学难题。
- ✅ **它是一个"很像你、懂你、忠于你"的数字分身。** 你把"自己是谁、家人朋友是谁、经历过什么、什么性格"喂给它，它就能以你的口吻回应、按你设定的关系决定听谁的，并指挥机器人。

把它理解成一面**会成长、会执行的镜子**，而不是你本人。

## 30 秒看懂：跑一遍"一天"

`python scripts/demo.py`（零依赖、隔离运行，不动真实数据）实际输出节选：

```text
🌅 第一天 —— 唤醒「张明」的数字分身（7 条初始记忆）
① 小婷走进画面  → 🗣️ 小婷回来啦！我一直在等你呢。
② 白天对话（自动记进日记）
   张明: 我今天升职了，特别开心，老板当众表扬了我
   张明(分身): 哈哈那必须的，张明…我想起来：…（降级回复；接 Ollama 后用本人口吻）
③ 快递员: 把自己关机   → 我不会听快递员（陌生人）的命令。      ← 授权拦截
④ 夜里「睡一觉」→ 😴 巩固 2 条对话 → 新增 2 条长期记忆
       + 我今天升职了，特别开心，老板当众表扬了我
       + 小婷（老婆）跟我说：周末我们约好去看那部新上映的电影
⑤ 第二天: 我升职的事，你还记得吗？
   → 它翻出来的记忆：我今天升职了，特别开心，老板当众表扬了我    ← 昨天巩固的！
```
认人 → 对话 → 授权 → 巩固 → 次日记得，一条闭环。

## 它能做到你要的每一件事

| 你的需求 | 在本框架里的实现 | 代码 |
|---|---|---|
| 自己是谁 / 模仿性格 | 身份与性格配置 → 人格提示词 | `config/identity.yaml` · `dsoul/persona.py` |
| 朋友 / 老婆 / 家人是谁 | 关系图谱 + 信任等级 | `config/relationships.yaml` |
| 听谁的、什么人不听、爱谁守护谁 | 身份→信任→权限 的授权闸门 | `dsoul/authority.py` |
| 平常干嘛 / 生前经历 | 个人记忆库（RAG 检索） | `dsoul/memory.py` |
| 通过图片/视频/文档认人 | 人脸识别 + 文档摄取 | `dsoul/perception.py` · `scripts/ingest.py` |
| 专属"世界大模型"（本地、16G） | 接 Ollama 跑量化小模型当推理引擎 | `dsoul/llm.py` |
| 接入机器人 | 抽象动作接口（现模拟，后接硬件/ROS） | `dsoul/actions.py` · `dsoul/ros2_robot.py` |
| 语音交流（听 + 说） | 本地 Whisper 转文字 + 离线 TTS | `dsoul/voice.py` · `scripts/voice_chat.py` |
| 情感记忆 / 一生回顾 | 记忆自动打情感标签 + 时间线 | `dsoul/annotate.py` · `scripts/timeline.py` |
| 持续感知 / 主动打招呼 | 摄像头认人，进画面即主动问候 | `dsoul/presence.py` · `scripts/watch.py` |
| 贴近本人文风 | QLoRA 本地微调流水线 | `scripts/finetune_*.py` · `docs/finetune.md` |
| 越用越懂你 | 对话日记 + 睡眠巩固成长期记忆 | `dsoul/journal.py` · `dsoul/consolidate.py` · `scripts/sleep.py` |
| 桌面聊天界面 | Tkinter GUI（Python 自带） | `scripts/desktop.py` |
| 一键常驻 / 部署 | 感知+巩固守护进程 · 树莓派/机器人指南 | `scripts/daemon.py` · `docs/deploy.md` |
| 手机网页状态页 | 实时看"看到谁 / 七情条 / 记了啥 / 派了啥活 / 待办看板" | `dsoul/webstatus.py` |
| 轻量人脸(树莓派) | OpenCV LBPH 后端，免 dlib | `dsoul/perception_opencv.py` |
| 七情六欲 | 情绪随互动起伏、影响口吻 | `dsoul/emotions.py` |
| 多学科视角 | 心理/哲学/医学…思维调度 | `dsoul/knowledge.py` |
| 技能（做饭/家务）| 授权可执行的技能 | `dsoul/skills.py` |
| 隔空指挥智能体 | 大白话派活、主动提议、记进长期记忆、失败入待办并主动跟进重试 | `dsoul/remote_agents.py` · `dsoul/agent.py` · `dsoul/tasks.py` |
| 人格热切换 | 运行时一键换"灵魂" | `dsoul/personas.py` |

## 架构

```
            图片/视频  ─►  感知层 Perception ─┐ （认出"谁来了"）
                                            ▼
  你说的话 ──────────────────────►  授权层 Authority  ──► 听不听？能不能做这个动作？
                                            │
                          ┌─────────────────┼──────────────────┐
                          ▼                 ▼                  ▼
                    记忆库 Memory      人格 Persona        机器人 Actions
                  （想起相关经历）   （组装"你"的人设）    （执行：移动/守护…）
                          └─────────────────┼──────────────────┘
                                            ▼
                              本地大模型 LLM（Ollama，16G 可跑）
                                            ▼
                                   用"你"的口吻回应 / 行动
```

**关于"专属世界大模型"的现实做法**：不要从零训练（16G 跑不动、也没必要）。
正确姿势是拿一个**已训练好、量化过的开源小模型**当"大脑"，再用**个人记忆层**注入"你是谁"。
模型负责*会思考会说话*，记忆 + 人格 + 关系负责*是你*。想进一步贴近你的文风，可在此基础上做 LoRA 微调。

## 快速开始（零重型依赖也能跑）

```bash
cd digital-soul
pip install pyyaml          # 唯一必需依赖

python scripts/demo.py           # ★ 先看这个：一口气跑完"一天"的完整故事
python tests/test_authority.py   # 跑测试
python tests/test_memory.py
python scripts/chat.py           # 命令行对话
python scripts/desktop.py        # 或：桌面图形界面（Tkinter）
```

也可装成命令行工具：`pip install -e .` 后用 `digital-soul demo` / `digital-soul chat` / `digital-soul daemon` 等。

没接大模型时是**降级模式**：仍会认人、查权限、调记忆，只是用模板回复。

### 接入本地大模型（推荐，让回复真正"活"起来）

```bash
# 1. 装 Ollama: https://ollama.com
# 2. 拉一个 16G 内存能跑的 4-bit 量化模型
ollama pull qwen2.5:7b-instruct
# 3. 直接再跑 chat，框架会自动检测到并接上
python scripts/chat.py
```

## 怎么把它变成"你"

1. 改 `config/identity.yaml`：你的名字、性格、口头禅、日常。（`config/examples/` 有温柔妈妈 / 硬汉爸爸 / 搞笑损友模板，复制一份当起点）
2. 改 `config/relationships.yaml`：家人朋友、谁守护、谁的话不听。
3. 灌记忆：把日记/聊天记录/回忆写进 `data/memories/sources/`，或：
   ```bash
   python scripts/ingest.py text "我答应小婷周末去看电影"
   python scripts/ingest.py doc  我的回忆录.md
   ```
4. 登记人脸（需 `pip install face_recognition`）：
   ```bash
   python scripts/ingest.py face xiaoting 小婷的照片.jpg
   ```

## 试试授权系统（"听谁的"）

在 `chat.py` 里：

```
/as 小婷        # 老婆说话 → 守护对象，温柔回应
/do protect     # ✅ 家人有权限 → 机器人进入守护模式
/as 路人甲      # 陌生人
/do shutdown    # ⛔ 没权限，拒绝
/as 老钱        # 被拉黑的人
你好            # 它不信任也不服从他
```

## 接入真实机器人

实现 `dsoul/actions.py` 里的 `RobotInterface`（`say/move/look_at/protect`），
换成驱动你硬件或 ROS 的版本，把它传给 `build_agent(robot=YourRobot())` 即可，
其余逻辑零改动。

## 进阶能力

**🎙️ 语音交流（听 + 说）** —— 模型全在本地，16G 可跑；缺依赖就退化为键盘/打印。
```bash
pip install faster-whisper pyttsx3 sounddevice numpy   # 可选
python scripts/voice_chat.py
# 对麦克风说话 → 本地 Whisper 转文字 → 分身回应 → 离线 TTS 念出来
```

**🕰️ 情感时间线（一生回顾）** —— 每条记忆入库时自动打情感标签（喜悦/悲伤/深情/怀念…）并抽取年份。
```bash
python scripts/timeline.py
```

**🤖 接入 ROS2 机器人** —— `dsoul/ros2_robot.py` 把动作映射到 ROS2 话题（`/cmd_vel`、`/soul/speech`…）。
```python
from dsoul.loader import build_agent
from dsoul.ros2_robot import Ros2Robot
agent = build_agent(robot=Ros2Robot())   # 其余逻辑零改动
```

**👁️ 持续感知 + 主动打招呼** —— 摄像头认出走进画面的人，自动问候（"小婷回来啦！"）。
```bash
python scripts/watch.py                       # 摄像头实时（需 opencv + face_recognition）
python scripts/watch.py --simulate 小婷 老钱   # 无摄像头时模拟演示
```

**🧬 LoRA 微调（逼近你的文风）** —— 用记忆 + 真实聊天记录训练一个很小的 LoRA 适配器。
```bash
python scripts/finetune_prepare.py --chat 微信导出.txt   # 生成数据集
python scripts/finetune_train.py                         # QLoRA 训练（建议有 GPU）
# 训练完把适配器加载回 Ollama/llama.cpp，详见 docs/finetune.md
```

**😴 长期记忆巩固（"睡眠"机制）** —— 平时对话写进日记，定期"睡一觉"提炼成新记忆，越用越懂你。
```bash
python scripts/sleep.py            # 跑一次巩固
python scripts/sleep.py --loop 8   # 每 8 小时自动巩固（常驻）
# 或在 chat.py 里输入 /sleep 立即巩固
```
今天答应的事、聊到的事，明天它就记得了。

**🖥️ 桌面聊天界面** —— Python 自带的 Tkinter，跨平台、零额外依赖。
```bash
python scripts/desktop.py     # Linux 若缺 tkinter：sudo apt install python3-tk
```
窗口里能切换说话人（测不同人的权限/感情）、一键看时间线、一键"睡一觉"巩固记忆。

**🚀 一键常驻 + 部署到树莓派/机器人** —— 把感知与巩固合成一个守护进程。
```bash
python scripts/daemon.py                 # 持续感知 + 定时睡眠巩固
python scripts/daemon.py --robot ros2    # 动作走 ROS2 机器人
```
完整的树莓派安装、systemd 自启、机器人接线见 **[docs/deploy.md](docs/deploy.md)**。

**🩺 一键安装 + 开机自检** —— 树莓派/Debian 上一行装好，再自检各能力是否就绪。
```bash
./scripts/install.sh           # 核心；--full 连语音+视觉一起装
python scripts/doctor.py       # 自检：大模型/记忆/语音/摄像头/人脸/界面
```

**👂 全感官常驻（看 + 听 + 说）**
```bash
python scripts/daemon.py --voice         # 感知 + 语音对话 + 定时巩固
```
听到话时，它结合"当前画面里的人"判断在跟谁说话，再按关系回应。

**🐳 Docker（跑"大脑"容器）**
```bash
docker build -t digital-soul . && docker run --rm -e DSOUL_LLM_HOST=http://192.168.1.10:11434 digital-soul
```

**🛰️ 隔空指挥外部智能体** —— 机器人当大脑，把活儿派给笔记本/Mac 上的智能体（爱马仕/openclaw），干完回传。
```bash
python scripts/demo_agents.py            # 本地起两个 worker，一条命令跑通整条链路
# 真机：在那两台机器各跑 digital-soul worker --name openclaw --port 9302
```
端点配置见 `config/agents.yaml`；任何监听 `POST /task` 的智能体都能接。它是机器人，却能隔空驱动主机上的智能体干活、再把结果带回来。**直接用大白话**就行：对它说「让 openclaw 把这周代码打个包」，它会自动选中 openclaw、派活、并把结果回话给你（仍受 `control_agents` 授权约束）。它还会**主动提议**——你随口一句「周报还没弄」，它会问「要不要我让爱马仕帮你办了？」，你说声「好」它才真去办（绝不擅自行动）。**办成之后会把这件事记进长期记忆**：日后你问「周报弄了吗」，它能想起来「我已让爱马仕办了…」。万一**没联系上**外部智能体，它会把这事记进"待办本"，下次见到你时**主动跟进**——「上次想让爱马仕办的…还没成，要我再试一次吗？」，你说声「好」它就**重试**，办成自动销账（`dsoul/tasks.py`）；手机网页的"待办看板"上也有一个「↻ 重试全部待办」按钮，一键触发（同样走授权）。

**🎭 人格热切换 + 七情六欲** —— 运行时一键换"灵魂"，且情绪会随相处起伏。
```bash
digital-soul persona flirty-girlfriend --seed-memory   # 换人格(连"我们的故事")
```
对话中它的喜怒哀惧爱恶欲会变化并自然流露；还会用心理/哲学/医学等多学科视角帮你。

**📱 手机网页状态页 + 远程对话** —— 常驻时随手看它"看到谁 / 此刻心情 / 记了什么"，还能**在手机上直接跟它聊天**。
```bash
python scripts/daemon.py --web        # 浏览器打开 http://<树莓派IP>:8765/
```
页面里可选以谁的身份说话，对话同样走授权与人格（请仅在可信局域网开放）。

## 目录结构

```
digital-soul/
├── config/            身份与关系配置（改这里就改了"你"）
├── data/
│   ├── memories/      记忆（sources/ 放原始文档，index.json 自动生成）
│   └── faces/         人脸照片（隐私，默认 gitignore）
├── dsoul/             框架核心
│   ├── agent.py       编排：感知→授权→记忆→人格→模型→动作
│   ├── authority.py   授权：听谁的、能做什么
│   ├── memory.py      记忆：存与检索（RAG）+ 情感时间线
│   ├── annotate.py    情感标注 + 时间抽取
│   ├── persona.py     人格：组装"你"的提示词
│   ├── perception.py  感知：图片/视频认人
│   ├── voice.py       语音：本地 Whisper（听）+ TTS（说）
│   ├── llm.py         本地大模型（Ollama）
│   ├── actions.py     机器人动作接口（抽象）
│   ├── ros2_robot.py  动作接口的 ROS2 实现样例
│   ├── presence.py    持续感知：认人进画面 → 主动打招呼
│   ├── journal.py     对话日记（短期记忆）
│   ├── consolidate.py 睡眠巩固：对话 → 长期记忆
│   ├── emotions.py    七情六欲情绪状态
│   ├── knowledge.py   多学科视角调度
│   ├── skills.py      技能（做饭/家务…）
│   ├── remote_agents.py  隔空指挥外部智能体（爱马仕/openclaw）
│   ├── personas.py    人格切换共享逻辑
│   ├── perception_opencv.py  轻量人脸后端（OpenCV LBPH，免 dlib）
│   └── webstatus.py   手机网页状态页
├── scripts/           demo · chat · desktop · persona · ingest · timeline · voice_chat · watch · sleep · finetune_* · daemon · doctor · agent_worker · demo_agents
├── docs/              finetune.md（微调）· deploy.md（树莓派/机器人部署）
├── Dockerfile · scripts/install.sh   一键容器 / 一键安装
└── tests/             授权 / 记忆 / 情感 / 感知 / 巩固 单元测试
```

## 参与开发 / 扩展

想读懂或扩展它？见 [docs/architecture.md](docs/architecture.md)（模块与数据流、扩展点）
和 [CONTRIBUTING.md](CONTRIBUTING.md)（开发、测试、加新能力的姿势）。

## 路线图

- [x] 接 Whisper 做语音输入、TTS 做语音输出（"说话"）
- [x] 记忆加时间线与情感标注
- [x] ROS2 机器人驱动样例
- [x] 用真实聊天记录做 LoRA 微调，逼近本人文风
- [x] 多模态：让它"看见"摄像头实时画面，主动打招呼
- [x] 长期记忆巩固：定期把对话提炼成新记忆（"睡眠"机制）
