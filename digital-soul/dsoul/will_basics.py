"""立遗嘱常识：怎么立才有效、有哪几种形式、自书遗嘱要点、为什么最好去公证——
把身后的事提前安排明白，是对自己负责、也让子女少为难。纯逻辑、可单测。

⚠️ 这是通用常识，不是法律意见。立遗嘱关系重大，强烈建议咨询律师或到公证处办理，
确保合法有效；具体以《民法典》和专业意见为准。
"""

from __future__ import annotations

# 主题 -> (说明, 提醒)
_TOPICS = {
    "为什么立遗嘱": ("把财产按自己的意愿分配、把话交代清楚，能大大减少子女日后的纠纷和麻烦，"
                "也是对自己一生的一个交代。趁神志清楚、身体还好，早安排早安心。",
                "立了遗嘱，将来按遗嘱来；不立则按法定继承，未必合你心意。"),
    "遗嘱形式": ("法律认可几种：自书遗嘱（自己亲笔写）、代书遗嘱（别人代写）、打印遗嘱、"
              "录音录像遗嘱、公证遗嘱、危急时的口头遗嘱。每种都有各自的要求，弄不对会无效。",
              "最稳妥的是公证遗嘱；拿不准就去公证处或问律师。"),
    "自书遗嘱": ("自己从头到尾'亲笔手写'全文、写清楚把哪些财产留给谁、最后'亲笔签名'、"
              "并写上'年、月、日'。三样缺一不可。",
              "⚠️ 自书遗嘱不能打印、不能让别人代写，必须本人手写，否则可能无效。"),
    "公证遗嘱": ("本人带身份证、财产证明到公证处，由公证员办理。手续规范、证据效力强、最不容易被推翻，"
              "是最稳妥的一种。",
              "行动不便可问公证处能否上门；费用不高，买个踏实值。"),
    "见证人": ("代书、打印、录音录像这几种遗嘱，需要'两个以上'见证人在场。"
            "见证人不能是继承人、受遗赠人，也不能是和他们有利害关系的人（如其配偶子女）。",
            "见证人选错了，遗嘱会无效——这点最容易栽跟头。"),
    "遗嘱内容": ("写清楚：①立遗嘱人姓名、身份证号等信息；②财产清单（房子、存款、物件等）；"
              "③每样留给谁、怎么分；④立遗嘱人亲笔签名 + 年月日。表达要明确、别含糊。",
              "只能处分'自己'那份合法财产；夫妻共同财产只能分自己一半。"),
    "注意事项": ("立遗嘱时本人要'神志清醒、完全自愿'，不能被胁迫诱骗；"
              "对没有劳动能力又没有生活来源的继承人，要保留必要的份额；"
              "立了多份内容冲突的，以'最后'那份为准（现在公证遗嘱不再天然优先）。",
              "立好后告诉一个信得过的人放在哪，免得将来找不到。"),
}

_ALIAS = {
    "为什么立遗嘱": "为什么立遗嘱", "为什么要立遗嘱": "为什么立遗嘱", "要立遗嘱吗": "为什么立遗嘱", "立遗嘱有用吗": "为什么立遗嘱",
    "遗嘱形式": "遗嘱形式", "遗嘱有几种": "遗嘱形式", "几种遗嘱": "遗嘱形式", "什么形式": "遗嘱形式",
    "自书遗嘱": "自书遗嘱", "自己写遗嘱": "自书遗嘱", "手写遗嘱": "自书遗嘱", "亲笔遗嘱": "自书遗嘱",
    "公证遗嘱": "公证遗嘱", "遗嘱公证": "公证遗嘱", "去公证": "公证遗嘱",
    "见证人": "见证人", "证人": "见证人", "找人见证": "见证人",
    "遗嘱内容": "遗嘱内容", "遗嘱怎么写": "遗嘱内容", "遗嘱写什么": "遗嘱内容", "遗嘱格式": "遗嘱内容",
    "注意事项": "注意事项", "立遗嘱注意": "注意事项", "遗嘱注意": "注意事项", "必要份额": "注意事项",
}

_TAIL = "（通用常识、非法律意见；立遗嘱关系重大，建议咨询律师或到公证处办，确保有效。）"


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("will_basics") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("say"):
                d[str(name)] = (str(v["say"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问遗嘱的哪一块（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某一块的说明 + 提醒 + 免责。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    say, tip = d[key]
    return f"{key}：{say}" + (f"（{tip}）" if tip else "") + _TAIL


def overview() -> str:
    """立遗嘱总纲。"""
    return ("立遗嘱大致这样：①想清楚财产怎么分；②选种形式（最稳是'公证遗嘱'，自己写的是'自书遗嘱'）；"
            "③自书要全文亲笔手写 + 签名 + 年月日，代书/打印要两个合格见证人；④写清财产和给谁；"
            "⑤告诉信得过的人放哪。" + _TAIL)


def is_will_query(utterance, config=None) -> bool:
    """是不是在问立遗嘱的事。"""
    u = str(utterance or "")
    if "遗嘱" in u:
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "有效", "形式", "见证", "公证", "份额")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
