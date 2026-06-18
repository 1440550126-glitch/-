"""对话里记着你刚说的：人聊天会接着前面的话头，不会每句都当头一回听。
分身把这一席话的前几句记着，能回指、能接续——这正是"像个人"的关键一环。

recent_context_hint 把近几句整理给大模型当上下文；callback 给不接大模型时的朴素回指。
纯逻辑、可单测。
"""

from __future__ import annotations

# 太常见、不足以当"回指线索"的二字片段
_STOP = {"今天", "昨天", "我们", "你们", "他们", "这个", "那个", "什么", "怎么", "可以",
         "知道", "现在", "一下", "一个", "还是", "就是", "这样", "那样", "我的", "你的"}


def recent_context_hint(turns, k=3) -> str:
    """把这一席话最近几句整理成给大模型的上下文提示，让它接着话头说。"""
    lines = [str(t).strip() for t in (turns or []) if str(t).strip()]
    lines = lines[-k:]
    if not lines:
        return ""
    return ("（这会儿聊天里，TA刚还说过：" + "；".join(lines)
            + "。回应时接着这个话头，别当头一回听。）")


def callback(utterance, recent) -> str:
    """朴素回指：当前这句和刚才某句沾上同一个实词，就点一句"你刚还说…"。"""
    u = str(utterance or "")
    for prev in reversed([str(p) for p in (recent or []) if str(p).strip()]):
        if not prev or prev == u:
            continue
        for i in range(len(prev) - 1):
            w = prev[i:i + 2]
            if w in u and w not in _STOP and not w.isspace():
                return f"你刚还提到「{prev[:12]}」呢，"
    return ""
