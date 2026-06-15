"""自主反思：把"流水账"提炼成"领悟"。

借鉴 Generative Agents 的「记忆流 → 反思」范式：隔一段时间回看近期经历，
归纳出对主人状态、对关系、对自己的更高层洞见，作为新记忆写回——
让分身不只是"记录"，而是"想明白了点什么"，并影响日后的回应。

LLM 在场时用它归纳；不在场则用启发式（情绪倾向 / 高频话题 / 最常相处的人），
保证 16G 纯本地也能"反思"。
"""

from __future__ import annotations

import re
from collections import Counter

from .annotate import classify_emotion

_STOP = set("的了是我你他她它们这那有在和就都也不一个没很把被到去吧呢啊吗与而又且或着过得地多还会要说想")


def _bigrams(text: str) -> list[str]:
    chars = [c for c in (text or "") if "一" <= c <= "鿿"]
    return [a + b for a, b in zip(chars, chars[1:]) if a not in _STOP and b not in _STOP]


class Reflector:
    def __init__(self, memory, journal, emotions=None, llm=None, identity=None, authority=None) -> None:
        self.memory = memory
        self.journal = journal
        self.emotions = emotions
        self.llm = llm
        self.identity = identity or {}
        self.authority = authority

    def _recent(self, n: int) -> list[dict]:
        if self.journal is None:
            return []
        return list(self.journal._all()[-n:])

    def reflect(self, n: int = 20, max_insights: int = 3) -> list[str]:
        """回看最近 n 条经历 → 写回最多 max_insights 条"领悟"（tags=[reflection]）。

        返回本次"新"产生的领悟（已存在的不重复写、不重复报）。
        """
        rec = self._recent(n)
        if len(rec) < 3:
            return []  # 经历太少，不强行反思
        if self.llm is not None and getattr(self.llm, "available", False):
            insights = self._llm_insights(rec, max_insights)
        else:
            insights = self._heuristic_insights(rec, max_insights)
        gi = self._graph_insight()                 # 图谱视角：围绕核心实体的领悟
        if gi:
            insights = [gi] + insights
        out: list[str] = []
        for s in insights[:max_insights]:
            s = (s or "").strip()
            if not s or any(it["text"] == s for it in self.memory.items):
                continue  # 空的、或已经悟过的，跳过
            self.memory.add(s, source="reflection", tags=["reflection", "领悟"])
            out.append(s)
        return out

    # ---------- 启发式（无 LLM 也能反思）----------
    def _heuristic_insights(self, rec: list[dict], k: int) -> list[str]:
        utters = [e.get("utterance", "") for e in rec if e.get("utterance")]
        speakers = [e.get("speaker") for e in rec if e.get("speaker")]
        out: list[str] = []
        # 1) 情绪倾向
        labels = [classify_emotion(u)["label"] for u in utters]
        labels = [x for x in labels if x and x != "平静"]
        if labels:
            top, cnt = Counter(labels).most_common(1)[0]
            if cnt >= 2:
                out.append(f"这段时间，大家在我面前多次流露「{top}」——我留意到了，会更上心一些。")
        # 2) 高频话题
        bg: Counter = Counter()
        for u in utters:
            bg.update(set(_bigrams(u)))
        if bg:
            word, cnt = bg.most_common(1)[0]
            if cnt >= 2:
                out.append(f"最近「{word}」被反复提起，看来这阵子它对大家挺要紧，我得放在心上。")
        # 3) 最常相处的人
        me = self.identity.get("name")
        ppl = [s for s in speakers if s and s != me]
        if ppl:
            who, cnt = Counter(ppl).most_common(1)[0]
            if cnt >= 2:
                out.append(f"这些日子我和「{who}」聊得最多，我们之间好像又近了一点。")
        return out[:k]

    # ---------- 图谱视角：围绕核心实体的领悟 ----------
    def _graph_insight(self):
        if self.authority is None:
            return None
        try:
            from .graph import build_memory_graph
            g = build_memory_graph(self.memory, self.authority)
        except Exception:
            return None
        owner = next((p["name"] for p in self.authority.people.values()
                      if p.get("trust") == "owner"), None)
        persons = [n for n in g.nodes() if g.meta.get(n, {}).get("kind") == "person" and n != owner]
        if not persons:
            return None
        person = max(persons, key=lambda n: sum(g.adj[n].values()))
        topics = [n for n, _ in g.neighbors(person) if g.meta.get(n, {}).get("kind") == "topic"][:2]
        rel = g.meta[person].get("relation")
        rel_s = f"（{rel}）" if rel else ""
        tail = f"，常和「{'、'.join(topics)}」连在一起" if topics else ""
        return f"在我的记忆里，「{person}」{rel_s}始终是核心{tail}——我会更珍惜。"

    # ---------- LLM 归纳 ----------
    def _llm_insights(self, rec: list[dict], k: int) -> list[str]:
        lines = "\n".join(
            f"- {e.get('speaker', '?')}：{e.get('utterance', '')}"
            for e in rec if e.get("utterance")
        )
        name = self.identity.get("name", "我")
        system = (
            f"你是{name}的数字分身。下面是你最近的一些对话片段。"
            f"请像写日记一样，提炼出至多 {k} 条更高层、更长期的洞见"
            "（关于主人近况、关系变化、或你自己的体会），每条一句话、第一人称、"
            "简洁真诚，不要复述原话。只输出要点，每行一条。"
        )
        try:
            text = self.llm.chat(system, lines)
        except Exception:
            return self._heuristic_insights(rec, k)
        outs = [re.sub(r"^[\s\-\d.、)）]+", "", ln).strip() for ln in text.splitlines()]
        return [x for x in outs if x][:k]
