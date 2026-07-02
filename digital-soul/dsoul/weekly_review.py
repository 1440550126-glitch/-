"""一周回望：到周末，陪你把这一周过一遍——有什么开心事、操心啥、坚持了啥。
不流水账，是带着暖意的小结，让你看见日子在往前走。纯逻辑、可单测。
"""

from __future__ import annotations


def compose(joys=None, concerns=None, habits=None) -> str:
    """把一周的开心事 / 操心事 / 坚持的事，串成一段暖心小结。"""
    def _dedup(xs):
        out = []
        for x in (str(v).strip() for v in (xs or [])):
            if x and x not in out:
                out.append(x)
        return out

    joys = _dedup(joys)
    concerns = _dedup(concerns)
    habits = [(n, d) for n, d in (habits or []) if d and d > 0]

    parts = ["这一周，咱一块儿回望回望："]
    if joys:
        parts.append("开心的事有——" + "；".join(joys[:3]) + "。")
    if habits:
        hb = "、".join(f"{n}坚持了{d}天" for n, d in habits[:3])
        parts.append(f"难得的是，{hb}，真不容易，给你点个赞。")
    if concerns:
        parts.append("也有些操心的——" + "、".join(concerns[:3])
                     + "，别太往心里搁，慢慢都会好的。")
    if len(parts) == 1:
        parts.append("平平淡淡，没什么大风浪，安安稳稳就是福。")
    parts.append("日子在往前走呢，下周咱接着好好过。")
    return " ".join(parts)


def is_review_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("这周怎么样", "这一周", "周末小结", "回顾这周", "一周回望",
                                "这礼拜", "总结一下这周", "这周过得"))
