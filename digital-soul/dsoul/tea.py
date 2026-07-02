"""泡茶：各种茶怎么泡才好喝——绿茶别用开水烫、红茶暖胃、普洱要洗茶。
水温、时间、配什么、什么时候喝，说清楚。喝茶是老人的乐子，分身懂点更贴心。

养生功效是民间/中医说法，仅供参考。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 茶 → (水温, 冲泡, 特点与适合)
_TEAS = {
    "绿茶": ("80–85℃，别用刚烧开的水（会烫熟茶叶、发苦）", "泡 1–2 分钟，可续水",
             "清香解腻、提神，上午喝最好；龙井、碧螺春都是它。"),
    "红茶": ("90–95℃", "泡 3–5 分钟，可加奶加糖", "性温暖胃，秋冬、早晨喝舒坦；祁门、正山小种是代表。"),
    "普洱": ("沸水，先快冲一遍‘洗茶’再喝", "很耐泡，能泡七八道", "暖胃助消化，饭后一杯解油腻；熟普更温和。"),
    "乌龙": ("95–100℃，高温激香", "泡 1–2 分钟，多次冲泡", "半发酵，香气足、提神醒脑；铁观音、大红袍都是。"),
    "白茶": ("85–90℃", "泡 2–3 分钟", "清淡退火，‘一年茶、三年药、七年宝’；白毫银针、寿眉。"),
    "茉莉花茶": ("90℃左右", "泡 2–3 分钟", "香气怡人、疏肝理气，春天喝最应景。"),
    "菊花茶": ("85–90℃", "泡 3–5 分钟，可配枸杞", "清热明目、降火，对着电脑久了喝点好。"),
    "枸杞茶": ("温水或 80℃，泡开即可", "可反复加水，最后嚼了吃掉", "养肝明目、补气；别和绿茶一起泡。"),
    "黑茶": ("沸水，先洗茶", "耐泡", "暖胃去腻，边疆喝它配奶；安化黑茶、六堡茶。"),
}

_ALIAS = {"龙井": "绿茶", "碧螺春": "绿茶", "毛尖": "绿茶", "铁观音": "乌龙", "大红袍": "乌龙",
          "祁门红茶": "红茶", "正山小种": "红茶", "金骏眉": "红茶", "茉莉": "茉莉花茶",
          "菊花": "菊花茶", "枸杞": "枸杞茶", "白毫银针": "白茶", "寿眉": "白茶"}


def _table(config) -> dict:
    db = dict(_TEAS)
    if isinstance(config, dict) and isinstance(config.get("tea"), dict):
        for k, v in config["tea"].items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                db[str(k)] = (str(v[0]), str(v[1]), str(v[2]))
    return db


def teas(config=None) -> list:
    return list(_table(config).keys())


def find_tea(query, config=None) -> str:
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


def brew(query, config=None) -> str:
    """这茶怎么泡。认不出返回空。"""
    db = _table(config)
    name = query if query in db else find_tea(query, config)
    row = db.get(name)
    if not row:
        return ""
    temp, how, feat = row
    return f"{name}：水温{temp}；{how}。{feat}"


def is_tea_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if "泡茶" in u or "喝什么茶" in u:
        return True
    if find_tea(u, config) and any(k in u for k in ("怎么泡", "咋泡", "水温", "几度",
                                                    "泡多久", "功效", "好处", "怎么喝", "适合")):
        return True
    return False
