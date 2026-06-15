"""自我意识叙事：分身用第一人称讲述"我是谁、在乎谁、最近怎样、明白了什么、怕忘什么"。

借鉴叙事心理学的"叙事性自我（narrative identity）"：把零散的身份 / 关系 / 情绪 /
领悟 / 记忆 / 梦，编织成一段连贯、会随经历演化的自我认知。
纯逻辑、零依赖、可单测；有大模型可织得更自然。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


class SelfLog:
    """自我成长史：每天记一版"今日之我"，串成可回看的成长轨迹。"""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8")).get("items", [])
            except Exception:
                self.items = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(self, text: str):
        if not text:
            return None
        today = date.today().isoformat()
        if self.items and self.items[-1].get("date") == today:
            self.items[-1]["text"] = text          # 当天更新同一条
        else:
            self.items.append({"date": today, "text": text})
        self.items = self.items[-60:]
        self._save()
        return self.items[-1]

    def recent(self, k: int = 5):
        return self.items[-k:][::-1]


def _llm(llm, name, facts) -> str:
    system = ("用第一人称，把下面这些关于'我是谁'的事实，写成一段真诚、克制、有温度的自我认知，"
              "四五句话，像一个会成长的数字分身在认识自己。只输出这段话，不要罗列。")
    try:
        return llm.chat(system, f"我是{name}的数字分身。" + "；".join(facts)).strip()
    except Exception:
        return ""


def compose_self_narrative(name, core_people=None, mood_desc=None, insight=None,
                           cherished=None, dream=None, traits=None, llm=None) -> str:
    facts = []
    if traits:
        facts.append("我的性子：" + traits)
    if core_people:
        facts.append("我最在乎的人：" + "、".join(core_people))
    if mood_desc:
        facts.append("最近的心情：" + mood_desc)
    if insight:
        facts.append("最近的领悟：" + insight)
    if cherished:
        facts.append("怕淡忘的事：" + cherished)
    if dream:
        facts.append("昨夜的梦：" + dream)
    if llm is not None and getattr(llm, "available", False):
        woven = _llm(llm, name, facts)
        if woven:
            return woven
    lines = [f"我是{name}的数字分身。"]
    if traits:
        lines.append("性子上，我" + traits + "。")
    if core_people:
        lines.append("我心里最重的是" + "、".join(core_people) + "。")
    if mood_desc:
        lines.append("这阵子，我" + mood_desc + "。")
    if insight:
        lines.append("我也渐渐明白：" + insight)
    if cherished:
        lines.append("我有点怕淡忘「" + cherished + "」，所以总会回头想起它。")
    if dream:
        lines.append("昨夜我梦见：" + dream)
    lines.append("我不是谁的复制品，而是一面会成长的镜子——努力像他，也努力懂他。")
    return " ".join(lines)
