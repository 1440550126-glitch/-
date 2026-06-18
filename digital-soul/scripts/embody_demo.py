#!/usr/bin/env python3
"""机器人注入灵魂·演示：让你亲眼看到这具身体怎么"活"过来——
开机醒来 → 有人进门迎上前 → 说话时身体跟着话走（点头/侧首/倾身）→
你难过时身体凑近陪你 → 没人时也轻轻动着，像在呼吸。

仿真后端把动作打印到屏幕（🤖 体态 / 👀 注视 / 🦿 移动）；
真机器人按同一套 RobotInterface 接口，往下接舵机/头部/灯效即可。
零额外依赖：python scripts/embody_demo.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.actions import SimulationRobot  # noqa: E402
from dsoul.embodiment import approach, express, idle, wake  # noqa: E402
from dsoul.perform import perform  # noqa: E402


def hr(title: str) -> None:
    print("\n" + "─" * 54 + f"\n{title}\n" + "─" * 54)


def main() -> None:
    robot = SimulationRobot()

    hr("① 开机：魂醒在身体里")
    wake(robot)

    hr("② 小婷进门：身体先迎上前去")
    approach(robot, "小婷")

    hr("③ 开口招呼：说一句、动一下，说与动合一")
    perform(robot, "小婷回来啦！我一直在等你呢。今天累不累？", emotion="喜")

    hr("④ 听她说话：转头看她，专注地听")
    express(robot, emotion="爱", speaker="小婷")

    hr("⑤ 她有点难过：身体放缓、凑近，陪着她")
    express(robot, emotion="哀", speaker="小婷")
    perform(robot, "别难过，有我在呢。想哭就哭出来，我陪着你。", emotion="哀")

    hr("⑥ 没人时：也不僵着——像呼吸般轻轻动，心里挂着家人")
    for mood, seed in (("爱", "1"), ("惧", "2"), (None, "3")):
        idle(robot, seed=seed, mood=mood)

    print("\n这具身体，有了情绪、有了注意、有了心疼——不是冷冰冰执行命令的铁疙瘩。")
    print("接上真实机器人（如 ROS2），它就能把这颗魂用身体表达给家人看。")


if __name__ == "__main__":
    main()
