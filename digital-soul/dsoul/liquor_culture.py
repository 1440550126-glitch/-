"""酒文化：白酒几种香型、黄酒怎么喝、敬酒的讲究——聊聊桌上的酒，长长见识。
但话说前头：小酌怡情、过量伤身，上了年纪、吃着药、有基础病的，能不喝就不喝、别贪杯，更别酒驾。
纯逻辑、可单测。和"点菜请客"(dining_host 敬酒)、"服药常识"(吃药忌酒)接着用。
"""

from __future__ import annotations

_MODERATION = "（小酌怡情、过量伤身；吃药/有病别沾酒、头孢配酒可能致命；开车不喝、不强劝人。）"

# 主题 -> 介绍
_TOPICS = {
    "白酒香型": "白酒主要分几种香型：酱香型（如茅台，酱味浓厚、回味长）、浓香型（如五粮液、泸州老窖，窖香浓郁）、"
            "清香型（如汾酒，干净清爽）、米香型（如桂林三花，米香清雅）。香型不同，口感差别很大。",
    "名酒": "公认的名白酒有茅台、五粮液、泸州老窖、汾酒、西凤、洋河等;各有产地和香型。"
          "好酒重在品、不在多，浅尝即止。",
    "黄酒": "黄酒（如绍兴酒、女儿红）度数低、温着喝最好，冬天烫一壶、加点姜丝话梅，暖身;"
          "做菜也常用来去腥提香。度数低也别贪杯。",
    "敬酒": "桌上敬酒：主人先敬、长辈贵客优先;晚辈给长辈杯子端低些表尊敬;说句吉利话再喝;"
          "能喝多少量力，不会喝以茶代酒也行——好客不是劝酒，别硬劝。",
    "解酒": "⚠️ 别信'解酒药'、也别拿浓茶咖啡解酒（更刺激心脏）。真正醒酒靠时间 + 多喝温水 + 休息;"
          "喝多了别催吐（呛到危险）。最好的办法是当初就少喝。",
    "醉酒照护": "有人醉得厉害：让他'侧躺'别仰卧（防呕吐物呛到）、盖好保暖、有人守着别让独处;"
            "要是叫不醒、呼吸不规律、脸色发青，赶紧送医或打 120，别当睡着了。",
    "适量": "怎么算适量？越少越好、能不喝就不喝。世卫的说法是'没有所谓安全饮酒量';"
          "老人、肝胃不好、吃着药、血压高的，更要忌口。图个气氛抿一小口就行。",
}

_ALIAS = {
    "白酒香型": "白酒香型", "香型": "白酒香型", "酱香": "白酒香型", "浓香": "白酒香型", "清香": "白酒香型", "白酒区别": "白酒香型",
    "名酒": "名酒", "好酒": "名酒", "名白酒": "名酒", "茅台": "名酒", "五粮液": "名酒",
    "黄酒": "黄酒", "绍兴酒": "黄酒", "女儿红": "黄酒",
    "敬酒": "敬酒", "敬酒词": "敬酒", "劝酒": "敬酒", "怎么敬酒": "敬酒",
    "解酒": "解酒", "醒酒": "解酒", "解酒药": "解酒", "喝多了": "解酒",
    "醉酒照护": "醉酒照护", "喝醉了": "醉酒照护", "醉了怎么办": "醉酒照护", "醉酒": "醉酒照护",
    "适量": "适量", "喝多少": "适量", "适量饮酒": "适量", "喝多少合适": "适量",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("liquor_culture") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问酒的哪一块（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for word in list(_all(config)) + list(_ALIAS):
        if word and word in u and len(word) > best_len:
            best, best_len = _ALIAS.get(word, word), len(word)
    return best


def info(topic, config=None) -> str:
    """某一块介绍 + 节制提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    return f"{key}：{d[key]}{_MODERATION}"


def overview() -> str:
    """酒文化总览（带节制提醒）。"""
    return ("聊酒：白酒分酱香/浓香/清香/米香几种香型，名酒有茅台五粮液汾酒等;黄酒温着喝;"
            "敬酒讲长幼、不强劝;解酒靠的是少喝 + 多水 + 休息。" + _MODERATION)


def is_liquor_query(utterance, config=None) -> bool:
    """是不是在聊酒文化。"""
    u = str(utterance or "")
    if any(k in u for k in ("白酒", "黄酒", "酒文化", "香型", "什么酒")):
        return True
    if find_topic(u, config) and any(k in u for k in ("是什么", "区别", "怎么", "讲究", "怎么办",
                                                      "哪种", "啥意思", "怎么喝", "多少")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
