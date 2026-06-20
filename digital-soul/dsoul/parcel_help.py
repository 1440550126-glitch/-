"""快递帮手：取件码在哪看、驿站怎么取、快递柜怎么开、寄快递咋弄、签收要不要验货。
现在网购多、快递杂，长辈常被取件码、扫码取件绕晕。一步步说明白，再带句防骗叮嘱。
纯逻辑、可单测。和 antifraud（假快递理赔骗局）互补，这里管正经怎么取怎么寄。
"""

from __future__ import annotations

# 事项 -> (怎么办, 提醒)
_TOPICS = {
    "驿站取件": ("①收到短信或 App 通知，里头有'取件码'（一串数字字母）；②去快递驿站/菜鸟驿站，"
              "把取件码报给店员、或在自助机扫码/输码；③核对包裹名字是你的，再拿走。",
              "取件码就是凭证，别随便给陌生人；包裹外的姓名电话最好撕掉再扔。"),
    "快递柜取件": ("①短信里有取件码和柜子地址；②到快递柜，在屏幕上点'取件'、输取件码（或扫码），"
                "对应的格子'啪'弹开，拿出包裹关好门。",
                "超时不取有的要收费，早点去；取完顺手关柜门。"),
    "寄快递": ("①手机上叫快递员上门，或自己去快递网点；②填清楚寄件人、收件人的名字、电话、地址；"
             "③东西打包结实（易碎的多塞点填充），称重付钱，留好运单号。",
             "别在包裹里寄现金、证件原件；填地址电话当心别被旁人记走。"),
    "签收验货": ("①贵重、易碎或货到付款的，当面打开看一眼再签；②东西不对、破损了，"
               "可以当场拒收、让快递员带回；③签收后发现问题，拍照联系卖家/客服。",
               "别因为'快递员催'就稀里糊涂签收付款；货到付款先确认是你买的东西。"),
    "查物流": ("①短信/快递 App 里直接看到哪了；②或打快递公司客服电话报运单号查；"
             "③太久没动静，联系卖家或快递客服问问。",
             "查物流用官方 App / 官方电话；'物流异常点链接处理'多半是钓鱼骗局，别点。"),
    "退换货寄回": ("①在购物 App 里申请退换货，按提示选退货原因；②按平台给的退货地址，"
                "把东西原样打包寄回（多数能上门取或到驿站寄）；③留好退货运单号，等退款。",
                "退款只在原购物 App 里走；客服加你微信、让你扫码/转账'办退款'的，是诈骗。"),
}

_ALIAS = {
    "驿站取件": "驿站取件", "驿站": "驿站取件", "菜鸟驿站": "驿站取件", "取件码": "驿站取件",
    "取快递": "驿站取件", "拿快递": "驿站取件",
    "快递柜取件": "快递柜取件", "快递柜": "快递柜取件", "丰巢": "快递柜取件", "柜子取件": "快递柜取件",
    "寄快递": "寄快递", "寄件": "寄快递", "寄东西": "寄快递", "邮寄": "寄快递", "发快递": "寄快递",
    "签收": "签收验货", "验货": "签收验货", "货到付款": "签收验货", "当面验": "签收验货",
    "查物流": "查物流", "查快递": "查物流", "到哪了": "查物流", "物流": "查物流", "运单号": "查物流",
    "退货": "退换货寄回", "退换货": "退换货寄回", "换货": "退换货寄回", "寄回去": "退换货寄回",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("parcel_help") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("steps"):
                d[str(name)] = (str(v["steps"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪件快递事（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(topic, config=None) -> str:
    """某件快递事怎么办（步骤 + 提醒）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    steps, tip = d[key]
    return f"{key}：{steps}" + (f"（提醒：{tip}）" if tip else "")


def is_parcel_query(utterance, config=None) -> bool:
    """是不是在问快递怎么取/寄（认出事项 + 怎么/在哪 的意图）。"""
    u = str(utterance or "")
    if "快递" not in u and not find_topic(u, config):
        return False
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "如何", "在哪", "不会", "教教", "教我",
                                "流程", "步骤", "要不要", "用不用", "吗", "要不要紧"))


def count(config=None) -> int:
    return len(_all(config))
