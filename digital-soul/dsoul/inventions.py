"""中国古代发明：四大发明，还有算盘、瓷器、丝绸、地动仪、都江堰……老祖宗的智慧。
给孙辈讲讲，长志气。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_INVENTIONS = {
    "造纸术": "东汉蔡伦改进，用树皮破布造出便宜的纸，让书写和文化普及开来。",
    "印刷术": "从雕版到北宋毕昇的活字印刷，书籍能大量复制，知识传得更快。",
    "火药": "唐代炼丹时偶然发现，后来用于火器，也做成了节日的烟花爆竹。",
    "指南针": "从战国的‘司南’到航海罗盘，靠磁针指向辨方向，助远洋航行。",
    "算盘": "中国古代的‘计算器’，一颗颗算珠拨弄，珠算口诀又快又准。",
    "瓷器": "中国最早烧出真正的瓷器，温润如玉，‘China’也是瓷器的意思。",
    "丝绸": "中国人最早养蚕缫丝、织成丝绸，沿着丝绸之路远销西方。",
    "地动仪": "东汉张衡发明，能测出地震发生的方向，是世界上最早的地震仪。",
    "都江堰": "战国李冰父子修的水利工程，两千多年还在用，化水患为水利。",
    "针灸": "中医独有，扎银针、按穴位疏通经络，已传遍世界。",
    "茶": "中国是茶的故乡，神农尝百草识得茶，喝茶的习俗从这儿传向世界。",
    "二十四节气": "古人观天象总结出的农事历法，‘清明前后种瓜点豆’，指导耕种。",
    "赵州桥": "隋代李春设计的石拱桥，敞肩拱省料又结实，一千四百年不倒。",
    "浑天仪": "古代观测天体的仪器，张衡也造过，演示日月星辰运行。",
}

_ALIAS = {"活字印刷": "印刷术", "雕版印刷": "印刷术", "司南": "指南针", "罗盘": "指南针",
          "珠算": "算盘", "中医针灸": "针灸"}

_FOUR = ("造纸术", "印刷术", "火药", "指南针")


def inventions(config=None) -> list:
    db = dict(_INVENTIONS)
    if isinstance(config, dict) and isinstance(config.get("inventions"), dict):
        db.update(config["inventions"])
    return list(db)


def four_inventions() -> str:
    return "中国古代四大发明是：造纸术、印刷术、火药、指南针。"


def _table(config) -> dict:
    db = dict(_INVENTIONS)
    if isinstance(config, dict) and isinstance(config.get("inventions"), dict):
        for k, v in config["inventions"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def find_invention(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_invention(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_invention_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("四大发明", "古代发明", "中国发明")):
        return True
    if find_invention(u, config) and any(k in u for k in ("是什么", "谁发明", "怎么来", "介绍",
                                                          "讲讲", "什么意思", "由来", "谁造",
                                                          "谁修", "谁建", "修的", "建的")):
        return True
    return False
