"""惦记着没完的事：你上次提到要去办的、担心的、不舒服的，它记着，下次见你问一句
"上回你说要去X，办成了吗""上次说不舒服，这会儿好些没"。跨天记挂，像个真上心的人。

find_thread 从一句话里抽出值得跟进的线索；followup_line 生成下次的问候。纯逻辑、可单测。
"""

from __future__ import annotations

# (类型, 触发词, 下次跟进的话术)
_THREADS = [
    ("大事", ("面试", "考试", "手术", "搬家", "签合同", "答辩", "出差", "比赛"),
     "对了，那天说的{gist}，顺利吗？"),
    ("不适", ("不舒服", "疼", "难受", "头晕", "去检查", "去复查", "感冒", "失眠"),
     "上次你说{gist}，这会儿好些了没？"),
    ("打算", ("打算", "准备", "要去", "计划", "想去", "得去办", "回头去"),
     "上回你说{gist}，后来咋样了？"),
    ("难处", ("担心", "发愁", "为难", "烦心", "纠结"),
     "上回你提的{gist}，可有眉目了？"),
]

_QEND = ("吗", "吗？", "?", "？", "呢", "呢？")


def find_thread(utterance):
    """从一句话里抽出值得日后跟进的线索：返回 (类型, 摘要) 或 None。"""
    u = (utterance or "").strip()
    if not u or u.endswith(_QEND):       # 问句不算"留了个尾巴"
        return None
    for kind, kws, _tmpl in _THREADS:
        if any(k in u for k in kws):
            gist = u.strip("。.！!，,、 ")[:16]
            return (kind, gist)
    return None


def followup_line(kind, gist) -> str:
    """生成下次见面的跟进问候。"""
    gist = str(gist or "").strip()
    if not gist:
        return ""
    for k, _kws, tmpl in _THREADS:
        if k == kind:
            return tmpl.format(gist=gist)
    return f"对了，上回你说的{gist}，后来怎么样了？"
