"""遗物 / 信物的故事：一块表、一枚戒指、一本书，每样东西都有来历，
也有想交到谁手里的心意。问"爷爷那块表呢"能讲出故事，也能说清该传给谁、收在哪。

配在 config/heirlooms.yaml，或并入 legacy.heirlooms。纯逻辑、可单测、优雅降级。
注意：只记物件来历、心意归属与存放位置，不碰密码/账号这类敏感凭据。
"""

from __future__ import annotations


def collect_heirlooms(config=None, legacy=None) -> list:
    """汇总信物：config/heirlooms.yaml 的 items + legacy.heirlooms，规整成 dict 列表。

    每项 {item, story, from, to, year, where}；按物名去重保序。
    """
    raw = []
    if isinstance(config, dict):
        src = config.get("heirlooms", config.get("items"))
        if src is None and not {"item", "name"} & set(config):
            src = None
        raw += src if isinstance(src, list) else []
    elif isinstance(config, list):
        raw += config
    leg = (legacy or {}).get("heirlooms") if isinstance(legacy, dict) else None
    if isinstance(leg, list):
        raw += leg

    out, seen = [], set()
    for it in raw:
        if isinstance(it, str):
            it = {"item": it}
        if not isinstance(it, dict):
            continue
        name = str(it.get("item") or it.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({
            "item": name,
            "story": str(it.get("story") or "").strip(),
            "from": str(it.get("from") or "").strip(),
            "to": str(it.get("to") or "").strip(),
            "year": str(it.get("year") or "").strip(),
            "where": str(it.get("where") or "").strip(),
        })
    return out


def find_heirloom(items, query):
    """按物名在问话里找信物（子串匹配，名字长的优先）。"""
    if not items or not query:
        return None
    q = str(query)
    for it in sorted(items, key=lambda x: len(x["item"]), reverse=True):
        if it["item"] and it["item"] in q:
            return it
    return None


def story_of(it) -> str:
    """把一件信物讲成一段话：来历 + 故事 + 心意所属。"""
    if not it:
        return ""
    head = f"说起这{it['item']}"
    if it.get("from"):
        head += f"，是{it['from']}传下来的"
    if it.get("year"):
        head += f"，{it['year']}年的物件了"
    line = head + "。"
    if it.get("story"):
        line += it["story"].rstrip("。.") + "。"
    if it.get("to"):
        line += f"我想把它交给{it['to']}，记着这份念想。"
    return line


def bequest_to(items, name) -> list:
    """这个人该得的信物有哪些。"""
    if not items or not name:
        return []
    n = str(name).strip()
    return [it for it in items if it.get("to") and (it["to"] in n or n in it["to"])]


def list_items(items) -> str:
    """报一报家里都有哪些念想物件。"""
    names = [it["item"] for it in (items or []) if it.get("item")]
    return ("家里这些念想物件：" + "、".join(names) + "。") if names else ""


def where_is(it) -> str:
    """这件东西收在哪（只说位置，不碰敏感凭据）。"""
    if not it or not it.get("where"):
        return ""
    return f"{it['item']}收在{it['where']}。"
