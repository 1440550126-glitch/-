"""飞花令：诗词里的雅游戏——报一个字（月、花、春、风…），对出一句带这个字的诗。
跟孙辈玩，既添趣又长腹中诗书。是"对诗"的升级玩法。

只收传世名句（公有领域）。纯逻辑、可单测。可在 config 加自家爱的句子。
"""

from __future__ import annotations

# 飞花令常用字 → 含该字的名句
_LINES = {
    "月": ["床前明月光，疑是地上霜", "明月几时有，把酒问青天", "海上生明月，天涯共此时",
           "举头望明月，低头思故乡", "月落乌啼霜满天，江枫渔火对愁眠",
           "野旷天低树，江清月近人", "我寄愁心与明月，随风直到夜郎西"],
    "花": ["夜来风雨声，花落知多少", "感时花溅泪，恨别鸟惊心", "人面不知何处去，桃花依旧笑春风",
           "晓看红湿处，花重锦官城", "落花时节又逢君", "忽如一夜春风来，千树万树梨花开",
           "停车坐爱枫林晚，霜叶红于二月花"],
    "春": ["春眠不觉晓，处处闻啼鸟", "春风又绿江南岸，明月何时照我还", "好雨知时节，当春乃发生",
           "春色满园关不住，一枝红杏出墙来", "国破山河在，城春草木深",
           "等闲识得东风面，万紫千红总是春", "春潮带雨晚来急，野渡无人舟自横"],
    "风": ["春风又绿江南岸，明月何时照我还", "夜来风雨声，花落知多少", "古道西风瘦马，断肠人在天涯",
           "大风起兮云飞扬", "风急天高猿啸哀，渚清沙白鸟飞回", "随风潜入夜，润物细无声"],
    "雨": ["清明时节雨纷纷，路上行人欲断魂", "夜来风雨声，花落知多少", "好雨知时节，当春乃发生",
           "渭城朝雨浥轻尘，客舍青青柳色新", "春潮带雨晚来急，野渡无人舟自横",
           "七八个星天外，两三点雨山前"],
    "山": ["空山新雨后，天气晚来秋", "山重水复疑无路，柳暗花明又一村", "国破山河在，城春草木深",
           "远上寒山石径斜，白云生处有人家", "会当凌绝顶，一览众山小", "众鸟高飞尽，孤云独去闲"],
    "水": ["山重水复疑无路，柳暗花明又一村", "桃花潭水深千尺，不及汪伦送我情",
           "水光潋滟晴方好，山色空蒙雨亦奇", "君不见黄河之水天上来，奔流到海不复回",
           "白毛浮绿水，红掌拨清波", "蒹葭苍苍，白露为霜"],
    "云": ["云想衣裳花想容，春风拂槛露华浓", "黄河远上白云间，一片孤城万仞山",
           "行到水穷处，坐看云起时", "众鸟高飞尽，孤云独去闲", "千里黄云白日曛，北风吹雁雪纷纷"],
    "酒": ["葡萄美酒夜光杯，欲饮琵琶马上催", "劝君更尽一杯酒，西出阳关无故人",
           "借问酒家何处有，牧童遥指杏花村", "花间一壶酒，独酌无相亲", "莫笑农家腊酒浑，丰年留客足鸡豚"],
    "夜": ["夜来风雨声，花落知多少", "姑苏城外寒山寺，夜半钟声到客船", "春宵一刻值千金，花有清香月有阴",
           "今夜偏知春气暖，虫声新透绿窗纱", "何当共剪西窗烛，却话巴山夜雨时"],
}

_FLOWER_WORDS = ("飞花令", "对诗", "诗词接龙带", "玩诗")


def _merge(config) -> dict:
    db = {k: list(v) for k, v in _LINES.items()}
    if isinstance(config, dict) and isinstance(config.get("feihualing"), dict):
        for ch, lines in config["feihualing"].items():
            extra = [str(x).strip() for x in (lines or []) if str(x).strip()]
            if extra:
                db[str(ch)] = extra + db.get(str(ch), [])
    return db


def chars(config=None) -> list:
    return list(_merge(config).keys())


def lines_with(char, config=None) -> list:
    return list(_merge(config).get(str(char or "").strip(), []))


def contains(line, char) -> bool:
    """这句诗里有没有这个字（用来判用户对得对不对）。"""
    return bool(char) and str(char) in str(line or "")


def a_line(char, used=None, seed="", config=None) -> str:
    """给一句带该字、且不在 used 里的名句；都用过了返回空。"""
    used = set(used or [])
    pool = [ln for ln in lines_with(char, config) if ln not in used]
    if not pool:
        return ""
    return pool[len(str(seed)) % len(pool)]


def extract_char(utterance, config=None) -> str:
    """从"带月的诗句""飞花令，花"里取出那个字。取不到返回空。"""
    import re
    u = str(utterance or "")
    m = re.search(r"[带含](.)字?的", u)            # 带X字的 / 含X的
    if m and m.group(1) in _merge(config):
        return m.group(1)
    m = re.search(r"飞花令[，,：: ]*(.)", u)
    if m and m.group(1) in _merge(config):
        return m.group(1)
    for ch in _merge(config):                       # 兜底：句中出现的飞花令字
        if ch in u:
            return ch
    return ""


def is_feihualing(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in _FLOWER_WORDS):
        return True
    import re
    return bool(re.search(r"[带含].字?的诗", u))     # "带月的诗""含花字的诗句"
