"""食物保存：冰箱怎么放、各样能搁多久、剩菜怎么存、哪些东西别放冰箱、怎么解冻——
存对了不浪费、不闹肚子。纯逻辑、可单测。和"看食品标签"(food_label)、"辟谣"(debunk 隔夜菜)接着用。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "冰箱分区": ("冷藏室约 4℃：熟食、剩菜放上层，生肉、生鱼放下层（防血水滴到熟食），生熟分开、各自密封;"
             "门档温度高，放调料饮料、别放奶和蛋;冷冻室约 -18℃，存长期不吃的肉。别塞太满，留点缝透气。",
             "生熟分层、各自封好，是防交叉污染的关键。"),
    "能放多久": ("大致参考：熟菜剩饭冷藏 1～2 天;鲜肉冷藏 1～2 天、冷冻能放几个月;鸡蛋冷藏数周;"
             "绿叶菜 2～3 天、根茎菜久点;开封的牛奶尽快喝完。",
             "拿不准就闻一闻、看一看，有异味、发黏、变色就别吃了。"),
    "剩菜保存": ("剩菜放凉到不烫手再盖好/密封放冰箱（别一直晾在外头）;2 天内吃完、下顿'彻底热透'再吃;"
             "绿叶菜尽量别隔夜（亚硝酸盐升高），现做现吃最好。",
             "汤汤水水的更易坏，优先吃掉;一份菜别反复热。"),
    "别放冰箱": ("有些东西放冰箱反而坏得快或串味：香蕉、芒果（冻黑）、土豆、洋葱、大蒜（发芽串味）、"
             "蜂蜜（结晶）、没切开的西红柿、面包（变干变硬）。",
             "这些放阴凉通风处更好;切开的另说，封好冷藏。"),
    "解冻": ("最稳的是提前一晚放冷藏室慢慢化，或用微波炉解冻档;赶时间可密封后泡冷水。",
           "别在室温下放一下午化冻（细菌猛长）;'化了的别再冻回去'——反复冻化又不安全又难吃。"),
    "生熟分开": ("切生肉、生鱼的刀和砧板，和切熟食、果蔬的分开用（或洗净消毒再用）;"
             "冰箱里也生熟分层、各自包好。",
             "交叉污染是闹肚子的常见原因，这条最实在。"),
}

_ALIAS = {
    "冰箱分区": "冰箱分区", "冰箱怎么放": "冰箱分区", "冰箱": "冰箱分区", "冷藏": "冰箱分区", "冷冻": "冰箱分区",
    "能放多久": "能放多久", "放多久": "能放多久", "存多久": "能放多久", "保质多久": "能放多久", "能存多久": "能放多久",
    "剩菜保存": "剩菜保存", "剩菜": "剩菜保存", "剩饭": "剩菜保存", "隔夜菜": "剩菜保存",
    "别放冰箱": "别放冰箱", "不能放冰箱": "别放冰箱", "哪些不放冰箱": "别放冰箱",
    "解冻": "解冻", "化冻": "解冻", "怎么解冻": "解冻",
    "生熟分开": "生熟分开", "交叉污染": "生熟分开", "砧板": "生熟分开", "案板": "生熟分开",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("food_storage") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类保存（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类保存怎么做 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def overview() -> str:
    """食物保存要点。"""
    return ("食物保存记几条：冰箱生熟分层各自封好;熟菜剩饭冷藏 1～2 天、彻底热透再吃;"
            "香蕉土豆洋葱蜂蜜别放冰箱;解冻提前放冷藏、别室温久放、化了别再冻;切生熟的刀板分开。")


def is_storage_query(utterance, config=None) -> bool:
    """是不是在问食物怎么保存。"""
    u = str(utterance or "")
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "多久", "能放", "能存", "保存", "要注意", "能不能",
                                "该不该", "坏不坏", "怎么办", "哪些", "对不对"))


def count(config=None) -> int:
    return len(_all(config))
