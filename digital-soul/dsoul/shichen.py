"""十二时辰养生：老祖宗按时辰作息的讲究——子时睡好养胆、卯时起床喝水、午时小憩养心。
顺着时辰过日子，身子更舒坦。像个懂养生的老人，到点提一句。

中医说法，图个调养、仅供参考，不替代医嘱。纯数据 + 纯逻辑、可单测（传 now 可复现）。
"""

from __future__ import annotations

from datetime import datetime

# (时辰, 起, 止, 对应经络/脏腑, 该做啥)
_SHICHEN = [
    ("子时", 23, 1, "胆经", "该熟睡了，这会儿睡得好最养胆，别熬夜。"),
    ("丑时", 1, 3, "肝经", "深睡养肝、排毒解乏，这点还醒着最伤身。"),
    ("寅时", 3, 5, "肺经", "继续好好睡，养肺气，别折腾。"),
    ("卯时", 5, 7, "大肠经", "该起床了，排个便、喝杯温水，肠子通畅一天舒坦。"),
    ("辰时", 7, 9, "胃经", "好好吃顿早饭，这会儿胃最能消化，别空着肚子。"),
    ("巳时", 9, 11, "脾经", "上午精神最好，正适合做事、动脑。"),
    ("午时", 11, 13, "心经", "吃午饭，再眯一刻钟午觉，养心、下午有劲。"),
    ("未时", 13, 15, "小肠经", "多喝点水，帮着吸收营养。"),
    ("申时", 15, 17, "膀胱经", "多喝水、起来活动活动，这会儿头脑清楚、效率高。"),
    ("酉时", 17, 19, "肾经", "吃晚饭别太晚、别太饱，养肾气。"),
    ("戌时", 19, 21, "心包经", "散散步、放松放松，别动气、别太激动。"),
    ("亥时", 21, 23, "三焦经", "准备歇着了，泡泡脚、静下来，好入睡。"),
]


def shichen_of(hour):
    """这个钟点属哪个时辰。返回 (时辰, 起, 止, 脏腑, 建议)。"""
    h = int(hour) % 24
    for name, a, b, organ, tip in _SHICHEN:
        if a <= b:
            if a <= h < b:
                return (name, a, b, organ, tip)
        else:                                       # 子时跨午夜
            if h >= a or h < b:
                return (name, a, b, organ, tip)
    return _SHICHEN[0]


def now_advice(now=None) -> str:
    """此刻该养生做点啥。"""
    now = now or datetime.now()
    name, a, b, organ, tip = shichen_of(now.hour)
    return f"现在是{name}（{a}点–{b}点），走{organ}。{tip}"


def find_shichen(utterance):
    """从话里认出提到的时辰；没有返回 None。"""
    u = str(utterance or "")
    for row in _SHICHEN:
        if row[0] in u:
            return row
    return None


def advice_for(utterance) -> str:
    """点了某个时辰就讲那个；问"现在/这会儿"就按当下。认不出返回空。"""
    row = find_shichen(utterance)
    if row:
        name, a, b, organ, tip = row
        return f"{name}（{a}点–{b}点）走{organ}：{tip}"
    if any(k in str(utterance or "") for k in ("现在", "这会儿", "此刻", "这个点", "这时候")):
        return now_advice()
    return ""


def is_shichen_query(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("十二时辰", "时辰养生", "时辰", "几点该睡", "几点睡最好",
                            "这个点该", "这会儿该养", "什么时候睡养")):
        return True
    return bool(find_shichen(u)) and any(k in u for k in ("养生", "该干", "做啥", "干啥",
                                                          "讲究", "养什么"))
