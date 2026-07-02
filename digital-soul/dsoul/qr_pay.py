"""付款码 / 收款码安全：手机扫码付钱方便，可付款码和收款码最容易搞混、也最容易被骗。
讲清楚哪个是花钱、哪个是收钱、怎么设置更安全、丢了手机怎么办、遇到哪些套路是骗局。
纯逻辑、可单测。和"手机帮手"(phone_help)、"防诈骗"(antifraud)接着用。

⚠️ 一句记牢：付款码（那串数字/条码）就是钱，绝不发给、念给任何人！
"""

from __future__ import annotations

_TOPICS = {
    "付款码": ("付款码是'给商家扫'来付钱的条码 + 二维码（数字每分钟在变）。在收银台打开'付款码'，"
            "给收银员扫一下就付了。",
            "⚠️ 千万别主动把付款码截图、拍照、发给别人，也别把那串数字念给任何人——等于把钱送出去！"),
    "收款码": ("收款码是'你收钱用'的，可以打印贴出来、或发给对方，让别人扫你的码、把钱付给你。",
            "收款码可以给别人;但别把'付款码'当收款码发出去（最常见的栽法）。"),
    "区别": ("一句话分清：付款码=你花钱（给别人扫你）;收款码=你收钱（你扫别人或别人扫你收）。"
           "要付钱时打开'付款码'给商家扫;要收钱时给对方看'收款码'。",
           "搞混了，本想收钱却把付款码给人，钱就被扫走了——记牢这条。"),
    "安全设置": ("设好'支付密码'，开指纹或刷脸;'小额免密'按需谨慎使用（图方便但风险高，可关掉）;"
             "付款码用完就关掉、别一直亮着;别在手机上存银行卡密码。",
             "钱包里别放太多，常用账户和大额存款分开，丢了损失小。"),
    "丢手机": ("立刻：①用另一台设备或打客服'挂失冻结'微信/支付宝/银行卡支付;②改支付密码、登录密码;"
            "③给运营商挂失手机卡（防短信验证码被利用）;④必要时报警。",
            "提前记下各家客服电话、开启'手机找回'，关键时刻不抓瞎。"),
    "扫码防骗": ("陌生的二维码别乱扫;'扫码领红包/补贴/退款/做任务赚钱'多是骗局;"
             "有人借口让你'扫他的码'或'报付款码数字'，十有八九是骗钱，立刻停手。",
             "记住：正经收钱不需要你的付款码数字;一让你念付款码、扫陌生码，就是危险信号。"),
}

_ALIAS = {
    "付款码": "付款码", "付款二维码": "付款码", "怎么付款": "付款码",
    "收款码": "收款码", "收钱码": "收款码", "收款二维码": "收款码",
    "区别": "区别", "付款码和收款码": "区别", "有什么区别": "区别", "怎么分": "区别",
    "安全设置": "安全设置", "支付安全": "安全设置", "小额免密": "安全设置", "支付密码": "安全设置",
    "丢手机": "丢手机", "手机丢了": "丢手机", "手机被偷": "丢手机",
    "扫码防骗": "扫码防骗", "扫码安全": "扫码防骗", "陌生二维码": "扫码防骗", "扫码领红包": "扫码防骗",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("qr_pay") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("warn", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪一块（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某一块怎么做 + 警示。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, warn = d[key]
    return f"{key}：{how}" + (f" {warn}" if warn else "")


def overview() -> str:
    """付款码收款码总览。"""
    return ("手机扫码付钱记牢：付款码=你花钱（给别人扫你，那串数字就是钱、绝不发给念给别人）;"
            "收款码=你收钱（让别人扫你的码）。设好支付密码;丢手机马上挂失冻结;"
            "陌生码别扫、'扫码领红包/报付款码数字'都是骗局。")


def is_qr_query(utterance, config=None) -> bool:
    """是不是在问付款码/收款码/扫码支付。"""
    u = str(utterance or "")
    if any(k in u for k in ("付款码", "收款码", "收钱码", "扫码付", "扫码支付")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "区别", "安全", "是什么", "咋",
                                                      "怎么办", "丢了", "被偷", "防骗")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
