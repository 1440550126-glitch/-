"""看懂食品标签：配料表怎么看、营养成分表那串数字啥意思、"无糖低脂"是不是真的——
买东西会看标签，吃得明白、买得放心。纯逻辑、可单测。
和"营养"(nutrition 吃啥补啥)接着用，这里专管"看懂包装上的字"。
"""

from __future__ import annotations

# 主题 -> 通俗解释
_TOPICS = {
    "配料表": "配料按含量'从多到少'排，排第一的用得最多。要是'白砂糖、植物油'排很靠前，"
            "那就是高糖高油。配料越短、越是看得懂的天然东西，一般越干净。",
    "营养成分表": "看'每 100 克'或'每份'的几项：能量（千焦 kJ，约 4.2 千焦=1 千卡）、蛋白质、脂肪、"
               "碳水化合物、钠。右边 NRV% 是占一天需要的百分比，越高说明这项越多。",
    "钠含量": "钠就是盐的主要成分，钠×2.5 约等于盐的量。老人控盐就盯钠，一份钠占 NRV 老高的（>30%）"
            "就算高盐，少吃；每天盐别超过 5 克。",
    "糖含量": "看碳水里的'糖'。注意'0 蔗糖'不等于无糖，可能加了别的糖或代糖；"
            "真无糖是每 100 克糖≤0.5 克。控糖的多留意。",
    "保质期日期": "先找'生产日期'和'保质期'，算出能放到哪天，临过期的慎买、买了快吃。"
               "'此日期前最佳'过了未必坏，'保质期至'到了就别吃了；开封后保质期另算、尽快吃完。",
    "食品添加剂": "合规适量的添加剂（防腐、增稠、色素等）没那么可怕,国家有限量。"
               "但配料表里添加剂一长串的,说明加工重,偶尔吃可以、别当饭。",
    "宣传噱头": "'无糖、低脂、非油炸、零添加、纯天然'这些词要看实际成分:非油炸可能照样高油高盐,"
             "'儿童/老人'款未必更营养。别被包装词带着走,翻到背面看配料和成分表。",
    "生产许可": "正规预包装食品有'SC'开头的生产许可编号（以前叫 QS）。认准 SC 号、厂名厂址齐全的，"
             "三无产品（无厂名、无地址、无生产日期）别买。",
    "净含量": "看清'净含量'多少克/毫升，别被大包装、充气袋骗了，按单位价格算才知道划不划算。",
}

_ALIAS = {
    "配料表": "配料表", "配料": "配料表", "成分表里配料": "配料表",
    "营养成分表": "营养成分表", "营养成分": "营养成分表", "能量": "营养成分表", "千焦": "营养成分表", "NRV": "营养成分表",
    "钠含量": "钠含量", "钠": "钠含量", "含盐": "钠含量", "盐分": "钠含量",
    "糖含量": "糖含量", "含糖": "糖含量", "无糖": "糖含量", "0蔗糖": "糖含量", "代糖": "糖含量",
    "保质期日期": "保质期日期", "保质期": "保质期日期", "生产日期": "保质期日期", "过期": "保质期日期", "临期": "保质期日期",
    "食品添加剂": "食品添加剂", "添加剂": "食品添加剂", "防腐剂": "食品添加剂", "色素": "食品添加剂",
    "宣传噱头": "宣传噱头", "无糖低脂": "宣传噱头", "非油炸": "宣传噱头", "零添加": "宣传噱头", "纯天然": "宣传噱头",
    "生产许可": "生产许可", "SC": "生产许可", "QS": "生产许可", "三无产品": "生产许可", "三无": "生产许可",
    "净含量": "净含量", "分量": "净含量",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("food_label") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问标签的哪一块（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def explain(topic, config=None) -> str:
    """某一块怎么看。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}"


def overview() -> str:
    """看食品标签的总纲。"""
    return ("看食品标签翻到背面：①配料表（按含量从多到少，糖油排前就是高糖高油）；"
            "②营养成分表（重点看钠/盐、糖、能量）；③生产日期 + 保质期；④认准 SC 生产许可、别买三无。"
            "包装上'无糖低脂零添加'的词，对照成分表看真假。")


def is_label_query(utterance, config=None) -> bool:
    """是不是在问怎么看食品标签。"""
    u = str(utterance or "")
    if any(k in u for k in ("食品标签", "看标签", "看配料", "看成分", "包装上")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么看", "啥意思", "什么意思", "是什么",
                                                      "多少算", "怎么回事", "真的吗", "靠谱吗",
                                                      "高吗", "能吃吗", "咋看")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
