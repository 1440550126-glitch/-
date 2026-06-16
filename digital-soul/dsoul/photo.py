"""多模态·照片：把一张照片（谁、何时、在哪、做什么）变成一条带日期的记忆。

人物可由人脸识别自动认出（若装了视觉后端），也可手动指定；配上时间、地点与描述，
照片就汇入记忆 / 时间线 / 关系图谱——"那张全家福"也成了能被想起的回忆。
组装逻辑零依赖、可单测；认脸部分复用 perception（可选）。
"""

from __future__ import annotations


def photo_memory(people=None, when=None, caption=None, place=None) -> str:
    """把照片要素拼成一条第一人称记忆。"""
    parts = []
    if when:
        parts.append(f"{when}年")
    if place:
        parts.append(f"在{place}")
    if caption:
        parts.append(str(caption).strip())
    base = "，".join(parts) if parts else "拍了一张照片"
    ppl = "、".join(p for p in (people or []) if p)
    if ppl:
        base += f"（照片里有：{ppl}）"
    return "（照片）" + base + "。"


def member_tags(people, family) -> list:
    """照片里出现的人，凡是登记在册的家人（按名字或称呼），就给这条记忆打上 TA 的归属标签。

    于是"那张全家福"会成为照片里每一位家人各自的回忆——"叫出"TA 时优先想起。
    """
    from .family import members
    fam = {m["name"] for m in members(family or {})}
    rel = {m.get("relation"): m["name"] for m in members(family or {}) if m.get("relation")}
    out, seen = [], set()
    for p in (people or []):
        name = p if p in fam else rel.get(p)
        if name and name not in seen:
            seen.add(name)
            out.append(f"member:{name}")
    return out


def identify_faces(perception, image_path) -> list:
    """尽力用人脸识别认出照片里的人（没视觉后端则返回空）。"""
    if perception is None or not image_path:
        return []
    try:
        name = perception.identify(image_path)
        return [name] if name else []
    except Exception:
        return []
