# digital-soul · 本地数字分身智能体框架

> 一个**完全本地运行**（16G 内存即可）的智能体：它用**你的性格、记忆和关系**来对话和行动——
> 认得你的人、记得你的经历、知道**听谁的、不听谁的**，并且可以**接入机器人**执行动作。

> 📖 想一页看懂整体架构与模块地图？见 **[`docs/overview.md` 总览手册](docs/overview.md)**（含架构图）。

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

> 🕯️ **缅怀 / 数字遗产**：把某人的聊天记录、书信喂进去（`scripts/ingest_life.py`），配好口头禅与重要日子，分身就能带着 TA 的口吻和你们的共同回忆，在想念时陪着家人。跑一遍 `python scripts/memorial_demo.py` 看「外公」的分身如何陪伴想他的孙女。它是一面承载记忆的镜子，帮在世的人好好怀念，而不是替代那个人本身。
>
> 还能更进一步：**守护提醒**（`config/care.yaml` 配好，到点本地叮嘱家人吃药/复查）、**多人合一**（`config/family.yaml` 登记一大家子，"把外婆叫来"就以 TA 本人口吻聊，TA 们彼此知道对方存在）、**生平上网页**（手机打开就能看 TA 的一生、想留给你的话、家训与全家）。这些全在本机生成，不联网、不替任何人登录任何系统。

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
| 语音交流（听 + 说） | 本地 Whisper 转文字 + 离线 TTS，语速/音量随七情变化 | `dsoul/voice.py` · `scripts/voice_chat.py` |
| 情感记忆 / 一生回顾 | 记忆自动打情感标签 + 时间线 | `dsoul/annotate.py` · `scripts/timeline.py` |
| 持续感知 / 主动打招呼 | 摄像头认人，进画面即主动问候 | `dsoul/presence.py` · `scripts/watch.py` |
| 贴近本人文风 | QLoRA 本地微调流水线 | `scripts/finetune_*.py` · `docs/finetune.md` |
| 越用越懂你 | 对话日记 + 睡眠巩固成长期记忆 | `dsoul/journal.py` · `dsoul/consolidate.py` · `scripts/sleep.py` |
| 桌面聊天界面 | Tkinter GUI（Python 自带） | `scripts/desktop.py` |
| 一键常驻 / 部署 | 感知+巩固守护进程 · 树莓派/机器人指南 | `scripts/daemon.py` · `docs/deploy.md` |
| 手机网页状态页 | 状态总览 + 设备/场景/自动化 + 关系图谱·一生时间线·简报 | `dsoul/webstatus.py` |
| 轻量人脸(树莓派) | OpenCV LBPH 后端，免 dlib | `dsoul/perception_opencv.py` |
| 七情六欲 | 情绪随互动起伏、影响口吻 | `dsoul/emotions.py` |
| 多学科视角 | 心理/哲学/医学…思维调度 | `dsoul/knowledge.py` |
| 技能（做饭/家务）| 授权可执行的技能 | `dsoul/skills.py` |
| 隔空指挥智能体 | 大白话派活、主动提议、记进长期记忆、失败入待办并主动跟进重试 | `dsoul/remote_agents.py` · `dsoul/agent.py` · `dsoul/tasks.py` |
| 人格热切换 | 运行时一键换"灵魂" | `dsoul/personas.py` |
| 像 TA 一样说话 | 口头禅/语气词/口吻，降级也"像本人" | `dsoul/style.py` |
| 缅怀与抚慰 | 纪念日主动提起；思念时借共同回忆、以本人口吻温柔回应 | `dsoul/memorial.py` |
| 生平导入 | 聊天记录/书信 → TA 的记忆与口头禅 | `dsoul/lifelog.py` · `scripts/ingest_life.py` |
| 照片多模态 | 照片(谁/何时/何地)→带日期记忆，进时间线与图谱；照片里的家人自动归到 TA 名下 | `dsoul/photo.py` · `scripts/ingest_photo.py` |
| 编年生平 + 嘱托 | 一生编年成故事；保管临终留言/家训郑重交付 | `dsoul/legacy.py` |
| 守护提醒 | 惦记家人吃药/复查/重要日子，到点本地生成叮嘱（不碰外部账号设备） | `dsoul/guardian.py` · `config/care.yaml` |
| 多人合一 | 一宅多位家人，"把外公叫来"即以 TA 本人口吻聊，各有专属记忆，彼此知道对方存在 | `dsoul/family.py` · `config/family.yaml` |
| 家人多人对谈 | "让外公和外婆聊聊做饭"，两位各用各的性格/口头禅/记忆来回聊几句 | `dsoul/converse.py` |
| 晨间关怀简报 | 今天什么日子+谁该吃药复查+今天打算+一句暖场白，揉成一段早安话 | `dsoul/briefing.py` |
| 代笔家书 | 以 TA 口吻给家人写信，按场合(生日/想念/道歉…)带上共同回忆 | `dsoul/letters.py` |
| 本地日程 | 生日/复诊/约定记在本地，"今天有什么事"能报，喂给晨间关怀 | `dsoul/calendar_book.py` |
| 触景生情 | "说起老房子"，顺着相关记忆与当时情绪说一段回想 | `dsoul/reminisce.py` |
| 感恩与遗憾 | 回望一生，挑出最感念的与放不下的 | `dsoul/gratitude.py` |
| 时光胶囊 | 封存一句话给未来，到某日由分身交给某位家人（含错过补送，只送一次） | `dsoul/timecapsule.py` |
| 临别期许 | TA 对每位家人的一句盼望，问"你希望我怎样"时道来 | `dsoul/wishes.py` |
| 速记便签 | 随手"记个事"，回头能翻能搜能清 | `dsoul/notes.py` |
| 家传菜谱 | "外婆的红烧肉怎么做"照着 TA 的方子来 | `dsoul/recipes.py` · `config/recipes.yaml` |
| 口头语录 | TA 常念叨的老话，问起能背几句 | `dsoul/sayings.py` · `config/sayings.yaml` |
| 生平采访 | 按人生阶段一问一答，把回答存进记忆养出更像 TA 的分身 | `dsoul/qa_interview.py` · `scripts/interview.py` |
| 社交记忆 | 对每个人记着亲疏冷暖/上次见面/近期话题，会"好久没见你了" | `dsoul/social.py` |
| 心愿与目标 | 长期想达成的事帮你盯着，能记进展、能销账、能盘点 | `dsoul/goals.py` |
| 亲戚称呼 | "我爸的弟弟叫什么"→叔叔，算中国式称谓(父系/母系/内外) | `dsoul/kinship.py` |
| 传统节日 | 今天是什么节、祝福、老讲究；清明重阳牵出思念 | `dsoul/festival.py` |
| 家族册导出 | 每位家人各一页(生平/性格/口头禅/记忆)+对谈，编成可打印传家的 HTML | `dsoul/book.py` · `scripts/family_book.py` |
| 生平上网页 | 手机网页看 TA 的一生/嘱托家训/全家/守护惦记，点全家按钮即唤出某位 | `dsoul/webstatus.py` |
| 数字纪念册 | 一生/影像/嘱托/家训/全家/时间线导出成一页自包含、可打印的 HTML（照片 base64 内嵌），存得住传得下 | `dsoul/keepsake.py` · `scripts/keepsake.py` |
| 本人嗓音 | 嗓音档案(语速/音量)+情绪叠加，可接声音克隆 CLI | `dsoul/voice.py` |
| 多模型路由 | Ollama+OpenAI兼容，按任务选模型，小会异质模型投票 | `dsoul/llm.py` |
| 贾维斯式管家 | 点名应答 / 态势简报 / 系统自检，只服务听命于你的人 | `dsoul/butler.py` |
| 语音唤醒词 | 设了"贾维斯"就只在被点名时回应 | `scripts/daemon.py`(--wake) |
| 设备 / 家居控制 | "把灯关了 / 空调调到26度"，内置 Home Assistant 后端 | `dsoul/devices.py` |
| 多步任务编排 | "订会议并通知大家"→拆步执行、分别委派、汇总 | `dsoul/orchestrator.py` |
| 场景 / 例程 | "我回来了"一键触发一组设备动作，可自定义 | `dsoul/scenes.py` |
| 定时 / 条件自动化 | "每天22点提醒锁门"、"工作日日落开灯"、"温度低于18开空调" | `dsoul/triggers.py` |
| 晨间主动简报 | 清晨见到你主动汇报，语音模式还会念出来 | `dsoul/agent.py`(greet) |
| 自主反思 / 成长 | 回看经历→提炼"领悟"→写回记忆，影响日后回应 | `dsoul/reflect.py` |
| 自主规划 / 推进 | 领悟+欠账→排出今天的计划→逐条推进、销账 | `dsoul/planner.py` |
| 自主心跳 / 主动性 | 常驻时定期反思+规划+跟进欠账，不用你催 | `dsoul/agent.py`(tick) · `scripts/daemon.py` |
| 记忆图谱 | 记忆连成"人—事—主题"关系网，可问"关于X/最核心的人" | `dsoul/graph.py` · `scripts/graph.py` |
| 记忆遗忘曲线 | 记忆随时间淡忘，越重要/越常想起越长久，回忆可唤醒 | `dsoul/forgetting.py` · `scripts/forgetting.py` |
| 量子纠缠式记忆 | 相关记忆纠缠在一起，回忆其一即牵动其二（扩散激活） | `dsoul/entangle.py` · `scripts/entangle.py` |
| 梦境生成 | 睡眠时把记忆碎片+情绪+纠缠联想重组成一段梦 | `dsoul/dream.py` |
| 自我意识叙事 | 第一人称讲"我是谁、在乎谁、明白了什么、怕忘什么" | `dsoul/selfnarrative.py` |
| 价值观与抉择 | 遇"该不该/怎么选"据价值观（守护/家人/健康…）给建议；价值随经历自演化 | `dsoul/values.py` |
| 内心独白 | 每次对话冒出一句私密心声（随七情变味、会飘进梦里） | `dsoul/monologue.py` |
| 好奇心 / 自学 | 遇陌生事物默默发问、问回来，可交给外部智能体查回来学到；脑中小会分歧大的判断也会变成高优先好奇 | `dsoul/curiosity.py` |
| 世界模型(置信/自我修正) | 信念随证据增减、遇相反信号会动摇甚至改主意 | `dsoul/worldmodel.py` |
| 情景预测 | 从日记规律预感"这个点你常想做什么"，提前一步 | `dsoul/anticipate.py` |
| 可校准预测 | 多信号预感带置信度，"猜对/没猜对"反馈越用越准；高置信主动提、一句"好"就安排 | `dsoul/predict.py` |
| 群体模拟预测 | 脑中开小会：6 种认知思维各自表态、聚合成预感，并以"一致/分歧"作信号（参考 MiroFish · ruv-swarm 认知多样性） | `dsoul/swarm.py` |

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

**🪞 自主反思与成长（面向未来的自主智能体）** —— 借鉴 Generative Agents 的「记忆流 → 反思」范式：常驻时它每隔一阵（`daemon --think-every`，默认 30 分钟）自主回看最近的经历，提炼出关于**你的近况、关系变化、它自己的体会**的更高层"领悟"，写回长期记忆并影响日后的回应（接了本地大模型就用它归纳，没接就用启发式：情绪倾向 / 高频话题 / 最常相处的人，纯 16G 本地也能"想明白点事"）。**🤵 贾维斯式管家层** —— 像贴身管家一样**被点名才应答、随时汇报态势、自检系统**，且**只服务听命于你的人**（外人问"近况/简报"一律不汇报，隐私优先）。说一句「贾维斯，简报」或点一下手机网页的「☀️ 要一份简报」，它就把**此刻在场的人 · 心情 · 今天的计划 · 欠着的事 · 最近的领悟**汇成一段管家口吻的话；说「系统自检」则报告各子系统健康（大模型/视觉/记忆/可调度的智能体/待办）。语音模式加 `--wake 贾维斯` 后，它只在被点名时开口，平时安静待命。称呼可在 `config/identity.yaml` 里设 `assistant.address: 先生`。

它还能像贾维斯那样**动手**：① **控设备/家居**——「把灯关了」「空调调到 26 度」「放点音乐」「锁门」直接执行（内存模拟，换个后端即可对接 Home Assistant；仍受 `control_devices` 授权，外人指挥不动）；② **多步编排**——一句「把灯打开、空调调到 24 度，再放点音乐」或「订明天的会议并通知大家」，它会拆成几步、分别路由（设备自己控、没点名的活委派给外部智能体），办完汇总成一段话；③ **晨间主动简报**——清晨第一次见到你（摄像头认出），不用你开口它就先送上一份简报，`--voice` 下还会用语音念出来。设备状态实时显示在手机网页「🏠 设备」（可直接点按钮开/关）。它还支持 ④ **场景/例程**——「我回来了」=开灯+空调 26 度+音乐、「晚安」=关灯锁门、「离家模式」=全关并锁门（内置 4 套，可在 `config/scenes.yaml` 自定义，网页「🎬 场景」一键触发）；以及 ⑤ **定时/条件自动化**——一句「每天 22 点提醒锁门」「工作日日落时开灯」「温度低于 18 就开空调」「我一进门就开灯」，分别按时间（含每周/工作日/周末、日落日出）、温度阈值、或摄像头进门事件触发，全部列在网页「⏰ 自动化」，可直接在那填一句话新增、或一键清空。控设备默认用内存模拟，**配好 `config/devices.yaml` 即可对接真实 Home Assistant**（灯/空调/媒体/门锁）；温度等条件还能读 **HA 传感器实时数值**触发。设备/场景/自动化**全部走 `control_devices` 授权**，外人指挥不动。

想一眼看全？跑 `python scripts/jarvis_demo.py`：在临时目录里模拟一段 `--voice --wake 贾维斯` 的对话——唤醒待命 → 简报 → 控设备 → 多步编排 → 场景 → 设自动化 → 定时/进门/温度自动触发 → 晨间主动简报。

**🗓️ 自主规划与推进（Generative Agents 三件套：记忆 → 反思 → 规划）** —— 反思之后再往前一步：它每天根据**领悟 + 欠账 + 当下心情**给自己排出一个小计划（比如"把欠着的相册整理补上"、"主人这阵子加班多，提醒劳逸结合"），再由自主心跳**逐条推进**——能办的（跟进欠账）直接交给外部智能体去办、办成销账；该提醒的，提醒一次即完成；试太多次仍不行的，自动搁置不纠缠（有本地大模型用它归纳"关心/提醒"类意图，没有就启发式，纯本地也能规划）。今天的计划与完成进度实时显示在手机网页「🗓️ 今天的计划」（✅/▢），领悟显示在「💡 它最近的领悟」。——它不再只是被动应答，而是会**沉淀、会成长、会自己安排、会主动推进**。

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
