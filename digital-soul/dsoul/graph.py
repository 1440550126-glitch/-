"""记忆图谱：把扁平记忆升级成"人—事—主题"的关系网（GraphRAG 雏形）。

从记忆与关系里抽取实体（已知的人 + 高频主题）和它们的共现关系，支持：
- 中心度：谁 / 什么最核心
- 实体检索：围绕某人/某主题有哪些记忆与关联
- 连接：两个实体之间的联系（共享了哪些记忆）

纯逻辑、零依赖、可单测；有大模型可进一步增强，这里用启发式即可纯本地运行。
"""

from __future__ import annotations

from collections import Counter

from .reflect import _bigrams


class MemoryGraph:
    def __init__(self) -> None:
        self.adj: dict[str, dict[str, int]] = {}   # 邻接表（带权）
        self.meta: dict[str, dict] = {}            # 节点元信息
        self.mem: dict[str, list[str]] = {}        # 节点 -> 提到它的记忆

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


def build_memory_graph(memory, authority, topics_per_memory: int = 2, min_topic_df: int = 2) -> MemoryGraph:
    """从记忆库 + 关系图谱构建记忆图谱。

    主题只保留"跨记忆复现"（文档频率 ≥ min_topic_df）的高频二元组，
    滤掉"叫张""婆小"这类一次性跨词噪声。
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
    return g
