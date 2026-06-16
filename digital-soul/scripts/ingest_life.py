#!/usr/bin/env python3
"""把某人的聊天记录 / 书信导入成「TA 的记忆」，并提取 TA 的口头禅。

用于"模仿逝者生前言行"：喂进 TA 说过的话，分身就拥有 TA 的记忆与口吻。

用法：
  python scripts/ingest_life.py 聊天记录.txt --person 外公            # 预览（不写入）
  python scripts/ingest_life.py 聊天记录.txt --person 外公 --write    # 写入长期记忆
聊天记录每行形如：  外公: 今天天气好，记得加衣服   （可带 [2019-03-12] 前缀）
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.lifelog import candidate_phrases, parse_chatlog  # noqa: E402
from dsoul.memory import Memory  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="聊天记录 / 书信文本文件")
    ap.add_argument("--person", required=True, help="要导入的人（聊天记录里 TA 的名字）")
    ap.add_argument("--write", action="store_true", help="写入长期记忆（默认仅预览）")
    args = ap.parse_args()

    text = pathlib.Path(args.path).read_text(encoding="utf-8")
    lines = parse_chatlog(text, args.person)
    print(f"📜 从「{args.path}」里找到「{args.person}」说过的话 {len(lines)} 条。")
    for s in lines[:6]:
        print("   ·", s[:40])
    phrases = candidate_phrases(lines)
    if phrases:
        print(f"\n💬 TA 常说的（口头禅候选，建议加进 identity.yaml）：{ '、'.join(phrases) }")

    if args.write and lines:
        mem = Memory(ROOT / "data" / "memories" / "index.json")
        before = len(mem.items)
        for s in lines:
            mem.add(s, source=f"lifelog:{args.person}", tags=["lifelog", args.person])
        print(f"\n✅ 已写入长期记忆 {len(mem.items) - before} 条（去重后）。分身现在拥有 TA 的这些记忆了。")
    elif lines:
        print("\n（预览模式。加 --write 才会真正写入长期记忆。）")


if __name__ == "__main__":
    main()
