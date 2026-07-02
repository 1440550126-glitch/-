"""过日子的小窍门：长辈压箱底的生活智慧——油渍怎么去、毛衣缩了怎么办、回南天怎么防潮。
不是养生不是治病（那归食疗/急救），是**家务持家**的老经验，省心又省钱。

问着答、闲了也能教一条。纯数据 + 纯逻辑、可单测。可在 config 里加自家的窍门。
"""

from __future__ import annotations

# 每条：类别 / 触发词 / 窍门。都是家务持家类，不碰健康用药。
_HACKS = [
    # —— 清洁去渍 ——
    {"cat": "清洁", "keys": ["油渍", "油污", "油烟机", "抽油烟", "油垢"],
     "tip": "油渍别干擦——用温热的淘米水或加了小苏打的热水抹，油遇碱就化，一擦就亮。"},
    {"cat": "清洁", "keys": ["茶渍", "茶垢", "水杯", "杯子脏"],
     "tip": "杯里的茶垢，挤点牙膏用软布转两圈，或撒点盐搓一搓，比刷子还干净。"},
    {"cat": "清洁", "keys": ["血渍", "血迹"],
     "tip": "血渍只用冷水，千万别上热水——一烫蛋白就凝住，越洗越顽固。"},
    {"cat": "清洁", "keys": ["铁锈", "生锈", "锈迹"],
     "tip": "小铁锈拿白醋泡一会儿，或用半个柠檬蘸盐擦，锈就松了。"},
    {"cat": "清洁", "keys": ["白鞋", "小白鞋", "鞋发黄"],
     "tip": "白鞋刷完别晒太阳，拿白纸巾整个包上阴干，就不泛黄。"},
    {"cat": "清洁", "keys": ["水垢", "水壶", "热水壶"],
     "tip": "水壶里的水垢，烧一壶加了白醋的水泡半小时，再涮两遍，垢就掉了。"},
    # —— 厨房处理 ——
    {"cat": "厨房", "keys": ["切洋葱", "洋葱辣眼", "洋葱呛"],
     "tip": "切洋葱前把它在冰箱凉一会儿，或刀蘸点凉水，辣味挥发慢，不呛眼。"},
    {"cat": "厨房", "keys": ["米虫", "生虫", "大米", "米缸"],
     "tip": "米缸里放几瓣干大蒜或一小包花椒，米就不容易生虫。"},
    {"cat": "厨房", "keys": ["去腥", "鱼腥", "腥味"],
     "tip": "去腥靠葱姜料酒，洗鱼时抹点盐和白酒，腥味去大半。"},
    {"cat": "厨房", "keys": ["保鲜", "蔬菜放", "菜蔫", "存菜"],
     "tip": "绿叶菜用厨房纸包一层再装袋，吸了潮气不易烂；根朝下立着放更耐放。"},
    # —— 收纳整理 ——
    {"cat": "收纳", "keys": ["叠衣服", "衣柜挤", "收纳衣服", "衣服多"],
     "tip": "衣服竖着卷成卷立着放，一眼全看见、不压皱，抽屉还能多塞一半。"},
    {"cat": "收纳", "keys": ["数据线", "耳机线", "线缠", "充电线"],
     "tip": "线用卷筒纸芯分开卷好，或拿小夹子夹住，就不打结成一团。"},
    # —— 省钱省电 ——
    {"cat": "省钱", "keys": ["省电", "电费", "空调省", "费电"],
     "tip": "空调定 26 度配个电扇，凉得匀还省电；出门前十分钟先关，余凉还能撑会儿。"},
    {"cat": "省钱", "keys": ["冰箱省", "冰箱费电", "冰箱"],
     "tip": "冰箱七八分满最省电，别太满也别太空；离墙留条缝好散热。"},
    {"cat": "省钱", "keys": ["省水", "水费"],
     "tip": "淘米水、洗菜水攒着冲马桶、浇花，一个月水费省下不少。"},
    # —— 防潮防虫 ——
    {"cat": "防潮", "keys": ["回南天", "潮湿", "受潮", "防潮", "返潮"],
     "tip": "回南天关窗别开，衣柜里塞报纸或放几包竹炭吸潮；等晴了再开窗通风。"},
    {"cat": "防虫", "keys": ["蚊子", "防蚊", "蚊虫"],
     "tip": "窗台摆盆薄荷或晒干的橘子皮，蚊子不爱近；傍晚早点关纱窗最管用。"},
    {"cat": "防虫", "keys": ["蟑螂", "小强"],
     "tip": "缝隙撒点干苏打加糖，保持厨房干爽断了水源，蟑螂自然少。"},
    # —— 衣物保养 ——
    {"cat": "衣物", "keys": ["羽绒服洗", "羽绒服", "洗羽绒"],
     "tip": "羽绒服别拧，平铺压水，晾到八成干拍一拍让绒散开，就蓬松不结块。"},
    {"cat": "衣物", "keys": ["毛衣缩水", "毛衣缩", "毛衣"],
     "tip": "毛衣缩了，温水加点护发素泡两分钟能松回来；晾时平铺别挂，免得抻长。"},
    {"cat": "衣物", "keys": ["静电", "起电"],
     "tip": "衣服起静电，挂前喷点稀释的柔顺剂水，或拿金属衣架蹭一下放电。"},
]

_INTENT = ("怎么", "咋", "如何", "怎样", "窍门", "妙招", "办法", "去掉", "弄掉",
           "洗掉", "处理", "咋办", "怎么办", "有啥招", "支个招")


def all_tips() -> list:
    return list(_HACKS)


def categories() -> list:
    out = []
    for h in _HACKS:
        if h["cat"] not in out:
            out.append(h["cat"])
    return out


def tips_in(cat) -> list:
    return [h["tip"] for h in _HACKS if h["cat"] == str(cat or "")]


def _score(entry, u) -> int:
    return sum(1 for k in entry["keys"] if k in u)


def match(query, config=None) -> dict | None:
    """挑最对症的一条窍门（按命中关键词多少）。对不上返回 None。"""
    u = str(query or "")
    pool = list(_HACKS)
    if isinstance(config, dict) and isinstance(config.get("hacks"), list):
        pool = pool + [h for h in config["hacks"] if isinstance(h, dict) and h.get("tip")]
    best, best_s = None, 0
    for h in pool:
        s = _score(h, u)
        if s > best_s:
            best, best_s = h, s
    return best if best_s > 0 else None


def tip_for(query, config=None) -> str:
    h = match(query, config)
    return h["tip"] if h else ""


def random_tip(seed="", config=None) -> str:
    """随口教一条过日子的小窍门。"""
    pool = list(_HACKS)
    if not pool:
        return ""
    h = pool[len(str(seed)) % len(pool)]
    return f"教你个过日子的小窍门：{h['tip']}"


def is_lifehack_query(utterance, config=None) -> bool:
    u = utterance or ""
    if any(k in u for k in ("生活窍门", "小窍门", "小妙招", "过日子的窍门", "持家",
                            "生活小常识", "有什么窍门")):
        return True
    # 命中某个家务问题 + 像在求办法
    if match(u, config) is not None and any(k in u for k in _INTENT):
        return True
    return False
