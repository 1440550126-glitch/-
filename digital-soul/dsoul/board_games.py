"""棋牌规则：象棋怎么走、围棋怎么下、五子棋跳棋军棋怎么玩——给晚辈讲讲，陪长辈摆一盘。
棋盘上的功夫是几代人的传家乐。这一块把各种棋的基本规矩讲清楚，照着就能开局。
纯数据 + 纯逻辑、可单测。可在 config 的 board_games 里补自家爱玩的棋。
"""

from __future__ import annotations

# 棋名 -> (基本规则, 一句口诀/提醒)
_GAMES = {
    "中国象棋": (
        "棋盘有楚河汉界、九宫。红黑各 16 子。走法：车走直线远近不限；马走「日」字、蹩脚有子挡就走不了；"
        "炮走直线，吃子时中间必须隔一个子（架炮）；相/象走「田」字、不能过河；士/仕走斜线、只在九宫里；"
        "将/帅走一格、不出九宫（且将帅不能照面）；兵/卒过河前只能往前，过河后能左右走、但不后退。"
        "目标：把对方的将/帅「将死」（无处可逃）。",
        "马走日、象走田，炮隔山、车一线，小卒一去不回还。"),
    "围棋": (
        "棋盘 19 路（交叉点上落子），黑先白后，轮流下。棋子周围空着的交叉点叫「气」，"
        "被对方围得一口气都没有就被「提」掉。下棋就是圈地：终局时谁占的地盘（空 + 子）多谁赢。"
        "规矩里有「禁着点」（自己送死不能下）和「打劫」（不能立即提回成循环）。",
        "新手先学小棋盘（9 路）找感觉，记住「金角银边草肚皮」。"),
    "五子棋": (
        "在棋盘交叉点上，黑白轮流落子，先把自己的五个子连成一条线（横、竖、或斜）的就赢。"
        "落子不能移动、不能吃子，就比谁先连成五。",
        "盯着对方四连要赶紧堵；自己做「双活三」就难防了。"),
    "跳棋": (
        "六角星棋盘，每人十枚子放一个角。轮流走：要么挪到相邻空格，要么跳过紧挨着的棋子（自己的或对方的都行）、"
        "落到它正后方的空格，能连跳就连跳。谁先把十枚子全部跳到正对面的角里，谁赢。",
        "提前架好「跳板」连跳，一步顶好几步。"),
    "军棋": (
        "棋子按官阶大小：司令 > 军长 > 师长 > 旅长 > 团长 > 营长 > 连长 > 排长 > 工兵；还有炸弹、地雷、军旗。"
        "碰面时大吃小、一样大同归于尽；工兵能挖地雷，炸弹和谁碰都同归于尽，地雷不能动。"
        "扛走对方军旗、或让对方无棋可走就赢。翻棋玩法是棋子盖着、翻开碰运气。",
        "工兵别浪费，留着挖雷；炸弹专炸司令。"),
}

_ALIAS = {
    "中国象棋": "中国象棋", "象棋": "中国象棋", "下象棋": "中国象棋",
    "围棋": "围棋", "下围棋": "围棋", "黑白子": "围棋",
    "五子棋": "五子棋", "连五子": "五子棋", "五目": "五子棋",
    "跳棋": "跳棋", "跳跳棋": "跳棋",
    "军棋": "军棋", "陆战棋": "军棋", "翻棋": "军棋",
}


def _all(config=None) -> dict:
    d = dict(_GAMES)
    cfg = (config or {}).get("board_games") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        for name, v in cfg.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("rules"):
                d[str(name)] = (str(v["rules"]), str(v.get("tip", "")))
            elif isinstance(v, str):
                d[str(name)] = (v, "")
    return d


def games(config=None) -> list:
    return list(_all(config).keys())


def find_game(utterance, config=None):
    """听出问的哪种棋（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for g in _all(config):
        if g in u:
            return g
    return None


def how_to(game, config=None) -> str:
    """某种棋怎么下（规则 + 口诀）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(game or ""), str(game or ""))
    if key not in d:
        return ""
    rules, tip = d[key]
    return f"{key}怎么下：{rules}" + (f"（口诀：{tip}）" if tip else "")


def is_board_game_query(utterance, config=None) -> bool:
    """是不是在问下棋规则（认出棋名 + 怎么下/规则/教 的意图）。"""
    u = str(utterance or "")
    g = find_game(u, config)
    if not g:
        return False
    return any(k in u for k in ("怎么下", "怎么玩", "规则", "走法", "教教", "教我", "咋下",
                                "咋玩", "怎么走", "不会下", "下法"))


def count(config=None) -> int:
    return len(_all(config))
