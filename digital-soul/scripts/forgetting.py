#!/usr/bin/env python3
"""记忆遗忘曲线演示：随时间推移，哪些记忆变淡、哪些长留，回忆又如何唤醒。

隔离运行、不动真实数据。用法：python scripts/forgetting.py
"""

import pathlib
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.forgetting import classify, importance, strength  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _isolated_base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-forget-"))
    shutil.copytree(ROOT / "config", tmp / "config")
    shutil.copytree(ROOT / "data" / "memories" / "sources", tmp / "data" / "memories" / "sources")
    (tmp / "data" / "faces").mkdir(parents=True, exist_ok=True)
    return tmp


def _show(agent, now, title):
    print(f"\n{title}")
    rows = sorted(((strength(it, now), it) for it in agent.memory.items), key=lambda x: x[0])
    for s, it in rows:
        bar = "█" * round(s * 10)
        print(f"  [{classify(s):2}] {s:4.2f} {bar:<10} 重要性{importance(it):.1f} | {it['text'][:26]}")


def main() -> None:
    base = _isolated_base()
    try:
        agent = build_agent(base_dir=base)
        now0 = time.time()
        _show(agent, now0, "① 刚记下时——都还清晰")

        later = now0 + 45 * 86400          # 快进 45 天
        _show(agent, later, "② 45 天后——琐碎/平淡的开始淡忘，情感深的仍清晰")

        # "回忆"一条正在变淡的记忆 → 被唤醒强化
        faint = min(agent.memory.items, key=lambda it: strength(it, later))
        agent.memory.reinforce([faint["id"]], now=later)
        print(f"\n③ 回忆了一下：「{faint['text'][:26]}」")
        print(f"   唤醒后强度：{strength(faint, later):.2f}（回忆刷新了记忆，并提高了稳定度）")

        print("\n✅ 记忆像人一样：会随时间淡忘，越重要/越常想起越长久。"
              "（手机网页「🧠 正在淡忘」实时可见）")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
