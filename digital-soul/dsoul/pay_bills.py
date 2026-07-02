"""缴费帮手：水电燃气、物业话费宽带——在哪交、怎么交、怎么查欠费，别让停水停电吓一跳。
长辈怕忘了交、又怕网上操作错。这一块说清楚线上线下都怎么弄，再叮嘱一句别点短信里的链接。
纯逻辑、可单测。和"记账"(household_ledger)、"家务板"(family_board)各管一摊。
"""

from __future__ import annotations

# 通用线上/线下两条路
_ONLINE = ("线上：微信→'我'→'服务/钱包'→'生活缴费'，或支付宝→'生活缴费'，"
           "或你家银行的手机 App，选对项目、输户号、确认金额就能交。")
_OFFLINE = ("线下：去对应的营业厅、银行柜台/自助机，有的便利店、社区代收点也能交，带上户号或上次的缴费单。")

# 缴费项目 -> (在哪交/要啥, 提醒)
_BILLS = {
    "电费": ("国家电网'网上国网'App、微信/支付宝生活缴费，或供电营业厅；要'用户编号'(电费单上有)。",
            "智能电表余额低会停电，余额不多就提前充。"),
    "水费": ("当地自来水公司 App/公众号、微信支付宝生活缴费，或水司营业厅；要'用户号'。",
            "水表箱里有户号，或看上一张水费单。"),
    "燃气费": ("燃气公司公众号/App、微信支付宝生活缴费，或燃气营业厅；要'燃气户号'。",
             "插卡式燃气表要去买气充卡；余额低及时充，别半夜断气。"),
    "物业费": ("物业公司的小程序/公众号，或直接去物业办公室交，现金、刷卡、扫码都行。",
             "交完留好收据，按年交有的有优惠。"),
    "话费": ("运营商 App(如'中国移动/联通/电信')、微信支付宝充值，或营业厅、便利店充值卡。",
            "余额不足会停机，可设置自动充值或到点提醒。"),
    "宽带费": ("装宽带那家运营商的 App/营业厅续费；常和手机套餐绑在一起。",
             "到期前续，断了要重新报装就麻烦了。"),
    "有线电视费": ("广电营业厅、对应公众号/App，或自助机；要'数字电视用户号'。",
                "欠费会停信号、电视没台，按年交省事。"),
    "暖气费": ("供热公司营业厅、对应公众号/App，每年采暖季前缴；要'用热户号'。",
             "北方采暖季前一定交齐，不然不给供暖。"),
}

_ALIAS = {
    "电费": "电费", "交电费": "电费", "电卡": "电费",
    "水费": "水费", "交水费": "水费",
    "燃气费": "燃气费", "煤气费": "燃气费", "天然气费": "燃气费", "气费": "燃气费", "买气": "燃气费",
    "物业费": "物业费", "物业管理费": "物业费",
    "话费": "话费", "手机费": "话费", "电话费": "话费", "充话费": "话费",
    "宽带费": "宽带费", "宽带": "宽带费", "网费": "宽带费",
    "有线电视费": "有线电视费", "电视费": "有线电视费", "数字电视费": "有线电视费",
    "暖气费": "暖气费", "采暖费": "暖气费", "供暖费": "暖气费",
}


def _all(config=None) -> dict:
    d = dict(_BILLS)
    cfg = (config or {}).get("pay_bills") if isinstance(config, dict) else None
    extra = (cfg or {}).get("bills") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("where"):
                d[str(name)] = (str(v["where"]), str(v.get("tip", "")))
    return d


def bills(config=None) -> list:
    return list(_all(config).keys())


def find_bill(utterance, config=None):
    """认出要交哪种费（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(bill, config=None) -> str:
    """某种费怎么交（哪交 + 提醒 + 通用线上线下 + 防骗）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(bill or ""), str(bill or ""))
    if key not in d:
        return ""
    where, tip = d[key]
    return (f"交{key}：{where}" + (f"（{tip}）" if tip else "") +
            f" {_ONLINE} {_OFFLINE}"
            "（叮嘱：只在官方 App / 正规渠道交，别点短信里'欠费停电'的链接，那多是骗局。）")


def general() -> str:
    """没指明哪种费时，给个通用怎么交。"""
    return ("交水电燃气这些费，两条路：" + _ONLINE + " " + _OFFLINE +
            " 交之前备好'户号'（在缴费单或表箱上）。"
            "（只走官方渠道，短信里的缴费链接别点。）")


def is_pay_query(utterance, config=None) -> bool:
    """是不是在问怎么交费（认出费种或'缴费' + 怎么交/在哪交 的意图）。"""
    u = str(utterance or "")
    has = find_bill(u, config) is not None or any(k in u for k in ("缴费", "交费"))
    if not has:
        return False
    return any(k in u for k in ("怎么交", "在哪交", "怎么缴", "去哪交", "咋交", "怎么充",
                                "网上交", "手机交", "怎么查", "欠费", "怎么办", "教教", "教我",
                                "怎么弄", "咋弄"))


def count(config=None) -> int:
    return len(_all(config))
