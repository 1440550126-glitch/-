#!/usr/bin/env python3
"""睡眠巩固：把日记里的对话提炼成长期记忆，让分身越用越懂你。

用法：
  python scripts/sleep.py              # 跑一次巩固
  python scripts/sleep.py --loop 8     # 每 8 小时自动巩固一次（常驻）
"""

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402


def one_cycle(agent) -> None:
    before = len(agent.memory.items)
    report = Consolidator(
        agent.memory, agent.journal, llm=agent.llm,
        identity=agent.identity, authority=agent.authority,
    ).run()
    print(
        f"😴 巩固 {report['processed']} 条对话 → 新增 {len(report['learned'])} 条长期记忆"
        f"（记忆库 {before} → {len(agent.memory.items)}）"
    )
    for m in report["learned"]:
        print(f"  + {m}")
    if report.get("learned") and hasattr(agent, "sediment_memories"):   # 巩固出的记忆也连进知识库
        try:
            mrep = agent.sediment_memories(report["learned"])
            if mrep.get("touched"):
                print(f"🕸️  记忆入库 {len(mrep['touched'])} 条，连上人物："
                      + "、".join(mrep["people_linked"][:8] or ["—"]))
        except Exception as e:
            print(f"🕸️  记忆入库跳过（{str(e)[:30]}）")
    if hasattr(agent, "sediment_knowledge"):    # 睡前把当天聊到的知识沉进知识库
        try:
            sed = agent.sediment_knowledge()
            if sed.get("touched"):
                print(f"📚 沉淀知识 {len(sed['touched'])} 条 → 知识库："
                      + "、".join(sed["touched"][:8]) + ("…" if len(sed["touched"]) > 8 else ""))
        except Exception as e:
            print(f"📚 知识沉淀跳过（{str(e)[:30]}）")
    if hasattr(agent, "dream"):
        d = agent.dream()                       # 睡着了，做个梦
        if d:
            print(f"🌙 梦见：{d}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=float, default=None, help="每 N 小时巩固一次（常驻）")
    args = ap.parse_args()

    agent = build_agent()
    if args.loop is None:
        one_cycle(agent)
        return

    print(f"🌙 睡眠巩固常驻，每 {args.loop} 小时一次。Ctrl+C 结束。")
    try:
        while True:
            one_cycle(agent)
            time.sleep(args.loop * 3600)
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
