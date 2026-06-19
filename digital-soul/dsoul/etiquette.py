"""人情礼俗：红白喜事的礼数——婚礼丧事该穿啥、说啥、忌啥，送礼有哪些忌讳。
中国人最讲究这些场面上的分寸，分身懂点，能帮老人和嘴拙的我们不失礼。

讲礼数与禁忌（不说具体随多少钱，那看人情和当地行情）。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

# 场合 → 礼数提点
_ETIQUETTE = {
    "婚礼": "带上红包（图双数吉利，忌4）；穿喜庆点，别穿纯白/纯黑抢了新人。"
            "到场多说吉利话，敬酒随意、别贪杯失态。",
    "丧事": "穿素色、神情庄重，忌大红大绿和笑闹。少说话、多搭手帮忙，"
            "见到家属说一句「节哀顺变」就好，别追问细节。礼金用白包。",
    "探病": "带点易消化的水果或营养品（忌送梨——谐音「离」，忌送钟）；"
            "说宽心话、别多问病情，待一小会儿就走，让病人好好歇着。",
    "满月": "送个红包或小孩用品（衣服、银饰都行），说句「长命百岁」，别空手去。",
    "乔迁": "送绿植、字画或红包图个吉利，进门说「乔迁之喜、越住越旺」。",
    "寿宴": "晚辈给长辈祝寿，送寿桃、寿面或红包；说「福如东海，寿比南山」；忌送钟、伞。",
    "拜年": "带份像样的年礼，进门先说吉利话，给小辈压岁钱（红包双数）。",
    "升学宴": "送红包或文具、好书，说「金榜题名、前程似锦」。",
}

_ALIAS = {"结婚": "婚礼", "喜酒": "婚礼", "婚宴": "婚礼", "办喜事": "婚礼",
          "白事": "丧事", "葬礼": "丧事", "丧礼": "丧事", "奔丧": "丧事", "吊唁": "丧事",
          "看病人": "探病", "看望病人": "探病", "探望": "探病",
          "孩子满月": "满月", "搬家": "乔迁", "新居": "乔迁", "贺乔迁": "乔迁",
          "祝寿": "寿宴", "大寿": "寿宴", "做寿": "寿宴",
          "过年": "拜年", "升学": "升学宴", "谢师宴": "升学宴"}

# 送礼忌讳（谐音/寓意不好）
_TABOO = [
    "钟——「送终」，忌讳；",
    "梨——「分离」，探病、送人都避开；",
    "伞——「散」，怕散伙；",
    "鞋——「走」，怕送走人（除非象征性收一块钱）；",
    "扇子——「散」，朋友间少送；",
    "绿帽子——万万不可；",
    "白色/黑色包装的礼——喜事上不吉利。",
]


def occasions() -> list:
    return list(_ETIQUETTE.keys())


def normalize_occasion(name) -> str:
    n = str(name or "").strip()
    if n in _ETIQUETTE:
        return n
    for k, v in _ALIAS.items():
        if k in n:
            return v
    for k in _ETIQUETTE:
        if k in n:
            return k
    return ""


def detect_occasion(utterance) -> str:
    u = str(utterance or "")
    best, blen = "", 0
    for k in list(_ETIQUETTE) + list(_ALIAS):
        if k in u and len(k) > blen:
            best, blen = k, len(k)
    return normalize_occasion(best) if best else ""


def etiquette_for(occasion) -> str:
    occ = normalize_occasion(occasion) or detect_occasion(occasion)
    tip = _ETIQUETTE.get(occ)
    return f"{occ}的礼数：{tip}" if tip else ""


def gift_taboos() -> str:
    return "送礼几样忌讳记一下：" + "".join(_TABOO)


def is_etiquette_query(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("送礼忌讳", "送礼禁忌", "送礼讲究", "礼数", "什么忌讳", "送礼避讳")):
        return True
    # 某个场合 + 在问礼数/注意/带啥/穿啥（"送什么礼物给X"归送礼参考，不在这）
    if detect_occasion(u) and any(k in u for k in ("讲究", "注意", "规矩", "礼数", "带什么",
                                                   "带啥", "穿什么", "穿啥", "怎么随礼",
                                                   "要注意", "有啥讲究", "禁忌")):
        return True
    return False
