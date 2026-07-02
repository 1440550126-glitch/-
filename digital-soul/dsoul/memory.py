"""个人记忆库（RAG 的"存"与"取"）。

设计目标：零重型依赖也能跑。
- 如果装了 sentence-transformers，就用真正的语义向量；
- 没装就自动降级到内置的"词法向量"（字符 + 二元组哈希），对中文也有效。

存储只保存原文（text/source/tags），向量在加载时重算，所以索引文件干净、可读。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path

from .annotate import classify_emotion, extract_when


class Embedder:
    """把一段文字变成稀疏向量 dict[str, float]。优先语义，降级词法。"""

    def __init__(self) -> None:
        self.model = None
        try:  # 可选：真正的语义模型
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.model = None

    @property
    def mode(self) -> str:
        return "semantic" if self.model is not None else "lexical"

    def embed(self, text: str) -> dict[str, float]:
        if self.model is not None:
            vec = self.model.encode(text or "")
            return {str(i): float(v) for i, v in enumerate(vec)}
        return self._lexical(text)

    @staticmethod
    def _lexical(text: str) -> dict[str, float]:
        text = (text or "").lower()
        chars = [c for c in text if c.strip() and not c.isspace()]
        tokens: list[str] = []
        tokens.extend(chars)                                   # 单字（中文友好）
        tokens.extend(a + b for a, b in zip(chars, chars[1:]))  # 二元组
        tokens.extend(re.findall(r"[a-z0-9]+", text))          # 英文词
        vec: dict[str, float] = {}
        for t in tokens:
            vec[t] = vec.get(t, 0.0) + 1.0
        return vec


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class Memory:
    """可检索的个人记忆库。"""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.embedder = Embedder()
        self.items: list[dict] = []
        self._load()

    # ---------- 持久化 ----------
    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = data.get("items", [])
            for it in self.items:  # 加载时重算向量
                it["vec"] = self.embedder.embed(it["text"])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        clean = [{k: v for k, v in it.items() if k != "vec"} for it in self.items]
        self.path.write_text(
            json.dumps({"items": clean}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---------- 读写 ----------
    def add(self, text: str, source: str = "manual", tags=None,
            when=None, emotion=None) -> str | None:
        text = (text or "").strip()
        if not text:
            return None
        mid = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        if any(it["id"] == mid for it in self.items):  # 去重
            return mid
        self.items.append(
            {
                "id": mid,
                "text": text,
                "source": source,
                "tags": tags or [],
                "when": when if when is not None else extract_when(text),
                "emotion": emotion if emotion is not None else classify_emotion(text)["label"],
                "created": time.time(),
                "vec": self.embedder.embed(text),
            }
        )
        self._save()
        return mid

    def reinforce(self, ids, now: float | None = None) -> None:
        """被回忆即强化：刷新计时（间隔重复）并累计回忆次数，让记忆更难淡忘。"""
        now = time.time() if now is None else now
        wanted = set(ids)
        changed = False
        for it in self.items:
            if it["id"] in wanted:
                it["recalls"] = it.get("recalls", 0) + 1
                it["last_recall"] = now
                changed = True
        if changed:
            self._save()

    def recall(self, query: str, k: int = 4) -> list[tuple[float, dict]]:
        """返回与 query 最相关的 k 条记忆：[(相似度, 记忆), ...]。"""
        qv = self.embedder.embed(query)
        scored = [(cosine(qv, it["vec"]), it) for it in self.items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(s, it) for s, it in scored[:k] if s > 0]

    def timeline(self) -> list[dict]:
        """按时间（年份）升序返回记忆，时间未知的排在最后。"""

        def key(it):
            w = it.get("when")
            return (0, int(w)) if (w and str(w).isdigit()) else (1, 0)

        return sorted(self.items, key=key)
