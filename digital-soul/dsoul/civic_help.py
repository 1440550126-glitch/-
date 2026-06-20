"""办事指南：办身份证、社保卡、敬老卡、医保异地备案……去哪办、带什么、注意啥。
长辈办证最怵跑冤枉路、被"代办"忽悠。这一块说个大方向，少折腾。纯逻辑、可单测。

⚠️ 各地流程、材料略有不同；办之前打当地政务热线 12345 问清楚、或在政务 App/小程序上看，
最准。别信路边"花钱包办"的代办，多是坑。
"""

from __future__ import annotations

# 事项 -> (去哪办 + 带什么, 提醒)
_MATTERS = {
    "身份证": ("到户籍所在地派出所，或开通'异地受理'的派出所/政务大厅办；带户口本，现场拍照采集；"
             "丢了先在'国家政务服务平台'或派出所挂失、再补办。",
             "急用可办'临时身份证'；快递到家或自取都行。"),
    "户口本": ("到户籍所在地派出所户籍窗口办理（新立、迁移、补办、信息变更）；带身份证等相关材料。",
             "迁户口、改信息材料多，先打电话问清要带啥再去。"),
    "社保卡": ("到合作银行网点或社保经办点新办/换卡；带身份证（代办再加代办人身份证和委托）。",
             "现在多是'社保卡'和'医保'合一；线上可在'电子社保卡'小程序领电子版。"),
    "敬老卡": ("到了年纪（多数地方满 60 或 65 岁）凭身份证到公交公司、政务大厅或社区办；",
             "办了能免费或优惠坐公交、逛公园，具体年龄和优惠看当地。"),
    "医保异地": ("跨省看病前，先在'国家医保服务平台'App 或参保地经办点做'异地就医备案'，再到联网医院刷卡结算。",
              "没备案可能不能直接报销；提前一两天办好。"),
    "护照": ("本人到出入境管理局/政务大厅办，带身份证、现场拍照、按指纹；",
           "本人必须到场；出国前留意有效期，过期或不足半年要换。"),
    "残疾证": ("到户籍地残联申请，按要求到指定医院做残疾鉴定，再办证；带身份证、病历、照片。",
            "办下来能享受相关补贴和优惠，材料找残联问清楚。"),
    "房产证": ("买卖、继承、过户到当地不动产登记中心办；带身份证、合同、原证等。",
            "继承、过户材料复杂，可先在政务 App 预约、问清材料清单。"),
    "结婚登记": ("男女双方到一方户籍地（部分地区已可异地）婚姻登记处，带身份证、户口本、各自照片。",
             "现在多地能网上预约；离婚登记有冷静期。"),
}

_ALIAS = {
    "身份证": "身份证", "办身份证": "身份证", "补身份证": "身份证", "换身份证": "身份证", "身份证丢了": "身份证",
    "户口本": "户口本", "户口": "户口本", "迁户口": "户口本", "落户": "户口本",
    "社保卡": "社保卡", "办社保卡": "社保卡", "换社保卡": "社保卡", "社保": "社保卡",
    "敬老卡": "敬老卡", "老年卡": "敬老卡", "老人卡": "敬老卡", "老年证": "敬老卡",
    "医保异地": "医保异地", "异地就医": "医保异地", "异地报销": "医保异地", "医保备案": "医保异地",
    "护照": "护照", "办护照": "护照", "出国证件": "护照",
    "残疾证": "残疾证", "办残疾证": "残疾证",
    "房产证": "房产证", "不动产证": "房产证", "房本": "房产证", "过户": "房产证",
    "结婚登记": "结婚登记", "领结婚证": "结婚登记", "办结婚证": "结婚登记", "结婚证": "结婚登记",
}

_TAIL = "（各地材料/流程不同，办前打 12345 政务热线或上政务 App 问清楚最稳；别信花钱'包办'的代办。）"


def _all(config=None) -> dict:
    d = dict(_MATTERS)
    cfg = (config or {}).get("civic_help") if isinstance(config, dict) else None
    extra = (cfg or {}).get("matters") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("where"):
                d[str(name)] = (str(v["where"]), str(v.get("tip", "")))
    return d


def matters(config=None) -> list:
    return list(_all(config).keys())


def find_matter(utterance, config=None):
    """认出办的哪件事（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(matter, config=None) -> str:
    """某件事去哪办、带什么（含通用提醒）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(matter or ""), str(matter or ""))
    if key not in d:
        return ""
    where, tip = d[key]
    return f"办{key}：{where}" + (f"（{tip}）" if tip else "") + _TAIL


def is_civic_query(utterance, config=None) -> bool:
    """是不是在问怎么办证/办事（认出事项 + 怎么办/在哪办/要带啥 的意图）。"""
    u = str(utterance or "")
    if not find_matter(u, config):
        return False
    return any(k in u for k in ("怎么办", "在哪办", "去哪办", "咋办", "怎么补", "怎么换", "怎么领",
                                "要带", "带什么", "带啥", "需要什么", "流程", "上哪办", "怎么弄",
                                "怎么报销", "怎么备案", "报销", "备案"))


def count(config=None) -> int:
    return len(_all(config))
