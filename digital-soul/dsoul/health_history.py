"""家族病史：长辈知道一家人的老毛病，把"会遗传、要当心"的事交代给后人。

问"我身体要注意什么"，分身能把家族里反复出现的病、长辈的叮嘱、谁对什么过敏，
一并说清。这是能救命的知识传承。配在 config/health.yaml。纯逻辑、可单测。

隐私：这类信息很私密，建议只用本地模型，别发往云端。
"""

from __future__ import annotations

from collections import Counter


def collect_conditions(config=None) -> list:
    """汇总病史条目：[{who, condition, note}, ...]。"""
    out = []
    for c in ((config or {}).get("conditions") or []):
        if isinstance(c, dict) and c.get("condition"):
            out.append({
                "who": str(c.get("who", "")).strip(),
                "condition": str(c["condition"]).strip(),
                "note": str(c.get("note", "")).strip(),
            })
    return out


def hereditary(conditions, threshold=2) -> list:
    """出现在 threshold 人及以上的病，算家族遗传倾向，按出现次数从多到少排。"""
    cnt = Counter(c["condition"] for c in conditions)
    return [cond for cond, n in cnt.most_common() if n >= threshold]


def people_with(conditions, condition) -> list:
    """哪些人有这个病。"""
    return [c["who"] for c in conditions if c["condition"] == condition and c["who"]]


def advice_for(conditions, condition) -> list:
    """某个病，长辈留下的叮嘱。"""
    return [c["note"] for c in conditions if c["condition"] == condition and c["note"]]


def health_warning(conditions) -> str:
    """一段家族病史交代：优先讲有遗传倾向的病 + 叮嘱；没有则把已知病史报一报。"""
    if not conditions:
        return ""
    her = hereditary(conditions)
    if her:
        lines = []
        for cond in her:
            who = "、".join(people_with(conditions, cond))
            note = "；".join(advice_for(conditions, cond))
            line = f"{cond}咱家{who}都有，是会遗传的，你要当心"
            if note:
                line += "——" + note
            lines.append(line)
        return "我把家里的病史交代给你：" + "。".join(lines) + "。"
    bits = [f"{c['who']}有{c['condition']}" for c in conditions if c["who"]][:4]
    return ("家里的老毛病：" + "、".join(bits) + "，你平时也留个心。") if bits else ""


def allergies(config=None) -> list:
    """汇总过敏：[{who, to}, ...]。"""
    out = []
    for a in ((config or {}).get("allergies") or []):
        if isinstance(a, dict) and a.get("to"):
            out.append({"who": str(a.get("who", "")).strip(), "to": str(a["to"]).strip()})
    return out


def allergy_of(config, name) -> list:
    """某人对什么过敏（做饭/买东西前查一查）。"""
    if not name:
        return []
    n = str(name)
    return [a["to"] for a in allergies(config) if a["who"] and (a["who"] in n or n in a["who"])]


def allergy_line(config, name) -> str:
    """一句过敏提醒。"""
    al = allergy_of(config, name)
    return (f"记着，{name}对{('、'.join(al))}过敏，千万避开。") if al else ""
