"""节日筹备：快到节了，提个醒该张罗的事——年夜饭、团圆、红包、走亲访友。
让节日有仪式感、不手忙脚乱。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

_PREP = {
    "春节": ["备年货、张罗年夜饭", "给小辈备好红包", "贴春联、挂灯笼", "打电话约家人回来团圆"],
    "除夕": ["年夜饭的菜单定了吗", "守岁的零食备上", "给晚辈的红包包好", "和家人一起看春晚"],
    "元宵": ["煮一锅汤圆", "出门看花灯、猜灯谜", "一家人热热闹闹"],
    "清明": ["准备祭扫的物件", "天好就去踏踏青", "做点青团应景"],
    "端午": ["包粽子", "门口插艾草", "给孩子系五彩绳"],
    "中秋": ["买月饼", "约家人一起赏月团圆", "给长辈送份节礼"],
    "重阳": ["陪老人登高望远", "给长辈买块重阳糕", "给老人打个电话问候"],
    "冬至": ["北方包饺子、南方煮汤圆", "一家人围一桌", "天冷加件衣"],
    "腊八": ["熬一锅腊八粥", "泡上腊八蒜，等过年"],
}


def festivals() -> list:
    return list(_PREP.keys())


def prep_for(festival) -> list:
    """某个节该张罗的事。"""
    name = str(festival or "").strip().rstrip("节")
    for key, items in _PREP.items():
        if name and (name in key or key in name or name == key.rstrip("节")):
            return list(items)
    return []


def detect_festival(utterance):
    """问话里点到了哪个节。"""
    u = utterance or ""
    for key in _PREP:
        if key in u or key.rstrip("节") in u:
            return key
    if "过年" in u or "新年" in u:
        return "春节"
    return None


def is_prep_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("准备什么", "准备啥", "要张罗", "筹备", "该备点啥",
                                "怎么过", "准备点什么"))


def prep_text(festival) -> str:
    """一段话报该张罗的事。"""
    items = prep_for(festival)
    if not items:
        return ""
    return f"快到{festival}了，该张罗起来咯：" + "；".join(items) + "。"
