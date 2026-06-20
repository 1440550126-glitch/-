"""看病就诊技巧：去医院前怎么准备、怎么跟医生说清楚、医嘱怎么记牢、复诊带什么——
看一趟病不容易，准备好了少跑冤枉路、把病说明白。纯逻辑、可单测。
和"导诊"(triage 挂哪科)、"预约挂号"(appointments)接着用，这里讲'怎么看得明白'。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "看病前准备": ("理清楚症状：什么时候开始的、哪儿不舒服、什么感觉、什么时候加重或缓解;"
              "带上以前的病历、检查单、正在吃的药（或拍张照）;列两三个最想问的问题;"
              "要抽血等检查的别吃早饭（空腹）。",
              "带齐医保卡、身份证、够用的钱;老人最好有人陪着去。"),
    "怎么跟医生说": ("捡重点、先说最难受的那条;说清楚'多久了、怎么个不舒服、变化';"
              "别隐瞒在吃的药、以前的病、过敏史;医生说的没听懂，当场就问、别不好意思。",
              "时间有限，把要紧的先讲，别绕远。"),
    "记住医嘱": ("把医生交代的记下来：这药怎么吃、吃多久、注意啥、要不要复查、什么情况赶紧再来;"
              "记不住就让医生写下来或拍下来，临走再问一遍确认。",
              "别一出门就忘了——记牢医嘱，治疗才不打折。"),
    "复诊": ("按医生说的时间复查，别自己觉得好了就不去;复诊带上之前的检查单、病历和在吃的药;"
           "跟医生说说吃药后的变化、有没有不舒服。",
           "慢病更要按时复查、调药，别擅自停。"),
    "有人陪诊": ("老人看病最好有家人陪：帮着排队挂号、记医嘱、问问题、跑腿拿药取报告，也是个底气。",
              "一个人去也别怕，让导医台、志愿者帮忙;实在不行打电话让家人远程帮着记。"),
    "挂号窍门": ("能网上/手机提前预约挂号就别现场排长队;专家号紧张可先看普通号、需要再转;"
              "上午号多、检查也好当天做完。",
              "不知道挂哪个科，先去'分诊台'或挂'全科'让医生帮分。"),
}

_ALIAS = {
    "看病前准备": "看病前准备", "看病前": "看病前准备", "看病准备": "看病前准备", "去医院前": "看病前准备", "就诊准备": "看病前准备",
    "怎么跟医生说": "怎么跟医生说", "跟医生说": "怎么跟医生说", "怎么说病情": "怎么跟医生说", "描述症状": "怎么跟医生说",
    "记住医嘱": "记住医嘱", "医嘱": "记住医嘱", "记不住医生说的": "记住医嘱",
    "复诊": "复诊", "复查": "复诊", "要不要复查": "复诊",
    "有人陪诊": "有人陪诊", "陪诊": "有人陪诊", "陪老人看病": "有人陪诊",
    "挂号窍门": "挂号窍门", "怎么挂号": "挂号窍门", "挂号": "挂号窍门", "预约挂号": "挂号窍门", "挂号排队": "挂号窍门",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("see_doctor") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类就诊技巧（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类就诊技巧怎么做 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def overview() -> str:
    """看病就诊的几条要点。"""
    return ("看病少跑冤枉路：①去前理清症状、带好病历和在吃的药、列好想问的;②跟医生先讲最难受的、"
            "别隐瞒过敏旧病;③医嘱记下来、临走再确认一遍;④按时复诊带上单子;⑤老人最好有人陪。"
            "（不知挂哪科先问分诊台。）")


def is_see_doctor_query(utterance, config=None) -> bool:
    """是不是在问怎么看病/就诊技巧。"""
    u = str(utterance or "")
    if any(k in u for k in ("看病前", "看病准备", "就诊技巧", "怎么看病", "看病要带什么",
                            "看病注意", "陪老人看病")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "咋", "技巧", "注意", "准备",
                                                      "带什么", "要带", "怎么办", "怎么记")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
