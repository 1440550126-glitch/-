#!/usr/bin/env python3
"""持续感知：摄像头认人，有人进入画面就【主动打招呼】。

真实模式需要 opencv-python + face_recognition + 已登记人脸。
没有摄像头时用 --simulate 演示。

用法：
  python scripts/watch.py                          # 摄像头实时
  python scripts/watch.py --simulate 小婷 路人甲 老钱   # 模拟依次出现的人
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402
from dsoul.presence import PresenceMonitor  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", nargs="*", default=None, help="模拟依次出现的人名")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    agent = build_agent()
    me = agent.identity.get("name", "我")

    def on_enter(name: str) -> None:
        print(f"\n👁️  检测到【{name}】进入画面")
        text = agent.greet(name)
        print(f"   → {me}: {text}")

    def on_leave(name: str) -> None:
        print(f"👋 【{name}】离开了画面")

    mon = PresenceMonitor(
        agent.perception, on_enter=on_enter, on_leave=on_leave, camera_index=args.camera
    )

    if args.simulate is not None:
        print("（模拟模式：依次让这些人出现在画面）")
        t = 0.0
        for name in args.simulate:
            mon.observe({name}, now=t)
            mon.observe(set(), now=t + 100)  # 让其离开，便于演示下一个
            t += 200
        return

    if not mon.available:
        print("⚠️  摄像头 / 人脸识别不可用。")
        print("   请 `pip install opencv-python face_recognition` 并登记人脸后再试，")
        print("   或先用模拟模式：python scripts/watch.py --simulate 小婷 路人甲")
        return

    print("📹 持续感知中... 按 Ctrl+C 结束")
    try:
        mon.run()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
