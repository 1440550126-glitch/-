"""没话找话：分身也会主动开口，没人说话时挑个话头唠两句，让相处不冷场、更主动。
按时段、按惦记的人，挑一句自然的开场。present-tense、可单测。
"""

from __future__ import annotations

# 通用话头
_STARTERS = [
    "对了，问你个事——最近睡得还好吗？",
    "哎，今天过得咋样，有没有什么新鲜事？",
    "好久没听你说说近况了，最近忙啥呢？",
    "想起来问问，那件事后来怎么样了？",
    "跟你唠两句啊，今天我心里挺敞亮的。",
    "歇会儿不？陪我说说话呗。",
]

# 按时段的话头
_BY_TOD = {
    "清晨": ["早饭吃了吗？今天打算干点啥？"],
    "中午": ["晌午了，今儿吃的啥好的？"],
    "傍晚": ["快到饭点了，今天累不累？"],
    "晚上": ["忙完啦？坐下歇歇，陪我聊聊今天。"],
    "深夜": ["还没睡呀？有心事就跟我念叨念叨。"],
}


def starter(seed="", people=None, tod=None) -> str:
    """挑一句开场白；惦记着谁就顺口提一句谁。"""
    pool = list(_BY_TOD.get(tod or "", [])) + _STARTERS
    line = pool[len(str(seed)) % len(pool)]
    ppl = [p for p in (people or []) if p]
    if ppl and len(str(seed)) % 3 == 0:
        who = ppl[len(str(seed)) % len(ppl)]
        line = f"对了，{who}最近还好吧？有阵子没见着了。"
    return line


def is_invite(utterance) -> bool:
    """对方招呼"陪我聊聊/陪我说说话"。"""
    u = utterance or ""
    return any(k in u for k in ("陪我聊", "陪我说说", "陪我唠", "没话找话", "找你聊",
                                "聊聊天", "说说话吧", "陪我待会"))
