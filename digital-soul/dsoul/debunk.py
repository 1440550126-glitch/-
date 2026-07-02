"""生活谣言辟谣：隔夜菜致癌？喝醋软化血管？食物相克？——
长辈最容易被养生谣言唬住。这一块用大白话讲讲真相，该破的破、该当真的当真，不夸张不吓人。
纯逻辑、可单测。和"防诈骗"(antifraud)一个心思：别被忽悠，守好钱和健康。

口径：以科学共识为准；个别说法有一点道理就如实说，不一刀切。拿不准的健康问题问医生。
"""

from __future__ import annotations

# (说法, [触发词], 真相)
_MYTHS = [
    ("食物相克", ["食物相克", "相克", "不能一起吃", "虾和维C", "菠菜豆腐"],
     "绝大多数'食物相克'是夸大或讹传，正常饮食的量根本没事——别被吓得这也不敢吃那也不敢吃。"
     "真要注意的是卫生和过敏，不是'相克'。"),
    ("隔夜菜致癌", ["隔夜菜", "隔夜饭", "剩菜致癌"],
     "隔夜菜不会'致癌'。但绿叶菜放久了亚硝酸盐会升高，所以绿叶菜尽量当顿吃完；"
     "肉菜、米饭冷藏好、下顿彻底热透再吃，没问题。"),
    ("喝醋软化血管", ["喝醋软化血管", "醋软化血管", "软化血管", "喝醋降压"],
     "没用。醋一进胃就被胃酸中和了，到不了血管、也软化不了。护血管靠少油少盐、戒烟限酒、多运动、按医嘱吃药。"),
    ("微波炉致癌", ["微波炉致癌", "微波炉辐射", "微波炉有害"],
     "正规使用很安全。微波只是让食物里的水分子振动生热，不会让食物'带辐射'或产生致癌物；门关好就不漏微波。"
     "记得别用金属容器就行。"),
    ("酸碱体质", ["酸碱体质", "碱性食物", "酸性体质", "碱性体质"],
     "'酸碱体质'是彻头彻尾的伪科学、已被揭穿是骗局。人体酸碱由自身严格调节，靠吃东西改变不了，"
     "更没有'碱性食物能治病防癌'这回事，别花冤枉钱。"),
    ("木耳久泡", ["木耳久泡", "泡木耳", "银耳久泡", "泡发太久"],
     "这条要当真！木耳、银耳泡太久（尤其隔夜、室温）可能滋生致命的'米酵菌酸'，中毒很凶险。"
     "现泡现吃、泡发别超过 1～2 小时，泡好放冰箱，发黏有异味就扔。"),
    ("骨头汤补钙", ["骨头汤补钙", "喝骨头汤", "大骨汤补钙"],
     "骨头汤里的钙其实很少，白白的那是脂肪不是钙。真补钙靠牛奶、豆制品、绿叶菜 + 晒太阳，比汤实在多了。"),
    ("保健品治病", ["保健品治病", "保健品能治", "吃保健品", "保健品代替药"],
     "保健品不是药，不能治病、不能代替药。最怕的是听信'神效保健品'把正规药停了——那是拿命冒险，千万别。"),
    ("偏方治大病", ["偏方", "土方子治病", "祖传秘方"],
     "别拿偏方耽误正规治疗。有些偏方没用，有些还有毒、伤肝肾。身体有大问题先看医生，别讳疾忌医。"),
    ("红糖补血", ["红糖补血", "红糖水补血"],
     "红糖含铁很少、补血作用有限，主要是糖。真贫血要去查原因（缺铁？别的病？），对因调理，别指望红糖水。"),
    ("趁热吃", ["趁热吃", "趁烫吃", "热的养胃"],
     "太烫（超过 65℃）的饭菜、热饮反而烫伤食道、长期增加食道癌风险。放到不烫嘴再吃，温的最舒服。"),
    ("喝粥养胃", ["喝粥养胃", "白粥养胃"],
     "胃不舒服时喝点粥好消化，没错；但长期只喝粥、不嚼东西，营养跟不上、胃功能反而退化。养胃靠规律吃、细嚼慢咽、别暴饮暴食。"),
]


def _all(config=None) -> list:
    items = list(_MYTHS)
    cfg = (config or {}).get("debunk") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 3:
                items.append((str(it[0]), list(it[1]), str(it[2])))
            elif isinstance(it, dict) and it.get("claim"):
                items.append((str(it["claim"]), list(it.get("triggers") or []), str(it.get("truth", ""))))
    return items


def myths(config=None) -> list:
    return [m[0] for m in _all(config)]


def find_myth(utterance, config=None):
    """认出问的哪条说法（名/触发词，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for m in _all(config):
        for kw in [m[0]] + list(m[1]):
            if kw and kw in u and len(kw) > best_len:
                best, best_len = m, len(kw)
    return best


def truth(myth, config=None) -> str:
    """某条说法的真相。查不到返回空。"""
    m = myth if isinstance(myth, tuple) else find_myth(myth, config)
    return f"关于「{m[0]}」：{m[2]}" if m else ""


def recall(seed="", config=None) -> str:
    """随口辟一条谣。"""
    items = _all(config)
    if not items:
        return ""
    m = items[len(str(seed)) % len(items)]
    return f"破个常见的谣——{m[0]}：{m[2]}"


def count(config=None) -> int:
    return len(_all(config))


def is_myth_query(utterance, config=None) -> bool:
    """是不是在求证某个说法/辟谣。"""
    u = str(utterance or "")
    if any(k in u for k in ("是真的吗", "是不是真的", "可信吗", "辟谣", "是谣言吗", "靠谱吗",
                            "有科学依据吗", "真的假的")) and find_myth(u, config):
        return True
    if find_myth(u, config) and any(k in u for k in ("真的吗", "对吗", "有道理吗", "可信", "是不是",
                                                     "致癌吗", "管用吗", "有用吗", "能信吗", "有毒吗",
                                                     "能治吗", "能治病吗", "能软化", "该信吗", "真假")):
        return True
    return False
