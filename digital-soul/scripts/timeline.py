#!/usr/bin/env python3
"""按时间线 + 情感打印数字分身的记忆。

用法：python scripts/timeline.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.annotate import EMOJI  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402


def main() -> None:
    agent = build_agent()
    rows = agent.memory.timeline()
    print(f"🕰️  情感时间线（共 {len(rows)} 条记忆）")
    print("=" * 60)
    cur = None
    for it in rows:
        when = it.get("when") or "时间未知"
        if when != cur:
            print(f"\n【{when}】")
            cur = when
        emo = it.get("emotion", "平静")
        print(f"  {EMOJI.get(emo, '·')} {emo}  {it['text']}")


if __name__ == "__main__":
    main()
