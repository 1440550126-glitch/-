"""记忆图谱：把扁平记忆升级成"人—事—主题"的关系网（GraphRAG 雏形）。

从记忆与关系里抽取实体（已知的人 + 高频主题）和它们的共现关系，支持：
- 中心度：谁 / 什么最核心
- 实体检索：围绕某人/某主题有哪些记忆与关联
- 连接：两个实体之间的联系（共享了哪些记忆）

纯逻辑、零依赖、可单测；有大模型可进一步增强，这里用启发式即可纯本地运行。
"""

from __future__ import annotations

import re
from collections import Counter

from .reflect import _bigrams


class MemoryGraph:
    def __init__(self) -> None:
        self.adj: dict[str, dict[str, int]] = {}   # 邻接表（带权）
        self.meta: dict[str, dict] = {}            # 节点元信息
        self.mem: dict[str, list[str]] = {}        # 节点 -> 提到它的记忆
        self.elabels: dict[tuple, str] = {}        # 边 -> 语义关系标签（LLM 抽取）

    def _node(self, name: str, kind: str) -> None:
        self.adj.setdefault(name, {})
        self.mem.setdefault(name, [])
        self.meta.setdefault(name, {"kind": kind, "count": 0})

    def _edge(self, a: str, b: str, w: int = 1) -> None:
        if a == b:
            return
        self.adj[a][b] = self.adj[a].get(b, 0) + w
        self.adj[b][a] = self.adj[b].get(a, 0) + w

    def add_relation(self, a: str, b: str, label: str) -> None:
        self._node(a, "person")
        self._node(b, "person")
        self.meta[b]["relation"] = label
        self._edge(a, b, 2)

    def add_labeled_edge(self, a: str, rel: str, b: str) -> None:
        """带语义标签的关系边（如 张明 —妻子→ 小婷）。"""
        self._node(a, self.meta.get(a, {}).get("kind", "entity"))
        self._node(b, self.meta.get(b, {}).get("kind", "entity"))
        self._edge(a, b, 2)
        self.elabels[(a, b)] = rel
        self.elabels[(b, a)] = rel

    def relation(self, a: str, b: str):
        return self.elabels.get((a, b))

    def add_memory(self, text: str, entities) -> None:
        seen = []
        for name, kind in entities:
            self._node(name, kind)
            self.meta[name]["count"] += 1
            if text not in self.mem[name]:
                self.mem[name].append(text)
            seen.append(name)
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                self._edge(seen[i], seen[j], 1)

    # ---------- 查询 ----------
    def neighbors(self, node: str, k: int = 6):
        return sorted(self.adj.get(node, {}).items(), key=lambda x: -x[1])[:k]

    def about(self, node: str, k: int = 5):
        return self.mem.get(node, [])[:k]

    def central(self, k: int = 6):
        deg = {n: sum(w.values()) for n, w in self.adj.items()}
        return sorted(deg.items(), key=lambda x: -x[1])[:k]

    def between(self, a: str, b: str) -> dict:
        shared_b = set(self.mem.get(b, []))
        shared = [m for m in self.mem.get(a, []) if m in shared_b]
        return {"edge": self.adj.get(a, {}).get(b, 0), "shared": shared[:5]}

    def nodes(self):
        return list(self.meta)


def _owner(authority):
    for p in authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return None


def _llm_triples(llm, text: str):
    """用大模型从一句话抽取 (实体1, 关系, 实体2) 三元组。"""
    if not (text or "").strip():
        return []
    system = ("从这句话里抽取人物/事物之间的关系三元组，每行一个，格式：实体1|关系|实体2；"
              "只输出三元组，没有就什么都不输出，不要解释。")
    try:
        out = llm.chat(system, text)
    except Exception:
        return []
    triples = []
    for line in out.splitlines():
        parts = [p.strip() for p in re.split(r"[|｜，,、]", line) if p.strip()]
        if len(parts) == 3:
            triples.append((parts[0], parts[1], parts[2]))
    return triples


def build_memory_graph(memory, authority, topics_per_memory: int = 2, min_topic_df: int = 2,
                       llm=None) -> MemoryGraph:
    """从记忆库 + 关系图谱构建记忆图谱。

    主题只保留"跨记忆复现"（文档频率 ≥ min_topic_df）的高频二元组，滤掉跨词噪声。
    传入可用的 llm 时，额外抽取带语义标签的关系边（如 豆豆 —宠物→ 张明）。
    """
    g = MemoryGraph()
    people = [p["name"] for p in authority.people.values() if p.get("name")]
    owner = _owner(authority)
    if owner:
        for p in authority.people.values():
            if p.get("name") and p["name"] != owner:
                g.add_relation(owner, p["name"], p.get("relation", "认识"))
    texts = [it.get("text", "") for it in memory.items]
    df: Counter = Counter()
    for t in texts:
        df.update(set(_bigrams(t)))
    allow = {w for w, c in df.items() if c >= min_topic_df}   # 主题白名单
    for text in texts:
        ents = [(n, "person") for n in people if n and n in text]
        topics = [w for w, _ in Counter(_bigrams(text)).most_common() if w in allow][:topics_per_memory]
        ents += [(t, "topic") for t in topics]
        if ents:
            g.add_memory(text, ents)
    if llm is not None and getattr(llm, "available", False):   # 语义关系抽取（可选增强）
        for text in texts[:40]:
            for a, rel, b in _llm_triples(llm, text):
                g.add_labeled_edge(a, rel, b)
    return g
