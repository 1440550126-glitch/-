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

    def gesture(self, name: str, detail: str = "") -> None:
        """表情 / 体态动作（默认不做；有身体的机器人可实现成驱动头部/舵机/灯效）。

        这是给机器身体"注入灵魂"的通道：随情绪点头、垂首、倾身、戒备……
        非抽象，旧的机器人实现不强制改动即可继续用。
        """
        return None

    def face(self, channels: dict) -> None:
        """驱动面部舵机：channels 形如 {"mouth_l": 1700, "jaw": 1300, ...}（通道→脉宽微秒）。

        默认不做；有脸的机器人实现成给每个舵机发 PWM。配合 face_motors 把"表情"换成舵机角度，
        再配合 expression_feedback 的视觉闭环，就能边看自己边把表情调到位。
        """
        return None


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

    def gesture(self, name: str, detail: str = "") -> None:
        print(f"🤖 [体态] {name}" + (f"（{detail}）" if detail else ""))

    def face(self, channels: dict) -> None:
        pretty = "  ".join(f"{c}={int(v)}" for c, v in sorted((channels or {}).items()))
        print(f"😶 [面部舵机] {pretty}")
