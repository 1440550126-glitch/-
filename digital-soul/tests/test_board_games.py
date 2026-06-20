"""棋牌规则测试。可直接运行：python tests/test_board_games.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.board_games import (  # noqa: E402
    count, find_game, games, how_to, is_board_game_query,
)


def test_games_present():
    gs = games()
    for k in ("中国象棋", "围棋", "五子棋", "跳棋", "军棋"):
        assert k in gs
    assert count() == 5


def test_find_game_alias():
    assert find_game("象棋怎么走") == "中国象棋"
    assert find_game("陆战棋咋玩") == "军棋"
    assert find_game("连五子怎么赢") == "五子棋"
    assert find_game("今天天气好") is None


def test_how_to_has_rules_and_tip():
    s = how_to("中国象棋")
    assert "马走" in s and "九宫" in s and "口诀" in s
    assert "气" in how_to("围棋")
    assert how_to("不存在") == ""


def test_how_to_via_alias():
    assert how_to("象棋").startswith("中国象棋怎么下")


def test_is_query_gating():
    assert is_board_game_query("象棋怎么走")
    assert is_board_game_query("围棋规则是啥")
    assert is_board_game_query("教我下跳棋")
    assert not is_board_game_query("今天天气好")
    assert not is_board_game_query("下盘棋吧")              # 邀约玩，不是问规则 → 留给 games/boredom
    assert not is_board_game_query("象棋")                  # 光提名字、没问怎么下


def test_config_extra_game():
    cfg = {"board_games": {"斗兽棋": ["象>狮>虎...鼠能吃象，把子走进对方兽穴就赢", "鼠克象是精髓"]}}
    assert "斗兽棋" in games(cfg)
    assert how_to("斗兽棋", cfg).startswith("斗兽棋怎么下")
    assert find_game("斗兽棋怎么玩", cfg) == "斗兽棋"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ board_games: all tests passed")
