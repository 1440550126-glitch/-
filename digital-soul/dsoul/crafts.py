"""传统手工艺：剪纸、刺绣、陶瓷、景泰蓝、年画、风筝……老手艺各有各的讲究和产地。
跟孙辈讲讲老祖宗的巧手，也勾起小时候的年味儿。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

_CRAFTS = {
    "剪纸": "一把剪刀、一张红纸，剪出花鸟人物；过年贴窗花最喜庆，北方尤其盛行。",
    "刺绣": "一针一线绣山水花鸟；四大名绣是苏绣、湘绣、蜀绣、粤绣，苏绣以精细雅洁著称。",
    "陶瓷": "景德镇瓷器天下闻名，青花、白瓷、玲珑瓷温润如玉，‘中国’的英文 China 也是瓷器。",
    "景泰蓝": "北京的特种工艺，铜胎上掐丝、填珐琅釉，以蓝色为主，富丽堂皇。",
    "年画": "过年贴的画，天津杨柳青、苏州桃花坞最有名，门神、胖娃娃、年年有余。",
    "风筝": "纸鸢飞上天，山东潍坊是‘风筝之都’，沙燕、龙头蜈蚣样样精巧。",
    "泥人": "天津‘泥人张’捏的小泥人活灵活现，无锡惠山泥人也很有名。",
    "紫砂壶": "江苏宜兴的紫砂，透气养茶，越用越润，是茶客的心头好。",
    "中国结": "一根红绳编出盘长结、如意结，寓意团圆吉祥、红红火火。",
    "皮影": "又叫灯影戏，牛羊皮刻成人物，幕布后头操纵着又唱又演。",
    "糖画": "用熬化的麦芽糖在石板上画龙画凤、画小动物，孩子最爱围着看。",
    "脸谱": "京剧脸谱用颜色和图案画出人物——红忠、黑直、白奸、金银神怪。",
}

_ALIAS = {"窗花": "剪纸", "苏绣": "刺绣", "湘绣": "刺绣", "蜀绣": "刺绣", "瓷器": "陶瓷",
          "青花瓷": "陶瓷", "杨柳青年画": "年画", "纸鸢": "风筝", "泥人张": "泥人",
          "宜兴紫砂": "紫砂壶", "糖人": "糖画", "京剧脸谱": "脸谱"}


def _table(config) -> dict:
    db = dict(_CRAFTS)
    if isinstance(config, dict) and isinstance(config.get("crafts"), dict):
        for k, v in config["crafts"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def crafts(config=None) -> list:
    return list(_table(config))


def find_craft(query, config=None) -> str:
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
    name = query if query in db else find_craft(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_craft_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("手工艺", "非遗", "传统工艺", "老手艺")):
        return True
    if find_craft(u, config) and any(k in u for k in ("是什么", "怎么做", "介绍", "讲讲",
                                                      "哪里的", "产地", "什么讲究", "啥样")):
        return True
    return False
