"""银行办事帮手：ATM 怎么取钱、卡丢了怎么挂失、忘了密码咋办、怎么转账才不被骗。
长辈办银行的事最容易紧张、也最容易被坑。一步步教清楚，再三叮嘱"密码谁也不给"。
纯逻辑、可单测。涉及钱的事，处处带防骗提醒（和 antifraud 一个心思）。
"""

from __future__ import annotations

# 事项 -> (一步步怎么办, 防骗/提醒)
_TOPICS = {
    "ATM取钱": ("①插银行卡（按箭头方向）；②输 6 位密码，用手挡着别人；③选'取款'，"
              "输入金额或选固定数额；④先取卡、再取钱，别忘了拿卡和凭条。",
              "周围有人凑近就停手；密码绝不告诉任何人，包括自称'银行/警察'的电话。"),
    "ATM存钱": ("①插卡输密码；②选'存款'，把钱理平整放进钞票口（别夹纸币、别放硬币）；"
              "③确认金额对不对、按确认；④存好取卡、拿凭条。",
              "只在正规银行的机器上存；机器吞钱别走开，当场打银行客服。"),
    "查余额": ("①ATM 插卡输密码选'查询'；②或用手机银行 App 登录就能看；"
             "③也可去柜台、拿身份证和卡查。",
             "短信/电话说你账户'异常、要核实'多半是骗局，挂掉、打卡背面官方电话。"),
    "银行卡挂失": ("①第一时间打发卡银行的客服电话（卡背面或官网那个）口头挂失、冻结；"
                "②再带身份证去柜台办正式挂失、补卡；③想想卡里钱、绑定的代扣要不要处理。",
                "只打卡背面的官方电话；别信路边小广告或来电给的'挂失专线'。"),
    "转账汇款": ("①核对收款人姓名、账号、开户行，一个字都不能错；②柜台/手机银行/ATM 都能转，"
               "金额大建议去柜台；③转完留好凭证。",
               "⚠️ 关键：但凡有人催你转账——'公检法''客服退款''孙子出事''稳赚理财'——"
               "九成是骗子！先挂电话，给家里人打个电话核实，别急着转。我也帮你把把关。"),
    "忘记密码": ("①密码忘了或输错锁了，别再猜；②带本人身份证和银行卡去柜台重置；"
               "③手机银行有的能验证身份后改密码。",
               "重置密码只能本人去柜台；任何'帮你改密码'要你报密码/验证码的都是骗子。"),
    "社保医保卡": ("①看病、买药在医院药店直接刷它结算；②查余额可在药店、自助机或手机上；"
                "③丢了打社保热线 12333 或去社保经办点挂失补办。",
                "社保卡密码也要保密；'医保卡可套现/激活'的电话别理，是诈骗。"),
    "大额取现": ("①取大额（比如 5 万以上）最好提前一天打电话或去柜台预约；②带好身份证；"
               "③柜员可能按规定问问钱的用途，如实说就行，是为了防诈骗保护你。",
               "如果是别人'指导'你取一大笔现金交给谁，立刻停手、报警 110，这是典型骗局。"),
}

_ALIAS = {
    "ATM取钱": "ATM取钱", "取钱": "ATM取钱", "取款": "ATM取钱", "自动取款机": "ATM取钱",
    "atm取钱": "ATM取钱", "取现金": "ATM取钱", "怎么取钱": "ATM取钱",
    "ATM存钱": "ATM存钱", "存钱": "ATM存钱", "存款": "ATM存钱",
    "查余额": "查余额", "查询余额": "查余额", "看余额": "查余额", "还剩多少钱": "查余额",
    "挂失": "银行卡挂失", "银行卡挂失": "银行卡挂失", "卡丢了": "银行卡挂失", "卡丢": "银行卡挂失",
    "银行卡丢": "银行卡挂失", "冻结卡": "银行卡挂失",
    "转账": "转账汇款", "汇款": "转账汇款", "转钱": "转账汇款", "打钱": "转账汇款",
    "忘记密码": "忘记密码", "忘了密码": "忘记密码", "密码忘了": "忘记密码", "密码锁了": "忘记密码",
    "社保卡": "社保医保卡", "医保卡": "社保医保卡", "社保": "社保医保卡", "医保": "社保医保卡",
    "大额取现": "大额取现", "取一大笔": "大额取现", "取很多钱": "大额取现", "预约取款": "大额取现",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("bank_help") if isinstance(config, dict) else None
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
    """认出办的哪件事（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(topic, config=None) -> str:
    """某件银行事怎么办（步骤 + 防骗提醒）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    steps, tip = d[key]
    return f"{key}：{steps}" + (f"（叮嘱：{tip}）" if tip else "")


def is_bank_query(utterance, config=None) -> bool:
    """是不是在问银行办事（认出事项 + 怎么办/不会 的意图）。"""
    u = str(utterance or "")
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "如何", "不会", "教教", "教我", "流程", "步骤",
                                "在哪办", "去哪办", "能不能", "可以吗"))


def count(config=None) -> int:
    return len(_all(config))
