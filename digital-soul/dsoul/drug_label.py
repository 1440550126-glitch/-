"""看懂药品说明书：那张折叠的小纸、密密麻麻的字——适应症、用法用量、不良反应、禁忌……
每一栏说的啥、该重点看哪几栏，讲明白，吃药更踏实。纯逻辑、可单测。
和"服药常识"(med_safety 怎么吃)、"小药箱"(medicine_cabinet 备啥)接着用。

⚠️ 说明书看不懂就问医生药师；和医嘱不一致时，以医生交代的为准。
"""

from __future__ import annotations

# 栏目/名词 -> 通俗解释
_SECTIONS = {
    "适应症": "也叫'功能主治'，说这药是治什么的。先看这栏——对症才吃，不对症别瞎吃。",
    "用法用量": "一次吃几片（多少毫克）、一天几次、饭前还是饭后。严格照这个来，别自己加量减量。",
    "不良反应": "可能出现的副作用（如犯困、恶心、皮疹）。列出来是依法告知，不一定都会有；"
             "出现严重的（呼吸困难、大面积皮疹、心慌）赶紧停药就医。",
    "禁忌": "哪些人、哪些情况'绝对不能用'（如对成分过敏、孕妇、某些肝肾病）。这栏最要紧，碰上一条就别吃。",
    "注意事项": "'慎用'的人群、和别的药/食物的相互作用、忌口（如忌酒、忌西柚）。吃前扫一眼。",
    "规格": "每片/每粒含多少毫克。算用量、对剂量时看它。",
    "有效期": "也看'生产日期/批号'，过了有效期的别吃，药效没了甚至变质。",
    "贮藏": "怎么存：常温阴凉避光，还是要冷藏（2～8℃）。存错了药会失效。",
    "孕妇儿童": "孕妇、哺乳期、儿童、老人能不能用、怎么减量，单独标出来，照着来。",
    "OTC标志": "盒上有标志：红色 OTC 是'甲类非处方药'，药店买、最好问问药师；"
             "绿色 OTC 是'乙类'，相对安全、超市也能买。没有 OTC、写'Rx/处方药'的，必须医生开方。",
}

_ALIAS = {
    "适应症": "适应症", "功能主治": "适应症", "治什么": "适应症", "管啥病": "适应症",
    "用法用量": "用法用量", "怎么吃": "用法用量", "吃几片": "用法用量", "用量": "用法用量", "一天几次": "用法用量",
    "不良反应": "不良反应", "副作用": "不良反应", "有什么反应": "不良反应",
    "禁忌": "禁忌", "禁忌症": "禁忌", "不能用": "禁忌", "哪些人不能吃": "禁忌",
    "注意事项": "注意事项", "慎用": "注意事项", "相互作用": "注意事项",
    "规格": "规格", "多少毫克": "规格", "一片多少": "规格",
    "有效期": "有效期", "保质期": "有效期", "过期药": "有效期", "生产批号": "有效期",
    "贮藏": "贮藏", "怎么存": "贮藏", "存放": "贮藏", "要冷藏吗": "贮藏",
    "孕妇儿童": "孕妇儿童", "孕妇能吃吗": "孕妇儿童", "小孩能吃吗": "孕妇儿童", "儿童用量": "孕妇儿童",
    "OTC": "OTC标志", "otc": "OTC标志", "非处方药": "OTC标志", "处方药": "OTC标志", "红色标志": "OTC标志", "绿色标志": "OTC标志",
}


def _all(config=None) -> dict:
    d = dict(_SECTIONS)
    cfg = (config or {}).get("drug_label") if isinstance(config, dict) else None
    extra = (cfg or {}).get("sections") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def sections(config=None) -> list:
    return list(_all(config).keys())


def find_section(utterance, config=None):
    """认出问的哪一栏（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def explain(section, config=None) -> str:
    """某一栏怎么看。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(section or ""), str(section or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}"


def overview() -> str:
    """看说明书重点看哪几栏。"""
    return ("看药品说明书，重点扫这几栏：①适应症（治不治你这病）；②用法用量（一次几片、一天几次、饭前后）；"
            "③禁忌（你是不是不能用的人）；④不良反应和注意事项（副作用、忌口、和别的药冲不冲）；"
            "⑤有效期（过没过期）。看不懂就问药师，别硬猜。")


def is_drug_label_query(utterance, config=None) -> bool:
    """是不是在问怎么看药品说明书。"""
    u = str(utterance or "")
    if any(k in u for k in ("药品说明书", "药的说明书", "说明书怎么看", "看说明书")) and "药" in u:
        return True
    if find_section(u, config) and any(k in u for k in ("是什么", "啥意思", "什么意思", "怎么看",
                                                        "哪一栏", "说明书", "怎么回事", "看哪")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
