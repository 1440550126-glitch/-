"""怀旧老物件：一提搪瓷缸、煤油灯、粮票、二八大杠，长辈的话匣子就开了。
这些老物件是一代人共同的记忆。提到哪个，就接一句勾回忆的话，陪着唠唠当年。
也能主动翻出一件来开话头。纯数据 + 纯逻辑、可单测。

和"老电影"(classic_films)、"老游戏"(folk_games)是一脉的怀旧伙伴，专管"老东西"。
"""

from __future__ import annotations

# (物件名, [别名], 年代, 勾回忆的一句话)
_OBJECTS = [
    ("搪瓷缸", ["搪瓷杯", "茶缸子", "缸子"], "五六十年代起",
     "印着红字奖励的搪瓷缸，泡茶喝水都用它，磕掉瓷了也舍不得扔。"),
    ("煤油灯", ["油灯", "罩子灯"], "通电以前",
     "没电的晚上点煤油灯，灯芯一挑亮一点，写作业熏得鼻孔都是黑的。"),
    ("缝纫机", ["蜜蜂牌", "蝴蝶牌缝纫机", "脚踏缝纫机"], "结婚三大件之一",
     "脚一踏哒哒哒地响，一家人的衣服、补丁全靠它，是当年的'大件'。"),
    ("粮票", ["布票", "油票", "票证"], "计划经济年代",
     "买粮买布都得凭票，攒粮票像攒宝贝，那是物资紧巴巴的年月。"),
    ("二八大杠", ["二八自行车", "永久牌", "凤凰牌自行车", "大梁自行车"], "七八十年代",
     "二八大杠的自行车，前面大梁能带娃、后座能驮粮，叮铃铃骑遍全城。"),
    ("收音机", ["半导体", "匣子", "戏匣子"], "电视普及前",
     "守着收音机听评书、听戏、听天气预报，'下面播送'一响全家围过来。"),
    ("黑白电视", ["黑白电视机", "九寸电视"], "八十年代",
     "一条街就一台黑白电视，搬到院里，邻居搬着小板凳来看，雪花点也看得津津有味。"),
    ("算盘", ["算盘珠"], "电子计算器前",
     "噼里啪啦打算盘，账房先生的看家本事，'三下五除二'就是从这儿来的。"),
    ("蒲扇", ["芭蕉扇", "大蒲扇"], "没空调的夏天",
     "夏夜摇着大蒲扇乘凉，扇风又赶蚊子，奶奶摇着摇着我就睡着了。"),
    ("热水瓶", ["暖水瓶", "暖壶", "竹壳暖瓶"], "家家必备",
     "竹壳或铁壳的暖水瓶，灌满开水留着泡茶冲奶粉，瓶塞一拔'嘭'的一声。"),
    ("铝饭盒", ["饭盒", "铝制饭盒"], "上班上学带饭",
     "铝饭盒装上饭菜，搁单位食堂蒸笼里热一热，盖子上还刻着自己名字。"),
    ("连环画", ["小人书", "小画书"], "孩子的最爱",
     "巴掌大的小人书，两分钱看一本，趴在小人书摊上能看一下午。"),
    ("拨浪鼓", ["货郎鼓"], "哄娃 / 货郎",
     "拨浪鼓咚咚咚一摇，娃就乐了；走街串巷的货郎也摇它招呼人。"),
    ("缝纫顶针", ["顶针", "针线笸箩"], "做针线活",
     "套在手指上的顶针，纳鞋底一针一线，针线笸箩里全是过日子的讲究。"),
    ("麦乳精", ["乐口福"], "稀罕的营养品",
     "一罐麦乳精冲一杯，香甜得不得了，那时候是走亲访友的体面礼。"),
    ("粮店", ["副食店", "供销社"], "凭票买货的地方",
     "供销社、粮店，打酱油拿空瓶去灌，称糖用纸包，是一条街的中心。"),
]


def _all(config=None) -> list:
    items = list(_OBJECTS)
    cfg = (config or {}).get("old_objects") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 4:
                items.append((str(it[0]), list(it[1]), str(it[2]), str(it[3])))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []),
                              str(it.get("era", "")), str(it.get("memory", ""))))
    return items


def objects(config=None) -> list:
    return [o[0] for o in _all(config)]


def find_object(utterance, config=None):
    """提到了哪件老物件就揪出来（名/别名，最长匹配），返回那条元组；没有返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for o in _all(config):
        for name in [o[0]] + list(o[1]):
            if name and name in u and len(name) > best_len:
                best, best_len = o, len(name)
    return best


def memory_of(utterance, config=None) -> str:
    """提到的那件老物件的回忆话。没有返回空。"""
    o = find_object(utterance, config)
    return o[3] if o else ""


def recall(seed="", config=None) -> str:
    """主动翻出一件老物件开话头。"""
    items = _all(config)
    if not items:
        return ""
    o = items[len(str(seed)) % len(items)]
    return f"还记得{o[0]}吗？{o[3]} 你那会儿家里还有啥老物件？"


def count(config=None) -> int:
    return len(_all(config))


def is_old_object_query(utterance, config=None) -> bool:
    """是不是在聊老物件（提到具体物件 + 怀旧/回忆/还记得，或泛泛要聊老东西）。"""
    u = str(utterance or "")
    if any(k in u for k in ("老物件", "老东西", "怀旧的东西", "以前的老物件")):
        return True
    if find_object(u, config) and any(k in u for k in ("还记得", "记得", "以前", "那会儿", "小时候",
                                                       "想起", "怀念", "怀旧", "用过", "见过")):
        return True
    return False
