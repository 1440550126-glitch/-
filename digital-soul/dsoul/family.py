"""多人合一：一座数字宅里，住着不止一个人。

config/family.yaml 里配多位家人，每位有自己的名字 / 称呼 / 性格 / 口头禅 / 生活。
可以问"我们家都有谁"，也可以把某位"叫出来"（become），由 TA 本人的口吻继续说话；
TA 们彼此知道对方的存在，会自然地提起家里其他人。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations


def members(family) -> list:
    """规整成 [{name, relation, ...}, ...]，跳过没名字的非法项。"""
    out = []
    for m in (family or {}).get("members", []) or []:
        if isinstance(m, dict) and m.get("name"):
            out.append(m)
    return out


def roster_line(family) -> str:
    """一句话报全家：『咱们这一大家子有：外公（姥爷）、外婆、我。』"""
    ms = members(family)
    if not ms:
        return ""
    parts = []
    for m in ms:
        rel = m.get("relation", "")
        parts.append(f"{m['name']}（{rel}）" if rel else m["name"])
    return f"咱们这一大家子有：{'、'.join(parts)}。"


def find_member(family, query) -> dict | None:
    """按名字或称呼找人：『把外公叫来』『我想和妈妈说说话』。"""
    if not query:
        return None
    q = str(query)
    for m in members(family):
        name, rel = m.get("name", ""), m.get("relation", "")
        if (name and name in q) or (rel and rel in q):
            return m
    return None


def member_identity(member, family=None) -> dict:
    """把一位家人变成 Persona / style 能用的 identity 字典，并让 TA 知道家里还有谁。"""
    idy = {
        "name": member.get("name", "我"),
        "summary": member.get("summary", ""),
        "personality": {
            "traits": member.get("traits", []) or [],
            "catchphrases": member.get("catchphrases", []) or [],
            "speaking_style": member.get("speaking_style", ""),
            "values": member.get("values", []) or [],
        },
        "daily_life": member.get("daily_life", []) or [],
    }
    if member.get("voice") is not None:
        idy["voice"] = member["voice"]
    others = [m["name"] for m in members(family or {}) if m.get("name") != member.get("name")]
    if others:
        idy["family_others"] = others
    return idy
