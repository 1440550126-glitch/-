"""花语：送花送什么、哪种花代表啥心意——玫瑰是爱情、康乃馨给母亲、向日葵送病人。
送花也是门学问，分身懂点，帮你把心意送对、不闹笑话。

纯数据 + 纯逻辑、可单测。可在 config 加自家的。
"""

from __future__ import annotations

# 花 → (花语, 适合送给/场合)
_FLOWERS = {
    "玫瑰": ("热烈的爱情（红玫瑰尤甚）", "送爱人、表白、纪念日"),
    "康乃馨": ("母爱、感恩与祝福", "送母亲、长辈、母亲节"),
    "百合": ("纯洁、百年好合", "送新人、祝福、探望"),
    "向日葵": ("阳光、忠诚与希望", "送病人、鼓励、毕业"),
    "满天星": ("甘做配角的真心、思念", "配花、表真心"),
    "郁金香": ("博爱、体贴（红色示爱）", "送爱人、朋友"),
    "勿忘我": ("永恒的爱、不要忘记我", "送恋人、远行话别"),
    "茉莉": ("质朴、忠贞、清纯", "送知己、长辈"),
    "菊花": ("高洁长寿；白菊则寄哀思", "黄/红菊敬长辈贺寿；白菊用于追思"),
    "桔梗": ("真诚不变的爱", "送恋人、好友"),
    "薰衣草": ("等待爱情、宁静", "送恋人、表心意"),
    "扶郎花": ("互敬互爱、坚持", "送爱人、开业（又名非洲菊）"),
    "绣球": ("团圆美满、希望", "送新人、贺乔迁"),
    "雏菊": ("纯真、藏在心底的爱", "送暗恋、清新心意"),
    "栀子花": ("喜悦、坚强而珍贵的爱", "送恋人、毕业季"),
    "风信子": ("只要点燃生命之火，便可同享丰盛人生；也寓意道歉与重生", "表歉意、送新生"),
}

_ALIAS = {"红玫瑰": "玫瑰", "母亲花": "康乃馨", "太阳花": "向日葵", "非洲菊": "扶郎花"}

# 送花忌讳
_TABOO = ("送长辈、贺喜，别用白菊/白花（多用于追思）；"
          "探病忌送整盆（怕「久病成根」）和浓香的花，向日葵、康乃馨更稳妥；"
          "送花数目也有讲究——示爱常用单枝或 99/11，丧事忌喜庆颜色。")


def flowers() -> list:
    return list(_FLOWERS.keys())


def _norm(name) -> str:
    n = str(name or "").strip()
    if n in _FLOWERS:
        return n
    for a, real in _ALIAS.items():
        if a in n:
            return real
    for k in _FLOWERS:
        if k in n:
            return k
    return ""


def meaning_of(flower) -> str:
    name = _norm(flower)
    row = _FLOWERS.get(name)
    if not row:
        return ""
    lang, who = row
    return f"{name}的花语是「{lang}」，适合{who}。"


_OCC = {"母亲": "康乃馨", "妈妈": "康乃馨", "母亲节": "康乃馨", "爱人": "玫瑰",
        "表白": "玫瑰", "恋人": "玫瑰", "老婆": "玫瑰", "病人": "向日葵",
        "探病": "向日葵", "毕业": "向日葵", "新人": "百合", "结婚": "百合",
        "长辈": "康乃馨", "祝寿": "菊花", "道歉": "风信子"}


def recommend(utterance) -> str:
    """按对象/场合推荐送什么花。认不出返回空。"""
    u = str(utterance or "")
    best, blen = "", 0
    for k, fl in _OCC.items():
        if k in u and len(k) > blen:
            best, blen = fl, len(k)
    if not best:
        return ""
    m = meaning_of(best)
    return ("送" + best + "最合适。" + m) if m else f"送{best}最合适。"


def gift_taboos() -> str:
    return "送花的讲究：" + _TABOO


def find_flower(utterance) -> str:
    return _norm(utterance)


def is_flower_query(utterance) -> bool:
    u = str(utterance or "")
    if "花语" in u or "送花" in u:
        return True
    if find_flower(u) and any(k in u for k in ("代表什么", "什么意思", "啥意思", "寓意",
                                               "代表啥", "象征")):
        return True
    if "送什么花" in u or "送啥花" in u:
        return True
    return False
