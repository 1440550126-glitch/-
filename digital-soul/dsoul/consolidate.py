"""长期记忆巩固（"睡眠"机制）。

把日记里尚未巩固的对话，提炼成简短的第一人称长期记忆，写进记忆库：
- 接了本地大模型：让模型总结"值得记住的事"。
- 没接模型：规则挑出有信息量的话（情感强 / 含时间 / 含承诺 / 提到熟人）。
巩固后推进 journal 的 cursor，保证幂等（再跑一次不会重复学习）。
"""

from __future__ import annotations

from .annotate import classify_emotion, extract_when

_CUES = [
    "答应", "约好", "约定", "计划", "决定", "打算", "升职", "结婚", "生日",
    "搬家", "旅行", "第一次", "再也", "终于", "梦想", "希望", "买了", "去了",
    "见了", "学会", "完成", "失去", "离开",
]


class Consolidator:
    def __init__(self, memory, journal, llm=None, identity=None, authority=None) -> None:
        self.memory = memory
        self.journal = journal
        self.llm = llm
        self.identity = identity or {}
        self.authority = authority

    def run(self, max_new: int = 5) -> dict:
        entries = self.journal.unconsolidated()
        if not entries:
            return {"processed": 0, "learned": []}

        if self.llm is not None and getattr(self.llm, "available", False):
            try:
                candidates = self._llm_distill(entries, max_new)
            except Exception:
                candidates = self._rule_distill(entries, max_new)
        else:
            candidates = self._rule_distill(entries, max_new)

        existing = {it["text"] for it in self.memory.items}
        learned = []
        for m in candidates:
            m = m.strip()
            if m and m not in existing:
                self.memory.add(m, source="consolidated")
                existing.add(m)
                learned.append(m)

        self.journal.mark_consolidated()
        return {"processed": len(entries), "learned": learned}

    # ---------- 规则版（无大模型时）----------
    def _owner_names(self) -> set:
        return {self.identity.get("name")} | set(self.identity.get("aka") or [])

    def _salient(self, u: str) -> bool:
        if len(u) < 6:
            return False
        if classify_emotion(u)["label"] != "平静":
            return True
        if extract_when(u):
            return True
        if any(c in u for c in _CUES):
            return True
        if self.authority is not None:
            for name in self.authority.people:
                if name and name in u:
                    return True
        return False

    def _rule_distill(self, entries, max_new):
        owners = self._owner_names()
        out = []
        for e in entries:
            u = (e.get("utterance") or "").strip()
            if not self._salient(u):
                continue
            spk = e.get("speaker") or ""
            rel = e.get("speaker_relation") or ""
            if spk in owners or rel == "本人":
                out.append(u)
            else:
                out.append(f"{spk}（{rel}）跟我说：{u}")
            if len(out) >= max_new:
                break
        return out

    # ---------- 大模型版 ----------
    def _llm_distill(self, entries, max_new):
        name = self.identity.get("name", "我")
        lines = []
        for e in entries:
            lines.append(f"{e.get('speaker', '?')}：{e.get('utterance', '')}")
            if e.get("reply"):
                lines.append(f"{name}：{e['reply']}")
        transcript = "\n".join(lines)
        system = f"你是{name}。请从对话里提炼值得长期记住的事，用第一人称写成简短记忆。"
        prompt = (
            f"以下是最近的对话记录。请提炼最多 {max_new} 条值得我长期记住的事情，"
            "每条一行、简短、第一人称，不要编造未提到的内容，只输出记忆本身：\n\n"
            + transcript
        )
        raw = self.llm.chat(system, prompt)
        out = []
        for ln in raw.splitlines():
            ln = ln.strip().lstrip("-•*0123456789.、） )").strip()
            if len(ln) >= 4:
                out.append(ln)
        return out[:max_new]
