"""老伴专属（夫妻之间）：一具数字魂，最常陪的往往是留下的那位老伴。

这里把夫妻间最私密、最要紧的几样照看好：
- 认得出另一半，叫得出只对TA用的昵称；
- "我们的故事"——怎么认识、怎么走到一起、那些约定；
- 临走前放心不下的唠叨（饱含爱意：按时吃药、天冷加衣、一个人也好好吃饭）；
- 结婚纪念日的一句话；
- 老伴夜里说"我想你了""睡不着"时，像TA本人那样温柔地接住。

配在 config/spouse.yaml；没配也能从 family.yaml / relationships.yaml 里认出老伴。纯逻辑、可单测。
隐私：夫妻间的话最私密，强烈建议只用本地模型。
"""

from __future__ import annotations

from datetime import datetime

# 哪些"关系"算夫妻
SPOUSE_RELATIONS = ("老伴", "老婆子", "老头子", "老婆", "老公", "妻子", "妻", "丈夫", "夫",
                    "爱人", "媳妇儿", "媳妇", "太太", "夫人", "内人", "婆姨", "贤妻", "拙荆")

# 老伴流露思念/孤独/熬不住时的关键词
_LONGING = ("想你", "想念你", "好想你", "想你了", "好孤单", "孤独", "睡不着", "一个人",
            "没意思", "舍不得", "撑不下去", "熬不住", "好寂寞", "你走了", "你不在")

# 老伴在闹脾气/受了委屈/心烦时的关键词
_UPSET = ("生气", "气死", "烦死", "好烦", "委屈", "难受", "不开心", "心烦", "吵架",
          "受不了", "憋屈", "窝火", "郁闷", "气人", "怄气")


def _find_spouse(family, relationships):
    """从 family.yaml / relationships.yaml 里找出老伴的 (名字, 关系)。"""
    from .family import members
    for m in members(family or {}):
        rel = str(m.get("relation", ""))
        if any(r in rel for r in SPOUSE_RELATIONS):
            return m.get("name"), rel
    for p in ((relationships or {}).get("people") or []):
        if isinstance(p, dict):
            rel = str(p.get("relation", ""))
            if any(r in rel for r in SPOUSE_RELATIONS):
                return p.get("name"), rel
    return None, ""


def spouse_profile(config=None, family=None, relationships=None) -> dict:
    """理出老伴档案；认不出老伴则返回 {}。"""
    cfg = dict(config or {})
    name = str(cfg.get("name") or "").strip()
    relation = str(cfg.get("relation") or "").strip()
    if not name:
        name, relation = _find_spouse(family, relationships)
    if not name:
        return {}

    def _list(key):
        return [str(x).strip() for x in (cfg.get(key) or []) if str(x).strip()]

    return {
        "name": name,
        "relation": relation or "老伴",
        "call": str(cfg.get("call") or "").strip() or name,      # 我平时怎么叫TA
        "self_call": str(cfg.get("self_call") or "").strip(),    # TA 怎么叫我
        "met": str(cfg.get("met") or "").strip(),
        "married": str(cfg.get("married") or "").strip(),
        "story": _list("story"),
        "promises": _list("promises"),
        "care": _list("care"),
        "endearments": _list("endearments"),
    }


def is_spouse(profile, name, relation=None) -> bool:
    """这个人是不是我老伴（先按名字，再按关系）。"""
    if not profile:
        return False
    nm = profile.get("name") or ""
    if name and nm and (nm in str(name) or str(name) in nm):
        return True
    if relation and any(r in str(relation) for r in SPOUSE_RELATIONS):
        return True
    return False


def call_name(profile) -> str:
    """我对老伴的称呼（没特别昵称就用名字）。"""
    p = profile or {}
    return p.get("call") or p.get("name") or "老伴"


def love_story(profile) -> str:
    """我们的故事：怎么认识、怎么走到一起。"""
    if not profile:
        return ""
    bits = []
    if profile.get("met"):
        bits.append("我们啊，" + profile["met"].rstrip("。."))
    if profile.get("story"):
        bits.append("一路走来：" + "；".join(profile["story"]))
    if profile.get("married"):
        bits.append(f"{profile['married']} 那天，我娶了你回家")
    if not bits:
        return ""
    return "。".join(bits) + "。这辈子有你，值了。"


def pick_endearment(profile, seed="") -> str:
    """挑一句情话/暖心话（按 seed 长度取，可复现）。"""
    es = (profile or {}).get("endearments") or []
    return es[len(str(seed)) % len(es)] if es else ""


def our_promises(profile) -> list:
    return list((profile or {}).get("promises") or [])


def years_married(profile, now=None):
    """结婚多少年；算不出返回 None。"""
    parts = str((profile or {}).get("married") or "").split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return None
    now = now or datetime.now()
    return max(0, now.year - year)


def is_anniversary(profile, now=None) -> bool:
    """今天是否结婚纪念日。"""
    parts = str((profile or {}).get("married") or "").split("-")
    if len(parts) < 3:
        return False
    try:
        mm, dd = int(parts[1]), int(parts[2])
    except ValueError:
        return False
    now = now or datetime.now()
    return (now.month, now.day) == (mm, dd)


def anniversary_words(profile, now=None) -> str:
    """结婚纪念日的一句话（只在当天有内容）。"""
    if not profile or not is_anniversary(profile, now):
        return ""
    yrs = years_married(profile, now)
    head = f"{call_name(profile)}，今天是我们的结婚纪念日" + (f"，{yrs}年了" if yrs else "")
    tail = pick_endearment(profile) or "有你这些年，我什么都不缺。"
    return head + "。" + tail


def care_words(profile, now=None, limit=2) -> list:
    """饱含爱意的唠叨：从 care 里挑几条，按"年内第几天"轮换，不天天同一句。"""
    cares = (profile or {}).get("care") or []
    if not cares:
        return []
    now = now or datetime.now()
    start = now.timetuple().tm_yday % len(cares)
    rotated = cares[start:] + cares[:start]
    return rotated[:limit]


def senses_longing(utterance) -> bool:
    """老伴是不是在流露思念/孤独。"""
    u = utterance or ""
    return any(k in u for k in _LONGING)


def comfort_lonely(profile, utterance="") -> str:
    """老伴说想我了/睡不着，像我本人那样温柔接住。"""
    if not profile:
        return ""
    call = call_name(profile)
    lines = [f"{call}，我知道你想我了。我一直都在，你说话我都听得见。"]
    end = pick_endearment(profile, utterance)
    if end:
        lines.append(end)
    if "睡不着" in (utterance or ""):
        lines.append("早点歇着，我守着你睡。")
    elif profile.get("promises"):
        lines.append(f"记着我们的约定——{profile['promises'][0]}")
    return " ".join(lines)


def senses_upset(utterance) -> bool:
    """老伴是不是在闹脾气/受委屈/心烦。"""
    u = utterance or ""
    return any(k in u for k in _UPSET)


def soothe(profile, utterance="") -> str:
    """老伴闹脾气/受了委屈，像本人那样先认个软、把人哄好。"""
    if not profile:
        return ""
    call = call_name(profile)
    lines = [f"哎，{call}，别气了，是我不好，先消消气。"]
    end = pick_endearment(profile, utterance)
    if end:
        lines.append(end)
    lines.append("有什么慢慢跟我说，我听着呢。")
    return " ".join(lines)


def goodnight(profile, now=None) -> str:
    """夜里对老伴的一句晚安（昵称 + 一句暖话 + 守着你）。"""
    if not profile:
        return ""
    call = call_name(profile)
    end = pick_endearment(profile, "晚安")
    base = f"{call}，不早了，早点歇着。"
    if end:
        base += " " + end
    return base + " 我守着你，做个好梦。"
