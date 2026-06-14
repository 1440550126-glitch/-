# digital-soul · 本地数字分身智能体框架

> 一个**完全本地运行**（16G 内存即可）的智能体：它用**你的性格、记忆和关系**来对话和行动——
> 认得你的人、记得你的经历、知道**听谁的、不听谁的**，并且可以**接入机器人**执行动作。

## 先说清楚它是什么、不是什么

- ❌ **它不是"意识上传"，也不是永生。** 人脑的记忆目前无法被"读"出来，主观意识能否被复制更是悬而未决的哲学难题。
- ✅ **它是一个"很像你、懂你、忠于你"的数字分身。** 你把"自己是谁、家人朋友是谁、经历过什么、什么性格"喂给它，它就能以你的口吻回应、按你设定的关系决定听谁的，并指挥机器人。

把它理解成一面**会成长、会执行的镜子**，而不是你本人。

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

python tests/test_authority.py   # 跑测试
python tests/test_memory.py
python scripts/chat.py           # 开始对话
```

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

1. 改 `config/identity.yaml`：你的名字、性格、口头禅、日常。
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
│   └── consolidate.py 睡眠巩固：对话 → 长期记忆
├── scripts/           chat · ingest · timeline · voice_chat · watch · finetune_* · sleep
├── docs/              finetune.md（微调指南）
└── tests/             授权 / 记忆 / 情感 / 感知 / 巩固 单元测试
```

## 路线图

- [x] 接 Whisper 做语音输入、TTS 做语音输出（"说话"）
- [x] 记忆加时间线与情感标注
- [x] ROS2 机器人驱动样例
- [x] 用真实聊天记录做 LoRA 微调，逼近本人文风
- [x] 多模态：让它"看见"摄像头实时画面，主动打招呼
- [x] 长期记忆巩固：定期把对话提炼成新记忆（"睡眠"机制）
