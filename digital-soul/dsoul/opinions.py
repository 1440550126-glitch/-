"""观点主张：分身对常见的人生话题有自己的看法，问"你怎么看X"答得稳、前后一致。
像个有阅历、有主见的长辈。配在 config/opinions.yaml，或并入 identity.opinions。纯逻辑、可单测。
"""

from __future__ import annotations

_ASK = ("你怎么看", "你觉得", "你认为", "你的看法", "怎么看待", "你说", "对不对", "好不好")


def collect_opinions(config=None, identity=None) -> dict:
    """汇总观点：{话题: 主张}。config 优先，并入 identity.opinions。"""
    out = {}
    for src in (((identity or {}).get("opinions") if isinstance(identity, dict) else None),
                (config or {}).get("opinions") if isinstance(config, dict) else None):
        if isinstance(src, dict):
            for k, v in src.items():
                ks, vs = str(k).strip(), str(v).strip()
                if ks and vs:
                    out[ks] = vs
        elif isinstance(src, list):
            for it in src:
                if isinstance(it, dict) and it.get("topic") and it.get("view"):
                    out[str(it["topic"]).strip()] = str(it["view"]).strip()
    return out


def match_topic(opinions, utterance):
    """问话里点到了哪个话题（话题词长的优先），没有则 None。"""
    if not opinions or not utterance:
        return None
    u = str(utterance)
    for topic in sorted(opinions, key=len, reverse=True):
        if topic and topic in u:
            return topic
    return None


def is_opinion_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _ASK)


def opine(opinions, utterance) -> str:
    """对点到的话题给出一贯的看法；没匹配上则空。"""
    topic = match_topic(opinions, utterance)
    if not topic:
        return ""
    view = opinions[topic].rstrip("。.")
    return f"要我说啊，{view}。这是我的老看法了。"
