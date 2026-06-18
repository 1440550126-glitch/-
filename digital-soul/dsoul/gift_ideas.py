"""送礼参考：要给家里人挑礼物，按关系、TA 的喜好、什么场合，给几个实在的主意。
不让你空着手、也不让你乱花钱。纯逻辑、可单测。
"""

from __future__ import annotations

# 关系关键词 → 实在的礼物主意
_BY_RELATION = [
    (("父", "爸", "爷", "公"), ["一盒好茶", "保暖内衣", "颈肩按摩仪", "TA爱喝的那口酒"]),
    (("母", "妈", "奶", "婆", "姥"), ["一条丝巾", "护手霜套装", "羊绒衫", "一束花"]),
    (("老伴", "妻", "夫", "爱人"), ["陪TA出去走一趟", "TA念叨过的小物件", "拍张合影裱起来"]),
    (("儿", "女", "孩", "娃"), ["一本好书", "心仪已久的玩意儿", "一次说走就走的出游"]),
    (("孙", "外孙"), ["益智的玩具", "课外书", "一身新衣裳"]),
    (("朋友", "发小", "同学"), ["一顿好饭", "对方喜欢的小物", "一瓶酒叙叙旧"]),
]

# 场合 → 一句心意提示
_BY_OCCASION = {
    "生日": "挑TA一直想要、却舍不得买的那样。",
    "过年": "图个喜庆吉利，红火热闹最好。",
    "纪念日": "走心比贵重要，旧物件、老照片最戳人。",
    "看望": "带点实用的，吃的用的都成。",
    "乔迁": "送点添丁进口、红火过日子的彩头。",
}


def _ideas_by_relation(relation) -> list:
    rel = str(relation or "")
    for kws, ideas in _BY_RELATION:
        if any(k in rel for k in kws):
            return list(ideas)
    return ["挑TA平时用得上、又舍不得给自己买的东西"]


def gift_ideas(relation="", likes=None, occasion="") -> str:
    """给几个送礼主意：先按 TA 的喜好，再按关系补充，最后点一句场合心意。"""
    picks = []
    for x in (likes or []):
        s = str(x).strip()
        if s and s not in picks:
            picks.append(s)
    picks = picks[:2]
    picks += [i for i in _ideas_by_relation(relation) if i not in picks][:3 - len(picks)]
    if not picks:
        return ""
    line = "要不考虑这几样：" + "、".join(picks) + "。"
    occ = _BY_OCCASION.get(str(occasion).strip())
    if occ:
        line += occ
    return line


def detect_occasion(utterance) -> str:
    u = utterance or ""
    for occ in _BY_OCCASION:
        if occ in u:
            return occ
    return ""
