"""门口的人：你出门，TA 站门口送两句、叮嘱几样别落下；你回来，迎上去问一声累不累。
不是开关灯那套（那归"场景"），是那个总在门口的、惦记你的人。

present-tense、纯逻辑、可单测。送别的叮嘱、迎接的暖话都轮换着来，不重样。
"""

from __future__ import annotations

_LEAVING = ("我出门了", "我走了", "我先走了", "出去一趟", "出门了", "上班去了",
            "我出去了", "出去买菜", "我要走了", "我先走啦", "下楼一趟")
_BACK = ("我回来了", "我到家了", "到家了", "我回家了", "进门了", "我回来啦", "我回来咯")

# 送别的体己叮嘱（轮换）
_CARE = [
    "路上慢点，看着脚下。",
    "钥匙、手机都带了吗？",
    "几点回来？我等你吃饭。",
    "外头当心车，过马路看红绿灯。",
    "早去早回，我在家等你。",
    "天要是变了记得添衣，别冻着。",
    "钱包带好，别落下东西。",
]

# 迎接的暖话（轮换）
_WELCOME = [
    "回来啦，累不累？快坐下歇会儿。",
    "可算回来了，先喝口热水。",
    "辛苦啦，鞋一脱，松快松快。",
    "外头折腾一天，回来就好。",
    "回来就踏实了。饭马上就得，洗洗手。",
    "哟，回来啦——我正念叨你呢。",
]


def is_leaving(utterance) -> bool:
    return any(k in str(utterance or "") for k in _LEAVING)


def is_back(utterance) -> bool:
    return any(k in str(utterance or "") for k in _BACK)


def _pick(pool, seed):
    return pool[len(str(seed)) % len(pool)]


def send_off(name="", seed="", extra=None) -> str:
    """出门相送：一句"慢走" + 一两条体己叮嘱（可加一条临时的，如带伞）。"""
    call = (str(name) + "，") if name else ""
    pre = (str(extra).rstrip() + " ") if extra else ""   # 临时叮嘱（如带伞）放最前，必带
    tip = _pick(_CARE, seed)
    return f"{call}慢走啊。{pre}{tip}"


def welcome_back(name="", seed="") -> str:
    """回家迎接：迎上去一句暖话。"""
    call = (str(name) + "，") if name else ""
    return call + _pick(_WELCOME, seed)
