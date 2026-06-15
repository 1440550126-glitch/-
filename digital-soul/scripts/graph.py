#!/usr/bin/env python3
"""记忆图谱探索器：从你的记忆里画出"人—事—主题"的关系网。

隔离运行、不动真实数据。展示：最核心的实体、围绕某实体的关联与记忆、两人之间的联系。
用法：python scripts/graph.py
"""

import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.graph import build_memory_graph  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _isolated_base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-graph-"))
    shutil.copytree(ROOT / "config", tmp / "config")
    shutil.copytree(ROOT / "data" / "memories" / "sources", tmp / "data" / "memories" / "sources")
    (tmp / "data" / "faces").mkdir(parents=True, exist_ok=True)
    return tmp


def main() -> None:
    base = _isolated_base()
    try:
        agent = build_agent(base_dir=base)
        g = build_memory_graph(agent.memory, agent.authority)
        print(f"🕸️  记忆图谱：{len(g.nodes())} 个实体，来自 {len(agent.memory.items)} 条记忆\n")

        print("【最核心的实体（中心度）】")
        for name, score in g.central(8):
            kind = g.meta[name].get("kind")
            rel = g.meta[name].get("relation")
            tag = f"（{rel}）" if rel else f"（{kind}）"
            print(f"  ● {name}{tag}  关联度 {score}")

        people = [n for n in g.nodes() if g.meta[n].get("kind") == "person"]
        if people:
            who = max(people, key=lambda n: sum(g.adj[n].values()))
            print(f"\n【围绕「{who}」】")
            for nb, w in g.neighbors(who, 6):
                print(f"  {who} ─[{w}]─ {nb}")
            for m in g.about(who, 3):
                print(f"    · 记忆：{m}")

        if len(people) >= 2:
            a, b = people[0], people[1]
            bt = g.between(a, b)
            print(f"\n【「{a}」与「{b}」的联系】 共现强度 {bt['edge']}")
            for m in bt["shared"]:
                print(f"    · {m}")

        print("\n✅ 在对话里也能问：「关于<某人/某事>」「我的关系网」「最核心的人」")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
