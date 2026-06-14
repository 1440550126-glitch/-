#!/usr/bin/env python3
"""一键常驻服务：同时跑「持续感知（摄像头主动打招呼）」+「定时睡眠巩固」。

适合部署到树莓派 / 机器人，配合 systemd 开机自启（见 docs/deploy.md）。

用法：
  python scripts/daemon.py                    # 感知 + 每 8 小时巩固
  python scripts/daemon.py --sleep-every 6    # 每 6 小时巩固
  python scripts/daemon.py --no-vision        # 不开摄像头，仅定时巩固
  python scripts/daemon.py --robot ros2       # 动作走 ROS2 机器人
"""

import argparse
import pathlib
import sys
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402
from dsoul.presence import PresenceMonitor  # noqa: E402


def start_vision(agent) -> bool:
    me = agent.identity.get("name", "我")

    def on_enter(name: str) -> None:
        print(f"[感知] {name} 进入画面 → {me}: {agent.greet(name)}", flush=True)

    def on_leave(name: str) -> None:
        print(f"[感知] {name} 离开画面", flush=True)

    mon = PresenceMonitor(agent.perception, on_enter=on_enter, on_leave=on_leave)
    if not mon.available:
        print("[感知] 摄像头 / 人脸识别不可用，跳过视觉。", flush=True)
        return False
    threading.Thread(target=mon.run, daemon=True).start()
    print("[感知] 摄像头持续感知已启动。", flush=True)
    return True


def sleep_loop(agent, hours: float) -> None:
    while True:
        time.sleep(hours * 3600)
        rep = Consolidator(
            agent.memory, agent.journal, llm=agent.llm,
            identity=agent.identity, authority=agent.authority,
        ).run()
        print(f"[睡眠] 巩固 {rep['processed']} 条 → 新增 {len(rep['learned'])} 条记忆", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep-every", type=float, default=8.0, help="每 N 小时巩固一次")
    ap.add_argument("--no-vision", action="store_true", help="不启用摄像头感知")
    ap.add_argument("--robot", choices=["sim", "ros2"], default="sim", help="动作执行后端")
    args = ap.parse_args()

    robot = None
    if args.robot == "ros2":
        from dsoul.ros2_robot import Ros2Robot

        robot = Ros2Robot()
    agent = build_agent(robot=robot)

    me = agent.identity.get("name", "我")
    llm = "✅" if agent.llm.available else "降级"
    print(
        f"🤖 {me} 的数字分身常驻服务启动 ｜ 大模型:{llm} ｜ 记忆 {len(agent.memory.items)} 条"
        f" ｜ 机器人:{args.robot}",
        flush=True,
    )

    if not args.no_vision:
        start_vision(agent)
    threading.Thread(target=sleep_loop, args=(agent, args.sleep_every), daemon=True).start()
    print(f"🌙 每 {args.sleep_every} 小时自动巩固一次。Ctrl+C 退出。", flush=True)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
