"""老行当：剃头挑子、磨刀匠、货郎、爆米花……这些走街串巷的老手艺，是一代人的街头记忆。
如今大多见不着了。提到哪个，就讲讲那时候的光景，陪长辈唠唠、给晚辈说说过去。

和"老物件"(old_objects)、"老电影"(classic_films)一脉，专管"老手艺、老营生"。
纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

# (行当名, [别名], 勾回忆的一句话)
_TRADES = [
    ("剃头匠", ["剃头挑子", "理发挑子", "剃头的"],
     "剃头挑子一头热——一头是烧水的小炉子，一头是凳子，走街串巷给人剃头刮脸。"),
    ("磨刀匠", ["磨剪子", "戗菜刀", "磨刀的"],
     "一声'磨剪子嘞——戗菜刀——'的吆喝拖得老长，肩上扛条板凳就是全部家当。"),
    ("货郎", ["货郎担", "卖货郎", "摇拨浪鼓的"],
     "摇着拨浪鼓的货郎挑着担子来了，针头线脑、糖球头绳，小孩追着跑。"),
    ("补锅匠", ["补锅的", "焊洋瓷盆"],
     "生火化铁水补铁锅，搪瓷盆漏了也能补，'补锅嘞'一喊一条街的破锅都端出来。"),
    ("爆米花", ["崩爆米花", "爆米花机", "炸苞米花"],
     "黑乎乎的转炉摇啊摇，'砰'的一声巨响，白胖的爆米花喷一麻袋，孩子捂着耳朵又馋又怕。"),
    ("弹棉花", ["弹棉花匠", "弹棉被"],
     "一张大弓嘣嘣地弹，把板结的旧棉被弹得蓬松，雪沫子似的棉绒飞一屋。"),
    ("修鞋匠", ["钉鞋掌", "修鞋的", "补鞋"],
     "街角一个小马扎、一台手摇补鞋机，纳鞋底、钉后跟，几毛钱让破鞋多穿一年。"),
    ("捏面人", ["面塑", "捏面花"],
     "五颜六色的面团在手里几下就成了孙悟空、白娘子，插在草靶子上，娃娃挪不动脚。"),
    ("吹糖人", ["糖人", "吹糖"],
     "一小团熬化的糖稀，又吹又捏，转眼成了小老鼠、大公鸡，又是玩意儿又能吃。"),
    ("锔碗", ["锔瓷", "锔盆", "钉碗的"],
     "'没有金刚钻别揽瓷器活'说的就是这手艺——打孔上锔钉，碎碗也能滴水不漏。"),
    ("修钢笔", ["修笔", "换笔尖"],
     "钢笔金贵，写秃了、漏水了拿去修，换个笔尖、通通墨囊，又能用上好几年。"),
    ("铁匠", ["打铁", "钉马掌", "铁匠铺"],
     "炉火通红，叮叮当当抡大锤，打镰刀锄头、给牲口钉马掌，火星子四溅。"),
    ("收废品", ["收破烂", "废品回收", "破铜烂铁"],
     "'收破烂喽——'拉着板车走街串巷，旧报纸、牙膏皮、破铜烂铁都能换俩钱。"),
    ("箍桶匠", ["箍桶", "修木桶"],
     "给散了架的木桶木盆重新上箍,过去打水洗澡的木桶坏了，全靠他一双巧手。"),
    ("修伞", ["修雨伞", "补伞"],
     "油纸伞、长柄伞骨折了能修，换伞骨、补伞面，那会儿东西坏了头一念是修，不是扔。"),
]


def _all(config=None) -> list:
    items = list(_TRADES)
    cfg = (config or {}).get("old_trades") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 3:
                items.append((str(it[0]), list(it[1]), str(it[2])))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []), str(it.get("memory", ""))))
    return items


def trades(config=None) -> list:
    return [t[0] for t in _all(config)]


def find_trade(utterance, config=None):
    """提到了哪个老行当就揪出来（名/别名，最长匹配）。没有返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for t in _all(config):
        for name in [t[0]] + list(t[1]):
            if name and name in u and len(name) > best_len:
                best, best_len = t, len(name)
    return best


def describe(utterance, config=None) -> str:
    """提到的那个老行当的描述。没有返回空。"""
    t = find_trade(utterance, config)
    return t[2] if t else ""


def recall(seed="", config=None) -> str:
    """主动翻出一个老行当开话头。"""
    items = _all(config)
    if not items:
        return ""
    t = items[len(str(seed)) % len(items)]
    return f"想起一个老行当——{t[0]}：{t[2]} 这些走街串巷的手艺，你那会儿见过吧？"


def count(config=None) -> int:
    return len(_all(config))


def is_old_trade_query(utterance, config=None) -> bool:
    """是不是在聊老行当（泛说，或提到具体行当 + 怀旧意图）。"""
    u = str(utterance or "")
    if any(k in u for k in ("老行当", "老手艺", "老营生", "过去的手艺", "走街串巷")):
        return True
    if find_trade(u, config) and any(k in u for k in ("还记得", "记得", "以前", "那会儿", "小时候",
                                                      "想起", "怀念", "见过", "过去")):
        return True
    return False
