#!/usr/bin/env python3
"""用 QLoRA 在本地微调，让分身贴近"你"的文风。

16G 内存 + 一块入门级 GPU 即可（无 GPU 可 CPU 慢跑）。缺依赖时只打印安装指引、
不会崩。产物是一个体积很小的 LoRA 适配器，加载方式见 docs/finetune.md。

用法：
  python scripts/finetune_prepare.py            # 先准备数据
  python scripts/finetune_train.py              # 再训练
  python scripts/finetune_train.py --base Qwen/Qwen2.5-7B-Instruct --epochs 3
"""

import argparse
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
DATASET = BASE / "data" / "finetune" / "dataset.jsonl"
OUT = BASE / "data" / "finetune" / "lora-adapter"

REQUIRED = ["torch", "transformers", "peft", "trl", "datasets"]


def _missing() -> list[str]:
    miss = []
    for m in REQUIRED:
        try:
            __import__(m)
        except Exception:
            miss.append(m)
    return miss


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--cpu", action="store_true", help="无 GPU 时强制用 CPU（很慢）")
    args = ap.parse_args()

    miss = _missing()
    if miss:
        print("⚠️  缺少训练依赖：", " ".join(miss))
        print("安装（建议在有 GPU 的机器上）：")
        print("  pip install torch transformers peft trl datasets accelerate bitsandbytes")
        print("装好后重跑本脚本即可。")
        return
    if not DATASET.exists():
        print("找不到数据集，请先运行：python scripts/finetune_prepare.py")
        return

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(args.base)

    quant = None
    if not args.cpu and torch.cuda.is_available():
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.base, quantization_config=quant, device_map="auto" if quant else None
    )

    ds = load_dataset("json", data_files=str(DATASET), split="train")
    ds = ds.map(lambda ex: {"text": tok.apply_chat_template(ex["messages"], tokenize=False)})

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    cfg = SFTConfig(
        output_dir=str(OUT), num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, logging_steps=5, save_strategy="epoch",
        dataset_text_field="text", max_seq_length=1024,
    )
    trainer = SFTTrainer(model=model, train_dataset=ds, peft_config=lora, args=cfg)
    trainer.train()
    trainer.save_model(str(OUT))
    print(f"✅ LoRA 适配器已保存到 {OUT}")
    print("加载回 Ollama / llama.cpp 的说明见 docs/finetune.md")


if __name__ == "__main__":
    main()
