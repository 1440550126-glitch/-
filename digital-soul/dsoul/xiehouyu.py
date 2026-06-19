"""歇后语：'外甥打灯笼——照旧（舅）''泥菩萨过江——自身难保'。
中国人嘴边的俏皮智慧，逗趣又传神。说前半截，分身能接后半截，也能讲讲意思、出个题考你。

像个肚里有货、爱跟你逗两句的长辈。纯数据 + 纯逻辑、可单测。可在 config 加自家的。
"""

from __future__ import annotations

# 前半截 → (后半截, 意思)
_XIE = {
    "外甥打灯笼": ("照旧（舅）", "还跟原来一样，没变。"),
    "泥菩萨过江": ("自身难保", "自己都顾不过来，哪还能管别人。"),
    "哑巴吃黄连": ("有苦说不出", "心里苦，却没法跟人讲。"),
    "黄鼠狼给鸡拜年": ("没安好心", "假意亲热，其实图谋不轨。"),
    "猫哭耗子": ("假慈悲", "假惺惺地装好心。"),
    "竹篮打水": ("一场空", "白忙活，到头来什么也没落下。"),
    "八仙过海": ("各显神通", "各人拿出各人的本事。"),
    "姜太公钓鱼": ("愿者上钩", "心甘情愿地中招，不怪别人。"),
    "芝麻开花": ("节节高", "日子越过越好，一节比一节强。"),
    "张飞穿针": ("大眼瞪小眼", "彼此都没辙，干瞪眼。"),
    "铁公鸡": ("一毛不拔", "极其吝啬小气。"),
    "狗拿耗子": ("多管闲事", "管了不该自己管的事。"),
    "千里送鹅毛": ("礼轻情意重", "东西虽小，心意却深。"),
    "小葱拌豆腐": ("一清二白", "清清白白，明明白白。"),
    "周瑜打黄盖": ("一个愿打一个愿挨", "两厢情愿的事，旁人别插嘴。"),
    "孔夫子搬家": ("净是书（输）", "老是输，谐音打趣。"),
    "热锅上的蚂蚁": ("团团转", "急得不行，坐立不安。"),
    "哑巴吃饺子": ("心里有数", "嘴上不说，心里清楚得很。"),
    "老王卖瓜": ("自卖自夸", "自己夸自己的东西好。"),
    "肉包子打狗": ("有去无回", "东西出去了就别指望回来。"),
    "兔子尾巴": ("长不了", "维持不了多久。"),
    "丈二和尚": ("摸不着头脑", "一头雾水，弄不明白。"),
    "门缝里看人": ("把人看扁了", "瞧不起人。"),
    "茶壶里煮饺子": ("有货倒不出", "肚里有东西，却说不出来。"),
}


def _merge(config) -> dict:
    db = dict(_XIE)
    if isinstance(config, dict) and isinstance(config.get("xiehouyu"), dict):
        for k, v in config["xiehouyu"].items():
            if isinstance(v, (list, tuple)) and v:
                tail = str(v[0]).strip()
                mean = str(v[1]).strip() if len(v) > 1 else ""
                if tail:
                    db[str(k).strip()] = (tail, mean)
            elif isinstance(v, str) and v.strip():
                db[str(k).strip()] = (v.strip(), "")
    return db


def _bare(s) -> str:
    return "".join(ch for ch in str(s or "") if ch not in "，,。.！!？?、—－- （）()…“”\"' 　\n\t")


def fronts(config=None) -> list:
    return list(_merge(config).keys())


def tail_of(front, config=None) -> str:
    """给前半截，接后半截。对不上返回空。"""
    return _merge(config).get(str(front or "").strip(), ("", ""))[0]


def find_front(utterance, config=None) -> str:
    """从话里认出提到的歇后语前半截（去标点比对）。认不出返回空。"""
    u = _bare(utterance)
    if not u:
        return ""
    for f in _merge(config):
        if _bare(f) and _bare(f) in u:
            return f
    return ""


def answer(front, config=None) -> str:
    """接上一句完整的歇后语 + 意思。"""
    db = _merge(config)
    f = str(front or "").strip()
    if f not in db:
        f = find_front(front, config)
    if not f or f not in db:
        return ""
    tail, mean = db[f]
    s = f"{f}——{tail}"
    return s + (f"，意思是{mean}" if mean else "。")


def random_one(seed="", config=None) -> str:
    db = list(_merge(config).items())
    if not db:
        return ""
    f, (tail, mean) = db[len(str(seed)) % len(db)]
    return f"{f}——{tail}。" + (f"（{mean}）" if mean else "")


def quiz(seed="", config=None) -> tuple:
    """出个题：返回 (前半截问句, 后半截答案)。"""
    db = list(_merge(config).items())
    if not db:
        return ("", "")
    f, (tail, _mean) = db[len(str(seed)) % len(db)]
    return (f"我说上半句，你接下半句啊——“{f}——？”", tail)


def is_xiehouyu_request(utterance) -> bool:
    u = utterance or ""
    if "歇后语" in u:
        return True
    f = find_front(u)
    # 光抛了前半截（可能带个破折号）等着接："小葱拌豆腐——"
    if f and _bare(u).replace(_bare(f), "", 1) == "":
        return True
    # "外甥打灯笼下半句/后半句/怎么接"
    if f and any(k in u for k in ("下半句", "后半句", "下一句", "怎么接",
                                              "接下句", "是啥", "怎么说", "什么意思",
                                              "啥意思", "意思", "接下半句")):
        return True
    return False
