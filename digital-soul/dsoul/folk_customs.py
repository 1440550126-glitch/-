"""老讲究：本命年穿红、正月不剃头、筷子别插饭上……老一辈的民俗讲究和忌讳。
长辈在意这些老理儿，晚辈未必懂。这一块讲讲"为啥有这说法"，多是图个心安、求个吉利，
不迷信、也不扫兴——懂了来由，顺着长辈的心意，也是孝顺。纯逻辑、可单测。

口径：这些是民俗"说法"，不是科学定论；该看医生看医生、该挑日子图踏实，心里有数就好。
"""

from __future__ import annotations

# (讲究, [触发词], 说法/来由, 怎么看待)
_CUSTOMS = [
    ("本命年穿红", ["本命年", "穿红", "红腰带", "红内衣"],
     "轮到自己属相那年叫本命年，老话说'犯太岁'，讲究系红腰带、穿红袜红内衣辟邪求顺。",
     "图个吉利和心气儿，戴上踏实就好。"),
    ("正月不剃头", ["正月剃头", "正月理发", "正月不剪头", "死舅舅", "正月", "剃头", "理发"],
     "'正月剃头死舅舅'其实是'思旧'的讹传——清初汉人正月不剃发以'思旧'，传走音成了'死舅'。",
     "纯属误传，不必当真；但老人讲究，就等出了正月再剪，图个和气。"),
    ("筷子不插饭上", ["筷子插", "筷子立", "插饭上", "立筷子"],
     "把筷子直插在饭碗里，像给逝者上香的'倒头饭'，犯忌讳。",
     "平时把筷子搁碗边或筷架上，既得体也卫生。"),
    ("初一不扫地", ["初一扫地", "初一倒垃圾", "大年初一", "扫走财气"],
     "大年初一讲究不扫地、不倒垃圾，怕把一年的财气、福气扫出门。",
     "真要扫就往屋里扫、垃圾先囤着，过了初一再清，讨个口彩。"),
    ("数字讲究", ["数字忌讳", "几不吉利", "4不吉利", "6和8", "号码吉利"],
     "4 谐音'死'多回避，6 取'六六大顺'、8 取'发'最讨喜；红事图双数、白事不同。",
     "挑车牌门牌图个顺口顺心，别为这个多花冤枉钱。"),
    ("搬家看日子", ["搬家看日子", "搬家挑日子", "入宅", "动土", "黄道吉日"],
     "搬家、动土、办大事，老人爱挑个'黄道吉日'，图个开头顺、住得安。",
     "挑个全家方便的好天好日子，心里踏实最要紧。"),
    ("孕妇忌讳", ["孕妇忌讳", "孕妇不能去", "孕妇红白事"],
     "老说法孕妇不参加丧事、不看动土，其实多是怕劳累、怕情绪大起大落伤身。",
     "顺着这层关心：孕期少奔波、别太累、心情顺，比啥讲究都管用。"),
    ("床的讲究", ["镜子对床", "床头朝门", "床对门", "床的摆法"],
     "老讲究里镜子别正对床、床头别正冲门，说是睡不安稳。",
     "睡得安稳是真的要紧——避开穿堂风、夜里不晃眼，比风水更实在。"),
    ("祝寿的讲究", ["祝寿忌讳", "过寿", "做寿", "73", "84", "做九不做十"],
     "给老人祝寿忌说'死'字，多说'福如东海寿比南山';有'七十三、八十四'是坎的说法,也讲'做九不做十'(提前一年办整寿)。",
     "这些图的是老人安心顺气;真要紧的是常陪伴、定期体检，把日子过踏实。"),
    ("乔迁讲究", ["乔迁讲究", "进新房", "暖房", "搬新家讲究"],
     "进新居讲究带上旧居的米、盐、一壶水或一盆火，寓意'衣食不愁、香火延续'，再请亲友暖暖房。",
     "搬个顺心、热闹喜庆就好,东西带不带齐别太较真。"),
]


def _all(config=None) -> list:
    items = list(_CUSTOMS)
    cfg = (config or {}).get("folk_customs") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 4:
                items.append((str(it[0]), list(it[1]), str(it[2]), str(it[3])))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("triggers") or []),
                              str(it.get("saying", "")), str(it.get("view", ""))))
    return items


def customs(config=None) -> list:
    return [c[0] for c in _all(config)]


def find_custom(utterance, config=None):
    """认出问的哪条老讲究（名/触发词，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for c in _all(config):
        for kw in [c[0]] + list(c[1]):
            if kw and kw in u and len(kw) > best_len:
                best, best_len = c, len(kw)
    return best


def explain(custom, config=None) -> str:
    """某条老讲究：说法 + 怎么看待。查不到返回空。"""
    c = custom if isinstance(custom, tuple) else find_custom(custom, config)
    if not c:
        return ""
    return f"{c[0]}：{c[2]}{c[3]}"


def recall(seed="", config=None) -> str:
    """随口聊一条老讲究。"""
    items = _all(config)
    if not items:
        return ""
    c = items[len(str(seed)) % len(items)]
    return f"说个老讲究——{c[0]}：{c[2]}{c[3]}"


def count(config=None) -> int:
    return len(_all(config))


def is_custom_query(utterance, config=None) -> bool:
    """是不是在问老讲究/民俗忌讳。"""
    u = str(utterance or "")
    if any(k in u for k in ("老讲究", "老规矩", "民俗", "老理儿", "什么说法", "有啥讲究", "为啥忌讳",
                            "为什么忌讳", "迷信", "老话说")):
        return True
    if find_custom(u, config) and any(k in u for k in ("讲究", "忌讳", "为什么", "为啥", "说法",
                                                       "什么意思", "怎么回事", "能不能", "可以吗",
                                                       "有讲究吗", "吗", "咋回事")):
        return True
    return False
