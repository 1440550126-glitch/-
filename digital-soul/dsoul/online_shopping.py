"""网购帮手：怎么挑东西、怎么看评价、怎么下单付款、怎么退货、怎么不被坑。
长辈学网购，最怕买到假货、付错钱、退不了。这一块一步步教，再三叮嘱"太便宜的别贪、
客服让加微信扫码退款的别理"。纯逻辑、可单测。和"快递"(parcel_help)、"防骗"(antifraud)接着用。
"""

from __future__ import annotations

# 环节 -> (怎么做, 提醒)
_TOPICS = {
    "挑商品": ("①在购物 App 搜你要的东西（说得具体点，如'老人手机 大字 大声'）；②看销量高、评分好的；"
             "③点进去看主图、详情、参数；④货比三家，别只看一个。",
             "贵得离谱、便宜得离谱都要当心；认准正规店铺、旗舰店更稳。"),
    "看评价": ("①往下翻'评价'，重点看中评差评说了啥问题；②多看'带图'的真实买家秀；"
             "③同样的好评一模一样、堆一块，多半是刷的，别全信。",
             "差评里说的毛病，正是你要不要买的关键。"),
    "下单付款": ("①选好规格（颜色、尺码、数量）点'加入购物车'或'立即购买'；②填收货地址、电话；"
               "③确认订单金额，选付款方式付钱；④拿不准就选'货到付款'，验完货再给钱最稳。",
               "付款只在 App 内完成；别脱离平台、别按陌生人指点转账。"),
    "用优惠": ("①领店铺优惠券、平台满减再下单更便宜；②比价小心'先涨后降'的假优惠；"
             "③别为了'凑满减'买一堆用不上的。",
             "优惠是省钱的，不是让你多花的——按需买。"),
    "收货验货": ("①快递到了对照订单看是不是你买的；②贵重、易碎当面拆验，不对可拒收；"
               "③确认无误再在 App 点'确认收货'，钱才打给卖家。",
               "没验货别急着点'确认收货'；点了再退就麻烦。"),
    "退换货": ("①多数支持'7 天无理由'：在订单里点'退货/退款'，选原因，按提示寄回；"
             "②生鲜、定制、贴身的可能不支持，先看清；③退款会原路退回付款账户。",
             "退款只在购物 App 里走！客服加你微信、让你扫码/输验证码'办退款'的，是诈骗。"),
    "防坑": ("①陌生短信、链接里的'超低价/中奖/砍一刀'别乱点；②直播间别被'最后一单'冲动带货；"
            "③'定金不退''尾款翻倍'的套路看清规则再下手。",
            "记住：占大便宜的多半是陷阱；拿不准就问我、问孩子，别急着付钱。"),
}

_ALIAS = {
    "挑商品": "挑商品", "怎么挑": "挑商品", "怎么搜": "挑商品", "搜东西": "挑商品", "选商品": "挑商品", "买什么好": "挑商品",
    "看评价": "看评价", "评价": "看评价", "评论": "看评价", "买家秀": "看评价", "差评": "看评价",
    "下单": "下单付款", "下单付款": "下单付款", "怎么买": "下单付款", "怎么付款": "下单付款", "怎么下单": "下单付款", "付钱": "下单付款",
    "优惠": "用优惠", "优惠券": "用优惠", "满减": "用优惠", "凑单": "用优惠", "便宜点": "用优惠",
    "收货": "收货验货", "验货": "收货验货", "确认收货": "收货验货",
    "退货": "退换货", "退换货": "退换货", "退款": "退换货", "换货": "退换货", "七天无理由": "退换货", "7天无理由": "退换货",
    "防坑": "防坑", "网购被骗": "防坑", "假货": "防坑", "砍一刀": "防坑", "直播带货": "防坑",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("online_shopping") if isinstance(config, dict) else None
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
    """认出问的哪个网购环节（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(topic, config=None) -> str:
    """某个网购环节怎么弄（步骤 + 提醒）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    steps, tip = d[key]
    return f"网购·{key}：{steps}" + (f"（提醒：{tip}）" if tip else "")


def general() -> str:
    """没指明环节时，给个网购入门 + 防坑总纲。"""
    return ("网购大致这么走：搜东西→看销量评价→选规格下单→填地址付款（拿不准选货到付款）→"
            "收货当面验→有问题在 App 里退换。一句要紧的：太便宜的别贪、客服让加微信扫码退款的别理，"
            "拿不准就问我或问孩子。")


def is_shopping_query(utterance, config=None) -> bool:
    """是不是在问网购怎么弄。"""
    u = str(utterance or "")
    has = any(k in u for k in ("网购", "网上买", "淘宝", "网店", "购物 App", "购物app", "网上购物")) \
        or find_topic(u, config) is not None
    if not has:
        return False
    return any(k in u for k in ("怎么", "咋", "如何", "不会", "教教", "教我", "流程", "步骤",
                                "要注意", "靠谱吗", "安全吗", "会不会被骗"))


def count(config=None) -> int:
    return len(_all(config))
