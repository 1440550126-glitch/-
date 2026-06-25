"""记忆入库：把"记忆巩固"提炼出的私人长期记忆，也在知识库里建一篇笔记，
连上其中提到的[[人物]]——让"世界是什么样"(知识)和"我和谁发生过什么"(记忆)在 Obsidian 里连成一张网。

记忆是第一人称的（"我答应小婷退休带她去看极光"）；这里：
  · 给每条记忆建一篇 #记忆 笔记，正文就是那句话；
  · 认出里头提到的已知家人/熟人，建/连 [[人物]] 笔记，互相成图；
  · 人物笔记攒着 ta 相关的记忆，越连越懂这个人。
纯逻辑、可单测（喂 vault + 记忆列表 + 人名表）。
"""

from __future__ import annotations

import re

_LEAD = re.compile(r"^(我们|我|咱们|咱)\s*")
_CLAUSE = re.compile(r"[。！？\.!?\n]")


def people_in(text: str, names) -> list:
    """文本里提到了哪些"已知的人"（按名字长度从长到短，避免子串误伤）。去重保序。"""
    text = str(text or "")
    work, hit = text, []
    for name in sorted({str(n) for n in names if str(n).strip()}, key=len, reverse=True):
        if name in work:
            hit.append(name)
            work = work.replace(name, "　")      # 命中后遮掉，"小婷"里的"婷"不再误命中
    return sorted(set(hit), key=lambda n: text.find(n))   # 按在原文里出现的先后


def memory_title(text: str, max_len: int = 18) -> str:
    """从一条记忆里取个简短可读的标题：去掉开头的"我/我们"，取第一小句、截短。"""
    s = str(text or "").strip()
    first = _CLAUSE.split(s, 1)[0].strip()
    first = _LEAD.sub("", first).strip().strip("，、,. ")
    if len(first) <= max_len:
        return first or "一段记忆"
    cut = first[:max_len]
    idx = max(cut.rfind("，"), cut.rfind("、"), cut.rfind(","))   # 断在词边界，别切碎
    if idx >= 6:
        cut = cut[:idx]
    return cut.strip("，、, ") or "一段记忆"


def ensure_person(vault, name, relation="", *, now=None) -> bool:
    """确保有一篇 #人物 笔记；新建返回 True，已存在（补上 #人物 标签）返回 False。"""
    name = str(name).strip()
    if not name:
        return False
    if vault.has(name):
        # 已有（可能是别处带出的桩）→ 补上 #人物 标签，别重复正文
        vault.grow(name, "", tags=["人物"], now=now)
        return False
    body = "人物。" + (f"关系：{relation}。" if relation else "")
    vault.grow(name, body, tags=["人物"], source="记忆巩固", now=now)
    return True


def _memory_prose(note_body: str) -> str:
    """从一篇记忆笔记的正文里，抠出那句记忆本身（去掉标题/关联/标签行，留补记内容）。"""
    out = []
    for ln in str(note_body or "").split("\n"):
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("- [["):
            continue
        out.append(s)
    return " ".join(out)


def update_bio(vault, name, relation="", *, now=None) -> bool:
    """给一个人物笔记重写"## 小传"：把连到 ta 的记忆归纳成一段。无记忆/无此篇则跳过。"""
    md = vault.read(name)
    if md is None:
        return False
    from . import obsidian as ob
    from . import person_bio
    mems = []
    for t in vault.backlinks(name):
        n = vault.note(t)
        if not n:
            continue
        if "记忆" not in (n["tags"] or []):      # 只用 #记忆 笔记，别把别的链接也当经历
            continue
        pr = _memory_prose(n["body"])
        if pr:
            mems.append(pr)
    bio = person_bio.compose_bio(name, relation, mems)
    if not bio:
        return False
    vault._write(name, ob.set_section(md, "## 小传", bio))
    return True


def sediment_memories(vault, memories, people=None, *, now=None, daily=True) -> dict:
    """把一批已巩固的记忆写进知识库：每条建一篇 #记忆 笔记，连上提到的[[人物]]。
    people：[(名, 关系)] 或 [名]；用来认出记忆里的人、建/连人物笔记。"""
    # 规整 people → 名→关系
    rel = {}
    for p in (people or []):
        if isinstance(p, (list, tuple)) and p:
            rel[str(p[0])] = str(p[1]) if len(p) > 1 else ""
        elif str(p).strip():
            rel[str(p)] = ""
    names = list(rel.keys())

    mem_notes, person_notes, touched = [], [], []
    for text in (memories or []):
        text = str(text or "").strip()
        if len(text) < 4:
            continue
        who = people_in(text, names)
        # 先确保人物笔记在（这样记忆连过去不会留个空白桩）
        for p in who:
            if ensure_person(vault, p, rel.get(p, ""), now=now):
                person_notes.append(p)
        title = memory_title(text)
        if vault.has(title):
            cur = vault.note(title) or {}
            if text and text not in (cur.get("body") or ""):
                vault.grow(title, text, tags=["记忆"], links=who, now=now)
                touched.append(title)
        else:
            vault.grow(title, text, tags=["记忆"], links=who,
                       source="记忆巩固", now=now)
            mem_notes.append(title)
            touched.append(title)

    # 给牵涉到的人物刷新"小传"（把连到 ta 的记忆归纳成一段人物志）
    people_linked = sorted(set(p for m in (memories or []) for p in people_in(str(m), names)))
    bios = []
    for p in people_linked:
        if update_bio(vault, p, rel.get(p, ""), now=now):
            bios.append(p)

    if daily and touched:
        vault.daily_note("巩固了这些记忆：" + "、".join(touched), links=touched, now=now)
    return {"memory_notes": mem_notes, "person_notes": person_notes,
            "touched": touched, "people_linked": people_linked, "bios": bios}
