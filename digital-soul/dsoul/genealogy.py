"""家谱 / 家族树：一家人按辈分理一理——谁是哪一辈、各自生日、长幼次序。
配合 kinship 模块能答称呼，也能报近期谁过生日。

数据来自 config/family.yaml（每人 name/relation/birthday，可选 gen）。纯逻辑、可单测。
"""

from __future__ import annotations

from datetime import date, datetime

# 关系关键词 → 代际（相对"本尊/自己"这一辈为 0；负数为长辈，正数为晚辈）
_GEN = {
    "太": -3, "高祖": -3,
    "祖": -2, "奶奶": -2, "爷爷": -2, "外公": -2, "外婆": -2, "姥": -2,
    "爸": -1, "妈": -1, "父": -1, "母": -1, "伯": -1, "叔": -1,
    "姑": -1, "姨": -1, "舅": -1, "婶": -1,
    "哥": 0, "姐": 0, "弟": 0, "妹": 0, "妻": 0, "夫": 0, "老伴": 0, "爱人": 0, "嫂": 0,
    "孙": 2, "外孙": 2,            # "孙"要排在"子/女"前面判，更具体
    "儿": 1, "女": 1, "侄": 1, "甥": 1,
}

_GEN_NAME = {-3: "高祖辈", -2: "祖辈", -1: "父辈", 0: "平辈", 1: "子辈", 2: "孙辈", 3: "曾孙辈"}


def _gen_of(member) -> int:
    """先看显式 gen，再按关系词推断；都没有算平辈(0)。"""
    if member.get("gen") is not None:
        try:
            return int(member["gen"])
        except (TypeError, ValueError):
            pass
    rel = str(member.get("relation") or "")
    for kw, g in _GEN.items():        # dict 保序：更具体的"孙/外孙"排在"儿/女"前
        if kw in rel:
            return g
    return 0


def build_tree(family_cfg) -> list:
    """把 family.yaml 整理成按辈分、再按生日排好的成员列表。"""
    from .family import members
    out = []
    for m in members(family_cfg):
        mm = dict(m)
        mm["gen"] = _gen_of(m)
        out.append(mm)
    out.sort(key=lambda x: (x["gen"], str(x.get("birthday") or "9999")))
    return out


def by_generation(tree) -> list:
    """按辈分分组：[(辈分名, [成员名…]), …]。"""
    groups: dict = {}
    for m in tree:
        groups.setdefault(m["gen"], []).append(m["name"])
    return [(_GEN_NAME.get(g, f"第{g}辈"), names) for g, names in sorted(groups.items())]


def roster_by_gen(tree) -> str:
    """一段话报家谱（按辈分）。"""
    lines = [f"{label}：{'、'.join(names)}" for label, names in by_generation(tree)]
    return ("咱家这几辈人——" + "；".join(lines) + "。") if lines else ""


def _parse_bday(s):
    parts = str(s).strip().split("-")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0], nums[1]
    if len(nums) == 3:
        return nums[1], nums[2]
    return None


def upcoming_birthdays(tree, now=None, within=30) -> list:
    """近 within 天内谁过生日：[(name, days_left), …]，按远近排序。"""
    now = now or datetime.now()
    today = now.date()
    out = []
    for m in tree:
        md = _parse_bday(m.get("birthday"))
        if not md:
            continue
        month, day = md
        try:
            nxt = date(today.year, month, day)
        except ValueError:
            continue
        if nxt < today:
            try:
                nxt = date(today.year + 1, month, day)
            except ValueError:
                continue
        left = (nxt - today).days
        if 0 <= left <= within:
            out.append((m["name"], left))
    out.sort(key=lambda t: t[1])
    return out


def birthday_line(tree, now=None, within=30) -> str:
    """近期生日的一句提醒。"""
    ups = upcoming_birthdays(tree, now, within)
    if not ups:
        return ""
    bits = []
    for name, left in ups:
        when = "今天" if left == 0 else ("明天" if left == 1 else f"还有{left}天")
        bits.append(f"{name}{when}过生日")
    return "记着啊——" + "；".join(bits) + "。"
