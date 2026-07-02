"""养花知识：屋里那几盆花草该怎么伺候——绿萝多浇会烂根、多肉宁干勿湿、君子兰怕积水。
养花是老人顶舒心的事，分身懂点门道，能搭把手。（按几天浇水提醒的是 plant_care，这儿讲养护。）

纯数据 + 纯逻辑、可单测。常见家养花草的养护要点，可在 config 加。
"""

from __future__ import annotations

# 花草 → 养护要点
_CARE = {
    "绿萝": "喜阴耐阴，放散光处就行，别暴晒。土面干了再浇透；叶子发黄多半是浇多了，少浇点。",
    "多肉": "喜光、少水，宁干勿湿。一两周浇一次、浇透，盆土要透气；徒长就是光不够，多晒太阳。",
    "君子兰": "喜散射光，土干透了再浇透，最怕积水烂根。两年换次盆，叶子定期擦灰。",
    "茉莉": "喜光喜肥，夏天几乎天天浇、见干见湿，多晒才开花香；用偏酸的土，薄肥勤施。",
    "月季": "要充足光照，勤剪残花和病枝；薄肥勤施，注意防蚜虫、白粉病。",
    "吊兰": "好养，喜湿润和散光，土面干就浇。叶尖发干是太干或水质硬，多喷喷水。",
    "仙人掌": "极耐旱，半个月浇一次都行，宁可忘了浇也别多浇；要充足阳光。",
    "发财树": "最怕涝，半个多月浇一次、浇透就行。叶子发黄发软，八成是水浇多了。",
    "富贵竹": "水养要勤换水（三五天一次），加几滴营养液，避开阳光直射，根须烂了要剪掉。",
    "兰花": "喜通风和散射光，用专门的兰石/植料，见干浇水、忌积水，怕闷、怕晒。",
    "蟹爪兰": "短日照才容易开花，花期别老搬动。土干了再浇，夏天注意遮阴通风。",
    "栀子花": "喜酸性土和充足光照，缺铁叶子会发黄，浇点硫酸亚铁；空气干就多喷水。",
    "长寿花": "喜光耐旱，少浇水，花谢了及时剪掉；想多开花要保证日照。",
    "文竹": "喜湿润散光，最怕干和强光，叶子发黄发干就是太干太晒了，常喷水。",
}

_ALIAS = {"绿箩": "绿萝", "肉肉": "多肉", "多肉植物": "多肉", "金桔": "月季",
          "蟹爪": "蟹爪兰", "栀子": "栀子花"}


def _table(config) -> dict:
    db = dict(_CARE)
    if isinstance(config, dict) and isinstance(config.get("gardening"), dict):
        for k, v in config["gardening"].items():
            if str(v).strip():
                db[str(k).strip()] = str(v).strip()
    return db


def plants(config=None) -> list:
    return list(_table(config).keys())


def find_plant(query, config=None) -> str:
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


def care_for(query, config=None) -> str:
    """这盆花怎么养。认不出返回空。"""
    db = _table(config)
    name = query if query in db else find_plant(query, config)
    tip = db.get(name)
    return f"{name}：{tip}" if tip else ""


def is_gardening_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if "养花" in u or "花草怎么" in u:
        return True
    if find_plant(u, config) and any(k in u for k in ("怎么养", "咋养", "怎么浇", "浇多少",
                                                      "养护", "怎么伺候", "好养吗", "怎么照顾",
                                                      "黄了", "蔫了", "烂根", "不开花")):
        return True
    return False
