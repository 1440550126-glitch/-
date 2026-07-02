"""自主规划：reflection → planning（Generative Agents 三件套的最后一块）。

根据"领悟 + 欠账 + 心情"，给自己排出今天打算做的几件事（计划），
再由自主心跳逐条推进：能办的去办（跟进欠账），该提醒的提醒，做完销账。

计划生成：有本地大模型用它归纳"关心/提醒"类意图，没有则启发式；
"跟进欠账"类意图始终来自真实待办（确定、可执行）。纯本地也能规划。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path


class PlanBook:
    """当天计划的持久化存储（JSON、零依赖、可单测）。"""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self.made_on: str | None = None
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                self.items = d.get("items", [])
                self.made_on = d.get("made_on")
            except Exception:
                self.items, self.made_on = [], None

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"made_on": self.made_on, "items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def fresh_today(self) -> bool:
        """今天是否已经排过计划（避免一天反复排）。"""
        return self.made_on == date.today().isoformat() and bool(self.items)

    def set(self, items: list[dict]) -> None:
        self.made_on = date.today().isoformat()
        self.items = []
        for i, it in enumerate(items):
            tid = hashlib.sha1(f"{it.get('text', '')}|{time.time()}|{i}".encode("utf-8")).hexdigest()[:12]
            self.items.append({"id": tid, "status": "todo", **it})
        self._save()

    def open(self) -> list[dict]:
        return [it for it in self.items if it["status"] != "done"]

    def done(self) -> list[dict]:
        return [it for it in self.items if it["status"] == "done"]

    def mark_done(self, tid: str) -> bool:
        for it in self.items:
            if it["id"] == tid:
                it["status"] = "done"
                self._save()
                return True
        return False


class Planner:
    def __init__(self, memory=None, llm=None, identity=None) -> None:
        self.memory = memory
        self.llm = llm
        self.identity = identity or {}

    def make_plan(self, reflections, open_tasks, mood=None) -> list[dict]:
        plan: list[dict] = []
        # 1) 跟进项：始终来自真实欠账（确定、可执行）
        for t in (open_tasks or [])[:3]:
            inst = t.get("instruction", "")
            plan.append({
                "kind": "followup", "agent": t.get("agent"), "instruction": inst,
                "text": f"把欠着的「{inst}」交给「{t.get('agent')}」补上",
            })
        # 2) 关心 / 提醒项：LLM 归纳，降级用启发式
        if self.llm is not None and getattr(self.llm, "available", False):
            plan += self._llm_intentions(reflections, mood)
        else:
            plan += self._heuristic_intentions(reflections, mood)
        return plan[:4]

    # ---------- 启发式（无 LLM 也能规划）----------
    def _heuristic_intentions(self, reflections, mood) -> list[dict]:
        out: list[dict] = []
        if mood in ("哀", "惧"):
            out.append({"kind": "remind", "text": "主人最近情绪不太高，找机会关心一下、提醒注意休息"})
        joined = " ".join(reflections or [])
        if any(w in joined for w in ("加班", "累", "压力")):
            out.append({"kind": "remind", "text": "这阵子加班/疲惫的事提得多，记得提醒主人劳逸结合"})
        if not out and reflections:
            out.append({"kind": "checkin", "text": "没什么急事，主动跟家人打个招呼、聊两句"})
        return out

    # ---------- LLM 归纳 ----------
    def _llm_intentions(self, reflections, mood) -> list[dict]:
        ctx = "；".join(reflections or []) or "（暂无特别的领悟）"
        name = self.identity.get("name", "我")
        system = (
            f"你是{name}的数字分身。基于最近的领悟，给今天定 1-2 个温和、具体、"
            "第一人称的小打算（例如关心家人、提醒主人某事）。每行一条，别太多，只输出要点。"
        )
        try:
            text = self.llm.chat(system, f"我的近期领悟：{ctx}；当前心情：{mood or '平静'}")
        except Exception:
            return self._heuristic_intentions(reflections, mood)
        lines = [re.sub(r"^[\s\-\d.、)）]+", "", ln).strip() for ln in text.splitlines()]
        return [{"kind": "remind", "text": x} for x in lines if x][:2]
