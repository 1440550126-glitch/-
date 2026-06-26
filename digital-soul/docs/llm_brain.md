# 给"灵魂"接一个大脑（本地 Ollama / MiniMax 云端）

"灵魂"平时靠记忆 + 规则就能开口；接上大模型后，回话才真正灵动、会推理、有自己的口吻。
框架支持三类大脑，配置都在 `config/models.yaml`，**不接也能跑**（自动降级成记忆拼接的朴素回复）。

| provider | 是什么 | 适合 |
| --- | --- | --- |
| `ollama` | 本地开源模型（默认） | 私密回忆、离线、不花钱 |
| `openai` | 任何 OpenAI 兼容端点（llama.cpp / LM Studio / vLLM / 云） | 已有自己的推理服务 |
| `minimax` | MiniMax 云端大模型（付费） | 中文强、日常闲聊 / 知识问答、想配声音克隆 |

> 🔐 **一条红线**：私密的人、逝者、家里的事，**优先留给本地 `ollama`**。
> 云端再好，也是把话发出门了。把云模型只挂到"日常闲聊"这类任务上，最稳妥（见下文 `tasks:`）。

---

## 一、默认：本地 Ollama（推荐，私密、免费、离线）

```bash
# 16G 内存机器：
ollama pull qwen2.5:7b-instruct
# 24G 统一内存（Apple Silicon）更舒服：qwen3:14b（会推理）/ gemma3:12b（口吻自然）
```

装好就能用，`config/models.yaml` 留空即走默认。换模型把 `default.model` 改掉即可：

```yaml
default:
  provider: ollama
  model: qwen3:14b
  host: http://localhost:11434
```

> Qwen3 / Gemma 这类"推理模型"会先吐一段 `<think>…</think>` 再给答案；
> 框架在 `dsoul/llm.py` 里已自动剥掉思考块，只把最终回答说给家人听。

---

## 二、接 MiniMax 云端大模型（中文顶、付费、要联网）

MiniMax 的对话接口是 **OpenAI 兼容**的（路径 `/text/chatcompletion_v2`），框架已单列为
`provider: minimax`、自带合理默认，你只要填三行 + 一把环境变量里的密钥。

### 第 1 步：密钥**只放环境变量**（绝不写进配置 / 代码 / 仓库）

```bash
export DSOUL_LLM_KEY=sk-...      # 对话用；没设时会自动回退读 MINIMAX_API_KEY
# 已经为语音克隆设过 MINIMAX_API_KEY？那把就够了，对话会复用它，不必重复设。
```

> 🔐 **安全红线**：密钥就像家门钥匙。**只放环境变量**（或一个被 `.gitignore` 掉、用 `source` 加载的本地文件），
> 永远别写进 `config/models.yaml` 或任何会提交的文件。一旦不小心贴进聊天 / 截图 / 代码，
> **立刻去 MiniMax 平台吊销重置**，再换新的。本项目代码只从环境变量读，不会、也请你别把它落盘入库。

### 第 2 步：填配置（`config/models.yaml`，只填这三行，密钥不在这）

```yaml
default:
  provider: minimax
  model: MiniMax-Text-01        # 也可 abab6.5s-chat（更快更省）/ MiniMax-M1（更强）
  host: https://api.minimax.io/v1   # 国内站改成 https://api.minimaxi.com/v1
```

### 第 3 步：体检确认连通

```bash
python scripts/doctor.py
# 看这一行：✅ 大模型(MiniMax 云端) — https://api.minimax.io/v1 · MiniMax-Text-01 · 连通
# 若显示"未连通"，多半是没 export DSOUL_LLM_KEY（或密钥失效 / 余额用尽）。
```

连通后正常跟它说话即可（`python scripts/chat.py` 或语音）；密钥错了也不会崩——
框架会兜底降级成记忆朴素回复，并在末尾提示出错原因。

---

## 三、又要云端流畅、又要私密落地：按任务分流

主脑用本地、只把云模型挂到某个场景，是兼顾隐私与体验的推荐做法：

```yaml
default:                                  # 平时、私密对话：本地
  provider: ollama
  model: qwen3:14b
tasks:
  chat: { provider: minimax, model: abab6.5s-chat }   # 仅"日常闲聊"上云
```

代码里用 `llm_router.for_task("chat")` 取对应模型；没配的任务自动回退 `default`。

---

## 四、环境变量速查

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `DSOUL_LLM_MODEL` | 覆盖默认模型名 | `qwen2.5:7b-instruct` |
| `DSOUL_LLM_HOST` | 覆盖默认地址 | `http://localhost:11434` |
| `DSOUL_LLM_KEY` | 云端对话密钥（minimax/openai） | 回退读 `MINIMAX_API_KEY` |
| `MINIMAX_API_KEY` | 语音合成密钥（也被对话复用） | 无 |

密钥相关变量**只在环境里活**，永不进仓库。配置文件里只写 provider / model / host。
