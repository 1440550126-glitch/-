#!/usr/bin/env python3
"""量子纠缠式记忆演示：回忆一条记忆，如何"瞬间"牵动与之纠缠的记忆。

隔离运行、不动真实数据。用法：python scripts/entangle.py
"""

import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.entangle import entangled_with, spreading_activation  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _isolated_base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-ent-"))
    shutil.copytree(ROOT / "config", tmp / "config")
    shutil.copytree(ROOT / "data" / "memories" / "sources", tmp / "data" / "memories" / "sources")
    (tmp / "data" / "faces").mkdir(parents=True, exist_ok=True)
    return tmp


def main() -> None:
    base = _isolated_base()
    try:
        agent = build_agent(base_dir=base)
        names = [p.get("name") for p in agent.authority.people.values()]
        items = agent.memory.items

        print("🔗 记忆纠缠网（每条记忆与谁最相关）\n")
        for it in items:
            partners = entangled_with(it, items, names, k=2)
            if partners:
                ps = "；".join(f"{p['text'][:16]}…({s:.2f})" for s, p in partners)
                print(f"  「{it['text'][:18]}…」\n    ⇄ {ps}")

        print("\n🧪 测量（回忆）一条 → 坍缩出纠缠伙伴：")
        seed = max(items, key=lambda it: sum(s for s, _ in entangled_with(it, items, names, k=8)))
        print(f"  回忆：「{seed['text'][:24]}…」")
        for w, it in spreading_activation([seed], items, names=names, k=3):
            print(f"    ↯ 牵动({w:.2f})：{it['text'][:30]}")

        print("\n💬 对话里它会自然带出联想：")
        r = agent.handle("张明", "聊聊小婷吧")
        print("  问：聊聊小婷吧")
        print("  纠缠联想：", agent.handle("张明", "聊聊小婷吧").get("associations"))

        print("\n✅ 相关记忆纠缠在一起：回忆其一即牵动其二（并顺带强化），"
              "检索就是从一团相关记忆里坍缩出要说的那几条。")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
