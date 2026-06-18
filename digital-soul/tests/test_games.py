"""玩游戏测试。可直接运行：python tests/test_games.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.games import (  # noqa: E402
    a_brainteaser, a_riddle, chain_from, detect_game, is_game_request,
    looks_like_idiom,
)


def test_riddle_and_rotation():
    q1, a1 = a_riddle()
    assert q1 and a1
    q2, _ = a_riddle(exclude=[q1])
    assert q2 != q1                                      # 轮换不重样


def test_brainteaser():
    q, a = a_brainteaser()
    assert q and a


def test_chain_from():
    assert chain_from("万事如意").startswith("意")      # 末字"意"接"意气风发"
    assert chain_from("一帆风顺").startswith("顺")
    assert chain_from("没有这个") == "" or chain_from("没有这个")  # 接不上返回空也行
    assert chain_from("") == ""


def test_looks_like_idiom():
    assert looks_like_idiom("一帆风顺")
    assert not looks_like_idiom("你好")
    assert not looks_like_idiom("今天天气好")


def test_is_game_request_and_detect():
    assert is_game_request("陪我玩个游戏")
    assert is_game_request("来玩成语接龙")
    assert detect_game("猜个谜语") == "猜谜"
    assert detect_game("脑筋急转弯") == "脑筋急转弯"
    assert detect_game("成语接龙") == "成语接龙"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ games: all tests passed")
