"""看天识天：老辈传下的天气谚语——朝霞不出门、燕子低飞要下雨、蚂蚁搬家蛇过道。
没有天气预报的年月，庄稼人就靠这些看云识天。逗趣又有智慧，跟孙辈讲讲也长见识。

纯数据 + 纯逻辑、可单测。可在 config 加自家乡的看天经验。
"""

from __future__ import annotations

# 征兆关键词 → (谚语, 意思)
_LORE = {
    "朝霞": ("朝霞不出门，晚霞行千里。", "早上满天红霞，多半要下雨；傍晚红霞，明天多半是晴天。"),
    "晚霞": ("朝霞不出门，晚霞行千里。", "傍晚的红霞，是明天好天气的兆头。"),
    "燕子低飞": ("燕子低飞要下雨。", "气压低，虫子飞得低，燕子追着虫子贴地飞——快下雨了。"),
    "蚂蚁搬家": ("蚂蚁搬家蛇过道，明天必有大雨到。", "小虫小兽都往高处躲，是大雨将至的信号。"),
    "蜻蜓低飞": ("蜻蜓低飞江湖畔，大雨即将来眼前。", "蜻蜓贴着水面低飞，多半要下雨。"),
    "月晕": ("月晕而风，础润而雨。", "月亮周围起了光晕要刮风；柱子石础返潮要下雨。"),
    "鱼鳞云": ("天上鱼鳞斑，晒谷不用翻。", "天上是鱼鳞状的云，多是晴好天气。"),
    "东虹": ("东虹日头西虹雨。", "彩虹在东边出太阳，在西边要下雨。"),
    "西虹": ("东虹日头西虹雨。", "虹在西边，是要下雨的兆头。"),
    "星稀": ("星星稀，落雨地；星星密，好天气。", "星星稀疏要下雨，繁密则是好天。"),
    "日落红": ("日落胭脂红，无雨便是风。", "太阳落山时红得像胭脂，不下雨也要刮风。"),
    "久晴大雾": ("久晴大雾必阴，久雨大雾必晴。", "晴久了起大雾要转阴，雨久了起大雾要放晴。"),
    "蛤蟆叫": ("蛤蟆大叫，大雨就到。", "蛙声一片叫得欢，多半要下雨。"),
}

_ALIAS = {"燕子飞得低": "燕子低飞", "蚂蚁搬": "蚂蚁搬家", "蜻蜓飞得低": "蜻蜓低飞",
          "月亮有晕": "月晕", "鱼鳞斑": "鱼鳞云", "晚霞红": "晚霞", "朝霞红": "朝霞"}


def _table(config) -> dict:
    db = dict(_LORE)
    if isinstance(config, dict) and isinstance(config.get("weather_lore"), dict):
        for k, v in config["weather_lore"].items():
            if isinstance(v, (list, tuple)) and v:
                db[str(k)] = (str(v[0]), str(v[1]) if len(v) > 1 else "")
    return db


def signs(config=None) -> list:
    return list(_table(config).keys())


def find_sign(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for k in db:
        if k in u and len(k) > blen:
            best, blen = k, len(k)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def lore_for(query, config=None) -> str:
    """看到某个征兆，给对应的谚语+意思。认不出返回空。"""
    sign = find_sign(query, config)
    row = _table(config).get(sign)
    if not row:
        return ""
    saying, meaning = row
    return f"{saying}（{meaning}）" if meaning else saying


def random_lore(seed="", config=None) -> str:
    db = list(_table(config).items())
    if not db:
        return ""
    _sign, (saying, meaning) = db[len(str(seed)) % len(db)]
    return f"{saying}（{meaning}）" if meaning else saying


# 只会是"看天"的征兆，单提就算（不像"晚霞/朝霞"可能是人名）
_STANDALONE = ("蚂蚁搬家", "蚂蚁搬", "燕子低飞", "燕子飞得低", "蜻蜓低飞", "蜻蜓飞得低",
               "鱼鳞云", "鱼鳞斑", "月晕", "月亮有晕", "久晴大雾", "蛤蟆大叫", "蛤蟆叫")


def is_weather_lore_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("天气谚语", "看天", "看云识天", "看天识天", "天气的老话",
                            "农谚")):
        return True
    if any(k in u for k in _STANDALONE):           # 这些铁定是在看天
        return True
    # 别的征兆（朝霞/晚霞/虹…）+ 在问要不要变天
    if find_sign(u, config) and any(k in u for k in ("要下雨", "要变天", "是不是要下",
                                                     "什么兆头", "啥兆头", "是要下雨吗",
                                                     "天气咋样", "会下雨", "兆头")):
        return True
    return False
