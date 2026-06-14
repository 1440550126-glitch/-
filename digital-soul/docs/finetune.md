# LoRA 微调指南：让分身真正"像你说话"

记忆 + 人格提示词已经能让分身"知道你的事、按你的关系行事"。但要让它的**遣词、语气、
口头禅**也像你，最好的办法是用你的真实语料做一次轻量微调（QLoRA）。产物是一个体积
很小（几十 MB）的 **LoRA 适配器**，叠加在本地基座模型上即可。

> 训练建议在有 GPU 的机器上（哪怕一块入门级 GPU）。推理仍然 16G 内存本地跑。

## 1. 准备数据

```bash
# 仅用已有身份 + 记忆：
python scripts/finetune_prepare.py
# 强烈建议并入真实聊天记录（微信/QQ 导出成文本，每行 "说话人: 内容"）：
python scripts/finetune_prepare.py --chat 微信导出.txt
```

产出 `data/finetune/dataset.jsonl`（chat 格式）。本人（`identity.yaml` 的 name/aka）
说过的话会被当作"分身应答"来学习。

## 2. 训练

```bash
pip install torch transformers peft trl datasets accelerate bitsandbytes
python scripts/finetune_train.py --base Qwen/Qwen2.5-7B-Instruct --epochs 3
```

产出 `data/finetune/lora-adapter/`。脚本默认 4-bit QLoRA，只训注意力投影层，显存占用低。

## 3. 加载回本地推理（两条路）

### A. 合并后转 GGUF，给 Ollama 用（最稳）

```python
# merge.py —— 把 LoRA 合并进基座
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer
m = AutoPeftModelForCausalLM.from_pretrained("data/finetune/lora-adapter")
m = m.merge_and_unload()
m.save_pretrained("data/finetune/merged")
AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct").save_pretrained("data/finetune/merged")
```

```bash
# 用 llama.cpp 转 GGUF 并量化（16G 可跑 q4_K_M）
python llama.cpp/convert_hf_to_gguf.py data/finetune/merged --outfile soul.gguf
./llama.cpp/llama-quantize soul.gguf soul.q4_K_M.gguf q4_K_M

# 做成 Ollama 模型
printf 'FROM ./soul.q4_K_M.gguf\nSYSTEM "你就是张明本人。"\n' > Modelfile
ollama create my-soul -f Modelfile
```

### B. 直接挂 LoRA 适配器（更快，省去合并）

```bash
python llama.cpp/convert_lora_to_gguf.py data/finetune/lora-adapter --outfile soul-lora.gguf
printf 'FROM qwen2.5:7b-instruct\nADAPTER ./soul-lora.gguf\n' > Modelfile
ollama create my-soul -f Modelfile
```

## 4. 让框架用上你的专属模型

```python
from dsoul.loader import build_agent
agent = build_agent(llm_model="my-soul")   # 指向上面 ollama create 的名字
```

或在 `scripts/chat.py` 里改 `build_agent(llm_model="my-soul")`。之后对话就是
**你的记忆 + 你的关系 + 你的文风** 三合一了。

## 小贴士

- 数据越真实、越多越像你；几百到几千条对话即可见效。
- 过拟合会让它复读，`--epochs` 别太大（2–3 通常够）。
- 隐私：`dataset.jsonl` 和 `lora-adapter/` 默认已被 `.gitignore`，不会误传。
