"""口头语录：TA 常挂嘴边的老话、爱讲的道理，攒成一本"语录"。

配在 config/sayings.yaml（一组话），或并入 identity 的口头禅。问"外公常说啥"能背几句；
也能按当下话题挑一句应景的，撒进回复里更像本人。纯逻辑、可单测。
"""

from __future__ import annotations


def collect_sayings(sayings=None, identity=None) -> list:
    """汇总语录：config 的 sayings + identity 口头禅，去重保序。"""
    out: list[str] = []
    seen = set()

    def _add(x):
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    src = sayings.get("sayings", sayings) if isinstance(sayings, dict) else sayings
    for s in (src or []):
        _add(s)
    for c in ((identity or {}).get("personality", {}) or {}).get("catchphrases", []) or []:
        _add(c)
    return out


def pick_for(sayings, topic=None) -> str | None:
    """挑一句应景的：与 topic 字面重合最多的那句优先；都不沾边就给第一句。"""
    if not sayings:
        return None
    if topic:
        chars = set(str(topic))
        best, best_score = None, 0
        for s in sayings:
            score = sum(1 for ch in chars if ch in s)
            if score > best_score:
                best, best_score = s, score
        if best is not None:
            return best
    return sayings[0]


def recite(sayings, k=5) -> str:
    """背几句语录。"""
    items = [s for s in (sayings or []) if s][:k]
    if not items:
        return ""
    return "我常念叨的那几句：" + " / ".join(f"「{s}」" for s in items)
