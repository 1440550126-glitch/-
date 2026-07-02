"""童谣：哄孙辈、逗小孩念的传统儿歌——小老鼠上灯台、拉大锯、小兔子乖乖。
一辈辈口口相传的调子，爷爷奶奶嘴边都有。给孩子念念，屋里就热闹了。

只收传唱已久的传统童谣。纯数据 + 纯逻辑、可单测。可在 config 加自家的。
"""

from __future__ import annotations

_RHYMES = {
    "小老鼠上灯台": "小老鼠，上灯台，偷油吃，下不来，喵喵喵，猫来了，叽里咕噜滚下来。",
    "拉大锯": "拉大锯，扯大锯，姥姥家，唱大戏，接闺女，请女婿，小外孙子也要去。",
    "摇到外婆桥": "摇啊摇，摇啊摇，摇到外婆桥，外婆叫我好宝宝，糖一包，果一包。",
    "小兔子乖乖": "小兔子乖乖，把门儿开开，快点开开，我要进来；不开不开我不开，妈妈没回来，谁来也不开。",
    "拔萝卜": "拔萝卜，拔萝卜，嘿哟嘿哟拔萝卜，嘿哟嘿哟拔不动；老太婆，快快来，快来帮我们拔萝卜。",
    "两只老虎": "两只老虎，两只老虎，跑得快，跑得快；一只没有耳朵，一只没有尾巴，真奇怪，真奇怪。",
    "丢手绢": "丢手绢，丢手绢，轻轻地放在小朋友的后面，大家不要告诉他，快点快点抓住他。",
    "找朋友": "找呀找呀找朋友，找到一个好朋友，敬个礼，握握手，你是我的好朋友。",
    "数蛤蟆": "一只蛤蟆一张嘴，两只眼睛四条腿，扑通一声跳下水。",
    "排排坐": "排排坐，吃果果，你一个，我一个，宝宝不在留一个。",
    "小白兔": "小白兔，白又白，两只耳朵竖起来，爱吃萝卜爱吃菜，蹦蹦跳跳真可爱。",
    "虫虫飞": "虫虫虫虫飞，飞到南山喝露水，露水喝不到，回来吃青草。",
}

_ALIAS = {"上灯台": "小老鼠上灯台", "小老鼠": "小老鼠上灯台", "外婆桥": "摇到外婆桥",
          "乖乖": "小兔子乖乖", "拔萝卜歌": "拔萝卜"}


def _table(config) -> dict:
    db = dict(_RHYMES)
    if isinstance(config, dict) and isinstance(config.get("nursery_rhymes"), dict):
        for k, v in config["nursery_rhymes"].items():
            if str(v).strip():
                db[str(k).strip()] = str(v).strip()
    return db


def rhymes(config=None) -> list:
    return list(_table(config).keys())


def find(query, config=None) -> str:
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


def get(name, config=None) -> str:
    """念某首童谣。认不出返回空。"""
    db = _table(config)
    key = name if name in db else find(name, config)
    text = db.get(key)
    return f"《{key}》：{text}" if text else ""


def random_rhyme(seed="", config=None) -> str:
    db = list(_table(config).items())
    if not db:
        return ""
    name, text = db[len(str(seed)) % len(db)]
    return f"《{name}》：{text}"


def is_rhyme_request(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("童谣", "儿歌", "念个儿歌", "哄孩子念", "给孩子念")):
        return True
    if find(u, config) and any(k in u for k in ("念", "来个", "来一首", "怎么念", "教", "唱")):
        return True
    return False
