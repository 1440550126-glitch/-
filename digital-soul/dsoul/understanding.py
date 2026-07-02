"""我眼里的你：相处越久越懂你。把每次聊天里看出的东西沉淀下来——
你常烦心的事、近来的心绪、跟我处得有多近。下次见你，我心里有数，不用重新打量。

本地持久化为干净 JSON，纯逻辑、可单测。Agent 每次对话后 update，需要时取 portrait。
"""

from __future__ import annotations

import json
from pathlib import Path

# 复用"看出门道"的烦心主题
from .observe import _THEMES

# 主导心绪 → 脾气的一句概括
_TEMPER = {
    "哀": "你心思重，爱把事往心里搁",
    "惧": "你容易操心、放心不下",
    "喜": "你性子敞亮，爱说爱笑",
    "乐": "你性子敞亮，爱说爱笑",
    "怒": "你性子直，有话搁不住",
    "爱": "你心软、重感情",
    "恶": "你眼里揉不得沙子",
    "欲": "你心里有股劲、想头多",
}


class Understanding:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.people: dict = {}     # name -> {count, concerns:{theme:n}, moods:[...]}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.people = json.loads(self.path.read_text(encoding="utf-8")).get("people", {})
            except Exception:
                self.people = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"people": self.people}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def _rec(self, name) -> dict:
        return self.people.setdefault(
            str(name), {"count": 0, "concerns": {}, "moods": []})

    def observe(self, name, utterance, emotion=None) -> None:
        """从一次互动里沉淀：数一数烦心主题，记下心绪。"""
        name = (name or "").strip()
        if not name:
            return
        rec = self._rec(name)
        rec["count"] += 1
        text = str(utterance or "")
        for theme, kws in _THEMES.items():
            if any(k in text for k in kws):
                rec["concerns"][theme] = rec["concerns"].get(theme, 0) + 1
        if emotion:
            rec["moods"] = (rec["moods"] + [emotion])[-12:]    # 只留近 12 次心绪
        self._save()

    def top_concerns(self, name, k=2) -> list:
        rec = self.people.get(str(name))
        if not rec:
            return []
        return [t for t, _ in sorted(rec["concerns"].items(), key=lambda kv: -kv[1])[:k]]

    def dominant_mood(self, name):
        rec = self.people.get(str(name))
        moods = (rec or {}).get("moods") or []
        if not moods:
            return None
        from collections import Counter
        return Counter(moods).most_common(1)[0][0]

    def familiarity(self, name) -> str:
        n = (self.people.get(str(name)) or {}).get("count", 0)
        if n >= 20:
            return "知根知底"
        if n >= 6:
            return "渐渐熟了"
        return "还在慢慢了解"

    def brief(self, name) -> str:
        """一句话的"我对你的了解"，供思考/提示用（不够熟就不妄下判断，返回空）。"""
        rec = self.people.get(str(name))
        if not rec or rec["count"] < 3:
            return ""
        bits = []
        temper = _TEMPER.get(self.dominant_mood(name))
        if temper:
            bits.append(temper)
        concerns = self.top_concerns(name, 1)
        if concerns:
            bits.append(f"近来为「{concerns[0]}」烦心")
        return "、".join(bits)

    def portrait(self, name) -> str:
        """说说"在我眼里你是怎样的人"。"""
        rec = self.people.get(str(name))
        if not rec or rec["count"] < 1:
            return f"我跟{name}还不算熟，正慢慢了解你呢。"
        bits = [f"咱处了 {rec['count']} 回，{self.familiarity(name)}"]
        temper = _TEMPER.get(self.dominant_mood(name))
        if temper:
            bits.append(temper)
        concerns = self.top_concerns(name, 2)
        if concerns:
            bits.append("这阵子你常为「" + "、".join(concerns) + "」的事烦心")
        return f"在我眼里——{('；'.join(bits))}。处得越久，我越懂你。"
