"""文房四宝：笔、墨、纸、砚——读书人案头的老物件，写字画画的根基。
聊聊各是什么讲究、哪儿的最有名、怎么用怎么养。给爱写字的长辈、学书法的孩子添点谈资。
纯逻辑、可单测。和"书法"(calligraphy 怎么写)接着用，这里讲"用什么写"。
"""

from __future__ import annotations

# (宝, [别名], 介绍/门道)
_TREASURES = [
    ("笔", ["毛笔", "湖笔", "狼毫", "羊毫", "兼毫"],
     "毛笔分狼毫（弹性好、写小字）、羊毫（柔软、含墨多）、兼毫（软硬适中、最好上手）。"
     "浙江湖州的'湖笔'最有名。用完要洗净余墨、捋顺笔锋、挂起来阴干，别老泡水里。"),
    ("墨", ["墨锭", "徽墨", "墨条", "墨汁"],
     "传统是'墨锭'，在砚台上加清水慢慢研磨出墨；安徽的'徽墨'最负盛名，分松烟（乌黑）、油烟（带光）。"
     "图省事用现成墨汁也行，但研墨那份静气，是写字前的修心。"),
    ("纸", ["宣纸", "生宣", "熟宣", "毛边纸"],
     "写毛笔字画国画多用'宣纸'，产自安徽泾县。生宣吸墨洇得开、适合写意；熟宣不洇、适合工笔小楷。"
     "练字省着用可先拿便宜的毛边纸。"),
    ("砚", ["砚台", "端砚", "歙砚", "洮砚"],
     "砚台是磨墨盛墨的。四大名砚里，广东的'端砚'、安徽的'歙砚'最出名，发墨细腻、温润。"
     "用完洗净、别存干墨结块，好砚养着越用越亮。"),
    ("文房杂项", ["笔架", "笔洗", "镇纸", "印章", "笔筒", "印泥"],
     "案头还少不了这些：笔架（搁笔）、笔洗（涮笔）、镇纸（压住纸角）、笔筒、印章和印泥（落款盖印）。"
     "凑齐一套，写字的仪式感就足了。"),
]


def _all(config=None) -> list:
    items = list(_TREASURES)
    cfg = (config or {}).get("scholar_tools") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 3:
                items.append((str(it[0]), list(it[1]), str(it[2])))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []), str(it.get("intro", ""))))
    return items


def treasures(config=None) -> list:
    return [t[0] for t in _all(config)]


def find_treasure(utterance, config=None):
    """认出问的哪一宝（名/别名，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for t in _all(config):
        for name in [t[0]] + list(t[1]):
            if name and name in u and len(name) > best_len:
                best, best_len = t, len(name)
    return best


def explain(treasure, config=None) -> str:
    """某一宝的介绍/门道。查不到返回空。"""
    t = treasure if isinstance(treasure, tuple) else find_treasure(treasure, config)
    return f"{t[0]}：{t[2]}" if t else ""


def overview() -> str:
    """文房四宝总述。"""
    return ("文房四宝就是笔、墨、纸、砚——写字画画的四样根基。"
            "笔数湖笔、墨数徽墨、纸数宣纸、砚数端砚歙砚。想细聊哪样跟我说。")


def count(config=None) -> int:
    return len(_all(config))


def is_scholar_query(utterance, config=None) -> bool:
    """是不是在聊文房四宝。"""
    u = str(utterance or "")
    if any(k in u for k in ("文房四宝", "笔墨纸砚")):
        return True
    if find_treasure(u, config) and any(k in u for k in ("是什么", "啥讲究", "怎么用", "怎么养",
                                                         "哪里的好", "哪儿的好", "什么意思", "讲讲",
                                                         "怎么选", "怎么挑", "有什么讲究")):
        return True
    return False
