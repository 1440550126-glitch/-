"""动物叫声：教小娃认动物——"小狗怎么叫？汪汪汪！"配一句小常识，逗趣又启蒙。
爷爷奶奶膝头逗孙子的开心事。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 动物 → (叫声, 一句小常识)
_ANIMALS = {
    "狗": ("汪汪汪", "看家护院的好帮手，对主人最忠诚。"),
    "猫": ("喵喵喵", "爱抓老鼠、爱干净，白天爱睡觉。"),
    "牛": ("哞——哞——", "帮农民伯伯耕地，力气可大了。"),
    "羊": ("咩咩咩", "吃青草、性子温顺，身上的毛能织毛衣。"),
    "鸡": ("公鸡喔喔喔、母鸡咯咯哒", "公鸡早上打鸣叫人起床，母鸡会下蛋。"),
    "鸭": ("嘎嘎嘎", "扁扁的嘴巴，会游泳，爱在水里玩。"),
    "鹅": ("嘎——嘎——", "脖子长长、走路高傲，会看门。"),
    "猪": ("哼哼哼", "爱吃爱睡、胖乎乎，其实很聪明。"),
    "马": ("咴儿——咴儿——", "跑得飞快，从前是人们出门的脚力。"),
    "青蛙": ("呱呱呱", "吃害虫的庄稼小卫士，会游泳会跳。"),
    "小鸟": ("叽叽喳喳", "会飞会唱歌，在树上搭窝。"),
    "老虎": ("嗷呜——", "森林之王，身上有花纹，威风极了。"),
    "狮子": ("吼——", "草原之王，公狮子有大鬃毛。"),
    "大象": ("吼——（长鼻子甩甩）", "陆地上最大的动物，鼻子能卷东西。"),
    "猴子": ("吱吱吱", "最爱爬树、爱吃桃子和香蕉，很机灵。"),
    "蜜蜂": ("嗡嗡嗡", "采花蜜、最勤劳，会跳舞告诉同伴花在哪。"),
    "知了": ("知了——知了——", "夏天在树上叫，又叫蝉。"),
    "老鼠": ("吱吱吱", "爱偷东西、最怕猫，牙齿一直长。"),
    "鸽子": ("咕咕咕", "象征和平，从前还能帮人送信。"),
    "鸭子": ("嘎嘎嘎", "扁嘴巴、会游泳，‘鸭’和‘鸭子’是一个。"),
}

_ALIAS = {"小狗": "狗", "小猫": "猫", "奶牛": "牛", "黄牛": "牛", "绵羊": "羊", "山羊": "羊",
          "公鸡": "鸡", "母鸡": "鸡", "小鸡": "鸡", "鸭子": "鸭", "大鹅": "鹅",
          "小猪": "猪", "白马": "马", "蛤蟆": "青蛙", "麻雀": "小鸟", "燕子": "小鸟",
          "老虎": "老虎", "猴儿": "猴子", "蜜蜂": "蜜蜂", "蝉": "知了", "耗子": "老鼠"}


def _table(config) -> dict:
    db = dict(_ANIMALS)
    if isinstance(config, dict) and isinstance(config.get("animal_sounds"), dict):
        for k, v in config["animal_sounds"].items():
            if isinstance(v, (list, tuple)) and v:
                db[str(k)] = (str(v[0]), str(v[1]) if len(v) > 1 else "")
    return db


def animals(config=None) -> list:
    return list(_table(config))


def find_animal(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for a in db:
        if a in u and len(a) > blen:
            best, blen = a, len(a)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def sound_of(query, config=None) -> str:
    """这动物怎么叫 + 一句小常识。认不出返回空。"""
    db = _table(config)
    a = query if query in db else find_animal(query, config)
    row = db.get(a)
    if not row:
        return ""
    sound, fact = row
    return f"{a}是这样叫的——{sound}！{fact}"


def is_sound_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_animal(u, config):
        return False
    return any(k in u for k in ("怎么叫", "怎样叫", "叫声", "怎么叫的", "咋叫", "叫起来"))
