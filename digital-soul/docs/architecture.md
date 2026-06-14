# 架构说明

给想读懂或扩展 `digital-soul` 的人。

## 设计原则

1. **本地优先**：默认全离线可跑，个人数据不出本机。
2. **优雅降级**：任何重型能力（大模型、语音、视觉）缺失都不报错，自动退到可用形态；只有 `pyyaml` 是硬依赖。
3. **接口解耦**：大模型 / 机器人 / 人脸后端都藏在接口后，可整块替换而不动其余代码。
4. **配置即"人"**：改 `config/*.yaml` 就改了"他是谁、听谁的"；代码与人格分离。

## 数据流

```
图片/视频 ─► Perception ─┐(认出谁来了)
                         ▼
你说的话 ───────────► Agent.handle ──► Authority(听不听/能不能做这动作)
                         │                       │允许
              ┌──────────┼───────────┐          ▼
              ▼          ▼           ▼      Robot(执行动作)
          Memory     Persona      Journal
         (想起记忆) (组装人设)   (记进日记)
              └──────────┼───────────┘
                         ▼
                       LLM  ──► 用"你"的口吻回应
                         ┊
              (夜里) Consolidator: Journal ─► 新的长期 Memory
```

## 模块职责

| 模块 | 职责 | 关键接口 |
|---|---|---|
| `agent.py` | 编排闭环；`handle()` / `greet()` | `Agent(identity,persona,memory,authority,perception,llm,robot,journal)` |
| `authority.py` | 身份→信任→权限 | `resolve(name)` · `can(name,action)` |
| `memory.py` | 记忆存取（RAG）+ 时间线 | `add()` · `recall(q,k)` · `timeline()` |
| `annotate.py` | 情感标注 + 时间抽取 | `classify_emotion()` · `extract_when()` |
| `persona.py` | 组装人格提示词 | `system_prompt(speaker,memories)` |
| `perception*.py` | 人脸识别（dlib / OpenCV 两后端） | `identify()` · `identify_frame()` · `build_perception()` |
| `presence.py` | 持续感知状态机 | `observe()` · `current_speaker()` · `run()` |
| `voice.py` | 听(STT) / 说(TTS) / 录音 | `Ears` · `Mouth` · `record_wav()` |
| `llm.py` | 本地大模型(Ollama) | `LLM(model,host)` · `available` · `chat()` |
| `actions.py` · `ros2_robot.py` | 机器人动作接口 | `RobotInterface` |
| `journal.py` · `consolidate.py` | 短期日记 → 长期记忆 | `Journal` · `Consolidator.run()` |
| `webstatus.py` | 网页状态页 + 远程对话 | `start_web()` |
| `loader.py` | 读配置、装配出 `Agent` | `build_agent(base_dir,robot,llm_model)` |

## 扩展点（怎么加东西）

- **接真实机器人**：实现 `actions.RobotInterface`（`say/move/look_at/protect`），
  `build_agent(robot=YourRobot())`。参考 `ros2_robot.py`。
- **换大模型后端**：`llm.py` 现走 Ollama HTTP。要接别的，做一个有
  `.available` 和 `.chat(system,user)->str` 的类传给 `Agent` 即可。
- **换人脸后端**：实现与 `Perception` 同接口的类（`available/identify/identify_frame/known/_face_id_to_name`），
  在 `build_perception()` 里挂上，或用 `DSOUL_FACE_BACKEND` 选择。
- **换记忆向量**：`memory.Embedder` 现支持 sentence-transformers / 词法降级；
  替换 `embed(text)->dict[str,float]` 即可，`cosine` 通用。
- **新增动作**：在 `agent._execute()` 里加分支，并在 `relationships.yaml` 的
  `permissions` 里授权。

## 数据与隐私

| 路径 | 内容 | 是否入库 |
|---|---|---|
| `config/*.yaml` | 身份与关系（示例占位） | ✅ 入库 |
| `data/memories/sources/` | 记忆原始文档 | ✅ 入库（示例） |
| `data/memories/index.json` | 生成的记忆索引 | ❌ gitignore |
| `data/faces/*` | 人脸照片 | ❌ gitignore |
| `data/journal/*` | 对话日记 | ❌ gitignore |
| `data/finetune/*` | 训练数据/适配器 | ❌ gitignore |

## 测试约定

- 纯逻辑（授权、记忆、情感、感知状态机、巩固）都有单测，**零重型依赖**即可跑。
- 每个测试文件可直接 `python tests/test_xxx.py`，也兼容 `pytest`。
- 重型能力（LLM/语音/视觉）在脚本里以 `available` 判定 + 降级，不进单测。
