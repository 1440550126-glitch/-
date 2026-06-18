"""今天穿什么 / 要不要带伞：按气温和天气，给一句实在的出门提醒。
像家里那个出门前总要叮嘱两句的人。纯逻辑、可单测。
"""

from __future__ import annotations


def dress_advice(temp) -> str:
    """按气温给穿衣建议。"""
    try:
        t = float(temp)
    except (TypeError, ValueError):
        return ""
    if t <= 0:
        return "天寒地冻，羽绒服、围巾、手套都安排上，别冻着。"
    if t <= 10:
        return "挺冷的，穿厚外套、加件毛衣，护好脖子和腿。"
    if t <= 18:
        return "微凉，外搭一件薄外套刚好，早晚加衣。"
    if t <= 26:
        return "天气正舒服，穿得轻便些就行。"
    if t <= 32:
        return "有点热，穿透气的衣裳，多喝水。"
    return "太热了，尽量待阴凉处，防晒别忘，多补水。"


def umbrella(condition) -> str:
    c = str(condition or "")
    if any(k in c for k in ("雨", "雷", "阵雨")):
        return "外头有雨，带把伞。"
    if "雪" in c:
        return "下雪路滑，穿防滑的鞋、慢点走。"
    return ""


def extras(condition) -> str:
    c = str(condition or "")
    bits = []
    if any(k in c for k in ("晒", "紫外线", "烈日")):
        bits.append("涂点防晒")
    if any(k in c for k in ("霾", "雾霾", "沙尘", "污染")):
        bits.append("戴个口罩")
    if any(k in c for k in ("大风", "风大")):
        bits.append("风大，戴顶帽子")
    return "；".join(bits)


def day_advice(temp=None, condition=None) -> str:
    """合成一句出门叮嘱。"""
    parts = [p for p in (dress_advice(temp), umbrella(condition), extras(condition)) if p]
    return " ".join(parts) if parts else "出门当心，照顾好自己。"
