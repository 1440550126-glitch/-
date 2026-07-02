"""动物小知识：熊猫爱吃竹子、猫头鹰夜里抓老鼠、蜜蜂会跳舞——逗小娃、长见识。
（叫声归 animal_sounds，这儿讲习性本领。）纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_FACTS = {
    "熊猫": "中国的国宝，最爱吃竹子，一天能吃十几个小时；黑白相间，憨态可掬。",
    "老虎": "森林之王，喜欢独来独往，会游泳；额头上的花纹像个‘王’字。",
    "大象": "陆地上最大的动物，长鼻子能卷水、卷食物、还能打招呼，记性特别好。",
    "长颈鹿": "脖子最长，专吃高处的树叶；它睡得很少，站着也能打盹。",
    "企鹅": "住在南极，不会飞却是游泳高手；帝企鹅是爸爸把蛋放脚上孵。",
    "袋鼠": "住在澳大利亚，妈妈肚子上有个育儿袋装宝宝，靠两条后腿蹦着走。",
    "海豚": "很聪明，用声音互相‘说话’，爱跃出水面，还会帮助落水的人。",
    "蚂蚁": "小小身体力气大，能搬动比自己重好多倍的东西，最讲团队合作。",
    "蜜蜂": "采花蜜酿蜂蜜，用‘跳舞’告诉同伴花在哪儿；一窝里只有一个蜂王。",
    "猫头鹰": "白天睡觉、夜里出动抓老鼠，脖子能转大半圈，眼睛在黑夜也看得清。",
    "蝙蝠": "唯一会飞的哺乳动物，靠发出超声波、听回声来辨路抓虫。",
    "变色龙": "能随环境变颜色，舌头又长又快，两只眼睛还能各看一个方向。",
    "乌龟": "很长寿，背上的硬壳能把头脚缩进去保护自己，走得慢吞吞。",
    "燕子": "春天飞来、秋天南去的候鸟，爱在屋檐下垒窝，专吃害虫，是益鸟。",
    "啄木鸟": "‘森林医生’，用尖嘴啄开树皮，把里头的虫子捉出来吃掉。",
    "蜘蛛": "结网捕虫，有八条腿（所以不是昆虫，昆虫是六条腿）。",
    "蚯蚓": "在土里钻来钻去帮着松土，是庄稼的好帮手；身子断了还能再长。",
    "萤火虫": "夏夜里一闪一闪会发光，那光来自它的尾巴，又叫‘流萤’。",
    "青蛙": "小时候是蝌蚪、长大才有腿；专吃蚊子苍蝇，是捉害虫的能手。",
    "蚕": "吃桑叶、吐丝结茧，丝能织成绸缎，‘春蚕到死丝方尽’。",
}

_ALIAS = {"大熊猫": "熊猫", "老虎大王": "老虎", "小燕子": "燕子", "蚕宝宝": "蚕",
          "猫头鹰夜": "猫头鹰"}


def _table(config) -> dict:
    db = dict(_FACTS)
    if isinstance(config, dict) and isinstance(config.get("animal_facts"), dict):
        for k, v in config["animal_facts"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def animals(config=None) -> list:
    return list(_table(config))


def find_animal(query, config=None) -> str:
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


def fact_of(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_animal(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_animal_fact_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_animal(u, config):
        return False
    return any(k in u for k in ("吃什么", "吃啥", "住哪", "住在哪", "有什么本领", "是什么动物",
                                "介绍", "讲讲", "小知识", "为什么", "怎么", "有什么", "厉害在"))
