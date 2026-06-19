"""名山大川 / 名胜古迹：泰山、长城、故宫、长江黄河……各在哪儿、有啥说道。
跟孙辈讲讲祖国的大好河山，也勾起想去看看的念想。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_LANDMARKS = {
    "泰山": "五岳之首（东岳），在山东，自古帝王封禅之地，‘会当凌绝顶，一览众山小’。",
    "华山": "五岳中的西岳，在陕西，以险著称，‘自古华山一条路’，有长空栈道。",
    "衡山": "五岳中的南岳，在湖南，以‘秀’闻名，又称寿岳。",
    "恒山": "五岳中的北岳，在山西，悬空寺挂在峭壁上最为奇绝。",
    "嵩山": "五岳中的中岳，在河南，少林寺就在这儿，禅宗与武术圣地。",
    "黄山": "在安徽，以奇松、怪石、云海、温泉‘四绝’闻名，‘五岳归来不看山，黄山归来不看岳’。",
    "长城": "万里长城，东起山海关西到嘉峪关，古代军事防线，世界奇迹，‘不到长城非好汉’。",
    "故宫": "又叫紫禁城，在北京，明清两代的皇宫，世界上现存最大的木结构宫殿群。",
    "长江": "中国第一长河，发源于青藏高原，奔流入海，三峡风光壮丽。",
    "黄河": "中华民族的母亲河，九曲十八弯，壶口瀑布最为雄壮，孕育了华夏文明。",
    "桂林山水": "在广西，‘桂林山水甲天下’，漓江两岸群峰倒影，如诗如画。",
    "西湖": "在杭州，‘上有天堂，下有苏杭’，断桥残雪、苏堤春晓，许仙白娘子的传说在这儿。",
    "兵马俑": "在西安，秦始皇陵的陪葬，千人千面、气势恢宏，被誉为‘世界第八大奇迹’。",
    "布达拉宫": "在西藏拉萨，依山而建，是世界屋脊上的明珠、藏传佛教圣地。",
    "莫高窟": "在甘肃敦煌，又叫千佛洞，壁画彩塑精美，是佛教艺术的宝库。",
    "黄鹤楼": "在武汉，江南三大名楼之一，崔颢一首‘昔人已乘黄鹤去’名垂千古。",
    "岳阳楼": "在湖南，范仲淹《岳阳楼记》‘先天下之忧而忧’传诵千年。",
    "滕王阁": "在江西南昌，王勃《滕王阁序》‘落霞与孤鹜齐飞’名动天下。",
}

_ALIAS = {"东岳": "泰山", "西岳": "华山", "南岳": "衡山", "北岳": "恒山", "中岳": "嵩山",
          "万里长城": "长城", "紫禁城": "故宫", "漓江": "桂林山水", "秦始皇陵": "兵马俑",
          "千佛洞": "莫高窟", "敦煌": "莫高窟"}

_FAMOUS_TOWERS = ("黄鹤楼", "岳阳楼", "滕王阁")


def landmarks(config=None) -> list:
    db = dict(_LANDMARKS)
    if isinstance(config, dict) and isinstance(config.get("landmarks"), dict):
        db.update(config["landmarks"])
    return list(db)


def _table(config) -> dict:
    db = dict(_LANDMARKS)
    if isinstance(config, dict) and isinstance(config.get("landmarks"), dict):
        for k, v in config["landmarks"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def find_landmark(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_landmark(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def five_mountains() -> str:
    return "五岳是：东岳泰山、西岳华山、南岳衡山、北岳恒山、中岳嵩山。"


def is_landmark_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("五岳", "四大名楼", "名山大川", "名胜古迹")):
        return True
    if find_landmark(u, config) and any(k in u for k in ("在哪", "是什么", "介绍", "讲讲",
                                                         "有什么", "怎么样", "在哪儿", "哪个省")):
        return True
    return False
