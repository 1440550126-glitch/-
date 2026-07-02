"""老人该打的疫苗：流感、肺炎、带状疱疹……上了年纪打几针该打的疫苗，少遭好些罪。
哪种防什么、多久打一次、去哪打、打前打后注意啥，说清楚。纯逻辑、可单测。

⚠️ 该不该打、有没有禁忌，由接种点医生评估为准；发烧或急性病期间先缓一缓。
"""

from __future__ import annotations

# 疫苗 -> (防什么/怎么打, 提醒)
_VACCINES = {
    "流感疫苗": ("防流行性感冒。老人、慢病患者尤其该打——每年'秋天'（9–11 月）打一针，因为流感病毒每年变、"
              "免疫力也只管一季。去社区卫生服务中心打。",
              "打了不是绝对不感冒，但能大大降低中招和变重症的风险。"),
    "肺炎疫苗": ("防肺炎球菌引起的肺炎、脑膜炎等。常用 23 价多糖疫苗，60 岁以上、有慢病的建议打；"
              "一般打一针，特殊情况几年后复种，听医生的。",
              "可以和流感疫苗一起打（不同胳膊），双保险。"),
    "带状疱疹疫苗": ("防'缠腰龙'（带状疱疹）——那种火烧火燎的神经痛，老人得了很遭罪、还可能留长期后遗痛。"
                "50 岁以上推荐打，多为自费、打两针。",
                "得过水痘的体内有病毒，年纪大、免疫力降就可能发出来，打疫苗划算。"),
    "新冠疫苗": ("按当地安排接种或打加强针，老人和有基础病的是重点保护人群。",
              "具体打哪种、要不要加强，看当地疾控通知。"),
    "破伤风疫苗": ("受了伤——尤其是被生锈铁器、泥土、动物咬抓伤的深伤口，要及时打破伤风（针或免疫球蛋白）。",
                "伤口深、脏、之前没打过或很久没打，赶紧去医院处理，别拖。"),
}

_ALIAS = {
    "流感疫苗": "流感疫苗", "流感": "流感疫苗", "感冒疫苗": "流感疫苗",
    "肺炎疫苗": "肺炎疫苗", "肺炎": "肺炎疫苗", "23价": "肺炎疫苗",
    "带状疱疹疫苗": "带状疱疹疫苗", "带状疱疹": "带状疱疹疫苗", "缠腰龙": "带状疱疹疫苗", "蛇盘疮": "带状疱疹疫苗",
    "新冠疫苗": "新冠疫苗", "新冠": "新冠疫苗", "加强针": "新冠疫苗",
    "破伤风疫苗": "破伤风疫苗", "破伤风": "破伤风疫苗",
}

_TAIL = "（该不该打、有无禁忌以接种点医生评估为准；发热或急性病期先缓打、打完留观 30 分钟。）"


def _all(config=None) -> dict:
    d = dict(_VACCINES)
    cfg = (config or {}).get("vaccines") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("about"):
                d[str(name)] = (str(v["about"]), str(v.get("tip", "")))
    return d


def vaccines(config=None) -> list:
    return list(_all(config).keys())


def find_vaccine(utterance, config=None):
    """认出问的哪种疫苗（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def info(vaccine, config=None) -> str:
    """某种疫苗：防什么/怎么打 + 提醒 + 免责。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(vaccine or ""), str(vaccine or ""))
    if key not in d:
        return ""
    about, tip = d[key]
    return f"{key}：{about}" + (f"（{tip}）" if tip else "") + _TAIL


def overview() -> str:
    """老人值得了解的几种疫苗。"""
    return ("上了年纪可了解这几种疫苗：流感疫苗（每年秋天打）、肺炎疫苗、带状疱疹疫苗（防缠腰龙），"
            "新冠按当地安排，受伤时记得破伤风。去社区卫生服务中心打。" + _TAIL)


def is_vaccine_query(utterance, config=None) -> bool:
    """是不是在问疫苗的事。"""
    u = str(utterance or "")
    has = ("疫苗" in u) or ("接种" in u) or (find_vaccine(u, config) is not None)
    if not has:
        return False
    return any(k in u for k in ("该打", "要打", "打不打", "多久", "哪里打", "去哪", "怎么打", "几针",
                                "什么时候", "啥时候", "什么疫苗", "哪些疫苗", "推荐", "预防", "该不该",
                                "要不要", "多少", "吗", "呢", "几岁", "多大"))


def count(config=None) -> int:
    return len(_all(config))
