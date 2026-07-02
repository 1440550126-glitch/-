"""量子纠缠式记忆：相关的记忆"纠缠"在一起，回忆其一会"瞬间"牵动其二。

把量子直觉落成可计算的机制（非玄学）：
- 纠缠（entanglement）：两条记忆若共享人物 / 主题 / 情感，就强相关；
- 测量即坍缩：回忆（measure）一条记忆，会按纠缠强度"扩散激活"它的伙伴
  （spreading activation），让它们一并被想起、并顺带被强化；
- 检索 = 在一团相关记忆的"叠加态"里，坍缩出要说的那几条。

纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from .reflect import _bigrams


def _entities(text: str, names=None) -> set:
    """一条记忆涉及的"实体"：出现的人名 + 显著主题（二元组）。"""
    ents = {n for n in (names or []) if n and n in (text or "")}
    ents |= set(_bigrams(text or ""))
    return ents


def entanglement(a_item: dict, b_item: dict, names=None) -> float:
    """两条记忆的纠缠强度 0~1：共享实体的 Jaccard + 同种强情感的加成。"""
    ea = _entities(a_item.get("text", ""), names)
    eb = _entities(b_item.get("text", ""), names)
    if not ea or not eb:
        return 0.0
    union = len(ea | eb)
    j = (len(ea & eb) / union) if union else 0.0
    ea_emo, eb_emo = a_item.get("emotion"), b_item.get("emotion")
    bonus = 0.15 if (ea_emo and ea_emo == eb_emo and ea_emo != "平静") else 0.0
    return min(1.0, j + bonus)


def entangled_with(item: dict, items, names=None, k: int = 5):
    """与某条记忆最纠缠的若干记忆：[(强度, 记忆), …]。"""
    out = []
    for other in items:
        if other is item or other.get("id") == item.get("id"):
            continue
        s = entanglement(item, other, names)
        if s > 0:
            out.append((s, other))
    out.sort(key=lambda x: -x[0])
    return out[:k]


def spreading_activation(seeds, items, names=None, k: int = 5):
    """测量 seeds（被回忆的记忆）→ 扩散激活与之纠缠、但不在 seeds 里的记忆。"""
    seed_ids = {it.get("id") for it in seeds}
    by_id = {it.get("id"): it for it in items}
    act: dict = {}
    for seed in seeds:
        for s, other in entangled_with(seed, items, names, k=8):
            oid = other.get("id")
            if oid in seed_ids:
                continue
            act[oid] = max(act.get(oid, 0.0), s)
    ranked = sorted(((w, by_id[oid]) for oid, w in act.items()), key=lambda x: -x[0])
    return ranked[:k]
