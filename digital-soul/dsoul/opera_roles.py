"""戏曲行当与脸谱：生旦净丑都演谁、红脸白脸代表啥——看戏门道讲给你听。
和"戏曲"(opera 起唱段)不一样，这里讲'角色行当'和'脸谱颜色'的讲究，看戏更明白。
纯逻辑、可单测。
"""

from __future__ import annotations

# 名词 -> 解释
_ITEMS = {
    "生": "男性角色。又分'老生'（中老年正派、挂髯口、重唱）、'小生'（年轻男子）、"
        "'武生'（会武打的）。诸葛亮、周瑜这类多是生。",
    "旦": "女性角色。'青衣'（端庄的正派女子、重唱）、'花旦'（活泼的姑娘）、'老旦'（老年妇女）、"
        "'武旦/刀马旦'（会武的女子）。",
    "净": "也叫'花脸'，性格鲜明、嗓门大、要勾脸谱的男角，重唱重做，如包公、张飞、曹操。",
    "丑": "'小花脸'，鼻梁抹一块白，插科打诨、逗乐的角色，文丑武丑都有；戏里少不了他添趣。",
    "红脸": "脸谱红色代表'忠勇正义'，最典型的是关羽（红脸关公）。",
    "黑脸": "黑色代表'刚正、勇猛、铁面无私'，如包公（铁面）、张飞、李逵。",
    "白脸": "白色（粉白）多代表'奸诈、阴险'，最有名的是曹操——'白脸奸臣'。",
    "黄脸": "黄色代表'凶狠、勇猛或暴躁'。",
    "蓝绿脸": "蓝、绿脸多表示'勇猛、桀骜、草莽英雄'，绿林好汉常见。",
    "金银脸": "金、银色多用于'神仙、佛祖、妖怪'，显其神秘威严，如孙悟空、二郎神。",
    "四功五法": "戏曲演员的基本功：'四功'是唱、念、做、打;'五法'是手、眼、身、法、步。台上一分钟，台下十年功。",
}

_ALIAS = {
    "生": "生", "老生": "生", "小生": "生", "武生": "生",
    "旦": "旦", "青衣": "旦", "花旦": "旦", "老旦": "旦", "刀马旦": "旦", "武旦": "旦",
    "净": "净", "花脸": "净",
    "丑": "丑", "小花脸": "丑", "丑角": "丑",
    "红脸": "红脸", "红色脸谱": "红脸", "关公脸": "红脸",
    "黑脸": "黑脸", "包公脸": "黑脸",
    "白脸": "白脸", "曹操脸": "白脸", "白脸奸臣": "白脸",
    "黄脸": "黄脸",
    "蓝脸": "蓝绿脸", "绿脸": "蓝绿脸", "蓝绿脸": "蓝绿脸",
    "金脸": "金银脸", "银脸": "金银脸", "金银脸": "金银脸",
    "四功五法": "四功五法", "唱念做打": "四功五法", "手眼身法步": "四功五法",
    "生旦净丑": "生", "行当": "生",
}


def _all(config=None) -> dict:
    d = dict(_ITEMS)
    cfg = (config or {}).get("opera_roles") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def items(config=None) -> list:
    return list(_all(config).keys())


def find_item(utterance, config=None):
    """认出问的哪个行当/脸谱（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def explain(item, config=None) -> str:
    """某个行当/脸谱怎么讲。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(item or ""), str(item or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}"


def roles_overview() -> str:
    """生旦净丑总述。"""
    return ("戏曲角色分四大行当：生（男角）、旦（女角）、净（花脸，性格鲜明）、丑（小花脸，逗趣）。"
            "脸谱颜色也有讲究：红忠、黑直、白奸、金银是神佛。想细说哪个跟我说。")


def is_opera_role_query(utterance, config=None) -> bool:
    """是不是在问戏曲行当/脸谱。"""
    u = str(utterance or "")
    if any(k in u for k in ("生旦净丑", "脸谱", "行当", "唱念做打")):
        return True
    if find_item(u, config) and any(k in u for k in ("是什么", "什么意思", "代表", "啥意思",
                                                     "怎么讲", "什么角色", "演谁", "是啥")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
