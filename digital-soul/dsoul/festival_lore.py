"""节日的吃食与来历：过节吃什么、为啥这么过——粽子记屈原、月饼盼团圆、腊八熬粥。
讲给孙辈听，把节过出味道、过出根。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

_LORE = {
    "春节": {
        "food": ["饺子", "年糕（年年高）", "鱼（年年有余）", "汤圆"],
        "story": "过年是辞旧迎新。老话说古时有个叫‘年’的怪兽，怕红、怕响，所以家家贴春联、放鞭炮、守岁，把它赶走，图个平安红火。"},
    "元宵": {
        "food": ["汤圆", "元宵"],
        "story": "正月十五闹元宵，吃汤圆、看花灯、猜灯谜，圆圆的汤圆讨个团团圆圆的好彩头。"},
    "清明": {
        "food": ["青团", "馓子"],
        "story": "清明扫墓踏青，是慎终追远——记着先人，也借春光出门走走，活人好好的，先人才安心。"},
    "端午": {
        "food": ["粽子", "咸鸭蛋", "雄黄酒"],
        "story": "端午吃粽子、赛龙舟，是纪念投江的爱国诗人屈原。门口插艾草、戴香囊，是为了驱邪避瘟、图个安康。"},
    "中秋": {
        "food": ["月饼", "桂花酒", "螃蟹"],
        "story": "中秋赏月、吃月饼，盼的是团圆。嫦娥奔月的故事就在这天，月亮最圆，人心也最想聚。"},
    "重阳": {
        "food": ["重阳糕", "菊花酒"],
        "story": "九月九重阳节，登高、赏菊、敬老。‘九九’谐音‘久久’，盼老人长长久久、康健安宁。"},
    "腊八": {
        "food": ["腊八粥", "腊八蒜"],
        "story": "腊八熬一锅杂粮粥，暖身暖心，也是提醒：年快到了，该张罗起来了。"},
    "冬至": {
        "food": ["饺子（北方）", "汤圆（南方）", "羊肉汤"],
        "story": "冬至大如年。老话说‘冬至不端饺子碗，冻掉耳朵没人管’，一家人围一桌，热乎乎过最冷的日子。"},
}


def festivals() -> list:
    return list(_LORE.keys())


def detect(utterance):
    u = utterance or ""
    for key in _LORE:
        if key in u or key.rstrip("节") in u:
            return key
    if "过年" in u or "新年" in u:
        return "春节"
    return None


def is_lore_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("吃什么", "吃啥", "的来历", "的故事", "为什么过", "怎么来的",
                                "由来", "为啥吃", "为什么吃", "怎么来的"))


def lore(festival) -> str:
    d = _LORE.get(festival)
    if not d:
        return ""
    return (f"{festival}讲究吃{('、'.join(d['food']))}。{d['story']}")


def food_of(festival) -> list:
    return list(_LORE.get(festival, {}).get("food", []))
