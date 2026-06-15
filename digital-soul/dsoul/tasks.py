"""派活待办本：记下"办成 / 没办成"的事，支持回顾、主动跟进、重试。

纯 JSON 持久化、零依赖、可单测。同一(智能体, 指令)若反复失败会累加重试次数，
成功后自动关闭。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class TaskBook:
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
        self.path.write_text(
            json.dumps({"items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def record(self, agent: str, instruction: str, ok: bool, detail: str = "") -> str:
        """记一笔派活结果。同一(智能体,指令)若已存在且未完成，则累加重试次数。"""
        status = "done" if ok else "open"
        for it in self.items:
            if it["agent"] == agent and it["instruction"] == instruction and it["status"] != "done":
                it["attempts"] += 1
                it["status"] = status
                it["detail"] = detail
                it["ts"] = time.time()
                self._save()
                return it["id"]
        tid = hashlib.sha1(f"{agent}|{instruction}|{time.time()}".encode("utf-8")).hexdigest()[:12]
        self.items.append({
            "id": tid, "agent": agent, "instruction": instruction,
            "status": status, "detail": detail, "attempts": 1, "ts": time.time(),
        })
        self._save()
        return tid

    def open(self) -> list[dict]:
        """未办成（没联系上 / 失败）的待办。"""
        return [it for it in self.items if it["status"] != "done"]

    def done(self) -> list[dict]:
        return [it for it in self.items if it["status"] == "done"]

    def mark_done(self, tid: str, detail: str = "") -> bool:
        for it in self.items:
            if it["id"] == tid:
                it["status"] = "done"
                if detail:
                    it["detail"] = detail
                self._save()
                return True
        return False
