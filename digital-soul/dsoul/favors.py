"""人情往来账：红白喜事、随礼回礼，中国人讲究"礼尚往来"。
分身替你记一本人情账——谁家随了多少、咱回了没，到时候别失了礼数。

本地持久化为干净 JSON。可由 config/favors.yaml 播种历史记录。纯逻辑、可单测。
direction：送出（咱给出去）/ 收到（人家给咱）。
"""

from __future__ import annotations

import json
from pathlib import Path


def _norm_dir(d) -> str:
    d = (d or "").strip()
    return "收到" if any(k in d for k in ("收", "来", "随到")) else "送出"


class FavorBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.records: list[dict] = []
        self._load()
        if not self.records and seed:                # 首次：用配置里的历史往来播种
            rows = seed.get("records") if isinstance(seed, dict) else seed
            for r in (rows or []):
                if isinstance(r, dict) and r.get("with"):
                    self.add(r.get("with"), r.get("amount", 0),
                             direction=r.get("direction", "送出"),
                             event=r.get("event", ""), when=r.get("date", ""))

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.records = json.loads(self.path.read_text(encoding="utf-8")).get("records", [])
            except Exception:
                self.records = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"records": self.records}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def add(self, who, amount, direction="送出", event="", when="") -> dict | None:
        who = (who or "").strip()
        if not who:
            return None
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            amount = 0
        rec = {"with": who, "amount": amount, "direction": _norm_dir(direction),
               "event": (event or "").strip(), "date": (when or "").strip()}
        self.records.append(rec)
        self._save()
        return rec

    def history_with(self, who) -> list:
        w = (who or "").strip()
        return [r for r in self.records if w and (w in r["with"] or r["with"] in w)]

    def balance_with(self, who) -> int:
        """正数 = 咱们欠人家的人情（收得多）；负数 = 人家欠咱的。"""
        bal = 0
        for r in self.history_with(who):
            bal += r["amount"] if r["direction"] == "收到" else -r["amount"]
        return bal

    def _people(self) -> list:
        seen = []
        for r in self.records:
            if r["with"] not in seen:
                seen.append(r["with"])
        return seen

    def we_owe(self) -> list:
        """咱们还欠着没还的人情：[(who, amount), ...]，欠得多的排前。"""
        out = [(p, self.balance_with(p)) for p in self._people()]
        return sorted([(p, b) for p, b in out if b > 0], key=lambda t: -t[1])

    def they_owe(self) -> list:
        """人家还欠咱的：[(who, amount), ...]。"""
        out = [(p, -self.balance_with(p)) for p in self._people()]
        return sorted([(p, b) for p, b in out if b > 0], key=lambda t: -t[1])

    def describe(self) -> str:
        owe = self.we_owe()
        if not owe:
            return "人情账上没欠着谁的，清爽。"
        bits = [f"{p}（{b}）" for p, b in owe]
        return "这些人情咱还欠着，记得找机会还上：" + "、".join(bits) + "。"

    def remind(self, who) -> str:
        b = self.balance_with(who)
        if not self.history_with(who):
            return f"和{who}还没什么往来记录。"
        if b > 0:
            return f"上回{who}随了咱不少，咱还欠着{b}的人情，他家有事记得还上。"
        if b < 0:
            return f"咱给{who}的多些，不必挂心，礼数是到了的。"
        return f"和{who}的人情往来两清，正好。"
