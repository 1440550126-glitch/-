#!/usr/bin/env python3
"""生平采访：用一串温和的问题，把一个人的人生一段段问出来，答案存进记忆库。

给"在世时就想留下点什么"的人，或替逝者补全记忆的家人用。完全本地。
用法：
  python scripts/interview.py            # 从上次问到的地方继续
  python scripts/interview.py --all      # 不论问过没问，从头走一遍
回答直接打字；空行=跳过这题；输入 q 回车=保存并退出。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.memory import Memory  # noqa: E402
from dsoul.qa_interview import all_questions, answer_to_memory, progress  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _asked(mem) -> set:
    return {it.get("q") for it in mem.items if it.get("source") == "interview" and it.get("q")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="不跳过已问过的题")
    args = ap.parse_args()

    mem = Memory(ROOT / "data" / "memories" / "index.json")
    asked = set() if args.all else _asked(mem)
    queue = [(s, q) for s, q in all_questions() if q not in asked]
    if not queue:
        print("这套题都问过啦。想重头再来，加 --all。")
        return

    print(f"开始生平采访，共 {len(queue)} 题（当前进度 {int(progress(asked) * 100)}%）。")
    print("直接打字回答；空行跳过；输入 q 保存退出。\n")
    saved = 0
    for stage, q in queue:
        try:
            ans = input(f"［{stage}］{q}\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if ans.lower() == "q":
            break
        rec = answer_to_memory(ans)
        if rec is None:
            continue
        mem.add(rec["text"], source="interview", tags=["interview", stage],
                when=rec["when"])
        # 记下这题问过了（占位，便于下次跳过）
        mem.add(f"（采访问题）{q}", source="interview_q", tags=["interview_q"])
        for it in mem.items:
            if it.get("text") == f"（采访问题）{q}":
                it["q"] = q
        saved += 1
        print("  ✓ 记下了\n")

    print(f"\n已保存 {saved} 段回忆，进度 {int(progress(_asked(mem)) * 100)}%。它们已进时间线与图谱。")


if __name__ == "__main__":
    main()
