"""授权系统：决定"听谁的、什么人不听、谁能让我做什么"。

每个人 -> 一个信任等级 -> 一组权限。
未登记的人一律按"陌生人"处理。被拉黑(blocked)的人永远不服从。
"""

from __future__ import annotations


class Authority:
    def __init__(self, config: dict) -> None:
        self.trust_levels: dict = config.get("trust_levels", {})
        self.permissions: dict = config.get("permissions", {})
        self.people: dict = {p["name"]: p for p in config.get("people", [])}

    def resolve(self, name: str | None) -> dict:
        """把一个名字解析成完整身份（含信任/权限/是否服从/是否守护）。"""
        person = self.people.get(name)
        if person is None:
            return {
                "name": name or "陌生人",
                "relation": "陌生人",
                "trust": "stranger",
                "trust_score": self.trust_levels.get("stranger", 0),
                "obey": False,
                "guard": False,
                "feelings": None,
                "permissions": list(self.permissions.get("stranger", [])),
                "face_id": None,
                "known": False,
            }
        trust = person.get("trust", "stranger")
        default_obey = trust not in ("blocked", "stranger")
        return {
            "name": person["name"],
            "relation": person.get("relation", "未知"),
            "trust": trust,
            "trust_score": self.trust_levels.get(trust, 0),
            "obey": person.get("obey", default_obey),
            "guard": person.get("guard", False),
            "feelings": person.get("feelings"),
            "permissions": list(self.permissions.get(trust, [])),
            "face_id": person.get("face_id"),
            "known": True,
        }

    def can(self, name: str | None, action: str) -> tuple[bool, dict, str]:
        """(是否允许, 身份, 原因)。"""
        who = self.resolve(name)
        if not who["obey"]:
            return False, who, f"我不会听{who['name']}（{who['relation']}）的命令。"
        if "*" in who["permissions"] or action in who["permissions"]:
            return True, who, "ok"
        return (
            False,
            who,
            f"{who['name']}（{who['relation']}）没有权限让我做「{action}」。",
        )

    def guarded_people(self) -> list[str]:
        return [p["name"] for p in self.people.values() if p.get("guard")]
