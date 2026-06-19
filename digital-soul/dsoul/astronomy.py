"""认星空：夏夜纳凉抬头看天——北斗七星怎么找北极星、银河是啥、月食日食咋回事。
跟孙辈讲讲，也勾起自己小时候数星星的念想。大白话、好懂。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_SKY = {
    "北斗七星": "天上像个大勺子的七颗亮星，勺口前两颗星连线、朝勺口方向延长约五倍，就找到北极星了。",
    "北极星": "正北方那颗不太亮、却几乎不动的星。古人没指南针，夜里就靠它辨南北。",
    "银河": "无数颗恒星挤成的一条朦胧光带，夏天夜里最清楚；牛郎星和织女星就隔着它遥遥相望。",
    "八大行星": "按离太阳由近到远是：水星、金星、地球、火星、木星、土星、天王星、海王星；地球排第三。",
    "月食": "太阳、地球、月亮排成一条线、地球在中间，月亮走进地球的影子里，就变暗甚至发红（红月亮）。",
    "日食": "月亮转到太阳和地球中间，把太阳光挡住了，白天的太阳被‘咬’掉一块甚至全黑。",
    "流星": "小石块、尘粒冲进大气层，摩擦烧得发亮，划出一道光，老话叫‘贼星’；流星雨时一晚能看好多。",
    "彗星": "拖着长长尾巴的星，绕太阳转一圈要几十上百年，像哈雷彗星，七十多年才回来一次。",
    "太阳": "离我们最近的一颗恒星，自己会发光发热，地球和八大行星都绕着它转。",
    "月亮": "地球的卫星，自己不发光，是反射太阳的光；它绕地球转，就有了阴晴圆缺。",
    "织女星": "夏夜银河西边最亮的一颗，和东边的牛郎星隔河相望，是七夕传说里的织女。",
    "牛郎星": "银河东边的亮星，两边还有两颗小星，像牛郎挑着一双儿女追织女。",
}

_ALIAS = {"勺子星": "北斗七星", "大熊座": "北斗七星", "北斗": "北斗七星",
          "天河": "银河", "行星": "八大行星", "贼星": "流星", "扫帚星": "彗星",
          "哈雷彗星": "彗星", "红月亮": "月食", "天狗食日": "日食"}


def _table(config) -> dict:
    db = dict(_SKY)
    if isinstance(config, dict) and isinstance(config.get("astronomy"), dict):
        for k, v in config["astronomy"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def topics(config=None) -> list:
    return list(_table(config))


def find_topic(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for t in db:
        if t in u and len(t) > blen:
            best, blen = t, len(t)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    t = query if query in db else find_topic(query, config)
    s = db.get(t)
    return f"{t}：{s}" if s else ""


def is_astro_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("认星星", "看星空", "天上的星", "星空", "天文")):
        return True
    if find_topic(u, config) and any(k in u for k in ("是什么", "是啥", "咋回事", "怎么回事",
                                                      "怎么找", "怎么看", "介绍", "讲讲",
                                                      "为什么", "在哪")):
        return True
    return False
