"""隔代教育：帮儿女带孙辈，是天伦之乐，也有讲究。怎么疼得有度、和孩子父母不拆台、
安全看护、科学带、还别把自己累垮——给上心的爷爷奶奶外公外婆出出主意。
鼓励、不教条，量力而行、开心为主。纯逻辑、可单测。
"""

from __future__ import annotations

# 主题 -> (建议, 暖心一句)
_TOPICS = {
    "别太溺爱": ("疼爱有度：别有求必应、别包办代替（能自己做的让他自己来）、该立的规矩立住。"
             "惯出来的脾气，将来吃亏的是孩子。",
             "爱他，是教他规矩和本事，不是什么都依着。"),
    "口径一致": ("和孩子的爸妈把教育的标准对齐，别当着孩子面拆台、护短;有不同意见私下商量，"
             "别让孩子学会'找奶奶要、绕过爸妈'。",
             "一家人一个调，孩子才不糊涂。"),
    "安全第一": ("看护到位最要紧：防烫（热水热汤别放边上）、防摔（楼梯阳台看牢）、防误食（小东西药品收好）、"
             "防走失（人多别撒手）、防溺水（水边寸步不离）。",
             "再多教育，都不如把娃看安全了。"),
    "多陪伴鼓励": ("多陪着玩、讲故事、带出去户外跑跑;多鼓励多夸、少吼少比较;蹲下来听孩子说话。"
              "陪伴和耐心，比给多少零食都金贵。",
              "你的好脾气和陪伴，是孩子记一辈子的暖。"),
    "科学带娃": ("有些老法子该更新了：别嚼饭喂、别把屎把尿、别一冷就裹成粽子、生病别乱用偏方——"
             "听医生、跟上新的育儿观念，对孩子好。",
             "你的经验是宝，再添点新知识，更稳当。"),
    "照顾好自己": ("带娃很累，别硬扛到自己垮:和子女分工、轮换着歇、留点自己的时间和爱好;"
              "身体不舒服早说，别为了带娃拖垮了。",
              "你先好好的，才是给一家人的福气;带孙是帮忙，不是把自己全搭进去。"),
}

_ALIAS = {
    "别太溺爱": "别太溺爱", "溺爱": "别太溺爱", "太惯": "别太溺爱", "惯孩子": "别太溺爱", "宠孩子": "别太溺爱",
    "口径一致": "口径一致", "和父母": "口径一致", "拆台": "口径一致", "护短": "口径一致", "教育分歧": "口径一致",
    "安全第一": "安全第一", "看孩子安全": "安全第一", "带娃安全": "安全第一", "防摔防烫": "安全第一",
    "多陪伴鼓励": "多陪伴鼓励", "陪孩子": "多陪伴鼓励", "怎么陪": "多陪伴鼓励", "鼓励孩子": "多陪伴鼓励",
    "科学带娃": "科学带娃", "科学育儿": "科学带娃", "老法子": "科学带娃", "把屎把尿": "科学带娃", "嚼饭": "科学带娃",
    "照顾好自己": "照顾好自己", "带娃累": "照顾好自己", "带孙累": "照顾好自己",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("grandparenting") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("advice"):
                d[str(name)] = (str(v["advice"]), str(v.get("warm", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类带娃建议（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    if any(b in u for b in ("带娃", "带孙", "带孩子")) and \
            any(k in u for k in ("太累", "好累", "扛不住", "累垮", "受不了")):
        return "照顾好自己"      # 带娃吐露太累，给那句"先把自己照顾好"
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类带娃建议 + 暖心话。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    adv, warm = d[key]
    return f"{key}：{adv}" + (f" {warm}" if warm else "")


def overview() -> str:
    """带孙辈的几条要点。"""
    return ("帮着带孙辈，记几条：疼爱别过度、立好规矩;和孩子爸妈口径一致别拆台;"
            "安全看护第一;多陪伴多鼓励;老法子该更新就更新、科学带;还有——照顾好自己别累垮。"
            "天伦之乐，量力而行、开心为主。")


def is_grandparenting_query(utterance, config=None) -> bool:
    """是不是在问怎么带孙辈/隔代教育。"""
    u = str(utterance or "")
    if any(k in u for k in ("隔代教育", "带孙", "带娃", "带孩子", "带外孙", "带孙子")) and \
            any(k in u for k in ("怎么", "建议", "注意", "该", "好不好", "技巧", "咋",
                                 "太累", "好累", "扛不住", "累垮", "受不了")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "建议", "注意", "该", "咋", "好不好")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
