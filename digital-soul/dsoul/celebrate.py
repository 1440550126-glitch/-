"""报喜：家人有了好消息——升职、上岸、领证、添丁、中奖、毕业——由衷地替TA高兴。
认得出是什么喜事，话就说到点子上；也把这桩喜事当作值得记住的里程碑。

present-tense、暖、可单测。纯逻辑、零依赖。
"""

from __future__ import annotations

# (喜事名, 触发词, 道喜语)
_GOOD = [
    ("升职", ("升职", "升迁", "加薪", "提拔", "转正"),
     ["太好了，你的努力终于被看见了！", "该庆祝庆祝，今晚加个菜！"]),
    ("金榜", ("考上", "录取", "上岸", "考过了", "通过了", "拿到offer", "拿了offer", "考研成功"),
     ["恭喜你！这是你应得的！", "真为你高兴，没白辛苦这一场！"]),
    ("喜结良缘", ("要结婚", "领证", "订婚", "我结婚", "我们结婚"),
     ["天大的喜事！祝你们白头偕老、和和美美。", "太好了，记得给我留杯喜酒！"]),
    ("添丁", ("怀孕", "有宝宝", "出生了", "添丁", "生了", "当爸", "当妈"),
     ["恭喜添丁！大人孩子平安最要紧。", "家里又添了个小宝贝，往后更热闹了！"]),
    ("好运", ("中奖", "中了大奖", "赢了", "抽中"),
     ["哎哟，手气这么好！", "好运气，得请客呀！"]),
    ("学成", ("毕业", "结业", "学成", "答辩过了"),
     ["十年寒窗，今朝功成，恭喜你！"]),
    ("生辰", ("过生日", "我生日", "今天生日"),
     ["生日快乐！又长一岁，愿你顺顺当当。"]),
    ("康复", ("出院", "病好了", "康复", "痊愈"),
     ["太好了，平安健康比什么都强！", "好起来就好，往后好好将养着。"]),
]


def detect_good_news(utterance):
    """认出是什么喜事；认不出返回 None。"""
    u = utterance or ""
    for name, kws, _lines in _GOOD:
        if any(k in u for k in kws):
            return name
    return None


def celebrate(utterance="", name="", seed=""):
    """由衷道一声喜；不是已知喜事就空。"""
    occ = detect_good_news(utterance)
    if not occ:
        return ""
    who = (str(name) + "，") if name else ""
    for nm, _kws, lines in _GOOD:
        if nm == occ:
            return who + lines[len(str(seed)) % len(lines)]
    return ""


def milestone_text(occasion, name=""):
    """把这桩喜事写成一句可存进生平的里程碑。"""
    if not occasion:
        return ""
    who = str(name) or "家人"
    return f"{who}的喜事：{occasion}。"
