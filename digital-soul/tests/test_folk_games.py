"""老游戏测试。可直接运行：python tests/test_folk_games.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.folk_games import find_game, games, how_to, is_folk_game_query  # noqa: E402


def test_games_cover():
    gs = games()
    for g in ("踢毽子", "跳皮筋", "滚铁环", "抖空竹"):
        assert g in gs


def test_how_to():
    assert "毽子" in how_to("踢毽子")
    assert "橡皮筋" in how_to("跳皮筋") or "歌谣" in how_to("跳皮筋")
    assert how_to("打电子游戏") == ""


def test_find_alias_longest():
    assert find_game("斗鸡怎么玩") == "撞拐"            # 别名
    assert find_game("弹珠玩法") == "弹玻璃球"
    assert find_game("今天天气") == ""


def test_how_to_from_sentence():
    assert "陀螺" in how_to("打陀螺怎么玩")


def test_is_folk_game_query():
    assert is_folk_game_query("踢毽子怎么玩")
    assert is_folk_game_query("讲讲小时候的游戏")
    assert is_folk_game_query("滚铁环玩法")
    assert not is_folk_game_query("今天几号")
    assert not is_folk_game_query("我会踢毽子")          # 没问玩法


def test_config_add():
    cfg = {"folk_games": {"丢手绢": "围坐一圈，悄悄把手绢丢在某人身后。"}}
    assert "丢手绢" in games(cfg)
    assert how_to("丢手绢怎么玩", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ folk_games: all tests passed")
