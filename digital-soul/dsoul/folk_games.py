"""老游戏：踢毽子、跳皮筋、滚铁环、抖空竹……老一辈小时候玩的，教给孙辈，热闹又怀旧。
没有手机的年月，一根绳、一把石子就能玩一下午。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_GAMES = {
    "踢毽子": "用脚内侧、外侧、脚尖把毽子颠起来，比谁踢得多、花样多；‘盘踢、磕、拐、绷’样样来。",
    "跳皮筋": "两人撑住橡皮筋，从脚踝一节节往上升，边跳边唱‘小皮球，香蕉梨’的歌谣，跳错就换人。",
    "滚铁环": "用一根铁钩推着铁环往前跑，看谁滚得稳、滚得远不倒。",
    "抖空竹": "两根小竹竿系一根线，抖动空竹让它嗡嗡转起来，能抛能接、玩出花样。",
    "丢沙包": "两头的人拿沙包砸中间躲闪的人，被砸中就下场，接住沙包能‘加一条命’。",
    "跳房子": "地上用粉笔画一排格子，单脚跳着把瓦片踢进格里，踩线就算输。",
    "老鹰捉小鸡": "一人当老鹰，一人当母鸡张开手护着身后一串‘小鸡’，老鹰专捉队尾那只。",
    "打陀螺": "用小鞭子一下下抽打陀螺，让它在地上飞快旋转，比谁的转得久。",
    "翻花绳": "一根线圈套在手指间，两人你翻我接，变出面条、五角星、降落伞各种花样。",
    "弹玻璃球": "蹲在地上用手指弹玻璃珠，弹中对方的珠子就把它赢过来。",
    "撞拐": "也叫斗鸡——单腿站立、双手抱起另一条腿，用膝盖互相撞，谁先倒下或松脚谁输。",
    "抓石子": "撒一把小石子，抛起一颗、趁空抓起几颗再接住，从一到五，考手快。",
    "跳大绳": "两人甩长绳，一群人轮流钻进去跳，‘马兰开花二十一’地数着跳。",
}

_ALIAS = {"踢键子": "踢毽子", "斗鸡": "撞拐", "抓子儿": "抓石子", "甩大绳": "跳大绳",
          "跳长绳": "跳大绳", "弹珠": "弹玻璃球", "玻璃珠": "弹玻璃球"}


def _table(config) -> dict:
    db = dict(_GAMES)
    if isinstance(config, dict) and isinstance(config.get("folk_games"), dict):
        for k, v in config["folk_games"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def games(config=None) -> list:
    return list(_table(config))


def find_game(query, config=None) -> str:
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


def how_to(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_game(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_folk_game_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("老游戏", "小时候的游戏", "民俗游戏", "传统游戏", "以前玩的游戏")):
        return True
    if find_game(u, config) and any(k in u for k in ("怎么玩", "咋玩", "玩法", "怎么弄",
                                                     "教我玩", "讲讲", "是什么")):
        return True
    return False
