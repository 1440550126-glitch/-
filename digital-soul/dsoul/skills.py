"""技能：做饭、做家务等可执行能力。

每个技能声明所需权限（走授权闸门），执行时落到机器人动作，或转交外部智能体。
内置几个示例技能；可用 register() 扩展。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Skill:
    name: str
    desc: str
    permission: str
    run: Callable  # run(agent, **params) -> str


def _cook(agent, dish: str = "拿手菜", **_) -> str:
    agent.robot.say(f"好嘞，我去给你做{dish}，等我～")
    return f"已开始做：{dish}"


def _clean(agent, area: str = "客厅", **_) -> str:
    agent.robot.say(f"我来收拾{area}，你歇着。")
    agent.robot.move("前", 1.0)
    return f"正在打扫：{area}"


def _remind(agent, what: str = "喝水", **_) -> str:
    agent.robot.say(f"提醒你：该{what}啦。")
    return f"已提醒：{what}"


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        # 内置技能（默认需要 control_devices 权限：家人/主人可用）
        self.register(Skill("cook", "做饭", "control_devices", _cook))
        self.register(Skill("clean", "做家务/打扫", "control_devices", _clean))
        self.register(Skill("remind", "提醒", "chat", _remind))

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def names(self) -> list[str]:
        return list(self._skills)

    def permission(self, name: str) -> str:
        s = self._skills.get(name)
        return s.permission if s else "chat"
