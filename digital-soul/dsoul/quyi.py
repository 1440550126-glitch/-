"""曲艺：相声、评书、快板、大鼓、评弹……收音机里听了一辈子的说唱玩意儿。
和"戏曲"(opera 那些唱念做打的剧种)不一样，曲艺是"说唱"的民间艺术：一张嘴、一副板、一面鼓，
就能逗你乐、给你讲一整部书。提到哪种就讲讲它的门道和名角儿。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

# (曲种, [别名], 介绍, 代表/名角儿)
_FORMS = [
    ("相声", ["对口相声", "单口相声", "群口相声"],
     "一逗一捧，说学逗唱四门功课，包袱一抖满堂笑。茶馆里、广播里最热闹的一档。",
     "马三立、侯宝林、马季、姜昆等；贯口名段如《报菜名》《地理图》。"),
    ("评书", ["说书", "讲书"],
     "一人、一桌、一块醒木，把一部长书说得活灵活现，每到紧要处'欲知后事如何，且听下回分解'。",
     "单田芳、刘兰芳、袁阔成；《三国》《隋唐》《岳飞传》听不够。"),
    ("快板", ["数来宝", "快板书", "竹板"],
     "手打竹板'呱嗒呱嗒'打着节奏，合辙押韵地数说，见啥说啥、又快又溜。",
     "高凤山、李润杰；数来宝就是它的近亲。"),
    ("京韵大鼓", ["大鼓", "鼓曲"],
     "自己击鼓打板、有弦师伴奏，半说半唱、字正腔圆，北京味儿十足。",
     "骆玉笙（小彩舞），一曲《重整河山待后生》荡气回肠。"),
    ("苏州评弹", ["评弹", "弹词", "苏州弹词"],
     "吴侬软语，三弦琵琶一弹一唱，又有'说噱弹唱'，江南茶馆里的温软风雅。",
     "蒋月泉等；《珍珠塔》《白蛇传》是常演的书。"),
    ("二人转", ["蹦蹦戏", "东北二人转"],
     "东北的连说带唱带扭，一旦一丑两个人，热闹诙谐接地气，手绢扇子耍得花。",
     "赵本山把它带火到全国。"),
    ("山东快书", ["快书"],
     "打着两片铜板（鸳鸯板）'当哩个当'，节奏明快地说唱武侠故事，最有名的就是武松。",
     "高元钧；《武松打虎》家喻户晓。"),
    ("双簧", ["双簧戏"],
     "一人坐前面光做动作不出声（前脸），一人藏后面说唱（后身），配合得天衣无缝才好笑。",
     "讲究'前脸'和'后身'对得严丝合缝。"),
    ("数来宝", ["顺口溜唱"],
     "原是旧时沿街乞讨的说唱，打着牛胯骨或竹板，看见什么夸什么，张口就来、合辙押韵。",
     "后来进了曲艺舞台，和快板是一家。"),
]

_ALIAS = {}
for _f in _FORMS:
    for _a in [_f[0]] + _f[1]:
        _ALIAS[_a] = _f[0]


def _all(config=None) -> list:
    items = list(_FORMS)
    cfg = (config or {}).get("quyi") if isinstance(config, dict) else None
    extra = (cfg or {}).get("forms") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 3:
                items.append((str(it[0]), list(it[1]), str(it[2]), str(it[3]) if len(it) > 3 else ""))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []),
                              str(it.get("intro", "")), str(it.get("stars", ""))))
    return items


def forms(config=None) -> list:
    return [f[0] for f in _all(config)]


def find_form(utterance, config=None):
    """认出问的哪种曲艺（名/别名，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    names = []
    for f in _all(config):
        names.extend([f[0]] + list(f[1]))
    for name in sorted(set(names), key=len, reverse=True):
        if name and name in u:
            canon = name
            for f in _all(config):
                if name == f[0] or name in f[1]:
                    canon = f[0]
                    break
            for f in _all(config):
                if f[0] == canon:
                    return f
    return None


def describe(form, config=None) -> str:
    """某种曲艺的介绍 + 名角儿。查不到返回空。"""
    f = form if isinstance(form, tuple) else find_form(form, config)
    if not f:
        return ""
    body = f"{f[0]}：{f[2]}"
    if f[3]:
        body += f"代表：{f[3]}"
    return body


def recall(seed="", config=None) -> str:
    """主动聊一种曲艺开话头。"""
    items = _all(config)
    if not items:
        return ""
    f = items[len(str(seed)) % len(items)]
    return f"说起曲艺——{f[0]}：{f[2]} 你爱听这个不？"


def count(config=None) -> int:
    return len(_all(config))


def is_quyi_query(utterance, config=None) -> bool:
    """是不是在聊曲艺（泛说，或提到具体曲种 + 想听/讲讲/是什么）。"""
    u = str(utterance or "")
    if any(k in u for k in ("曲艺", "说唱艺术", "听书", "听段")):
        return True
    if find_form(u, config) and any(k in u for k in ("是什么", "讲讲", "说说", "想听", "来段",
                                                     "介绍", "什么意思", "怎么回事", "名角", "代表")):
        return True
    return False
