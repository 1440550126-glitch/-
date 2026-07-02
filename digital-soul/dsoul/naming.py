"""起名取名：给新生儿/晚辈起个有寓意的好名字——挑寓意字、配姓氏、避坑、讲讲为什么。
家里添丁是大事，长辈最上心。这一块帮着出主意：按愿望（品德/才智/平安/美好…）挑字，
配上姓念顺口，解释每个字的意思，再提醒避开生僻字、不雅谐音。

纯数据 + 纯逻辑、可单测。可在 config 的 naming 里加自家的字辈、偏好字、忌讳字。
起名是给孩子一生的祝福，不是算命——这里只讲寓意与顺口，不许诺吉凶。
"""

from __future__ import annotations

# 按"愿望"分类的寓意好字：类别 -> [(字, 寓意)]
_MEANING = {
    "品德": [("仁", "仁爱宽厚"), ("德", "品德高尚"), ("谦", "谦逊有礼"), ("诚", "真诚守信"),
             ("正", "正直端方"), ("善", "与人为善"), ("廉", "清正廉洁"), ("信", "言而有信"),
             ("贤", "贤良温厚"), ("端", "端庄正派")],
    "才智": [("睿", "睿智通达"), ("哲", "明智善思"), ("敏", "聪敏机灵"), ("慧", "聪慧灵秀"),
             ("博", "博学多识"), ("文", "文采斐然"), ("学", "好学不倦"), ("思", "善于思考"),
             ("彦", "才学出众"), ("聪", "耳聪心明")],
    "志向": [("远", "志存高远"), ("航", "扬帆远航"), ("翔", "展翅高翔"), ("拓", "开拓进取"),
             ("毅", "坚毅不拔"), ("勤", "勤勉踏实"), ("奋", "奋发图强"), ("勇", "勇敢果决"),
             ("立", "自立自强"), ("逸", "超逸不凡")],
    "平安": [("安", "平安顺遂"), ("宁", "安宁康泰"), ("康", "健康强壮"), ("泰", "国泰民安"),
             ("顺", "诸事顺心"), ("祥", "吉祥如意"), ("和", "和顺安乐"), ("禄", "福禄绵长"),
             ("瑞", "祥瑞呈福"), ("吉", "逢凶化吉")],
    "美好": [("欣", "欣欣向荣"), ("悦", "喜悦欢欣"), ("嘉", "美好嘉善"), ("美", "美丽美好"),
             ("雅", "高雅大方"), ("馨", "温馨芬芳"), ("怡", "怡然自得"), ("乐", "快乐安康"),
             ("妍", "明媚妍丽"), ("婉", "温婉柔顺")],
    "自然": [("林", "树木成林"), ("川", "山高水长"), ("海", "胸怀如海"), ("阳", "阳光明朗"),
             ("月", "皎洁清辉"), ("星", "璀璨如星"), ("云", "高远舒卷"), ("松", "如松挺拔"),
             ("竹", "虚心有节"), ("晨", "朝气勃发")],
    "福气": [("福", "福气满满"), ("寿", "健康长寿"), ("喜", "欢喜常临"), ("贵", "尊贵有福"),
             ("丰", "丰衣足食"), ("盈", "丰盈充实"), ("裕", "宽裕富足"), ("庆", "喜庆吉庆"),
             ("熙", "光明兴盛"), ("茂", "繁茂兴旺")],
}

# 查询同义词：把口语映射到类别
_ALIAS = {
    "品德": "品德", "德行": "品德", "做人": "品德", "善良": "品德", "诚信": "品德",
    "才智": "才智", "聪明": "才智", "智慧": "才智", "学问": "才智", "有文化": "才智", "文气": "才智",
    "志向": "志向", "有出息": "志向", "上进": "志向", "坚强": "志向", "前途": "志向", "事业": "志向",
    "平安": "平安", "健康": "平安", "安康": "平安", "顺利": "平安", "平平安安": "平安",
    "美好": "美好", "漂亮": "美好", "好听": "美好", "优雅": "美好", "温柔": "美好",
    "自然": "自然", "大气": "自然", "山水": "自然", "阳光": "自然",
    "福气": "福气", "有福": "福气", "富贵": "福气", "兴旺": "福气", "长寿": "福气",
}

# 起名忌讳/常见生僻难认字（提醒避开，以免孩子一辈子被念错写错）
_AVOID_HINT = ["太生僻难认（别人不会念、电脑打不出）", "不雅谐音（连名带姓念一遍听听）",
               "和长辈名字重字（犯讳）", "笔画特别多（孩子考试写到哭）",
               "多音字歧义（到底念哪个音）"]


def categories(config=None) -> list:
    """所有可选的寓意类别。"""
    return list(_meaning(config).keys())


def _meaning(config=None) -> dict:
    """寓意字表（可被 config.naming.chars 扩充/覆盖）。"""
    m = {k: list(v) for k, v in _MEANING.items()}
    cfg = (config or {}).get("naming") if isinstance(config, dict) else None
    extra = (cfg or {}).get("chars") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for cat, items in extra.items():
            bucket = m.setdefault(str(cat), [])
            for it in (items or []):
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    bucket.append((str(it[0]), str(it[1])))
                elif isinstance(it, dict) and it.get("char"):
                    bucket.append((str(it["char"]), str(it.get("mean", ""))))
    return m


def find_wish(utterance, config=None):
    """从话里听出想要的寓意类别（"想要个聪明点的名字"→才智）。听不出返回 None。"""
    u = str(utterance or "")
    # 先按别名最长匹配
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    # 直接报了类别名
    for cat in _meaning(config):
        if cat in u:
            return cat
    return None


def chars_for(wish, config=None) -> list:
    """某类愿望下的寓意字 [(字, 寓意)]。"""
    cat = _ALIAS.get(str(wish or ""), str(wish or ""))
    return list(_meaning(config).get(cat, []))


def explain_char(ch, config=None) -> str:
    """这个字起名什么寓意？查不到返回空。"""
    for items in _meaning(config).values():
        for c, mean in items:
            if c == ch:
                return mean
    return ""


def _generation_char(config=None) -> str:
    """字辈：家族同辈固定的那个字（如"德"字辈）。没有返回空。"""
    cfg = (config or {}).get("naming") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        g = cfg.get("generation") or cfg.get("字辈")
        if g:
            return str(g)[0]
    return ""


def suggest_names(surname="", wish=None, n=3, seed="", config=None) -> list:
    """给几个候选名：返回 [(全名, 解释)]。
    有字辈就把字辈放第一个字；否则两个寓意字相配。"""
    cat = _ALIAS.get(str(wish or ""), str(wish or "")) or next(iter(_meaning(config)), "")
    pool = chars_for(cat, config) or [(c, m) for items in _meaning(config).values() for c, m in items]
    if not pool:
        return []
    surname = str(surname or "").strip()
    gen = _generation_char(config)
    s = len(str(seed))
    out, seen = [], set()
    for i in range(max(1, int(n)) * 4):
        if gen:
            c2, m2 = pool[(s + i) % len(pool)]
            given, mean = gen + c2, f"{gen}字辈，{m2}"
        else:
            c1, m1 = pool[(s + i) % len(pool)]
            c2, m2 = pool[(s + i * 3 + 1) % len(pool)]
            if c1 == c2:
                continue
            given, mean = c1 + c2, f"{m1}，{m2}"
        if given in seen:
            continue
        seen.add(given)
        full = surname + given
        out.append((full, mean))
        if len(out) >= max(1, int(n)):
            break
    return out


def tips() -> list:
    """起名避坑提醒。"""
    return list(_AVOID_HINT)


def is_naming_query(utterance, config=None) -> bool:
    """是不是在求起名（要有"名字"相关词 + 起/取/想 的意图）。"""
    u = str(utterance or "")
    has_name = any(k in u for k in ("起名", "取名", "起个名", "取个名", "名字", "起名字", "改名", "大名", "小名"))
    intent = any(k in u for k in ("起", "取", "想", "帮", "给", "怎么", "建议", "推荐", "好听", "寓意"))
    return has_name and intent


def explain_request(utterance) -> str:
    """是不是在问某个字起名的寓意（"睿字起名什么意思"）。返回那个字或空。"""
    u = str(utterance or "")
    if "字" in u and any(k in u for k in ("寓意", "意思", "好不好", "起名")):
        for ch in u:
            if '一' <= ch <= '鿿' and ch not in "字寓意思好不起名什么的怎么样":
                if explain_char(ch):
                    return ch
    return ""
