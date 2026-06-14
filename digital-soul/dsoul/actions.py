"""机器人动作接口（将来接入真实硬件 / ROS 的抽象层）。

现在用 SimulationRobot 把动作打印到屏幕；将来把 RobotInterface 实现成
驱动真实电机/语音/摄像头的版本，Agent 的其余代码一行都不用改。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class RobotInterface(ABC):
    @abstractmethod
    def say(self, text: str) -> None: ...

    @abstractmethod
    def move(self, direction: str, meters: float = 1.0) -> None: ...

    @abstractmethod
    def look_at(self, target: str) -> None: ...

    @abstractmethod
    def protect(self, target: str) -> None: ...


class SimulationRobot(RobotInterface):
    """把动作打印到控制台，便于在没有硬件时调试。"""

    def say(self, text: str) -> None:
        print(f"🗣️  [说] {text}")

    def move(self, direction: str, meters: float = 1.0) -> None:
        print(f"🦿 [移动] 朝「{direction}」走 {meters} 米")

    def look_at(self, target: str) -> None:
        print(f"👀 [注视] 看向 {target}")

    def protect(self, target: str) -> None:
        print(f"🛡️  [守护] 进入守护模式，全力保护 {target}")
