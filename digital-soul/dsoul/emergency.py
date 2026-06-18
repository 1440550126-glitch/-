"""应急：万一摔了、不舒服、有急事，第一时间先稳住人，给最直接的指引——
别慌、坐稳、含药、打这个电话。不替代 120，只在第一时间给安抚和指引。present-tense、可单测。
"""

from __future__ import annotations

# 情形关键词 → 第一时间的指引
_SITUATIONS = [
    ("摔倒", ("摔倒", "摔了", "跌倒", "起不来", "站不起来"),
     "先别急着起身，缓一缓，看看哪儿疼、能不能动。动不了就别硬撑，保持原样。"),
    ("胸口", ("胸口疼", "胸闷", "心口", "心脏", "胸痛", "胸口闷", "胸口好闷",
             "胸口发闷", "胸口憋", "胸口堵", "胸口疼得"),
     "马上坐下别动，把常备的救心丸/硝酸甘油含上，深呼吸。这种别扛，赶紧打120。"),
    ("喘不上气", ("喘不上气", "喘不过来", "呼吸困难", "憋气"),
     "坐直身子，松开领口，慢慢深呼吸，开扇窗透气。缓不过来就打120。"),
    ("头晕", ("头晕", "晕乎", "天旋地转", "站不稳"),
     "赶紧扶稳坐下或躺下，别站着，喝口温水，闭眼缓一缓。"),
    ("出血", ("出血", "流血", "划伤", "破了"),
     "按住伤口、抬高，用干净布压着止血。血止不住就赶紧就医。"),
    ("发烧", ("发烧", "高烧", "烧到"),
     "多喝温水，额头敷块温毛巾，量量体温。烧得高、退不下就去医院。"),
]

_SOS = ("救命", "不行了", "难受死了", "快不行", "急救", "120")


def detect_situation(utterance):
    u = utterance or ""
    for name, kws, _tip in _SITUATIONS:
        if any(k in u for k in kws):
            return name
    return None


def senses_emergency(utterance) -> bool:
    u = utterance or ""
    return detect_situation(u) is not None or any(k in u for k in _SOS) \
        or any(k in u for k in ("很不舒服", "好难受", "不舒服得厉害"))


def guide(utterance="", name="", contacts_line="") -> str:
    """先稳住、给情形指引、再把能找的人报出来。"""
    who = (str(name) + "，") if name else ""
    sit = detect_situation(utterance)
    tip = ""
    for nm, _kws, t in _SITUATIONS:
        if nm == sit:
            tip = t
            break
    if not tip:
        tip = "深呼吸，别慌，告诉我哪儿不舒服，我陪着你、帮你想办法。"
    line = f"{who}别慌，我在。{tip}"
    if contacts_line:
        line += f" 需要的话，我这就提醒你联系：{contacts_line}。"
    return line
