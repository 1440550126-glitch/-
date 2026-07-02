#!/usr/bin/env python3
"""把你的身份 / 记忆 / 聊天记录，转成 LoRA 微调数据集（JSONL，chat 格式）。

用法：
  python scripts/finetune_prepare.py                       # 用 identity + 记忆生成
  python scripts/finetune_prepare.py --chat 聊天记录.txt    # 额外并入真实聊天记录

聊天记录格式：每行 "说话人: 内容"；本人（identity.name 或 aka）说的话作为"分身应答"。
输出：data/finetune/dataset.jsonl
"""

import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402
from dsoul.persona import Persona  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent

USER_PROMPTS = [
    "跟我说说你自己吧",
    "你平常都喜欢干嘛？",
    "聊聊你的经历呗",
    "说点你印象最深的事",
    "你是个什么样的人？",
    "给我讲讲你的故事",
]


def from_memories(system: str, memories: list[str]) -> list[dict]:
    out = []
    for m in memories:
        out.append(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": random.choice(USER_PROMPTS)},
                    {"role": "assistant", "content": m},
                ]
            }
        )
    return out


def from_chat(system: str, path: pathlib.Path, owner_names: set[str]) -> list[dict]:
    out, convo = [], []
    for ln in path.read_text(encoding="utf-8").splitlines():
        sep = "：" if "：" in ln else (":" if ":" in ln else None)
        if not sep:
            continue
        spk, content = ln.split(sep, 1)
        spk, content = spk.strip(), content.strip()
        if not content:
            continue
        role = "assistant" if spk in owner_names else "user"
        convo.append({"role": role, "content": content})
        if role == "assistant" and any(c["role"] == "user" for c in convo):
            out.append({"messages": [{"role": "system", "content": system}] + list(convo)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", help="可选：真实聊天记录文本")
    ap.add_argument("--out", default=str(BASE / "data" / "finetune" / "dataset.jsonl"))
    args = ap.parse_args()

    agent = build_agent()
    system = Persona(agent.identity).system_prompt()
    owner_names = {agent.identity.get("name")} | set(agent.identity.get("aka") or [])

    examples = from_memories(system, [it["text"] for it in agent.memory.items])
    if agent.identity.get("summary"):
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": "你是谁？"},
                    {"role": "assistant", "content": agent.identity["summary"]},
                ]
            }
        )
    if args.chat:
        examples += from_chat(system, pathlib.Path(args.chat), owner_names)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"✅ 生成 {len(examples)} 条训练样本 -> {out}")
    if examples:
        sample = json.dumps(examples[0]["messages"][1:], ensure_ascii=False)
        print("样本示例:", sample[:90], "...")
    print("下一步：python scripts/finetune_train.py")


if __name__ == "__main__":
    main()
