"""戏曲：陪爱听戏的老人来两句——京剧、黄梅戏、越剧、豫剧、评剧。
那些耳朵磨出茧的老唱段，起个头，TA 能跟你哼上一句，是几代人的乡愁。

只收传唱已久的经典开篇唱词（短短一两句）。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

import re

# 剧种 → [(剧目, 经典开篇唱词)]
_OPERA = {
    "京剧": [
        ("《苏三起解》", "苏三离了洪洞县，将身来在大街前。"),
        ("《空城计》", "我正在城楼观山景，耳听得城外乱纷纷。"),
        ("《铡美案》", "包龙图打坐在开封府。"),
    ],
    "黄梅戏": [
        ("《天仙配》", "树上的鸟儿成双对，绿水青山带笑颜。"),
        ("《女驸马》", "为救李郎离家园，谁料皇榜中状元。"),
    ],
    "越剧": [
        ("《红楼梦》", "天上掉下个林妹妹，似一朵轻云刚出岫。"),
        ("《梁山伯与祝英台》", "十八相送情切切，你我鸿雁两分开。"),
    ],
    "豫剧": [
        ("《花木兰》", "刘大哥讲话理太偏，谁说女子享清闲。"),
        ("《穆桂英挂帅》", "辕门外三声炮如同雷震。"),
    ],
    "评剧": [
        ("《花为媒》", "报花名——春季里风吹万物生。"),
        ("《刘巧儿》", "巧儿我自幼儿许配赵家。"),
    ],
}

_ALIAS = {"京戏": "京剧", "国粹": "京剧", "黄梅": "黄梅戏", "豫": "豫剧",
          "河南梆子": "豫剧", "越": "越剧", "绍兴戏": "越剧", "评戏": "评剧"}


def _bare(s) -> str:
    return "".join(ch for ch in str(s or "")
                   if ch not in "，,。.！!？?、—－- （）()…“”\"'　 \n\t《》")


def genres(config=None) -> list:
    return list(_merge(config).keys())


def _merge(config) -> dict:
    db = {k: list(v) for k, v in _OPERA.items()}
    if isinstance(config, dict) and isinstance(config.get("opera"), dict):
        for g, items in config["opera"].items():
            rows = []
            for it in (items or []):
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    rows.append((str(it[0]), str(it[1])))
                elif isinstance(it, dict) and it.get("line"):
                    rows.append((str(it.get("title", "")), str(it["line"])))
            if rows:
                db.setdefault(g, [])
                db[g] = rows + db.get(g, [])
    return db


def normalize_genre(name) -> str:
    n = str(name or "").strip()
    if n in _OPERA:
        return n
    for k, v in _ALIAS.items():
        if k in n:
            return v
    for g in _OPERA:
        if g in n:
            return g
    return ""


def _resolve(genre, config=None) -> str:
    """认出剧种——内置/别名/config 里新加的都认。"""
    g = normalize_genre(genre)
    if g:
        return g
    n = str(genre or "").strip().strip("《》")
    db = _merge(config)
    if n in db:
        return n
    for k in db:
        if k and (k in n or n in k):
            return k
    return ""


def arias(genre, config=None) -> list:
    return list(_merge(config).get(_resolve(genre, config), []))


def famous(genre, seed="", config=None) -> str:
    """某剧种来一段经典唱词（带剧目）。认不出剧种返回空。"""
    g = _resolve(genre, config)
    rows = _merge(config).get(g, [])
    if not rows:
        return ""
    title, line = rows[len(str(seed)) % len(rows)]
    return f"{g}{title}：“{line}”"


def sing_opera(genre=None, seed="", config=None) -> str:
    """点了剧种唱那个；没点就挑一段，招呼你跟着哼。"""
    db = _merge(config)
    g = _resolve(genre, config)
    if not g:
        keys = list(db.keys())
        g = keys[len(str(seed)) % len(keys)] if keys else ""
    s = famous(g, seed, config)
    return (s + " 来，你也哼两句？") if s else ""


def recognize(line, config=None) -> str:
    """听句戏词，认是哪出（返回"剧种《剧目》"）。认不出空。"""
    u = _bare(line)
    if len(u) < 3:
        return ""
    for g, rows in _merge(config).items():
        for title, text in rows:
            # 整句或其中任一分句（≥4 字）对得上就算认出（用户常只报半句）
            for clause in re.split(r"[，,。.！!？?、]", text):
                b = _bare(clause)
                if len(b) >= 4 and (b in u or u in b):
                    return f"{g}{title}"
    return ""


def detect_genre(utterance) -> str:
    u = str(utterance or "")
    for k in list(_OPERA) + list(_ALIAS):
        if k in u:
            return normalize_genre(k)
    return ""


def is_opera_request(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("唱段戏", "来段戏", "听戏", "戏曲", "唱戏", "来出戏", "哼段戏")):
        return True
    if detect_genre(u) and any(k in u for k in ("唱", "来段", "来一段", "哼", "听", "段")):
        return True
    return False
